"""
Position Manager — Finzora AI'ın merkezi pozisyon karar motoru.

Sorumluluklar
-------------
1. Stop tetik teyidi (15 May 2026 politikası):
     İki ardışık günlük (daily) bar kapanışı stop_loss altında ise
     pozisyon otomatik kapatılır. Tek bar stop altı + ikinci bar üstü →
     wick atılır, tetik yok. Tek bar stop altı + ikinci henüz yok →
     "pending" durumu (DM bilgi, kapanış beklenir).

2. Target tetik teyidi:
     Son daily kapanış >= target ise pozisyon otomatik kapatılır.

3. Otomatik kapanış infazı:
     portfolio.close_position çağrısı + logs/events.jsonl event +
     Telegram GROUP'a formal satış raporu + DM'e teknik teyit.

4. Otomatik açılış infazı (15 May 2026 — Aşama 7):
     Aşama 6 signal_broadcaster sinyallerini takip eder. Yayın sonrası
     ilk fiyat çekiminde entry_zone içine girmiş sinyaller için
     portfolio.add_position çağrılır (adet izleme yok — sadece market
     fiyatından açılış kaydı; P&L yüzde bazlı, USD yok). Idempotent:
     aynı sinyal için `position_opened` event yazılır, sonraki taramalarda
     atlanır.

Tüm pozisyon değişikliği kararları bu modülden geçmelidir. Mevcut
agent.monitor.check_stop_proximity sadece "yakın/kırıldı" intraday
DM alert'i üretmeye devam eder (bilgi); kapatma kararı buraya aittir.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from agent import fmp, portfolio, telegram

REPO_ROOT   = Path(__file__).resolve().parents[1]
EVENTS_PATH = REPO_ROOT / "logs" / "events.jsonl"


# ----------------------------------------------------------------------
# Internals
# ----------------------------------------------------------------------

def _log_event(event_type: str, symbol: str, **fields) -> None:
    """Append a JSONL event row. Best-effort; does not raise on I/O error."""
    event = {
        "type": event_type,
        "symbol": symbol,
        "ts": datetime.now(timezone.utc).isoformat(),
        **fields,
    }
    try:
        EVENTS_PATH.parent.mkdir(parents=True, exist_ok=True)
        with EVENTS_PATH.open("a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[position_manager] events.jsonl append failed: {e}", file=sys.stderr)


def _format_group_close_msg(closed: dict, reason_text: str) -> str:
    entry  = float(closed["entry_price"])
    exit_p = float(closed["exit_price"])
    shares = closed.get("shares")
    pnl_pct = closed["pnl_pct"]
    hold_days = (
        datetime.fromisoformat(closed["exit_date"]).date()
        - datetime.fromisoformat(closed["entry_date"]).date()
    ).days

    if shares is not None:
        pnl_usd = round((exit_p - entry) * int(shares), 2)
        entry_line = f"<b>Giriş   :</b> ${entry:.2f} × {int(shares)} ({closed['entry_date']})\n"
        exit_line  = f"<b>Çıkış   :</b> ${exit_p:.2f} × {int(shares)} ({closed['exit_date']}, {hold_days}g)\n"
        pnl_line   = f"<b>P&amp;L     :</b> <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)\n\n"
    else:
        entry_line = f"<b>Giriş   :</b> ${entry:.2f} ({closed['entry_date']})\n"
        exit_line  = f"<b>Çıkış   :</b> ${exit_p:.2f} ({closed['exit_date']}, {hold_days}g)\n"
        pnl_line   = f"<b>P&amp;L     :</b> <b>{pnl_pct:+.2f}%</b>\n\n"

    return (
        f"🔴 <b>OTOMATİK STOP KAPANIŞI — {closed['symbol']}</b>\n\n"
        f"<b>Sektör  :</b> {closed['sector']}\n"
        f"{entry_line}"
        f"{exit_line}"
        f"<b>Stop    :</b> ${closed['stop_loss']:.2f}\n\n"
        f"{pnl_line}"
        f"<b>Çıkış nedeni:</b> {reason_text}"
    )


def _format_group_target_msg(closed: dict, reason_text: str) -> str:
    entry  = float(closed["entry_price"])
    exit_p = float(closed["exit_price"])
    shares = closed.get("shares")
    pnl_pct = closed["pnl_pct"]
    hold_days = (
        datetime.fromisoformat(closed["exit_date"]).date()
        - datetime.fromisoformat(closed["entry_date"]).date()
    ).days

    if shares is not None:
        pnl_usd = round((exit_p - entry) * int(shares), 2)
        entry_line = f"<b>Giriş   :</b> ${entry:.2f} × {int(shares)} ({closed['entry_date']})\n"
        exit_line  = f"<b>Çıkış   :</b> ${exit_p:.2f} × {int(shares)} ({closed['exit_date']}, {hold_days}g)\n"
        pnl_line   = f"<b>P&amp;L     :</b> <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)\n\n"
    else:
        entry_line = f"<b>Giriş   :</b> ${entry:.2f} ({closed['entry_date']})\n"
        exit_line  = f"<b>Çıkış   :</b> ${exit_p:.2f} ({closed['exit_date']}, {hold_days}g)\n"
        pnl_line   = f"<b>P&amp;L     :</b> <b>{pnl_pct:+.2f}%</b>\n\n"

    return (
        f"🟢 <b>OTOMATİK TARGET KAPANIŞI — {closed['symbol']}</b>\n\n"
        f"<b>Sektör  :</b> {closed['sector']}\n"
        f"{entry_line}"
        f"{exit_line}"
        f"<b>Target  :</b> ${closed.get('target', 0):.2f}\n\n"
        f"{pnl_line}"
        f"<b>Çıkış nedeni:</b> {reason_text}"
    )


# ----------------------------------------------------------------------
# Stop check (2-bar daily confirmation policy, 15 May 2026)
# ----------------------------------------------------------------------

def check_stop_trigger(symbol: str, stop_loss: float) -> dict:
    """
    Returns
    -------
    {
      "triggered":   bool,           # 2-bar teyit oldu mu
      "bars_below":  int,            # ardışık stop altı kapanış sayısı (0/1/2)
      "exit_price":  Optional[float],
      "reason":      str,            # human-readable
      "dates":       list[str],      # bar tarihleri (en yeni en sonda)
      "closes":      list[float],
    }
    """
    bars = fmp.historical_eod(symbol, limit=5)
    if not bars or len(bars) < 2:
        return {
            "triggered": False, "bars_below": 0, "exit_price": None,
            "reason": f"Yeterli daily data yok ({len(bars or [])} bar)",
            "dates": [], "closes": [],
        }

    # FMP returns newest-first by convention; sort ascending defensively
    bars = sorted(bars, key=lambda b: b["date"])[-2:]
    closes = [round(float(b["close"]), 4) for b in bars]
    dates  = [b["date"] for b in bars]
    below  = [c < stop_loss for c in closes]

    if all(below):
        return {
            "triggered": True, "bars_below": 2,
            "exit_price": closes[-1],
            "reason": (
                f"Stop teyit: {dates[0]} ${closes[0]:.2f} ve "
                f"{dates[1]} ${closes[1]:.2f} kapanışları stop ${stop_loss:.2f} altı (2 ardışık gün)"
            ),
            "dates": dates, "closes": closes,
        }
    if below[-1] and not below[0]:
        return {
            "triggered": False, "bars_below": 1,
            "exit_price": None,
            "reason": (
                f"Pending: {dates[1]} kapanışı ${closes[1]:.2f} stop ${stop_loss:.2f} altı, "
                f"önceki gün ${closes[0]:.2f} üstü — sonraki kapanış teyit getirirse kapanır"
            ),
            "dates": dates, "closes": closes,
        }
    # ikisi de üstü ya da [eski altı, yeni üstü] — wick reverse, alert yok
    return {
        "triggered": False, "bars_below": 0,
        "exit_price": None,
        "reason": "Stop üstü kapanış",
        "dates": dates, "closes": closes,
    }


# ----------------------------------------------------------------------
# Target check
# ----------------------------------------------------------------------

def check_target_hit(symbol: str, target: float) -> dict:
    """Son daily kapanış >= target ise tetik."""
    bars = fmp.historical_eod(symbol, limit=2)
    if not bars:
        return {"triggered": False, "exit_price": None, "reason": "Daily data yok"}
    bars = sorted(bars, key=lambda b: b["date"])
    last_close = round(float(bars[-1]["close"]), 4)
    last_date  = bars[-1]["date"]
    if last_close >= target:
        return {
            "triggered": True,
            "exit_price": last_close,
            "reason": f"Target teyit: {last_date} kapanış ${last_close:.2f} >= target ${target:.2f}",
        }
    return {
        "triggered": False, "exit_price": None,
        "reason": f"Target altı: {last_date} ${last_close:.2f} < ${target:.2f}",
    }


# ----------------------------------------------------------------------
# Auto close infaz
# ----------------------------------------------------------------------

def auto_close(symbol: str, exit_reason: str, exit_price: float,
               lessons: str = "", trigger_kind: str = "stop") -> dict:
    """
    Pozisyonu kapatır (portfolio.close_position), event yazar, Telegram atar.
    trigger_kind: "stop" veya "target" — Telegram mesaj formatını etkiler.
    """
    closed = portfolio.close_position(
        symbol=symbol,
        exit_price=exit_price,
        exit_reason=exit_reason,
        lessons=lessons,
    )

    entry   = float(closed["entry_price"])
    shares_val = closed.get("shares")
    if shares_val is not None:
        pnl_usd = round((exit_price - entry) * int(shares_val), 2)
    else:
        pnl_usd = None

    _log_event(
        "position_closed",
        symbol,
        actor="position_manager",
        trigger=trigger_kind,
        entry_price=entry,
        exit_price=exit_price,
        shares=shares_val,
        pnl_pct=closed["pnl_pct"],
        pnl_usd=pnl_usd,
        exit_reason=exit_reason,
    )

    # Telegram — best-effort; data kaydı bloklamaz
    if trigger_kind == "stop":
        group_msg = _format_group_close_msg(closed, exit_reason)
    else:
        group_msg = _format_group_target_msg(closed, exit_reason)
    try:
        telegram.send_to_group(group_msg, parse_mode="HTML")
    except Exception as e:
        print(f"[position_manager] Telegram GROUP send failed: {e}", file=sys.stderr)
    try:
        if pnl_usd is not None:
            dm_pnl = f"pnl_pct={closed['pnl_pct']:+.2f}% pnl_usd=${pnl_usd:+,.2f}"
        else:
            dm_pnl = f"pnl_pct={closed['pnl_pct']:+.2f}%"
        telegram.send_to_dm(
            f"✅ <b>position_manager: {symbol} kapatıldı ({trigger_kind})</b>\n"
            f"<code>exit_price={exit_price} {dm_pnl}</code>\n"
            f"Reason: {exit_reason}",
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"[position_manager] Telegram DM send failed: {e}", file=sys.stderr)

    return {**closed, "pnl_usd": pnl_usd}


# ----------------------------------------------------------------------
# Scan all open positions
# ----------------------------------------------------------------------

def scan_stops_and_targets(dry_run: bool = False) -> dict:
    """
    Tüm açık pozisyonları stop teyidi + target teyidi için tarar.
    Tetiklenen pozisyonları otomatik kapatır (dry_run=False).

    Stop teyidi target'ten önce kontrol edilir; tetiklenirse target
    kontrolü atlanır.
    """
    result = {
        "scanned": 0,
        "stop_closed":   [],
        "stop_pending":  [],
        "target_closed": [],
        "errors":        [],
    }

    for pos in portfolio.get_positions(enrich=False):
        sym = pos["symbol"]
        result["scanned"] += 1
        try:
            stop_res = check_stop_trigger(sym, float(pos["stop_loss"]))

            if stop_res["triggered"]:
                if not dry_run:
                    auto_close(sym, stop_res["reason"], stop_res["exit_price"],
                               trigger_kind="stop")
                result["stop_closed"].append({
                    "symbol": sym,
                    "exit_price": stop_res["exit_price"],
                    "closes": stop_res["closes"],
                })
                continue

            if stop_res["bars_below"] == 1:
                result["stop_pending"].append({
                    "symbol": sym,
                    "last_close": stop_res["closes"][-1] if stop_res["closes"] else None,
                    "stop": pos["stop_loss"],
                })

            if pos.get("target"):
                tgt_res = check_target_hit(sym, float(pos["target"]))
                if tgt_res["triggered"]:
                    if not dry_run:
                        auto_close(sym, tgt_res["reason"], tgt_res["exit_price"],
                                   trigger_kind="target")
                    result["target_closed"].append({
                        "symbol": sym,
                        "exit_price": tgt_res["exit_price"],
                    })

        except Exception as e:
            result["errors"].append({"symbol": sym, "msg": str(e)})

    return result


# ----------------------------------------------------------------------
# Auto OPEN (Aşama 7 — 15 May 2026)
# ----------------------------------------------------------------------
#
# Aşama 6 (signal_broadcaster.py) sinyali yayınlar, events.jsonl'a
# "signal_sent" event yazar. Bu fonksiyonlar son N gün sinyallerini
# tarar; fiyat entry_zone içine girmiş ve henüz portföyde olmayan her
# sinyal için pozisyon açar.
#
# Adet politikası (Zeynel kararı, 15 May 2026):
#   - Adet (shares) izlenmez. Sistem sadece market fiyatından pozisyon
#     açılış kaydı oluşturur; portfolio.json'da shares alanı yazılmaz.
#   - P&L sadece yüzde olarak hesaplanır (giriş fiyatı → çıkış fiyatı).
#   - Mevcut (eski) pozisyonların shares alanı korunur, geriye uyumluluk
#     için close mesajlarında "× N" + USD P&L gösterilir.
#
# Idempotency:
#   - position_opened event yazılır.
#   - Bir sembol için son LOOKBACK_DAYS içinde position_opened varsa atla.
#   - portfolio.json positions[].symbol kontrolü ek güvence.

SIGNAL_LOOKBACK_DAYS = 5  # son N gün signal_sent kayıtlarını tara
ZONE_TOLERANCE_PCT   = 1.0  # zone üst sınırının +%1 tolerans (slipaj için)


def _read_recent_signals(lookback_days: int = SIGNAL_LOOKBACK_DAYS) -> list[dict]:
    """events.jsonl'dan son N gün signal_sent kayıtlarını oku."""
    if not EVENTS_PATH.exists():
        return []
    cutoff = datetime.now(timezone.utc).timestamp() - lookback_days * 86400
    out = []
    try:
        for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") != "signal_sent":
                continue
            ts_str = e.get("ts") or e.get("timestamp") or ""
            try:
                # Parse ISO timestamp
                ts_dt = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                if ts_dt.timestamp() < cutoff:
                    continue
            except Exception:
                continue
            out.append(e)
    except Exception as e:
        print(f"[position_manager] events.jsonl read failed: {e}", file=sys.stderr)
    return out


