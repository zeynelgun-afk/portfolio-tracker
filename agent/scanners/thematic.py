#!/usr/bin/env python3
"""
Finzora AI — Thematic Discovery (Aşama 4)
==========================================

AI türeyen aktif tema tespiti. Günlük dar + haftalık geniş mod.

Akış:
1. Veri topla: sektör SPDR + sub-sector ETF + haber akışı + portföy
   ve watchlist hisseleri için haberler
2. OpenRouter Kimi'ye gönder, JSON çıktı al (5-8 aktif tema + skorlar +
   lifecycle + related_tickers + evidence)
3. agent.themes.add_theme ile katalog güncelle
4. Aktif temaların ticker'ları → agent.watchlist.add ile havuza ekle
5. Sönüşte temaların portföy hisseleri tespit edilirse DM uyarı

Tetikleyici (Railway scheduler):
    --mode daily   — Her hafta içi 23:00 TR civarı (gün sonu)
    --mode weekly  — Her Pazar 11:00 TR (haftalık geniş araştırma)

CLI:
    python scripts/thematic_discovery.py --mode daily --dry-run
    python scripts/thematic_discovery.py --mode weekly --dm
    python scripts/thematic_discovery.py --mode daily --telegram

14 May 2026 — Aşama 4b (tema tespit MVP).
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import requests

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from agent.fmp import fmp_get
from agent.themes import (
    add_theme, all_themes, get_dying_themes,
    get_portfolio_theme_map, archive_theme,
)
from agent.watchlist import add as watchlist_add

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "moonshotai/kimi-k2"

# Sektör ve sub-sector ETF'leri
SECTOR_ETFS = {
    "XLK": "Technology",
    "XLF": "Financials",
    "XLE": "Energy",
    "XLV": "Healthcare",
    "XLY": "Consumer Cyclical",
    "XLP": "Consumer Defensive",
    "XLI": "Industrials",
    "XLB": "Basic Materials",
    "XLU": "Utilities",
    "XLRE": "Real Estate",
    "XLC": "Communications",
}

# Sub-sector ETF'leri — daha spesifik tema kanıtları için
SUB_SECTOR_ETFS = {
    "SMH": "Semiconductors",
    "SOXX": "Semiconductors (alt)",
    "ARKK": "Innovation",
    "ICLN": "Clean Energy",
    "XBI": "Biotech",
    "KWEB": "China Internet",
    "JETS": "Airlines",
    "ITA": "Defense",
    "GDX": "Gold Miners",
    "URA": "Uranium",
    "TAN": "Solar",
    "FCG": "Natural Gas",
}


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [thematic] {msg}")


# ────────────────────────── 1. Veri Toplama ──────────────────────────


def fetch_etf_performance(etf_dict: dict) -> dict:
    """ETF'ler için 1g/5g/1ay/3ay performans çek."""
    results = {}
    for sym, name in etf_dict.items():
        try:
            quote = fmp_get("quote", {"symbol": sym})
            if not quote or not isinstance(quote, list):
                continue
            q = quote[0]
            current = q.get("price")
            day_chg = q.get("changePercentage", 0)

            # Tarihsel: 65 bar (3 ay)
            bars = fmp_get("historical-price-eod/light", {"symbol": sym, "limit": 65})
            week_chg = month_chg = quarter_chg = None
            if bars and len(bars) >= 5:
                p5 = bars[4].get("price") or bars[4].get("close")
                if p5 and current:
                    week_chg = (current - p5) / p5 * 100
            if bars and len(bars) >= 21:
                p21 = bars[20].get("price") or bars[20].get("close")
                if p21 and current:
                    month_chg = (current - p21) / p21 * 100
            if bars and len(bars) >= 63:
                p63 = bars[62].get("price") or bars[62].get("close")
                if p63 and current:
                    quarter_chg = (current - p63) / p63 * 100

            results[sym] = {
                "name": name,
                "price": current,
                "day_pct": round(day_chg, 2) if day_chg else 0,
                "week_pct": round(week_chg, 2) if week_chg is not None else None,
                "month_pct": round(month_chg, 2) if month_chg is not None else None,
                "quarter_pct": round(quarter_chg, 2) if quarter_chg is not None else None,
            }
        except Exception as e:
            log(f"  {sym} hata: {e}")
            continue
    return results


