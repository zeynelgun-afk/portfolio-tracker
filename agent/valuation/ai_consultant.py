"""
Finzora Valuation Framework v7 — Hybrid Plus (Kimi-led, framework as sanity check)
=====================================================================================
Mimari değişikliği (v6 → v7, Mayıs 2026):

v6 davranışı: framework karar verirdi, sadece "büyük gap / düşük güven" durumunda
              Kimi'ye danışılırdı (severity-tabanlı conditional consult).

v7 davranışı: Kimi BIRINCIL karar verici. Framework her zaman çalışır ama bir
              "sanity check" rolüne çekildi. Default blend ağırlığı tersine
              döndürüldü: framework 0.30, Kimi 0.70 (KIMI_VALUATION_BLEND env
              ile özelleştirilebilir).

v7 ek context: Kimi'ye sadece framework çıktısı değil, FMP'den çekilen 6 ek veri
               kategorisi de gönderilir — halüsinasyonu düşürmek için:
                 1. Forward analyst estimates (next 4Q EPS/Rev)
                 2. Price target history WITH dates (60g+ eski olanlar STALE)
                 3. Earnings surprises (4 çeyrek beat/miss)
                 4. Insider transactions (90 gün özet)
                 5. Peer multiples (sektör ortalaması)
                 6. 52w / 5y price percentile

Tetikleyici: artık severity şartı YOK — her hisse için Kimi consult edilir
             (bot/morning/swing tüm akışlarda). force=False parametresi geri
             uyumluluk için kabul edilir ama default davranışta etkisi yoktur.
"""

from __future__ import annotations
import os
import json
import re
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

# LLM client — via OpenRouter (Kimi K2 thinking)
import sys as _sys
from pathlib import Path as _Path
_agent_dir = _Path(__file__).resolve().parent.parent
if str(_agent_dir) not in _sys.path:
    _sys.path.insert(0, str(_agent_dir))
from llm_client import chat as _llm_chat, get_api_key as _get_api_key, DEFAULT_MODEL as _DEFAULT_MODEL

CLAUDE_MODEL = os.environ.get("KIMI_MODEL") or os.environ.get("CLAUDE_MODEL") or _DEFAULT_MODEL
CLAUDE_VALUATION_TIMEOUT = 120  # Kimi K2 thinking + zenginleştirilmiş context daha uzun

# Hybrid Plus blend: Kimi 0.70 / framework 0.30 (override: KIMI_VALUATION_BLEND env)
KIMI_VALUATION_BLEND = float(os.environ.get("KIMI_VALUATION_BLEND", "0.70"))

# Stale eşiği — analist hedefi N gün eski ise prompt'a "STALE" diye işaretlenir
STALE_TARGET_DAYS = int(os.environ.get("STALE_TARGET_DAYS", "60"))

# FMP zenginleştirilmiş context için
try:
    from fmp_client import fmp_get as _fmp_get
except ImportError:
    _fmp_get = None

# Observability (opsiyonel)
try:
    import sys
    from pathlib import Path as _P
    _agent = _P(__file__).resolve().parent.parent
    if str(_agent) not in sys.path:
        sys.path.insert(0, str(_agent))
    from observability import log_claude_call
except ImportError:
    log_claude_call = lambda *a, **kw: None

# Kimi valuation persistent log (sanity tracking + 30g hit rate analizi için)
_REPO_ROOT = _Path(__file__).resolve().parent.parent.parent
_KIMI_LOG_PATH = _REPO_ROOT / "logs" / "kimi_valuations.jsonl"


