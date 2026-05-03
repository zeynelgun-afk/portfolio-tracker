#!/usr/bin/env python3
"""
Finzora Agent — Trade Geri Bildirimi
======================================
Bir pozisyon kapandığında otomatik çalışır:
  1. Claude'a trade detaylarını gönderir
  2. Claude lessons + post-trade analiz yazar
  3. closed.json'daki lessons alanını günceller
  4. K-kuralı istatistiklerini günceller
  5. Kaynak (Twitter/haber) doğruluğunu kaydeder
  6. Telegram'a bildirim gönderir

Tetikleme:
  - Manuel: python agent/trade_feedback.py --symbol MRVL --portfolio aggressive
  - Otomatik: daily_update.py yeni kapanış tespitinde çağırır (Phase 5)
"""

import json
import sys
import os
import argparse
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from claude_agent import get_claude_decision
from tools import send_private_telegram
from memory_manager import append_learning
from learning_engine import update_k_rule_stats, auto_extract_lessons

REPO_ROOT  = Path(__file__).parent.parent
MEMORY_DIR = Path(__file__).parent / "memory"


# ── Kapanan Trade'i Bul ───────────────────────────────────────────────────────

def find_closed_trade(symbol: str, portfolio: str) -> dict | None:
    """
    closed.json veya portfolios/*.json'da kapanmış trade'i bulur.
    """
    # Önce closed.json'a bak (CANONICAL kapatilan_pozisyonlar)
    closed_path = REPO_ROOT / "data" / "swing" / "closed.json"
    if closed_path.exists():
        with open(closed_path, encoding="utf-8") as f:
            data = json.load(f)
        trades = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))
        for t in reversed(trades):
            if t.get("sembol") == symbol or t.get("symbol") == symbol:
                return t

    # Portfolio transactions'dan bak
    pf_path = REPO_ROOT / "data" / "portfolios" / f"{portfolio}.json"
    if pf_path.exists():
        with open(pf_path, encoding="utf-8") as f:
            pf = json.load(f)
        txns = pf.get("transactions", pf.get("islemler", []))
        sells = [t for t in txns
                 if (t.get("type") == "SELL" or t.get("tur") == "SATIŞ")
                 and t.get("symbol") == symbol]
        if sells:
            return sells[-1]

    return None


# ── Post-Trade Claude Analizi ─────────────────────────────────────────────────

def generate_post_trade_analysis(trade: dict, portfolio: str) -> str:
    """
    Claude'a trade detaylarını gönderip post-trade analiz üretir.
    """
    symbol      = trade.get("sembol") or trade.get("symbol", "?")
    entry_price = trade.get("giris_fiyati") or trade.get("entry_price") or trade.get("price", 0)
    exit_price  = trade.get("cikis_fiyati") or trade.get("exit_price", 0)
    # 29 Nis 2026: closed.json canonical 'kar_zarar_yuzde' ve 'tutulan_gun'.
    pnl_pct     = (
        trade.get("kar_zarar_yuzde")  # canonical
        or trade.get("pnl_yuzde")
        or trade.get("pnl_pct")
        or 0
    )
    hold_days   = (
        trade.get("tutulan_gun")      # canonical
        or trade.get("tutma_suresi")
        or trade.get("hold_days")
        or 0
    )
    exit_reason = trade.get("cikis_nedeni") or trade.get("exit_reason", "Bilinmiyor")
    entry_reason = trade.get("giris_nedeni") or trade.get("entry_reason", "")

    # K-kuralları özetini çek
    digest_path = MEMORY_DIR / "k_rules_digest.md"
    k_rules     = digest_path.read_text(encoding="utf-8") if digest_path.exists() else ""

    prompt = f"""
You are Finzora Agent. A position has just closed — produce a post-trade analysis.

TRADE DETAILS:
  Symbol:       {symbol}
  Portfolio:    {portfolio}
  Entry:        {entry_price}
  Exit:         {exit_price}
  P/L:          %{pnl_pct}
  Hold days:    {hold_days}
  Exit reason:  {exit_reason}
  Entry thesis: {entry_reason}

K-RULES (digest):
{k_rules[:1000]}

Analyze:
1. Which K-rule governed this trade?
2. Was the entry thesis correct? What actually happened?
3. Was the exit decision well-timed?
4. What 1-2 concrete lessons come out of this trade?
5. What should be done differently next time in a similar setup?

Write the answer in Turkish — short and sharp.
Use the evidence tags KESİN / MUHTEMEL / SPEKÜLATİF (Turkish, verbatim).
The final line MUST be exactly: "DERS: [single Turkish sentence summary]"
"""

    return get_claude_decision(prompt, mode="monitor")