def fetch_news_headlines(mode: str = "daily") -> list[dict]:
    """Son haberlerden başlıklar çek. daily=24h, weekly=7d."""
    limit = 30 if mode == "daily" else 80
    try:
        news = fmp_get("news/general-latest", {"limit": limit})
        if not news or not isinstance(news, list):
            return []
        return [
            {
                "title": n.get("title", "")[:200],
                "site": n.get("site", ""),
                "date": n.get("publishedDate", "")[:16],
                "text": (n.get("text", "") or "")[:300],
            }
            for n in news
        ]
    except Exception as e:
        log(f"  news fetch hata: {e}")
        return []


def fetch_portfolio_news() -> dict:
    """Portföy hisseleri için son haberler (her hisse ~3 haber)."""
    portfolio_path = REPO_ROOT / "data" / "portfolio.json"
    if not portfolio_path.exists():
        return {}
    try:
        d = json.loads(portfolio_path.read_text(encoding="utf-8"))
        symbols = [p.get("symbol", "").upper() for p in d.get("positions", [])]
        symbols = [s for s in symbols if s]
    except Exception:
        return {}

    if not symbols:
        return {}

    # FMP /stock-news endpoint — bir kerede 5 symbol max güvenli
    result = {}
    for i in range(0, len(symbols), 5):
        batch = symbols[i:i+5]
        try:
            news = fmp_get("news/stock-latest", {
                "symbols": ",".join(batch),
                "limit": 15,
            })
            if news and isinstance(news, list):
                for n in news:
                    sym = (n.get("symbol") or "").upper()
                    if sym in batch:
                        result.setdefault(sym, []).append({
                            "title": (n.get("title") or "")[:150],
                            "date": (n.get("publishedDate") or "")[:10],
                        })
            time.sleep(0.1)
        except Exception:
            continue

    # Her hisse için en fazla 3 haber
    return {s: news[:3] for s, news in result.items()}


# ────────────────────────── 2. LLM Çağrısı ──────────────────────────