def _log_kimi_valuation(ticker: str, framework_result: dict, kimi_result: dict) -> None:
    """
    Her başarılı Kimi consult'unu logla — /sanity komutu, A/B karşılaştırması ve
    30g hit-rate analizi için kaynak.

    Schema:
      timestamp, ticker, current_price, framework_fv, kimi_fv, blended_fv,
      blend_weight, sanity_flag, cycle_phase, tavsiye_etiket, confidence,
      rejim_var_mi, rejim_tip, stale_count, fresh_count, peer_pe, model
    """
    try:
        import json as _json
        from datetime import datetime as _dt
        _KIMI_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

        rich = kimi_result.get("_rich_context_used", {}) or {}
        rejim = kimi_result.get("rejim_degisikligi") or {}
        fv_blok = framework_result.get("fair_value", {}) or {}

        record = {
            "timestamp": _dt.utcnow().isoformat(timespec="seconds") + "Z",
            "ticker": ticker,
            "current_price": fv_blok.get("current_price"),
            "framework_fv": kimi_result.get("framework_fair_value"),
            "kimi_fv": kimi_result.get("claude_fair_value"),
            "blended_fv": kimi_result.get("blended_fair_value"),
            "blend_weight": kimi_result.get("blend_weight"),
            "sanity_flag": kimi_result.get("sanity_flag"),
            "cycle_phase": kimi_result.get("cycle_phase"),
            "tavsiye_etiket": kimi_result.get("tavsiye_etiket"),
            "confidence": kimi_result.get("confidence"),
            "rejim_var_mi": bool(rejim.get("var_mi")),
            "rejim_tip": rejim.get("tip"),
            "stale_count": rich.get("stale_target_count"),
            "fresh_count": (rich.get("price_target_count") or 0)
                            - (rich.get("stale_target_count") or 0),
            "peer_pe": rich.get("peer_pe"),
            "model": kimi_result.get("model"),
        }
        with _KIMI_LOG_PATH.open("a", encoding="utf-8") as f:
            f.write(_json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[ai_consultant] _log_kimi_valuation hatası: {e}")


SYSTEM_PROMPT = """You are Finzora's PRIMARY valuation engine — Zeynel's autonomous equity valuation assistant.

ROLE:
You are the lead valuation decision-maker. The mechanical framework runs first
and produces a baseline; your output is blended with it (your weight is the
larger share). Use the framework as a sanity check, NOT as ground truth.

INPUT CONTEXT (you will receive):
1. Framework's mechanical fair value (mid-cycle PE, DCF, EV/EBITDA, etc.)
2. Analyst consensus + each price target's age (some marked STALE)
3. Forward estimates (next 4 quarters EPS/Revenue)
4. Earnings surprise history (last 4 quarters beat/miss)
5. Insider transactions (last 90 days summary)
6. Peer multiples (industry average)
7. 52-week / 5-year price percentile
8. Macro regime + sector context

YOUR JOB (in order):
1. STRUCTURAL REGIME: is the underlying business at a structural inflection?
   Examples: AI/HBM for memory semis, GLP-1 for pharma, EV/SDV for autos,
   nuclear restart for utilities. Mid-cycle methods miss these → adjust upward.
2. CYCLE PHASE: early / mid / late / peak / bottom — based on margins, capex,
   growth deceleration, peer comparisons.
3. FORWARD METRICS WIN: weight forward (next 4Q) estimates OVER trailing TTM
   when available. TTM is a rear-view mirror.
4. STALE DATA HYGIENE: items marked "STALE" (>60 days old) must NOT anchor
   your fair value. Treat them as historical reference only. If consensus is
   mostly stale, lower your confidence.
5. INSIDER SIGNAL: clustered insider buying near 52w low + sector tailwind is
   a strong bull signal. Mention it in thesis.
6. PEER REALITY CHECK: if the stock's PE is 40x but the sector median is 28x,
   either it deserves the premium (regime change) or it's overvalued. Justify.
7. MACRO ALIGNMENT: in a tariff regime, exporters get penalty; in geopolitical
   crisis, energy/defense get bonus. Apply regime-aware multiplier.
8. SCENARIOS: bear / base / bull with single-sentence concrete catalyst each.

OUTPUT: ONLY the JSON below — no other text. JSON keys MUST stay exactly as
shown. Free-text VALUES (thesis, aciklama, framework_kritik, konsensus_aciklama,
tavsiye, stale_uyarisi) MUST be written in TURKISH plain ASCII (no Turkish
special chars: write "satis" not "satış"; no apostrophes — "Zeynelin" not
"Zeynel'in") to keep parsing safe.

```json
{
  "claude_fair_value": 350.0,
  "confidence": 75,
  "scenarios": {
    "bear": {"price": 200.0, "thesis": "Turkish ASCII — bear thesis, single sentence"},
    "base": {"price": 350.0, "thesis": "Turkish ASCII — base thesis"},
    "bull": {"price": 550.0, "thesis": "Turkish ASCII — bull thesis"}
  },
  "rejim_degisikligi": {
    "var_mi": true,
    "tip": "ai_memory_yapisal",
    "aciklama": "Turkish ASCII — single sentence rationale"
  },
  "cycle_phase": "mid",
  "forward_pe_yorumu": "Turkish ASCII — forward 12M PE comment, 1 sentence",
  "insider_yorumu": "Turkish ASCII — insider activity interpretation, 1 sentence (or 'aktivite yok')",
  "peer_yorumu": "Turkish ASCII — vs sector multiples, 1 sentence",
  "stale_uyarisi": "Turkish ASCII — list of stale data points ignored, 1 sentence",
  "framework_kritik": "Turkish ASCII — single sentence",
  "konsensus_aciklama": "Turkish ASCII — single sentence",
  "tavsiye": "Turkish ASCII — recommendation prose",
  "tavsiye_etiket": "MANUEL_REVIEW"
}
```

RULES:
- claude_fair_value: single 12-month target.
- tavsiye_etiket: one of UCUZ / ADIL / PAHALI / MANUEL_REVIEW.
- confidence: your own confidence (clarity of forward data + stale ratio + macro).
- thesis: short, single Turkish sentence, concrete catalyst, plain ASCII.
- tavsiye: MAX 200 characters, single paragraph, MUST end with a period (".").
  Don't get cut mid-sentence — write a complete, terminated thought.
- forward_pe_yorumu, peer_yorumu, stale_uyarisi, insider_yorumu,
  framework_kritik, konsensus_aciklama: each ONE sentence ending with period.
- ONLY return the JSON — no extra prose."""


# ─── Zenginleştirilmiş FMP Context ───────────────────────────────────────────

def _safe_fmp(endpoint: str, params: dict, default=None):
    """fmp_get yoksa veya hata olursa default dön."""
    if _fmp_get is None:
        return default if default is not None else []
    try:
        res = _fmp_get(endpoint, params)
        if res is None:
            return default if default is not None else []
        return res
    except Exception:
        return default if default is not None else []


def _days_ago(date_str: str) -> Optional[int]:
    """ISO date string'i bugünden kaç gün önce olduğuna çevir."""
    if not date_str:
        return None
    try:
        # FMP formatları: "2026-04-15", "2026-04-15 10:30:00", ISO
        cleaned = (date_str[:10]).strip()
        d = datetime.strptime(cleaned, "%Y-%m-%d")
        delta = (datetime.utcnow() - d).days
        return delta
    except Exception:
        return None


def _build_rich_fmp_context(ticker: str, sector: str = "", industry: str = "",
                            current_price: float = 0.0) -> dict:
    """
    FMP'den Kimi prompt'unu zenginleştirecek 6 kategori veri çek.
    Her FMP çağrısı try/except korumalı — eksik veri prompt'a "veri yok"
    olarak girer, exception fırlatmaz.
    """
    out = {
        "forward_estimates": [],
        "price_targets": [],
        "earnings_surprises": [],
        "insider_summary": {},
        "peer_pe": None,
        "price_percentiles": {},
    }
    if not ticker:
        return out

    # 1. Forward estimates (next 4 quarters)
    fe = _safe_fmp("analyst-estimates", {"symbol": ticker, "period": "quarter", "limit": 4})
    if isinstance(fe, list):
        future = []
        for e in fe[:4]:
            d = e.get("date", "")
            # Future olanları al
            try:
                if d and datetime.strptime(d[:10], "%Y-%m-%d") > datetime.utcnow():
                    future.append({
                        "date": d[:10],
                        "eps_avg": e.get("estimatedEpsAvg") or e.get("epsAvg"),
                        "rev_avg": e.get("estimatedRevenueAvg") or e.get("revenueAvg"),
                    })
            except Exception:
                continue
        out["forward_estimates"] = future

    # 2. Price target history with dates (stale tespiti için)
    pt = _safe_fmp("price-target-news", {"symbol": ticker, "limit": 15})
    if isinstance(pt, list):
        targets = []
        for p in pt[:15]:
            d = p.get("publishedDate") or p.get("publicationDate") or ""
            yas = _days_ago(d)
            target = p.get("priceTarget") or p.get("adjPriceTarget")
            analyst = p.get("analystName") or p.get("analystCompany", "?")
            if target:
                targets.append({
                    "target": float(target),
                    "analyst": analyst[:30],
                    "date": d[:10] if d else "?",
                    "age_days": yas if yas is not None else 999,
                    "stale": (yas is not None and yas > STALE_TARGET_DAYS),
                })
        out["price_targets"] = targets

    # 3. Earnings surprises — FMP'de "earnings" endpoint'i kullanılır (FMP_SKILL.md:461),
    #    surprise manuel hesaplanır
    es = _safe_fmp("earnings", {"symbol": ticker, "limit": 8})
    if isinstance(es, list):
        surprises = []
        for e in es:
            d = e.get("date", "")
            actual = e.get("epsActual") or e.get("actualEarningResult")
            estimate = e.get("epsEstimated") or e.get("estimatedEarning")
            # Sadece gerçekleşmiş (actual var) + son 4 çeyrek
            if actual is not None and estimate is not None:
                try:
                    actual_f = float(actual)
                    est_f = float(estimate)
                    surprise_pct = (actual_f - est_f) / abs(est_f) * 100 if est_f else None
                    surprises.append({
                        "date": d[:10],
                        "actual": round(actual_f, 4),
                        "estimate": round(est_f, 4),
                        "surprise_pct": round(surprise_pct, 1) if surprise_pct is not None else None,
                    })
                except Exception:
                    continue
            if len(surprises) >= 4:
                break
        out["earnings_surprises"] = surprises

    # 4. Insider transactions (son 90 gün)
    it = _safe_fmp("insider-trading", {"symbol": ticker, "limit": 50})
    if isinstance(it, list):
        cutoff = datetime.utcnow() - timedelta(days=90)
        buy_count, sell_count, buy_value, sell_value = 0, 0, 0.0, 0.0
        for tx in it:
            d_str = tx.get("transactionDate") or tx.get("filingDate", "")
            try:
                if d_str and datetime.strptime(d_str[:10], "%Y-%m-%d") < cutoff:
                    continue
            except Exception:
                continue
            tx_type = (tx.get("transactionType") or "").upper()
            value = float(tx.get("price", 0) or 0) * float(tx.get("securitiesTransacted", 0) or 0)
            if "P-PURCHASE" in tx_type or "BUY" in tx_type:
                buy_count += 1
                buy_value += value
            elif "S-SALE" in tx_type or "SELL" in tx_type:
                sell_count += 1
                sell_value += value
        out["insider_summary"] = {
            "buy_count_90d": buy_count,
            "sell_count_90d": sell_count,
            "buy_value_usd": int(buy_value),
            "sell_value_usd": int(sell_value),
            "net_flow_usd": int(buy_value - sell_value),
        }

    # 5. Peer multiples — FMP'de "industry-pe-snapshot" + date (FMP_SKILL.md:350)
    if industry:
        # Bugün veya en son iş günü dene (hafta sonu fallback)
        for days_back in (0, 1, 2, 3, 4):
            d = (datetime.utcnow().date() - timedelta(days=days_back)).isoformat()
            pp = _safe_fmp("industry-pe-snapshot", {"date": d, "exchange": "NYSE"})
            if isinstance(pp, list) and pp:
                # İndüstrinin satırını bul
                for row in pp:
                    row_industry = (row.get("industry") or "").lower()
                    if industry.lower() in row_industry or row_industry in industry.lower():
                        pe_val = row.get("pe")
                        if pe_val:
                            try:
                                pe_f = float(pe_val)
                                if 0 < pe_f < 200:
                                    out["peer_pe"] = round(pe_f, 1)
                            except Exception:
                                pass
                        break
                break  # bir tarih tutarsa diğerlerine bakma

    # 6. 52w / 5y price percentile
    today = datetime.utcnow().date()
    yr_ago = today - timedelta(days=365)
    yr5_ago = today - timedelta(days=365 * 5)
    # historical-price-eod/light → tarih + close, ucuz çağrı (FMP_SKILL.md:213)
    hist = _safe_fmp("historical-price-eod/light", {
        "symbol": ticker,
        "from": yr5_ago.isoformat(),
        "to": today.isoformat(),
    })
    if isinstance(hist, list) and hist:
        try:
            prices_5y = [float(h.get("price", 0) or h.get("close", 0) or 0)
                         for h in hist]
            prices_5y = [p for p in prices_5y if p > 0]
            prices_1y = []
            for h in hist:
                d = h.get("date", "")
                try:
                    if d and datetime.strptime(d[:10], "%Y-%m-%d").date() >= yr_ago:
                        p = float(h.get("price", 0) or h.get("close", 0) or 0)
                        if p > 0:
                            prices_1y.append(p)
                except Exception:
                    continue
            if prices_5y and current_price > 0:
                pct_5y = sum(1 for p in prices_5y if p < current_price) / len(prices_5y) * 100
                out["price_percentiles"]["pct_5y"] = round(pct_5y, 1)
            if prices_1y and current_price > 0:
                pct_1y = sum(1 for p in prices_1y if p < current_price) / len(prices_1y) * 100
                out["price_percentiles"]["pct_1y"] = round(pct_1y, 1)
                out["price_percentiles"]["high_1y"] = max(prices_1y)
                out["price_percentiles"]["low_1y"] = min(prices_1y)
        except Exception:
            pass

    return out


# ─── User Prompt (zenginleştirilmiş) ─────────────────────────────────────────

def _build_user_prompt(framework_result: dict, rich_ctx: dict = None) -> str:
    """Framework çıktısı + zengin FMP context'inden kapsamlı user mesajı."""
    ticker = framework_result.get("ticker", "?")
    fv = framework_result.get("fair_value", {})
    cls = framework_result.get("classification", {})
    conf = framework_result.get("confidence", {})
    methods = framework_result.get("methods_used", [])
    snap = framework_result.get("data_snapshot", {})
    analyst = framework_result.get("analyst_consensus") or {}
    regime = framework_result.get("market_regime") or {}
    rich_ctx = rich_ctx or {}

    method_lines = "\n".join(
        f"  - {m['name']}: ${m['fair_value']:.2f} (w={m['weight']:.0%})"
        for m in methods[:8]
    )

    pe = snap.get("pe_ttm", 0) or 0
    rev_g = (snap.get("rev_growth", 0) or 0) * 100
    op_m = (snap.get("op_margin", 0) or 0) * 100
    fcf_m = (snap.get("fcf_margin", 0) or 0) * 100
    roe = (snap.get("roe", 0) or 0) * 100
    roic = (snap.get("roic", 0) or 0) * 100

    current_price = fv.get('current_price', 0)

    # ── Forward estimates blok ──
    fwd = rich_ctx.get("forward_estimates", [])
    fwd_str = ""
    if fwd:
        fwd_str = "\n".join(
            f"  - {f['date']}: EPS ${f.get('eps_avg', '?')}, Rev "
            f"${(f.get('rev_avg', 0) or 0)/1e9:.2f}B"
            for f in fwd[:4]
        )
    else:
        fwd_str = "  (forward estimate verisi yok)"

    # ── Price targets (stale işaretli) blok ──
    pt = rich_ctx.get("price_targets", [])
    pt_str_parts = []
    stale_count = 0
    fresh_count = 0
    for p in pt[:10]:
        marker = " [STALE]" if p.get("stale") else ""
        if p.get("stale"):
            stale_count += 1
        else:
            fresh_count += 1
        pt_str_parts.append(
            f"  - ${p['target']:.2f} by {p['analyst']} ({p['date']}, "
            f"{p['age_days']}g eski){marker}"
        )
    pt_str = "\n".join(pt_str_parts) if pt_str_parts else "  (price target verisi yok)"
    pt_summary = f"Toplam: {fresh_count} taze, {stale_count} stale (>{STALE_TARGET_DAYS}g)"

    # ── Earnings surprises blok ──
    es = rich_ctx.get("earnings_surprises", [])
    es_str_parts = []
    for e in es[:4]:
        actual = e.get("actual")
        estimate = e.get("estimate")
        surprise = e.get("surprise_pct")
        if actual is not None and estimate is not None:
            beat = "✓ BEAT" if (actual or 0) > (estimate or 0) else "✗ MISS"
            es_str_parts.append(
                f"  - {e['date']}: act=${actual:.2f} vs est=${estimate:.2f} "
                f"({beat}, surprise={surprise}%)"
            )
    es_str = "\n".join(es_str_parts) if es_str_parts else "  (surprise verisi yok)"

    # ── Insider summary blok ──
    ins = rich_ctx.get("insider_summary", {}) or {}
    if ins:
        net = ins.get("net_flow_usd", 0)
        net_label = "NET BUY" if net > 0 else ("NET SELL" if net < 0 else "NEUTRAL")
        ins_str = (
            f"  Last 90d: {ins.get('buy_count_90d',0)} BUY (${ins.get('buy_value_usd',0)/1e6:.1f}M), "
            f"{ins.get('sell_count_90d',0)} SELL (${ins.get('sell_value_usd',0)/1e6:.1f}M)\n"
            f"  Net flow: ${net/1e6:+.1f}M ({net_label})"
        )
    else:
        ins_str = "  (insider verisi yok)"

    # ── Peer PE ──
    peer_pe = rich_ctx.get("peer_pe")
    peer_str = f"Sektör PE ort.: {peer_pe}x" if peer_pe else "Peer PE verisi yok"

    # ── Price percentiles ──
    pp = rich_ctx.get("price_percentiles", {}) or {}
    if pp:
        pp_str = (
            f"1y: %{pp.get('pct_1y', '?')} percentile "
            f"(high=${pp.get('high_1y', 0):.2f}, low=${pp.get('low_1y', 0):.2f}) | "
            f"5y: %{pp.get('pct_5y', '?')} percentile"
        )
    else:
        pp_str = "Tarihsel fiyat verisi yok"

    return f"""VALUATION ANALYSIS — {ticker}

PRICE: ${current_price:.2f}
ARCHETYPE: {cls.get('archetype_label', '?')} ({cls.get('archetype', '?')})

═══ FRAMEWORK RESULT (mechanical baseline — sanity check, not ground truth) ═══
Fair value: ${fv.get('point', 0):.2f}
Range: ${fv.get('range_low', 0):.2f} - ${fv.get('range_high', 0):.2f}
Upside: {fv.get('upside_pct', 0):+.1f}%
Verdict: {fv.get('karar', '?')}
Confidence: {conf.get('score', 0)}/100

METHODS USED:
{method_lines}

RED FLAGS: {', '.join(conf.get('red_flags', []))}

═══ ANALYST CONSENSUS (stale ratio matters) ═══
Median: ${analyst.get('median', 0):.2f}
High: ${analyst.get('high', 0):.2f}
Low: ${analyst.get('low', 0):.2f}
Framework gap: {analyst.get('framework_gap_pct', 0):+.1f}%

═══ PRICE TARGETS WITH AGES ({pt_summary}) ═══
{pt_str}

═══ FORWARD ESTIMATES (NEXT 4 QUARTERS — weight these) ═══
{fwd_str}

═══ EARNINGS SURPRISES (LAST 4Q) ═══
{es_str}

═══ INSIDER TRANSACTIONS (90D) ═══
{ins_str}

═══ PEER MULTIPLES ═══
{peer_str}
Stock PE (TTM): {pe:.1f}

═══ HISTORICAL PRICE PERCENTILES ═══
{pp_str}

═══ FUNDAMENTALS (TTM — rear-view) ═══
Sector: {snap.get('sector', '?')} / {snap.get('industry', '?')}
Market cap: ${(snap.get('mcap', 0) or 0)/1e9:.1f}B
Rev growth: {rev_g:+.1f}%
Op margin: {op_m:.1f}%  |  FCF margin: {fcf_m:.1f}%
ROE: {roe:.1f}%  |  ROIC: {roic:.1f}%

═══ MACRO REGIME ═══
{regime.get('detay', 'no regime data')}
Regime multiplier: {regime.get('multiplier', 1.0)}

═══ TASK ═══
You are the PRIMARY valuation engine. Use the framework as a sanity check only.
Weight forward estimates over TTM. Ignore STALE price targets as anchors. Note
insider signal strength. Compare PE to peer median. Apply macro regime context.
Produce 12-month fair value with bear/base/bull scenarios.

Reply with JSON ONLY (free-text values in plain-ASCII Turkish)."""


def _parse_json_response(text: str) -> Optional[dict]:
    """AI'nin cevabından JSON çıkar."""
    block_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if block_match:
        try:
            return json.loads(block_match.group(1))
        except json.JSONDecodeError:
            pass

    text = text.strip()
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


# ─── Ana Consult Fonksiyonu (Hybrid Plus) ────────────────────────────────────

def consult_claude(
    framework_result: dict,
    severity: float = 0.70,   # v7 default — geri uyumluluk için param duruyor
    force: bool = True,        # v7: her zaman consult (severity şartı kaldırıldı)
    verbose: bool = False
) -> Optional[dict]:
    """
    AI birincil değerleme görüşü al (Hybrid Plus).

    Args:
        framework_result: framework.valuate() çıktısı
        severity: artık etkisiz (v6 geri uyumluluk için kabul edilir)
        force: artık etkisiz (v7'de her zaman consult)
        verbose: stdout log

    Returns:
        Genişletilmiş JSON: claude_fair_value, scenarios, insider_yorumu,
        forward_pe_yorumu, peer_yorumu, stale_uyarisi, blended_fair_value, ...
        Hata durumunda {_error: ...} dict.
    """
    if not _get_api_key():
        if verbose:
            print("[ai_consultant] OPENROUTER_API_KEY tanımsız, atlandı")
        return {"_error": "OPENROUTER_API_KEY (veya ANTHROPIC_API_KEY) env var tanımsız"}

    # ── Zengin FMP context topla ──
    ticker = framework_result.get("ticker", "")
    snap = framework_result.get("data_snapshot", {})
    sector = snap.get("sector", "")
    industry = snap.get("industry", "")
    current_price = framework_result.get("fair_value", {}).get("current_price", 0) or 0

    rich_ctx = {}
    if ticker:
        try:
            rich_ctx = _build_rich_fmp_context(ticker, sector, industry, current_price)
            if verbose:
                print(f"[ai_consultant] {ticker} zengin context: "
                      f"forward={len(rich_ctx.get('forward_estimates', []))}, "
                      f"targets={len(rich_ctx.get('price_targets', []))}, "
                      f"insider={'+' if rich_ctx.get('insider_summary') else '-'}")
        except Exception as e:
            if verbose:
                print(f"[ai_consultant] zengin context hatası ({ticker}): {e}")

    user_prompt = _build_user_prompt(framework_result, rich_ctx)

    t0 = time.time()
    try:
        resp = _llm_chat(
            system=SYSTEM_PROMPT,
            user=user_prompt,
            model=CLAUDE_MODEL,
            max_tokens=10000,  # zengin context + thinking + tam JSON.
                               # Önceki 8000'de tavsiye alanı kesilebiliyordu.
            temperature=0.3,
            timeout=CLAUDE_VALUATION_TIMEOUT,
            apply_language_policy=False,
        )
        duration_ms = int((time.time() - t0) * 1000)
        raw = resp.text

        try:
            log_claude_call(
                mode="valuation_consult",
                model=CLAUDE_MODEL,
                input_tokens=resp.input_tokens,
                output_tokens=resp.output_tokens,
                duration_ms=duration_ms,
                metadata={"ticker": ticker, "blend": KIMI_VALUATION_BLEND},
            )
        except Exception:
            pass

    except Exception as e:
        if verbose:
            print(f"[ai_consultant] LLM API hatası: {type(e).__name__}: {e}")
        return {
            "_error": f"LLM API çağrısı başarısız: {type(e).__name__}: {e}",
            "model_attempted": CLAUDE_MODEL,
            "duration_ms": int((time.time() - t0) * 1000),
        }

    parsed = _parse_json_response(raw)
    if not parsed:
        if verbose:
            print(f"[ai_consultant] JSON parse başarısız:\n{raw[:300]}")
        return {
            "_error": "AI cevabı JSON formatında değil veya parse edilemedi",
            "raw_response_preview": raw[:500],
            "model": CLAUDE_MODEL,
            "duration_ms": duration_ms,
        }

    # ── Hybrid Plus blend ──
    framework_fv = framework_result.get("fair_value", {}).get("point", 0) or 0
    claude_fv = float(parsed.get("claude_fair_value", framework_fv))

    blend = KIMI_VALUATION_BLEND  # v7: env'den alınır, default 0.70
    blended = framework_fv * (1 - blend) + claude_fv * blend

    # Sanity check: framework ile Kimi arasında çok büyük sapma varsa bayrak
    sanity_flag = None
    if framework_fv > 0:
        gap_pct = abs(claude_fv - framework_fv) / framework_fv * 100
        if gap_pct > 100:
            sanity_flag = f"EXTREME_GAP_{gap_pct:.0f}%"
        elif gap_pct > 60:
            sanity_flag = f"LARGE_GAP_{gap_pct:.0f}%"

    parsed["blended_fair_value"] = round(blended, 2)
    parsed["blend_weight"] = round(blend, 3)
    parsed["framework_fair_value"] = round(framework_fv, 2)
    parsed["sanity_flag"] = sanity_flag
    parsed["raw_response"] = raw
    parsed["model"] = CLAUDE_MODEL
    parsed["duration_ms"] = duration_ms
    # Rich context'in özeti — observability için
    parsed["_rich_context_used"] = {
        "forward_estimate_count": len(rich_ctx.get("forward_estimates", [])),
        "price_target_count": len(rich_ctx.get("price_targets", [])),
        "stale_target_count": sum(1 for p in rich_ctx.get("price_targets", [])
                                   if p.get("stale")),
        "insider_data": bool(rich_ctx.get("insider_summary")),
        "peer_pe": rich_ctx.get("peer_pe"),
    }

    if verbose:
        flag_str = f" [{sanity_flag}]" if sanity_flag else ""
        print(f"[ai_consultant] {ticker} → AI FV: ${claude_fv:.2f}, "
              f"Framework FV: ${framework_fv:.2f}, "
              f"Blended (Kimi w={blend:.0%}): ${blended:.2f}{flag_str}")

    # Kalıcı log → /sanity komutu, A/B analizi, 30g hit-rate
    try:
        _log_kimi_valuation(ticker, framework_result, parsed)
    except Exception as _e:
        if verbose:
            print(f"[ai_consultant] log atlandı: {_e}")

    return parsed


def should_consult(framework_result: dict) -> tuple[bool, float, str]:
    """
    v6 geri uyumluluk shim — v7'de her zaman True döner çünkü Kimi her hisse için
    consult edilir. Severity hâlâ hesaplanır (log/observability için faydalı).
    """
    fv = framework_result.get("fair_value", {})
    conf = framework_result.get("confidence", {})
    analyst = framework_result.get("analyst_consensus") or {}
    methods = framework_result.get("methods_used", [])

    score = conf.get("score", 100)
    gap_pct = abs(analyst.get("framework_gap_pct") or 0)

    cv = 0.0
    if len(methods) >= 2:
        from statistics import median as _med
        vals = [m["fair_value"] for m in methods]
        med = _med(vals) or 0.01
        if med > 0:
            cv = sum(abs(v - med) for v in vals) / len(vals) / med

    severity = 0.0
    reasons = []
    if gap_pct >= 70:
        severity = max(severity, 0.95); reasons.append(f"konsensus_sapma_{gap_pct:.0f}%")
    elif gap_pct >= 50:
        severity = max(severity, 0.70); reasons.append(f"konsensus_sapma_{gap_pct:.0f}%")
    elif gap_pct >= 30:
        severity = max(severity, 0.40); reasons.append(f"konsensus_sapma_{gap_pct:.0f}%")
    if score < 40:
        severity = max(severity, 0.80); reasons.append(f"dusuk_guven_{score}")
    elif score < 50:
        severity = max(severity, 0.50); reasons.append(f"dusuk_guven_{score}")
    if cv >= 0.50:
        severity = max(severity, 0.60); reasons.append(f"metod_dispersion_{cv:.0%}")
    elif cv >= 0.40:
        severity = max(severity, 0.35); reasons.append(f"metod_dispersion_{cv:.0%}")

    # v7: HER ZAMAN True
    return True, severity, ",".join(reasons) if reasons else "v7_default_consult"


if __name__ == "__main__":
    # Test
    fake_result = {
        "ticker": "MU",
        "fair_value": {"point": 167.30, "current_price": 496.72,
                       "range_low": 84.17, "range_high": 245.08,
                       "upside_pct": -66.3, "karar": "PAHALI"},
        "classification": {"archetype": "mature_semi", "archetype_label": "Olgun yari iletken"},
        "confidence": {"score": 72, "red_flags": ["framework_bearish_vs_analysts"]},
        "methods_used": [
            {"name": "normalized_pe_midcycle", "fair_value": 75.15, "weight": 0.25},
            {"name": "dcf_2stage", "fair_value": 218.82, "weight": 0.20},
        ],
        "analyst_consensus": {"median": 429, "high": 550, "low": 310, "framework_gap_pct": -65},
        "data_snapshot": {
            "sector": "Technology", "industry": "Semiconductors",
            "mcap": 540e9, "pe_ttm": 23.4,
            "rev_growth": 0.57, "op_margin": 0.35,
            "fcf_margin": 0.20, "roe": 0.30, "roic": 0.20,
        },
        "market_regime": {"detay": "BOGA: SPY > SMA21", "multiplier": 1.12},
    }
    result = consult_claude(fake_result, verbose=True)
    if result and not result.get("_error"):
        print(json.dumps({k: v for k, v in result.items()
                         if k not in ("raw_response",)},
                        indent=2, ensure_ascii=False))
    elif result:
        print("ERROR:", result.get("_error"))
