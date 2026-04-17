#!/usr/bin/env python3
"""
Finzora Agent — Web Araştırma Modülü
======================================
Haber, makro takvim, earnings, insider verisi çeker.
Claude'a tool_use yerine ham veri olarak gönderilir → ucuz.
"""

import requests
import json
from datetime import datetime, timedelta
from pathlib import Path
import pytz

TR_TZ    = pytz.timezone("Europe/Istanbul")
FMP_KEY  = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"


# ── Haber Çekme ───────────────────────────────────────────────────────────────

def get_market_news(limit: int = 8) -> list[dict]:
    """
    FMP'den genel piyasa haberlerini çeker.
    Son 8 haber, başlık + özet.
    """
    try:
        r = requests.get(
            f"{FMP_BASE}/fmp-articles",
            params={"apikey": FMP_KEY, "limit": limit},
            timeout=10,
        ).json()

        news = []
        for item in r[:limit]:
            news.append({
                "baslik": item.get("title", ""),
                "ozet":   item.get("text", "")[:200],
                "kaynak": item.get("site", ""),
                "tarih":  item.get("publishedDate", "")[:16],
                "sembol": item.get("symbol", ""),
            })
        return news
    except Exception as e:
        print(f"[WebResearch] Haber hatası: {e}")
        return []


def get_stock_news(symbols: list[str], limit: int = 3) -> list[dict]:
    """Portföydeki hisselere ait haberleri çeker."""
    if not symbols:
        return []
    try:
        r = requests.get(
            f"{FMP_BASE}/news/stock-latest",
            params={
                "apikey":  FMP_KEY,
                "symbols": ",".join(symbols[:10]),
                "limit":   limit * len(symbols[:5]),
            },
            timeout=10,
        ).json()

        news = []
        for item in r[:limit * 3]:
            news.append({
                "sembol": item.get("symbol", ""),
                "baslik": item.get("title", ""),
                "ozet":   item.get("text", "")[:150],
                "tarih":  item.get("publishedDate", "")[:16],
            })
        return news
    except Exception as e:
        print(f"[WebResearch] Hisse haberi hatası: {e}")
        return []


# ── Earnings Takvimi ──────────────────────────────────────────────────────────

def get_upcoming_earnings(symbols: list[str]) -> list[dict]:
    """
    Portföydeki hisselerin yaklaşan earnings tarihlerini çeker.
    K-05 için kritik: 2 gün öncesinde swing kapatılmalı.
    """
    if not symbols:
        return []

    today    = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    in_week  = (datetime.now(TR_TZ) + timedelta(days=7)).strftime("%Y-%m-%d")

    try:
        r = requests.get(
            f"{FMP_BASE}/earnings-calendar",
            params={
                "apikey": FMP_KEY,
                "from":   today,
                "to":     in_week,
            },
            timeout=10,
        ).json()

        sym_set  = set(s.upper() for s in symbols)
        upcoming = []
        for item in r:
            if item.get("symbol", "").upper() in sym_set:
                earnings_date = item.get("date", "")
                days_left     = None
                if earnings_date:
                    try:
                        ed        = datetime.strptime(earnings_date, "%Y-%m-%d")
                        days_left = (ed - datetime.now(TR_TZ).replace(tzinfo=None)).days
                    except ValueError:
                        pass

                upcoming.append({
                    "sembol":    item.get("symbol"),
                    "tarih":     earnings_date,
                    "gun_kaldi": days_left,
                    "eps_tahmin": item.get("epsEstimated"),
                    "uyari":     "⚠️ K-05: 2 gün içinde earnings!" if days_left is not None and days_left <= 2 else "",
                })

        return sorted(upcoming, key=lambda x: x.get("gun_kaldi") or 99)
    except Exception as e:
        print(f"[WebResearch] Earnings hatası: {e}")
        return []


# ── Makro Takvim ──────────────────────────────────────────────────────────────