def build_llm_prompt(
    sector_data: dict,
    sub_sector_data: dict,
    news_headlines: list[dict],
    portfolio_news: dict,
    existing_themes: dict,
    mode: str,
) -> str:
    """LLM'e gidecek prompt'u oluştur."""
    # Sektör performansı tablo
    sector_lines = ["SEKTÖR PERFORMANSI (SPDR ETF'leri):"]
    for sym, d in sorted(sector_data.items(),
                          key=lambda kv: -(kv[1].get("month_pct") or -100)):
        sector_lines.append(
            f"  {sym} ({d['name']:18}): "
            f"1g {d.get('day_pct',0):+.2f}%, "
            f"5g {d.get('week_pct',0) or 0:+.2f}%, "
            f"1ay {d.get('month_pct',0) or 0:+.2f}%, "
            f"3ay {d.get('quarter_pct',0) or 0:+.2f}%"
        )

    # Sub-sector
    sub_lines = ["", "ALT SEKTÖR ETF'leri:"]
    for sym, d in sorted(sub_sector_data.items(),
                          key=lambda kv: -(kv[1].get("month_pct") or -100)):
        sub_lines.append(
            f"  {sym} ({d['name']:25}): "
            f"5g {d.get('week_pct',0) or 0:+.2f}%, "
            f"1ay {d.get('month_pct',0) or 0:+.2f}%, "
            f"3ay {d.get('quarter_pct',0) or 0:+.2f}%"
        )

    # Haber özetleri (kompakt)
    news_lines = ["", f"GENEL HABER AKIŞI (son {'24 saat' if mode=='daily' else '7 gün'}):"]
    for i, n in enumerate(news_headlines[:30], 1):
        news_lines.append(f"  {i}. [{n['date']}] {n['site']}: {n['title']}")

    # Portföy haberleri
    pf_lines = ["", "PORTFÖY HİSSELERİ - SON HABERLER:"]
    for sym, items in sorted(portfolio_news.items()):
        if items:
            pf_lines.append(f"  {sym}:")
            for it in items[:2]:
                pf_lines.append(f"    [{it['date']}] {it['title']}")

    # Mevcut temalar (LLM bunları update edebilir)
    existing_lines = ["", "MEVCUT TEMA KATALOĞU (güncellenebilir):"]
    if existing_themes:
        for tid, t in existing_themes.items():
            existing_lines.append(
                f"  {tid}: {t.get('name')} (stage={t.get('lifecycle_stage')}, "
                f"score={t.get('momentum_score')}, "
                f"tickers={t.get('related_tickers',[])[:8]})"
            )
    else:
        existing_lines.append("  (boş — sıfırdan başla)")

    instructions = f"""
GÖREV:
Yukarıdaki sektör performansları, alt sektör ETF'leri ve haber akışı üzerinden,
şu an piyasada aktif olan 5-8 yatırım temasını tespit et. Her tema için bir
JSON nesne döndür.

Tema yaşam döngüsü aşamaları:
  - "dogus"    : Tema yeni doğuyor, az haber ama momentum başladı, az ticker
  - "yukselis" : Tema yükselişte, haber akışı artıyor, sektör RS olumlu
  - "olgun"    : Tema yerleşmiş, geniş ticker tabanı, sürdürülebilir momentum
  - "sönüs"    : Tema bitiyor, haber azalıyor, RS negatife dönüyor

Momentum score 0-100:
  - 80+ : Güçlü, açık ara lider tema
  - 60-79 : Aktif, takip değerli
  - 40-59 : Olgun ama doygun
  - 20-39 : Zayıflıyor
  - <20   : Bitmiş

Eğer mevcut katalogda olan bir tema HALA AKTİFse, aynı id'yi kullan ve update yap.
Tema bittiyse "sönüs" stage'ine al.

ÇIKTI FORMATI (KESİNLİKLE JSON, başka metin yazma):
{{
  "themes": [
    {{
      "id": "tema_id_snake_case",
      "name": "Görünür Tema Adı",
      "description": "1-2 cümle açıklama",
      "lifecycle_stage": "dogus|yukselis|olgun|sönüs",
      "momentum_score": 75,
      "related_tickers": ["NVDA", "AMAT", ...],
      "evidence": [
        "Haber/veri özeti 1",
        "Haber/veri özeti 2"
      ],
      "signals": {{
        "sector_rs_4w_pct": 12.5,
        "news_velocity_7d": 47
      }}
    }}
  ]
}}

ÖNEMLİ:
- Türkçe karakter id'de YASAK (snake_case ASCII)
- related_tickers ABD borsasında listed olmalı (NYSE/NASDAQ)
- Her tema için 5-15 ticker
- Sadece JSON döndür, ek metin yazma
- {'GÜNLÜK MODE - dar tarama' if mode=='daily' else 'HAFTALIK MODE - geniş araştırma'}
"""

    return "\n".join(sector_lines + sub_lines + news_lines + pf_lines + existing_lines) + "\n" + instructions


