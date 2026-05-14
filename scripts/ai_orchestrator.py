#!/usr/bin/env python3
"""
Finzora AI — AI Orchestrator (Aşama 5)
=======================================

Watchlist üzerinde "öncelikli alım adayları" seçici. Tüm besleyicilerden
gelen sinyalleri (analist_takip, fair_value, tematik) ve teknik verileri
LLM ile sentezler, sıralı bir rapor üretir.

Akış:
1. Watchlist'i yükle (max 80 ticker)
2. Her ticker için sinyaller topla:
   - score_components (analist/fair_value/thematic — watchlist.json)
   - Mevcut fiyat, change %, RSI(14), SMA21, SMA50 — FMP
   - Tema bağlantıları — themes.json
3. OpenRouter Kimi'ye yapılandırılmış JSON gönder, top 5-10 sırala
4. agent.watchlist.update_score ile skor güncelle
5. DM'ye "Öncelikli alım adayları" raporu

Tetikleyici (Railway scheduler):
    --mode daily   — Her hafta içi 02:00 TR (kapanış sonrası)
    --mode weekly  — Her Pazar 13:00 TR (haftalık derin analiz)

14 May 2026 — Aşama 5 (AI orchestrator).
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

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from agent.fmp import fmp_get
from agent.watchlist import load as load_watchlist, update_score
from agent.themes import all_themes, get_themes_for_ticker

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
LLM_MODEL = "moonshotai/kimi-k2"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] [orchestrator] {msg}")


# ────────────────────────── 1. Veri Toplama ──────────────────────────


def enrich_ticker(symbol: str, watchlist_entry: dict) -> Optional[dict]:
    """Bir ticker için tüm sinyalleri topla."""
    try:
        # Mevcut fiyat
        quote = fmp_get("quote", {"symbol": symbol})
        if not quote or not isinstance(quote, list):
            return None
        q = quote[0]
        price = q.get("price")
        if not price:
            return None
        change_pct = q.get("changePercentage", 0)
        market_cap_b = round(q.get("marketCap", 0) / 1e9, 1) if q.get("marketCap") else None

        # Teknik göstergeler
        rsi = None
        sma21 = None
        sma50 = None
        try:
            r = fmp_get("technical-indicators/rsi", {
                "symbol": symbol, "periodLength": 14, "timeframe": "1day"})
            if r and isinstance(r, list):
                rsi = round(r[0].get("rsi", 0), 1)
            s21 = fmp_get("technical-indicators/sma", {
                "symbol": symbol, "periodLength": 21, "timeframe": "1day"})
            if s21 and isinstance(s21, list):
                sma21 = round(s21[0].get("sma", 0), 2)
            s50 = fmp_get("technical-indicators/sma", {
                "symbol": symbol, "periodLength": 50, "timeframe": "1day"})
            if s50 and isinstance(s50, list):
                sma50 = round(s50[0].get("sma", 0), 2)
        except Exception:
            pass

        # Teknik sinyaller
        above_21 = sma21 and price > sma21
        above_50 = sma50 and price > sma50
        technical_setup = (
            "uptrend" if above_21 and above_50 else
            "test_21sma" if above_50 and not above_21 else
            "test_50sma" if not above_50 and above_21 else
            "below_50sma"
        )

        # Tema bağlantıları
        theme_ids = get_themes_for_ticker(symbol)

        # Watchlist score_components (zaten doldu)
        sc = watchlist_entry.get("score_components", {})

        return {
            "symbol": symbol,
            "price": price,
            "change_pct": round(change_pct, 2) if change_pct else 0,
            "market_cap_b": market_cap_b,
            "rsi": rsi,
            "sma21": sma21,
            "sma50": sma50,
            "technical_setup": technical_setup,
            "themes": theme_ids,
            "sources": watchlist_entry.get("sources", [watchlist_entry.get("source")]),
            "analist_takip": sc.get("analist_takip"),
            "fair_value_discount_pct": sc.get("fair_value_discount_pct"),
            "fair_value_target": sc.get("fair_value_target"),
            "thematic_momentum": sc.get("thematic_momentum"),
            "thematic_id": sc.get("thematic_id"),
            "thematic_stage": sc.get("thematic_stage"),
            "added_at": watchlist_entry.get("added_at", "")[:10],
            "rationale": watchlist_entry.get("rationale", "")[:120],
        }
    except Exception as e:
        log(f"  {symbol} enrich hata: {e}")
        return None


def enrich_all_watchlist() -> list[dict]:
    """Tüm watchlist'i sinyallerle birlikte zenginleştir."""
    wl = load_watchlist()
    tickers = wl.get("tickers", {})
    log(f"Watchlist: {len(tickers)} ticker zenginleştiriliyor...")

    enriched = []
    for i, (sym, entry) in enumerate(tickers.items(), 1):
        r = enrich_ticker(sym, entry)
        if r:
            enriched.append(r)
        if i % 10 == 0:
            log(f"  ...{i}/{len(tickers)} işlendi")
    log(f"  {len(enriched)} ticker zenginleştirildi (toplam {len(tickers)})")
    return enriched