def _opened_recently(symbol: str, lookback_days: int = SIGNAL_LOOKBACK_DAYS) -> bool:
    """Idempotency: bu sembol için son N günde position_opened event var mı?"""
    if not EVENTS_PATH.exists():
        return False
    cutoff = datetime.now(timezone.utc).timestamp() - lookback_days * 86400
    sym_u  = symbol.upper()
    try:
        for line in EVENTS_PATH.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") != "position_opened":
                continue
            if (e.get("symbol") or "").upper() != sym_u:
                continue
            ts_str = e.get("ts") or e.get("timestamp") or ""
            try:
                if datetime.fromisoformat(ts_str.replace("Z", "+00:00")).timestamp() >= cutoff:
                    return True
            except Exception:
                continue
    except Exception:
        pass
    return False


def _parse_zone(zone_str: str) -> Optional[tuple[float, float]]:
    """'$410-415' veya '$1550-1580' → (alt, üst). Para sembolü/virgül temizlenir."""
    if not zone_str or not isinstance(zone_str, str):
        return None
    clean = zone_str.replace("$", "").replace(",", "").strip()
    if "-" in clean:
        parts = clean.split("-")
        if len(parts) == 2:
            try:
                return (float(parts[0].strip()), float(parts[1].strip()))
            except ValueError:
                return None
    try:
        v = float(clean)
        return (v * 0.99, v * 1.01)
    except ValueError:
        return None