def call_llm(prompt: str, max_tokens: int = 4000) -> Optional[dict]:
    """OpenRouter Kimi'yi çağır, JSON parse et."""
    if not OPENROUTER_API_KEY:
        log("OPENROUTER_API_KEY ortam değişkeni yok — LLM çağrısı atlanıyor.")
        return None
    try:
        resp = requests.post(
            OPENROUTER_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": LLM_MODEL,
                "messages": [
                    {"role": "system", "content": "Sen ABD piyasası tematik yatırım analistisin. Sadece JSON döndür."},
                    {"role": "user", "content": prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
            timeout=120,
        )
        if resp.status_code != 200:
            log(f"  LLM HTTP {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        log(f"  LLM tokens: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}")

        # JSON parse — bazen markdown ```json``` ile sarılı gelir
        content = content.strip()
        if content.startswith("```"):
            # ```json...```  veya ```...```
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            content = content.strip()
        if content.startswith("```"):
            content = content[3:].strip()

        return json.loads(content)
    except json.JSONDecodeError as e:
        log(f"  LLM JSON parse hata: {e}")
        log(f"  Response head: {content[:300] if 'content' in dir() else ''}")
        return None
    except Exception as e:
        log(f"  LLM çağrı hata: {e}")
        return None


# ────────────────────────── 3. Apply ──────────────────────────


def apply_themes(themes_payload: dict, mode: str) -> dict:
    """LLM'in döndürdüğü temaları katalog ve watchlist'e işle."""
    if not themes_payload or "themes" not in themes_payload:
        return {"added": 0, "updated": 0, "watchlist_added": 0}

    # ETF'leri filtrele — watchlist bireysel hisseler için
    known_etfs = set(SECTOR_ETFS.keys()) | set(SUB_SECTOR_ETFS.keys())
    # Yaygın diğer ETF'ler (sıkça LLM çıkarıyor)
    other_etfs = {"KRE", "GDXJ", "QQQ", "SPY", "DIA", "IWM", "VTI",
                  "IBB", "BBH", "PHO", "BOTZ", "ROBO", "ARKQ", "ARKW",
                  "VNQ", "SCHH", "REM"}
    known_etfs |= other_etfs

    added_themes = 0
    updated_themes = 0
    watchlist_added = 0

    # Faz 2 Adım 10b-iii-C-ii (17 May 2026): Polymarket kalibratör hook.
    # Tematik'te AI Gate yok — kalibrasyon bilgisi watchlist score_components'a
    # metadata olarak kaydedilir. Phase 10 analizinde performans takibi için.
    # Feature flag CALIBRATOR_ENABLED kapalı default → mevcut davranış.
    calibrator = None
    try:
        from agent.scanners.pipeline import is_calibrator_enabled
        if is_calibrator_enabled():
            from agent.scanners.calibrator import PolymarketCalibrator
            calibrator = PolymarketCalibrator()
            log(f"Polymarket kalibratör AKTİF (CALIBRATOR_ENABLED=true)")
    except Exception as e:
        log(f"Kalibratör başlatma hatası, devam ediliyor: {e}")
        calibrator = None

    for t in themes_payload.get("themes", []):
        # related_tickers içinden ETF'leri ayır (tema'da kalsın ama watchlist'e gitmesin)
        all_tickers = t.get("related_tickers", [])
        stock_tickers = [s for s in all_tickers if s.upper() not in known_etfs]

        result = add_theme(
            theme_id=t.get("id"),
            name=t.get("name", ""),
            description=t.get("description", ""),
            related_tickers=all_tickers,  # ETF dahil hepsi kataloğa
            lifecycle_stage=t.get("lifecycle_stage", "yukselis"),
            momentum_score=t.get("momentum_score", 50),
            signals=t.get("signals", {}),
            evidence=[
                {"date": datetime.now().strftime("%Y-%m-%d"), "text": e}
                for e in t.get("evidence", [])
            ],
            source=f"ai_thematic_discovery_{mode}",
        )

        if result["action"] == "added":
            added_themes += 1
        elif result["action"] == "updated":
            updated_themes += 1

        # Sadece aktif temalar (sönüş hariç) watchlist'i besler
        # ve sadece bireysel hisseler (ETF'siz)
        stage = t.get("lifecycle_stage", "yukselis")
        if stage in ("dogus", "yukselis", "olgun"):
            theme_id = t.get("id") or t.get("name", "").lower().replace(" ", "_")
            for ticker in stock_tickers:
                try:
                    # Faz 2 Adım 10b-iii-C-ii: ticker bazlı Polymarket kalibrasyon probe
                    calibration_info = None
                    if calibrator is not None:
                        try:
                            from agent.scanners.base import Candidate
                            probe = Candidate(
                                symbol=ticker,
                                score=0.5,  # probe — gerçek skor LLM momentum_score
                                reason="thematic probe",
                                source="thematic",
                            )
                            calibrator.calibrate([probe])
                            if probe.has_calibration:
                                calibration_info = {
                                    "flags": probe.calibration_flags,
                                    "multiplier": probe.calibration_multiplier,
                                }
                        except Exception as e:
                            log(f"  {ticker} kalibrasyon hatası: {e}")

                    score_components_dict = {
                        "thematic_momentum": t.get("momentum_score"),
                        "thematic_id": theme_id,
                        "thematic_stage": stage,
                    }
                    if calibration_info is not None:
                        score_components_dict["polymarket_calibration"] = calibration_info

                    wl_result = watchlist_add(
                        symbol=ticker,
                        source=f"tematik_{theme_id}",
                        rationale=f"Tema: {t.get('name')} ({stage}, score {t.get('momentum_score',50)})",
                        tags=[theme_id, stage],
                        score_components=score_components_dict,
                    )
                    if wl_result["action"] == "added":
                        watchlist_added += 1
                except Exception as e:
                    log(f"  watchlist {ticker} hata: {e}")

    return {
        "added": added_themes,
        "updated": updated_themes,
        "watchlist_added": watchlist_added,
    }


# ────────────────────────── 4. Sönüş Uyarısı ──────────────────────────


def check_dying_themes_portfolio_impact() -> list[dict]:
    """
    Sönüşteki temaların portföydeki hisselerini tespit et.
    Trail stop sıkılaştırma önerisi için DM uyarısı kaynağı.
    """
    dying = get_dying_themes()
    if not dying:
        return []

    portfolio_map = get_portfolio_theme_map()
    impacts = []
    for sym, theme_ids in portfolio_map.items():
        affecting = [tid for tid in theme_ids if tid in dying]
        if affecting:
            impacts.append({
                "symbol": sym,
                "dying_themes": affecting,
                "theme_details": [
                    {"id": tid, "name": dying[tid].get("name"),
                     "score": dying[tid].get("momentum_score")}
                    for tid in affecting
                ],
            })
    return impacts


# ────────────────────────── 5. Rapor ──────────────────────────


def build_summary_report(
    mode: str,
    apply_stats: dict,
    dying_impacts: list[dict],
    final_themes: dict,
) -> str:
    """DM'ye gidecek özet raporu."""
    lines = [f"🎯 <b>Tematik Keşif — {mode.upper()}</b>",
             f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>", ""]

    # Aktif temalar (sıralı)
    active = [(tid, t) for tid, t in final_themes.items()
              if t.get("lifecycle_stage") in ("dogus", "yukselis", "olgun")]
    active.sort(key=lambda kv: -kv[1].get("momentum_score", 0))

    lines.append(f"<b>Aktif temalar ({len(active)}):</b>")
    stage_emoji = {"dogus": "🌱", "yukselis": "📈", "olgun": "🟢", "sönüs": "🔴"}
    for tid, t in active[:8]:
        emoji = stage_emoji.get(t.get("lifecycle_stage"), "•")
        score = t.get("momentum_score", 0)
        name = t.get("name", tid)
        n_tickers = len(t.get("related_tickers", []))
        lines.append(f"  {emoji} <b>{name}</b> — skor {score:.0f}, {n_tickers} ticker")

    # Sönüşteki temalar
    dying = [(tid, t) for tid, t in final_themes.items()
             if t.get("lifecycle_stage") == "sönüs"]
    if dying:
        lines.append("")
        lines.append(f"<b>Sönüşte temalar ({len(dying)}):</b>")
        for tid, t in dying:
            lines.append(f"  🔴 {t.get('name')} — skor {t.get('momentum_score',0):.0f}")

    # Portföy etkisi (sönüş)
    if dying_impacts:
        lines.append("")
        lines.append("⚠️ <b>Portföy etkisi — kâr koruma uyarısı:</b>")
        for imp in dying_impacts:
            tnames = ", ".join(td["name"] for td in imp["theme_details"])
            lines.append(f"  • <b>{imp['symbol']}</b>: {tnames} sönüşte → trail stop sıkılaştır")

    # İstatistik
    lines.append("")
    lines.append(
        f"<b>Bu run:</b> +{apply_stats['added']} yeni tema, "
        f"{apply_stats['updated']} güncellendi, "
        f"+{apply_stats['watchlist_added']} hisse watchlist'e."
    )
    lines.append("")
    lines.append("<i>finzora ai — tematik keşif</i>")
    return "\n".join(lines)


# ────────────────────────── 6. Scanner Adaptörü (Faz 2) ──────────────────────────


def _build_candidates_from_llm_payload(payload: dict, mode: str) -> list:
    """LLM çıktısından Candidate listesi üret. Yan etki yok — pure transform.

    Mevcut apply_themes() içindeki watchlist ekleme mantığının saf hali:
    yan etki yapmadan aday üretir. apply_themes() yan etki ile devam eder
    (themes catalog yazımı, watchlist.json yazımı).

    Faz 2 — Adım 5 (17 May 2026).
    """
    # Lazy import — base modülü ancak bu scanner kullanıldığında yüklenir
    from agent.scanners.base import Candidate

    candidates: list = []
    if not payload or not isinstance(payload, dict):
        return candidates

    # ETF filtresi (apply_themes ile aynı liste)
    known_etfs = set(SECTOR_ETFS.keys()) | set(SUB_SECTOR_ETFS.keys())
    known_etfs |= {
        "KRE", "GDXJ", "QQQ", "SPY", "DIA", "IWM", "VTI",
        "IBB", "BBH", "PHO", "BOTZ", "ROBO", "ARKQ", "ARKW",
        "VNQ", "SCHH", "REM",
    }

    for t in payload.get("themes", []):
        if not isinstance(t, dict):
            continue

        stage = t.get("lifecycle_stage", "yukselis")
        # Sönüşteki temalar Candidate üretmez (apply_themes ile aynı kural)
        if stage not in ("dogus", "yukselis", "olgun"):
            continue

        theme_name = t.get("name", "")
        theme_id = t.get("id") or theme_name.lower().replace(" ", "_")
        momentum = t.get("momentum_score", 50)

        # Skor normalize: 0-100 → 0.0-1.0
        try:
            score = max(0.0, min(1.0, float(momentum) / 100.0))
        except (TypeError, ValueError):
            score = 0.5

        for ticker in t.get("related_tickers", []) or []:
            if not isinstance(ticker, str) or not ticker.strip():
                continue
            sym = ticker.strip().upper()
            if sym in known_etfs:
                continue  # ETF'ler Candidate olmaz, sadece kataloğa girer

            reason = (
                f"Tema: {theme_name} ({stage}, momentum {momentum}). "
                f"Mod: {mode}."
            )
            try:
                candidates.append(Candidate(
                    symbol=sym,
                    score=score,
                    reason=reason,
                    source="thematic",
                    metadata={
                        "theme_id": theme_id,
                        "theme_name": theme_name,
                        "lifecycle_stage": stage,
                        "momentum_score": momentum,
                        "mode": mode,
                    },
                ))
            except ValueError as e:
                # Geçersiz Candidate (örn. boş ticker) — log + atla
                log(f"  Candidate üretim hatası ({sym}): {e}")

    return candidates


class ThematicDiscoveryScanner:
    """BaseScanner adaptörü — Faz 2 Adım 5 (17 May 2026).

    Mevcut script mantığını (fetch_etf_performance, fetch_news_headlines,
    call_llm) yeniden kullanır. scan() yan etki yapmaz — sadece Candidate
    listesi döndürür. Yan etkiler (watchlist eklemesi, themes catalog
    yazımı) CLI main() içinde apply_themes() üzerinden devam eder.

    Tasarım: docs/PHASE2_SCANNER_CONSOLIDATION.md (Bölüm 5)
    """

    name = "thematic"

    def __init__(self, mode: str = "daily"):
        if mode not in ("daily", "weekly"):
            raise ValueError(f"mode 'daily' veya 'weekly' olmalı, alındı: {mode!r}")
        self.mode = mode

    def scan(self) -> list:
        """Veri topla → LLM çağır → Candidate listesi üret.

        Returns:
            list[Candidate]. Boş liste hata değil — LLM tema dönmedi anlamına gelir.

        Raises:
            RuntimeError: OPENROUTER_API_KEY yok veya LLM yanıtı alınamadı.
        """
        if not OPENROUTER_API_KEY:
            raise RuntimeError("OPENROUTER_API_KEY yok — scanner çalışamaz")

        # 1. Veri topla
        sector_data = fetch_etf_performance(SECTOR_ETFS)
        sub_data = fetch_etf_performance(SUB_SECTOR_ETFS)
        news = fetch_news_headlines(mode=self.mode)
        pf_news = fetch_portfolio_news()

        # 2. LLM çağır
        # all_themes lazy import — mevcut tema kataloğunu LLM bağlamına dahil etmek için
        try:
            from themes import all_themes  # type: ignore
            existing = all_themes()
        except Exception:
            existing = {}

        prompt = build_llm_prompt(sector_data, sub_data, news, pf_news, existing, self.mode)
        max_tokens = 4000 if self.mode == "daily" else 6000
        payload = call_llm(prompt, max_tokens=max_tokens)

        if not payload:
            raise RuntimeError("LLM yanıtı alınamadı (call_llm None döndürdü)")

        # 3. Candidate listesi üret
        return _build_candidates_from_llm_payload(payload, self.mode)

    def health_check(self) -> dict:
        return {
            "name": self.name,
            "ok": bool(OPENROUTER_API_KEY),
            "mode": self.mode,
            "llm_model": LLM_MODEL,
        }


# ────────────────────────── 7. Main ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--dry-run", action="store_true",
                        help="Hiçbir şey yazma, sadece veri topla + LLM cevabı yazdır")
    parser.add_argument("--dm", action="store_true", help="DM'ye rapor gönder")
    parser.add_argument("--telegram", action="store_true",
                        help="Group + DM'ye normal yayın")
    args = parser.parse_args()

    log(f"Başlat: mode={args.mode}, dry_run={args.dry_run}")

    # 1. Veri topla
    log("Sektör SPDR verilerini çekiliyor...")
    sector_data = fetch_etf_performance(SECTOR_ETFS)
    log(f"  {len(sector_data)} sektör veri çekildi")

    log("Alt sektör ETF'leri çekiliyor...")
    sub_data = fetch_etf_performance(SUB_SECTOR_ETFS)
    log(f"  {len(sub_data)} alt sektör çekildi")

    log("Haber akışı çekiliyor...")
    news = fetch_news_headlines(mode=args.mode)
    log(f"  {len(news)} haber çekildi")

    log("Portföy hisseleri için haber çekiliyor...")
    pf_news = fetch_portfolio_news()
    log(f"  {len(pf_news)} hisse için haber çekildi")

    # 2. LLM prompt + çağrı
    existing = all_themes()
    prompt = build_llm_prompt(sector_data, sub_data, news, pf_news, existing, args.mode)
    log(f"Prompt hazır (~{len(prompt)} char). LLM çağrılıyor...")

    if args.dry_run:
        print("\n\n=== PROMPT ===")
        print(prompt)
        print("\n\n=== / PROMPT ===\n")

    max_tokens = 4000 if args.mode == "daily" else 6000
    payload = call_llm(prompt, max_tokens=max_tokens)

    if not payload:
        log("LLM yanıtı alınamadı. Çıkıyor.")
        return 1

    if args.dry_run:
        print("\n=== LLM RESPONSE ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("=== / RESPONSE ===\n")
        log(f"DRY RUN — {len(payload.get('themes', []))} tema tespit edildi, kayıt yapılmadı.")
        return 0

    # 3. Uygula
    log(f"LLM'den {len(payload.get('themes', []))} tema geldi, işleniyor...")
    apply_stats = apply_themes(payload, args.mode)
    log(f"  +{apply_stats['added']} yeni tema, "
        f"{apply_stats['updated']} güncellendi, "
        f"+{apply_stats['watchlist_added']} watchlist eklemesi")

    # 4. Sönüş kontrolü
    dying_impacts = check_dying_themes_portfolio_impact()
    if dying_impacts:
        log(f"Sönüş etkisi: {len(dying_impacts)} portföy hissesi etkileniyor")
        for imp in dying_impacts:
            log(f"  {imp['symbol']}: {imp['dying_themes']}")

    # 5. Rapor
    final = all_themes()
    report = build_summary_report(args.mode, apply_stats, dying_impacts, final)
    print("\n" + report.replace("<b>", "**").replace("</b>", "**")
                .replace("<i>", "_").replace("</i>", "_"))

    if args.telegram or args.dm:
        try:
            from agent.telegram import send_to_dm
            sent = send_to_dm(report)
            log(f"DM gönderildi: {sent}")
        except Exception as e:
            log(f"DM gönderim hatası: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