# ────────────────────────── 2. LLM Çağrısı ──────────────────────────


def build_llm_prompt(
    enriched: list[dict],
    active_themes: dict,
    mode: str,
) -> str:
    """LLM'e gidecek prompt'u oluştur."""
    lines = []
    lines.append("FINZORA AI — ÖNCELİKLİ ALIM ADAYI SEÇİMİ")
    lines.append(f"Mode: {mode.upper()} | Tarih: {datetime.now().strftime('%Y-%m-%d')}")
    lines.append("")

    # Aktif temalar özet
    lines.append("AKTİF TEMALAR:")
    for tid, t in sorted(active_themes.items(),
                          key=lambda kv: -kv[1].get("momentum_score", 0)):
        stage = t.get("lifecycle_stage", "?")
        score = t.get("momentum_score", 0)
        lines.append(f"  [{stage:8}] {tid}: score {score}")
    lines.append("")

    # Her ticker için kompakt satır
    lines.append("WATCHLIST ADAYLARI (her satır bir hisse):")
    lines.append("  Format: SYM | $price ±chg% | RSI | tek.setup | tema | sinyaller")
    lines.append("")

    for e in enriched:
        # Sinyal özeti
        sigs = []
        if e["analist_takip"]:
            at = e["analist_takip"]
            if isinstance(at, dict):
                rc = at.get("raised_count")
                avg = at.get("avg_revision_pct")
                if rc and avg:
                    sigs.append(f"analist {rc}raise +{avg:.0f}%")
        if e["fair_value_discount_pct"]:
            sigs.append(f"FV +{e['fair_value_discount_pct']:.0f}%")
        if e["thematic_momentum"]:
            sigs.append(f"tema {e['thematic_id']} {e['thematic_stage']} score{e['thematic_momentum']:.0f}")
        sig_str = " | ".join(sigs) if sigs else "—"

        rsi_str = f"{e['rsi']}" if e["rsi"] is not None else "?"
        mcap_str = f"${e['market_cap_b']:.0f}B" if e["market_cap_b"] else "?"

        lines.append(
            f"  {e['symbol']:6} | ${e['price']:>8.2f} {e['change_pct']:+.2f}% | "
            f"RSI {rsi_str:>4} | {e['technical_setup']:11} | mcap {mcap_str:>6} | "
            f"{sig_str}"
        )

    lines.append("")

    instructions = f"""
GÖREV:
Yukarıdaki watchlist adaylarından öncelikli ALIM adaylarını seç. Sıralı bir
top-10 liste ver, her biri için gerekçe ve R/R hesabı yap.

KRİTERLER (önem sırası):
1. Çoklu sinyal birleşimi (analist + tema + FV iskonto)
2. Teknik momentum: 'uptrend' tercih, RSI 30-70 ideal (>75 aşırı alım, dikkat)
3. Tema yaşam döngüsü: 'olgun' veya 'yukselis' güçlü, 'dogus' fırsat
4. Likitide: market cap > $5B tercih (small cap atlanır)
5. FV iskonto >25% bonus

ÇIKTI FORMATI (KESİNLİKLE JSON, başka metin yazma):
{{
  "top_picks": [
    {{
      "rank": 1,
      "symbol": "NVDA",
      "score": 92,
      "reason": "1 cümle: niye bu hisse top pick",
      "entry_zone": "fiyat aralığı önerisi, örn $220-225",
      "stop_loss": 195,
      "target": 280,
      "risk_reward": "1:2.4",
      "primary_signals": ["analist 5raise", "tema AI olgun", "uptrend"],
      "warnings": "varsa risk veya dikkat noktası, yoksa null"
    }}
  ],
  "session_notes": "Bugünün genel piyasa havası, 1-2 cümle"
}}

ÖNEMLİ:
- top_picks'te 5-10 hisse olsun
- Score 0-100 (toplam çekicilik)
- Stop ve target hisseye özel mantıklı seviyeler
- Sadece JSON, başka metin yok
- {mode.upper()} mode: {'günlük dar tarama' if mode == 'daily' else 'haftalık derin analiz'}
"""
    return "\n".join(lines) + "\n" + instructions