def _get_sector(symbol: str) -> str:
    """FMP profile'dan sektör çek (best-effort)."""
    try:
        prof = fmp.fmp_get("profile", {"symbol": symbol})
        if isinstance(prof, list) and prof:
            return prof[0].get("sector") or "Unknown"
    except Exception:
        pass
    return "Unknown"


def _format_group_open_msg(opened: dict, score: float, source_zone: str,
                           entry_target: Optional[float]) -> str:
    """Otomatik açılış için GROUP rapor mesajı (adet izleme yok — sadece fiyat)."""
    sym    = opened["symbol"]
    sector = opened.get("sector", "?")
    price  = float(opened["entry_price"])
    stop   = float(opened["stop_loss"])
    target = opened.get("target")
    entry_date = opened.get("entry_date", "?")
    stop_pct   = (stop - price) / price * 100
    target_pct = (target - price) / price * 100 if target else None

    lines = [
        f"🟢 <b>OTOMATİK ALIM — {sym}</b>",
        f"<i>Aşama 7: zone-girişi otomatik açılış (skor {score:.0f})</i>",
        "",
        f"<b>Sektör  :</b> {sector}",
        f"<b>Giriş   :</b> ${price:.2f} ({entry_date})",
        f"<b>Zone    :</b> {source_zone}",
        f"<b>Stop    :</b> ${stop:.2f} ({stop_pct:+.2f}%)",
    ]
    if target:
        lines.append(f"<b>Target  :</b> ${float(target):.2f} ({target_pct:+.2f}%)")
    else:
        lines.append(f"<b>Target  :</b> —")

    rr = abs(target_pct / stop_pct) if (target and stop_pct != 0) else None
    if rr:
        lines.append(f"<b>R/R     :</b> 1:{rr:.2f}")
    return "\n".join(lines)