def get_macro_calendar() -> list[dict]:
    """
    Yaklaşan makro olaylar: Fed, CPI, NFP vb.
    FMP economic calendar endpoint.
    """
    today   = datetime.now(TR_TZ).strftime("%Y-%m-%d")
    in_week = (datetime.now(TR_TZ) + timedelta(days=5)).strftime("%Y-%m-%d")

    try:
        r = requests.get(
            f"{FMP_BASE}/economic-calendar",
            params={
                "apikey": FMP_KEY,
                "from":   today,
                "to":     in_week,
            },
            timeout=10,
        ).json()

        # Sadece yüksek etkili olayları al
        high_impact_keywords = [
            "Fed", "FOMC", "CPI", "NFP", "GDP", "PCE",
            "Unemployment", "Rate Decision", "Inflation",
            "Jobs", "PPI", "Retail Sales"
        ]

        events = []
        for item in r:
            event = item.get("event", "")
            if any(kw.lower() in event.lower() for kw in high_impact_keywords):
                events.append({
                    "olay":   event,
                    "tarih":  item.get("date", "")[:16],
                    "ulke":   item.get("country", ""),
                    "etki":   item.get("impact", ""),
                    "onceki": item.get("previous"),
                    "tahmin": item.get("estimate"),
                })

        return events[:5]
    except Exception as e:
        print(f"[WebResearch] Makro takvim hatası: {e}")
        return []


# ── Insider Tarama ────────────────────────────────────────────────────────────

def get_insider_activity(symbols: list[str]) -> list[dict]:
    """
    Portföydeki hisselerde son insider işlemleri.
    K-18: Yeni giriş öncesi insider kontrol zorunlu.
    """
    if not symbols:
        return []

    activities = []
    for sym in symbols[:8]:  # Max 8 sembol
        try:
            r = requests.get(
                f"{FMP_BASE}/insider-trading",
                params={
                    "apikey": FMP_KEY,
                    "symbol": sym,
                    "limit":  3,
                },
                timeout=8,
            ).json()

            for item in r[:2]:
                transaction_type = item.get("transactionType", "")
                shares           = item.get("securitiesTransacted", 0)
                value            = (shares or 0) * (item.get("price") or 0)

                # Büyük satışları işaretle (K-17/K-18)
                uyari = ""
                if "Sale" in transaction_type and value > 1_000_000:
                    uyari = f"⚠️ BÜYÜK INSIDER SATIŞI: ${value/1e6:.1f}M"

                activities.append({
                    "sembol":    sym,
                    "islem":     transaction_type,
                    "kisi":      item.get("reportingName", ""),
                    "adet":      shares,
                    "deger_usd": round(value),
                    "tarih":     item.get("transactionDate", "")[:10],
                    "uyari":     uyari,
                })
        except Exception:
            continue

    return activities


# ── Araştırma Özeti ───────────────────────────────────────────────────────────

def build_research_context(portfolio_symbols: list[str]) -> str:
    """
    Tüm araştırma verilerini tek string'e dönüştürür.
    Claude'un context'ine eklenir.
    """
    print("[WebResearch] Veriler çekiliyor...")

    news          = get_market_news(limit=6)
    stock_news    = get_stock_news(portfolio_symbols, limit=2)
    earnings      = get_upcoming_earnings(portfolio_symbols)
    macro         = get_macro_calendar()
    insider       = get_insider_activity(portfolio_symbols[:6])

    lines = ["=== ARAŞTIRMA VERİLERİ ===\n"]

    # Makro takvim
    if macro:
        lines.append("--- MAKRO TAKVİM (önümüzdeki 5 gün) ---")
        for e in macro:
            lines.append(f"  {e['tarih']} | {e['olay']} | Etki: {e['etki']} | Tahmin: {e['tahmin']} | Önceki: {e['onceki']}")
        lines.append("")

    # Earnings
    if earnings:
        lines.append("--- YAKLAŞAN EARNINGS ---")
        for e in earnings:
            uyari = f" {e['uyari']}" if e['uyari'] else ""
            lines.append(f"  {e['sembol']}: {e['tarih']} ({e['gun_kaldi']} gün){uyari}")
        lines.append("")

    # Piyasa haberleri
    if news:
        lines.append("--- PİYASA HABERLERİ ---")
        for n in news[:5]:
            lines.append(f"  [{n['tarih']}] {n['baslik']}")
        lines.append("")

    # Hisse haberleri
    if stock_news:
        lines.append("--- PORTFÖYDEKİ HİSSE HABERLERİ ---")
        for n in stock_news[:6]:
            lines.append(f"  {n['sembol']} [{n['tarih']}]: {n['baslik']}")
        lines.append("")

    # Insider
    insider_uyari = [i for i in insider if i.get("uyari")]
    if insider_uyari:
        lines.append("--- ⚠️ KRİTİK INSIDER UYARILARI ---")
        for i in insider_uyari:
            lines.append(f"  {i['sembol']}: {i['uyari']} | {i['kisi']} | {i['tarih']}")
        lines.append("")

    print(f"[WebResearch] Tamamlandı: {len(news)} haber, {len(earnings)} earnings, {len(macro)} makro olay")
    return "\n".join(lines)