def call_llm(prompt: str, max_tokens: int = 5000) -> Optional[dict]:
    """OpenRouter Kimi'yi çağır."""
    if not OPENROUTER_API_KEY:
        log("OPENROUTER_API_KEY ortam değişkeni yok — LLM atlanıyor.")
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
                "temperature": 0.2,
            },
            timeout=180,
        )
        if resp.status_code != 200:
            log(f"  LLM HTTP {resp.status_code}: {resp.text[:200]}")
            return None
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})
        log(f"  LLM tokens: in={usage.get('prompt_tokens')} out={usage.get('completion_tokens')}")

        # JSON parse
        content = content.strip()
        if content.startswith("```"):
            lines = content.split("\n")
            content = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
            content = content.strip()
        if content.startswith("```"):
            content = content[3:].strip()

        return json.loads(content, strict=False)
    except json.JSONDecodeError as e:
        log(f"  LLM JSON parse hata: {e}")
        log(f"  Response head (300 char): {content[:300]}")
        return None
    except Exception as e:
        log(f"  LLM çağrı hata: {e}")
        return None


# ────────────────────────── 3. Apply ──────────────────────────


def apply_orchestrator_output(payload: dict) -> dict:
    """LLM çıktısını watchlist score'lara yansıt."""
    if not payload or "top_picks" not in payload:
        return {"scored": 0}

    scored = 0
    for pick in payload["top_picks"]:
        sym = pick.get("symbol", "").upper()
        score = pick.get("score")
        if not sym or score is None:
            continue
        result = update_score(
            symbol=sym,
            score=float(score),
            components={
                "orchestrator_rank": pick.get("rank"),
                "orchestrator_reason": pick.get("reason"),
                "orchestrator_entry": pick.get("entry_zone"),
                "orchestrator_stop": pick.get("stop_loss"),
                "orchestrator_target": pick.get("target"),
                "orchestrator_rr": pick.get("risk_reward"),
            },
        )
        if result.get("action") == "scored":
            scored += 1
    return {"scored": scored}


# ────────────────────────── 4. Rapor ──────────────────────────


def build_report(payload: dict, mode: str) -> str:
    """DM'ye gidecek rapor."""
    lines = [
        f"🎯 <b>Öncelikli Alım Adayları — {mode.upper()}</b>",
        f"<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>",
        "",
    ]

    session_notes = payload.get("session_notes", "")
    if session_notes:
        lines.append(f"<i>{session_notes}</i>")
        lines.append("")

    top_picks = payload.get("top_picks", [])
    if not top_picks:
        lines.append("LLM herhangi bir aday önermedi.")
    else:
        for p in top_picks:
            rank = p.get("rank", "?")
            sym = p.get("symbol", "?")
            score = p.get("score", "?")
            reason = p.get("reason", "")
            entry = p.get("entry_zone", "?")
            stop = p.get("stop_loss", "?")
            target = p.get("target", "?")
            rr = p.get("risk_reward", "?")
            warnings = p.get("warnings")
            sigs = p.get("primary_signals", [])

            lines.append(f"<b>{rank}. {sym}</b> — skor {score}")
            lines.append(f"   {reason}")
            lines.append(f"   Giriş: {entry} | Stop: ${stop} | Target: ${target} | R/R: {rr}")
            if sigs:
                lines.append(f"   Sinyaller: {', '.join(sigs)}")
            if warnings:
                lines.append(f"   ⚠️ {warnings}")
            lines.append("")

    lines.append("<i>finzora ai — AI orchestrator (Aşama 5)</i>")
    return "\n".join(lines)


# ────────────────────────── 5. Main ──────────────────────────


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["daily", "weekly"], default="daily")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--dm", action="store_true")
    args = parser.parse_args()

    log(f"Başlat: mode={args.mode}, dry_run={args.dry_run}")

    # 1. Veri toplama
    enriched = enrich_all_watchlist()
    if not enriched:
        log("Watchlist boş veya enrich edilemedi. Çıkıyor.")
        return 1

    # Aktif temalar
    active = {tid: t for tid, t in all_themes().items()
              if t.get("lifecycle_stage") in ("dogus", "yukselis", "olgun")}

    # 2. LLM çağrısı
    prompt = build_llm_prompt(enriched, active, args.mode)
    log(f"Prompt hazır (~{len(prompt)} char). LLM çağrılıyor...")

    if args.dry_run:
        print("\n=== PROMPT (özet) ===")
        print(prompt[:3000])
        print("...\n")

    payload = call_llm(prompt, max_tokens=5000 if args.mode == "daily" else 6500)
    if not payload:
        log("LLM yanıt alamadı.")
        return 1

    if args.dry_run:
        print("\n=== LLM RESPONSE ===")
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        print("=== / ===\n")
        log("DRY RUN — kayıt yapılmadı.")
        return 0

    # 3. Apply
    apply_stats = apply_orchestrator_output(payload)
    log(f"  Score güncelleme: {apply_stats['scored']} ticker")

    # 4. Rapor
    report = build_report(payload, args.mode)
    print("\n" + report.replace("<b>", "**").replace("</b>", "**")
              .replace("<i>", "_").replace("</i>", "_"))

    if args.dm:
        try:
            from agent.telegram import send_to_dm
            sent = send_to_dm(report)
            log(f"DM gönderildi: {sent}")
        except Exception as e:
            log(f"DM gönderim hatası: {e}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