def auto_open(symbol: str, entry_price: float, stop_loss: float,
              target: Optional[float], score: float, source_zone: str,
              theme: Optional[str] = None) -> dict:
    """
    Pozisyonu otomatik açar (portfolio.add_position), event yazar,
    Telegram GROUP + DM mesajları gönderir.

    Adet izlenmez (15 May 2026 Zeynel kararı). Sadece market fiyatından
    pozisyon açılış kaydı oluşturulur; P&L sadece yüzde olarak hesaplanır.

    Returns
    -------
    Açılan pozisyon dict (portfolio.add_position çıktısı).
    """
    sector = _get_sector(symbol)
    score_int = int(round(score))
    theme_note = f", {theme}" if theme else ""
    entry_reason = (
        f"Aşama 6 sinyali (skor {score_int}{theme_note}). "
        f"Otomatik zone-girişi alım — market fiyatından."
    )

    # shares geçilmiyor — adet izleme yok (Zeynel kararı 15 May 2026)
    opened = portfolio.add_position(
        symbol       = symbol,
        sector       = sector,
        entry_price  = entry_price,
        entry_reason = entry_reason,
        stop_loss    = stop_loss,
        target       = target,
    )

    _log_event(
        "position_opened",
        symbol,
        actor="position_manager",
        trigger="signal_zone_entry",
        score=score,
        entry_price=entry_price,
        stop_loss=stop_loss,
        target=target,
        sector=sector,
        source_zone=source_zone,
        theme=theme,
    )

    # Telegram — best-effort
    group_msg = _format_group_open_msg(opened, score, source_zone, target)
    try:
        telegram.send_to_group(group_msg, parse_mode="HTML")
    except Exception as e:
        print(f"[position_manager] Telegram GROUP open send failed: {e}", file=sys.stderr)
    try:
        telegram.send_to_dm(
            f"✅ <b>position_manager: {symbol} otomatik açıldı</b>\n"
            f"<code>entry={entry_price} stop={stop_loss} "
            f"target={target if target else '—'}</code>\n"
            f"Skor: {score_int} | Zone: {source_zone}",
            parse_mode="HTML",
        )
    except Exception as e:
        print(f"[position_manager] Telegram DM open send failed: {e}", file=sys.stderr)

    return opened