# ── closed.json Güncelle ─────────────────────────────────────────────────────

def update_closed_json_lessons(symbol: str, lessons: str) -> bool:
    """
    closed.json'daki ilgili trade'in lessons alanını günceller.
    """
    path = REPO_ROOT / "data" / "swing" / "closed.json"
    if not path.exists():
        return False

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    trades  = data.get("kapatilan_pozisyonlar", data.get("kapali_pozisyonlar", data.get("closed_positions", [])))
    updated = False

    for t in reversed(trades):
        if t.get("sembol") == symbol or t.get("symbol") == symbol:
            t["ders"]                = lessons[:500]          # CANONICAL (dersler değil)
            t["dersler"]             = lessons[:500]          # Backward compat
            t["agent_analiz_tarihi"] = datetime.now().strftime("%Y-%m-%d")
            updated = True
            break

    if updated:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[TradeFeedback] {symbol} lessons güncellendi.")

    return updated


# ── Kapanış Tespiti ───────────────────────────────────────────────────────────

def detect_new_closings(portfolios: dict) -> list[dict]:
    """
    Son 24 saatte kapanan pozisyonları tespit eder.
    daily_update.py çalıştıktan sonra transactions.csv'yi kontrol eder.

    CSV şeması (canonical, 2026-04):
      date, action, symbol, shares, price, total, reason
    Portföy alanı CSV'de yok — aktif portföylere bakarak tespit ederiz.
    """
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if not tx_path.exists():
        return []

    import csv
    from datetime import timedelta

    # Pencere: son 48 saat (sabah + kapanış çift run, hafta sonu boşluğu)
    cutoff = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    closings = []

    # Mevcut portföylerde hangi sembol nerede? — sonrada backward tespit için
    # (satış anında artık portföyde olmadığı için geçmiş işlemleri de düşün)
    sym_to_portfolio = {}
    for pf_name, pf_data in (portfolios or {}).items():
        for pos in pf_data.get("pozisyonlar", []):
            sym = pos.get("sembol") or pos.get("symbol")
            if sym:
                sym_to_portfolio[sym] = pf_name

    with open(tx_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row_date = (row.get("date", "") or "").strip()
            # Canonical kolon: 'action' (SELL/BUY). Geriye uyum: 'type' de kabul et.
            row_action = (row.get("action") or row.get("type") or "").strip().upper()
            if row_date < cutoff:
                continue
            if row_action not in ("SELL", "SATIS", "SATIŞ"):
                continue

            symbol = (row.get("symbol") or "").strip()
            if not symbol:
                continue

            # Portföyü tahmin et: hâlâ aktif portföyde → oradan; değilse 'swing' (büyük ihtimalle)
            # Transaction reason içinde "swing" geçiyorsa swing kabul et.
            reason = (row.get("reason") or "")
            if "swing" in reason.lower():
                portfolio = "swing"
            else:
                portfolio = sym_to_portfolio.get(symbol, "unknown")

            closings.append({
                "symbol":    symbol,
                "portfolio": portfolio,
                "price":     (row.get("price") or 0),
                "date":      row_date,
                "reason":    reason,
            })

    return closings


# ── Ana İşlev ────────────────────────────────────────────────────────────────

def process_trade_feedback(symbol: str, portfolio: str) -> bool:
    """
    Bir trade için tam geri bildirim döngüsünü çalıştırır.
    """
    print(f"[TradeFeedback] {symbol} ({portfolio}) analiz ediliyor...")

    # Trade'i bul
    trade = find_closed_trade(symbol, portfolio)
    if not trade:
        print(f"[TradeFeedback] {symbol} için kapanmış trade bulunamadı.")
        return False

    # 29 Nis 2026 fix: closed.json canonical alan adi 'kar_zarar_yuzde'.
    # Eskiden 'pnl_yuzde' / 'pnl_pct' aranirdi ama bu alanlar yok →
    # 0 donerdi → 'GEV ❌ ZARAR %0' gibi yanlis mesajlar.
    pnl_pct  = (
        trade.get("kar_zarar_yuzde")  # canonical
        or trade.get("pnl_yuzde")
        or trade.get("pnl_pct")
        or 0
    )
    try:
        pnl_pct = float(pnl_pct)
    except (TypeError, ValueError):
        pnl_pct = 0.0
    sonuc    = "✅ KAR" if pnl_pct > 0 else ("⚪ NÖTR" if abs(pnl_pct) < 0.1 else "❌ ZARAR")

    # Claude analizi
    analysis = generate_post_trade_analysis(trade, portfolio)

    # DERS satırını çıkar
    ders = ""
    for line in analysis.split("\n"):
        if line.strip().startswith("DERS:"):
            ders = line.strip()
            break

    # closed.json güncelle
    update_closed_json_lessons(symbol, analysis)

    # Birikimli öğrenmeye ekle
    if ders:
        append_learning(f"{symbol}: {ders}", source="post_trade")

    # K-istatistik güncelle
    exit_reason = (trade.get("cikis_nedeni") or trade.get("exit_reason", "")).lower()
    fake_stats  = {"k_rule_tetik": {}}
    if "stop" in exit_reason:
        fake_stats["k_rule_tetik"]["stop_loss"] = 1
    if "k-11" in exit_reason:
        fake_stats["k_rule_tetik"]["K-11"] = 1
    update_k_rule_stats(fake_stats)

    # Telegram bildirimi
    msg = (
        f"📋 Post-Trade Analiz\n"
        f"{symbol} | {portfolio.upper()} | {sonuc} %{pnl_pct}\n\n"
        f"{analysis[:800]}"
    )
    send_private_telegram(msg)

    print(f"[TradeFeedback] {symbol} tamamlandı.")
    return True


def run_auto_feedback(portfolios: dict):
    """
    Otomatik kapanış tespiti ve geri bildirim döngüsü.
    Sabah/kapanış modunda çağrılır.

    Dedup: agent/memory/processed_closings.json dosyasında işlenmiş (symbol,date)
    tuple'larını tutarız — aynı kapanış iki kez analiz edilmesin.
    """
    closings = detect_new_closings(portfolios)
    if not closings:
        return

    # İşlenmiş kapanışları yükle
    processed_path = MEMORY_DIR / "processed_closings.json"
    processed = {}
    if processed_path.exists():
        try:
            with open(processed_path, encoding="utf-8") as f:
                processed = json.load(f)
        except Exception:
            processed = {}
    processed.setdefault("islenen", [])  # [{symbol, date}]

    islenen_set = {(p["symbol"], p["date"]) for p in processed["islenen"]}

    yeniler = [c for c in closings if (c["symbol"], c["date"]) not in islenen_set]

    if not yeniler:
        print(f"[TradeFeedback] {len(closings)} kapanış tespit edildi, hepsi zaten işlenmiş.")
        return

    print(f"[TradeFeedback] {len(yeniler)} yeni kapanış tespit edildi (toplam {len(closings)}).")

    for c in yeniler:
        ok = process_trade_feedback(c["symbol"], c["portfolio"])
        if ok:
            processed["islenen"].append({"symbol": c["symbol"], "date": c["date"]})

    # Sadece son 200 kaydı tut (dosya sonsuz büyümesin)
    processed["islenen"] = processed["islenen"][-200:]
    with open(processed_path, "w", encoding="utf-8") as f:
        json.dump(processed, f, ensure_ascii=False, indent=2)


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Trade geri bildirimi")
    parser.add_argument("--symbol",    required=True, help="Hisse kodu (ör: MRVL)")
    parser.add_argument("--portfolio", default="aggressive",
                        choices=["aggressive", "balanced", "dividend", "swing"],
                        help="Portföy adı")
    args = parser.parse_args()
    process_trade_feedback(args.symbol, args.portfolio)
