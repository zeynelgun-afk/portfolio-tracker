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

İleride bu modüle gelecek karar yetkileri (tek merkez prensibi):
    • set_stop_loss / set_target — pozisyon yaşam döngüsü içinde güncelleme
    • propose_entry — alım kararı pipeline (signal_tracker + ai_gate'i
      bu modülde finalize eden orchestrator)
    • confirm_entry — broker fiili fill sonrası kayıt

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
    shares = int(closed["shares"])
    pnl_usd = round((exit_p - entry) * shares, 2)
    pnl_pct = closed["pnl_pct"]
    hold_days = (
        datetime.fromisoformat(closed["exit_date"]).date()
        - datetime.fromisoformat(closed["entry_date"]).date()
    ).days
    return (
        f"🔴 <b>OTOMATİK STOP KAPANIŞI — {closed['symbol']}</b>\n\n"
        f"<b>Sektör  :</b> {closed['sector']}\n"
        f"<b>Giriş   :</b> ${entry:.2f} × {shares} ({closed['entry_date']})\n"
        f"<b>Çıkış   :</b> ${exit_p:.2f} × {shares} ({closed['exit_date']}, {hold_days}g)\n"
        f"<b>Stop    :</b> ${closed['stop_loss']:.2f}\n\n"
        f"<b>P&amp;L     :</b> <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)\n\n"
        f"<b>Çıkış nedeni:</b> {reason_text}"
    )


def _format_group_target_msg(closed: dict, reason_text: str) -> str:
    entry  = float(closed["entry_price"])
    exit_p = float(closed["exit_price"])
    shares = int(closed["shares"])
    pnl_usd = round((exit_p - entry) * shares, 2)
    pnl_pct = closed["pnl_pct"]
    hold_days = (
        datetime.fromisoformat(closed["exit_date"]).date()
        - datetime.fromisoformat(closed["entry_date"]).date()
    ).days
    return (
        f"🟢 <b>OTOMATİK TARGET KAPANIŞI — {closed['symbol']}</b>\n\n"
        f"<b>Sektör  :</b> {closed['sector']}\n"
        f"<b>Giriş   :</b> ${entry:.2f} × {shares} ({closed['entry_date']})\n"
        f"<b>Çıkış   :</b> ${exit_p:.2f} × {shares} ({closed['exit_date']}, {hold_days}g)\n"
        f"<b>Target  :</b> ${closed.get('target', 0):.2f}\n\n"
        f"<b>P&amp;L     :</b> <b>${pnl_usd:+,.2f}</b> ({pnl_pct:+.2f}%)\n\n"
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
    pnl_usd = round((exit_price - entry) * int(closed["shares"]), 2)

    _log_event(
        "position_closed",
        symbol,
        actor="position_manager",
        trigger=trigger_kind,
        entry_price=entry,
        exit_price=exit_price,
        shares=closed["shares"],
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
        telegram.send_to_dm(
            f"✅ <b>position_manager: {symbol} kapatıldı ({trigger_kind})</b>\n"
            f"<code>exit_price={exit_price} pnl_pct={closed['pnl_pct']:+.2f}% "
            f"pnl_usd=${pnl_usd:+,.2f}</code>\n"
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
# CLI
# ----------------------------------------------------------------------

def _cli() -> int:
    if len(sys.argv) < 2:
        print(
            "Kullanım:\n"
            "  python -m agent.position_manager scan [--dry-run]\n"
            "  python -m agent.position_manager check-stop SYMBOL\n"
            "  python -m agent.position_manager check-target SYMBOL"
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

    print(f"Bilinmeyen komut: {cmd}")
    return 1


if __name__ == "__main__":
    sys.exit(_cli())