def execute_pending_signals(dry_run: bool = False,
                            lookback_days: int = SIGNAL_LOOKBACK_DAYS) -> dict:
    """
    Son N gün signal_sent kayıtlarını tarar; entry_zone içine girmiş
    ve henüz açılmamış olanları otomatik açar.

    Returns
    -------
    {
      "scanned":         int,                    # taranan unique sembol
      "opened":          list[dict],             # gerçekten açılanlar
      "skipped_in_pf":   list[str],              # zaten portföyde
      "skipped_idempot": list[str],              # son N günde açılmış
      "skipped_no_zone": list[str],              # zone parse edilemedi
      "skipped_out_zone": list[dict],            # zone dışı (bekleyenler)
      "errors":          list[dict],
    }
    """
    result = {
        "scanned": 0,
        "opened":           [],
        "skipped_in_pf":    [],
        "skipped_idempot":  [],
        "skipped_no_zone":  [],
        "skipped_out_zone": [],
        "errors":           [],
    }

    # 1) Son N gün sinyallerini al, sembol başına en yeni'yi tut
    signals = _read_recent_signals(lookback_days)
    if not signals:
        return result

    latest_by_sym: dict[str, dict] = {}
    for s in signals:
        sym = (s.get("symbol") or "").upper()
        if not sym:
            continue
        ts_str = s.get("ts") or s.get("timestamp") or ""
        if sym not in latest_by_sym or ts_str > (
            latest_by_sym[sym].get("ts") or latest_by_sym[sym].get("timestamp") or ""
        ):
            latest_by_sym[sym] = s

    # 2) Mevcut portföy sembolleri
    try:
        pf_syms = {p["symbol"].upper() for p in portfolio.get_positions(enrich=False)}
    except Exception as e:
        result["errors"].append({"stage": "load_portfolio", "msg": str(e)})
        return result

    # 3) Her sinyali değerlendir
    for sym, sig in latest_by_sym.items():
        result["scanned"] += 1

        # 3a) Portföyde varsa atla
        if sym in pf_syms:
            result["skipped_in_pf"].append(sym)
            continue

        # 3b) Idempotency
        if _opened_recently(sym, lookback_days=lookback_days):
            result["skipped_idempot"].append(sym)
            continue

        # 3c) Zone parse
        zone_str = sig.get("entry_zone") or ""
        zone = _parse_zone(zone_str)
        if not zone:
            result["skipped_no_zone"].append(sym)
            continue
        zone_lo, zone_hi = zone
        zone_hi_tol = zone_hi * (1 + ZONE_TOLERANCE_PCT / 100)

        # 3d) Anlık fiyat
        try:
            q = fmp.quote(sym)
            if not q or not q.get("price"):
                result["errors"].append({"symbol": sym, "msg": "quote yok"})
                continue
            price = float(q["price"])
        except Exception as e:
            result["errors"].append({"symbol": sym, "msg": f"quote hata: {e}"})
            continue

        # 3e) Zone içi mi?
        if not (zone_lo <= price <= zone_hi_tol):
            result["skipped_out_zone"].append({
                "symbol": sym, "price": price,
                "zone": f"${zone_lo:.2f}-${zone_hi:.2f}",
            })
            continue

        # 3f) Tetik — aç
        stop   = sig.get("stop_loss")
        target = sig.get("target")
        score  = float(sig.get("score") or 0)

        if stop is None:
            result["errors"].append({"symbol": sym, "msg": "stop_loss yok"})
            continue

        try:
            if dry_run:
                result["opened"].append({
                    "symbol": sym, "price": price, "stop": stop, "target": target,
                    "score": score, "dry_run": True,
                })
            else:
                opened = auto_open(
                    symbol      = sym,
                    entry_price = price,
                    stop_loss   = float(stop),
                    target      = float(target) if target else None,
                    score       = score,
                    source_zone = zone_str,
                )
                result["opened"].append({
                    "symbol": sym, "price": price, "stop": float(stop),
                    "target": float(target) if target else None,
                    "score": score,
                })
        except Exception as e:
            result["errors"].append({"symbol": sym, "msg": f"auto_open hata: {e}"})

    return result


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------

def _cli() -> int:
    if len(sys.argv) < 2:
        print(
            "Kullanım:\n"
            "  python -m agent.position_manager scan [--dry-run]\n"
            "  python -m agent.position_manager check-stop SYMBOL\n"
            "  python -m agent.position_manager check-target SYMBOL\n"
            "  python -m agent.position_manager execute-signals [--dry-run]"
        )
        return 1

    cmd = sys.argv[1]

    if cmd == "scan":
        dry = "--dry-run" in sys.argv
        res = scan_stops_and_targets(dry_run=dry)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        if res["stop_pending"]:
            # DM bilgi — pending durumdaki pozisyonlar için tek mesaj
            pending_lines = "\n".join(
                f"  • {p['symbol']}: son kapanış ${p['last_close']} < stop ${p['stop']} (ikinci teyit bekleniyor)"
                for p in res["stop_pending"]
            )
            try:
                telegram.send_to_dm(
                    f"⏳ <b>Stop pending — kapanış teyidi bekliyor</b>\n\n{pending_lines}\n\n"
                    f"<i>Sonraki günlük kapanış da stop altı olursa otomatik kapanır.</i>",
                    parse_mode="HTML",
                )
            except Exception as e:
                print(f"[position_manager] Pending DM failed: {e}", file=sys.stderr)
        return 0

    if cmd == "check-stop":
        if len(sys.argv) < 3:
            print("Symbol gerek"); return 1
        sym = sys.argv[2].upper()
        pf = portfolio.load_portfolio()
        pos = next((p for p in pf["positions"] if p["symbol"].upper() == sym), None)
        if not pos:
            print(f"{sym} açık pozisyon değil"); return 1
        print(json.dumps(check_stop_trigger(sym, float(pos["stop_loss"])),
                         indent=2, ensure_ascii=False))
        return 0

    if cmd == "check-target":
        if len(sys.argv) < 3:
            print("Symbol gerek"); return 1
        sym = sys.argv[2].upper()
        pf = portfolio.load_portfolio()
        pos = next((p for p in pf["positions"] if p["symbol"].upper() == sym), None)
        if not pos or not pos.get("target"):
            print(f"{sym} target tanımlı değil"); return 1
        print(json.dumps(check_target_hit(sym, float(pos["target"])),
                         indent=2, ensure_ascii=False))
        return 0

    if cmd == "execute-signals":
        dry = "--dry-run" in sys.argv
        res = execute_pending_signals(dry_run=dry)
        print(json.dumps(res, indent=2, ensure_ascii=False))
        # DM özet — açılan varsa
        if res["opened"] and not dry:
            opened_lines = "\n".join(
                f"  • {o['symbol']}: ${o['price']:.2f} | stop ${o['stop']:.2f} "
                f"| target {('$%.2f' % o['target']) if o.get('target') else '—'} | skor {o['score']:.0f}"
                for o in res["opened"]
            )
            try:
                telegram.send_to_dm(
                    f"🚀 <b>Aşama 7 — otomatik açılış infaz raporu</b>\n\n"
                    f"<b>Açıldı ({len(res['opened'])}):</b>\n{opened_lines}\n\n"
                    f"<i>Market fiyatından açıldı, adet izlenmez.</i>",
                    parse_mode="HTML",
                )
            except Exception as e:
                print(f"[position_manager] Açılış özet DM failed: {e}", file=sys.stderr)
        return 0

    print(f"Bilinmeyen komut: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
