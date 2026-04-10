#!/usr/bin/env python3
"""
Finzora Agent — Twitter Sinyal Modülü
=======================================
Takip edilen hesapların tweetlerini çeker, sinyal olarak Claude'a verir.
Memory'de belirtildiği üzere: Bu veri sadece Claude context'ine girer,
raporlara veya JSON'lara YAZILMAZ.

RapidAPI twitter241 kullanır.
"""

import requests
import os
import json
from datetime import datetime, timedelta
import pytz

TR_TZ       = pytz.timezone("Europe/Istanbul")
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "") or "fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7"

# İzlenen Twitter hesapları ve odak alanları
TWITTER_ACCOUNTS = {
    "CheddarFlow":      "options flow, unusual activity",
    "BerkUcmz":         "Türk yatırımcı, teknik analiz",
    "berkdemirkiran_":  "Türk yatırımcı, makro",
    "RyanDetrick":      "makro, piyasa döngüsü",
    "VolSignals":       "volatilite, VIX",
    "Jake__Wujastyk":   "teknik analiz, momentum",
    "StockSavvyShay":   "swing trade, momentum",
    "onestoploss":      "risk yönetimi",
}

# Öncelikli hesaplar (her çağrıda bunları al, diğerlerini döngüsel)
PRIORITY_ACCOUNTS = ["CheddarFlow", "RyanDetrick", "VolSignals"]


def get_user_tweets(username: str, limit: int = 3) -> list[dict]:
    """search-v2 ile hesabın son tweetlerini çeker."""
    try:
        r = requests.get(
            "https://twitter241.p.rapidapi.com/search-v2",
            headers={
                "X-RapidAPI-Key":  RAPIDAPI_KEY,
                "X-RapidAPI-Host": "twitter241.p.rapidapi.com",
            },
            params={
                "query": f"from:{username}",
                "type":  "Latest",
                "count": str(limit * 2),
            },
            timeout=10,
        ).json()

        entries = (
            r.get("result", {})
             .get("timeline", {})
             .get("instructions", [{}])[0]
             .get("entries", [])
        )

        tweets = []
        for entry in entries:
            content = (
                entry.get("content", {})
                     .get("itemContent", {})
                     .get("tweet_results", {})
                     .get("result", {})
            )
            legacy = content.get("legacy", {})
            text   = legacy.get("full_text", "")

            if not text or text.startswith("RT @"):
                continue

            tweets.append({
                "hesap":  username,
                "tweet":  text[:280],
                "tarih":  legacy.get("created_at", "")[:16],
                "begeni": legacy.get("favorite_count", 0),
                "rt":     legacy.get("retweet_count", 0),
            })

            if len(tweets) >= limit:
                break

        return tweets

    except Exception as e:
        print(f"[Twitter] {username} hatası: {e}")
        return []


def get_combined_tweets(accounts: list[str], limit: int = 10) -> list[dict]:
    """
    Birden fazla hesabı tek sorguda çeker — API limiti tasarrufu.
    """
    query = " OR ".join(f"from:{acc}" for acc in accounts[:5])
    try:
        r = requests.get(
            "https://twitter241.p.rapidapi.com/search-v2",
            headers={
                "X-RapidAPI-Key":  RAPIDAPI_KEY,
                "X-RapidAPI-Host": "twitter241.p.rapidapi.com",
            },
            params={"query": query, "type": "Latest", "count": str(limit * 2)},
            timeout=12,
        ).json()

        entries = (
            r.get("result", {})
             .get("timeline", {})
             .get("instructions", [{}])[0]
             .get("entries", [])
        )

        tweets = []
        for entry in entries:
            content = (
                entry.get("content", {})
                     .get("itemContent", {})
                     .get("tweet_results", {})
                     .get("result", {})
            )
            legacy  = content.get("legacy", {})
            text    = legacy.get("full_text", "")
            screen  = (
                content.get("core", {})
                       .get("user_results", {})
                       .get("result", {})
                       .get("legacy", {})
                       .get("screen_name", "?")
            )

            if not text or text.startswith("RT @"):
                continue

            tweets.append({
                "hesap":  screen,
                "tweet":  text[:280],
                "tarih":  legacy.get("created_at", "")[:16],
                "begeni": legacy.get("favorite_count", 0),
                "rt":     legacy.get("retweet_count", 0),
            })

            if len(tweets) >= limit:
                break

        return tweets

    except Exception as e:
        print(f"[Twitter] Kombine sorgu hatası: {e}")
        return []


def extract_tickers_from_tweet(text: str) -> list[str]:
    """Tweet metninden $TICKER formatındaki hisse kodlarını çıkarır."""
    import re
    tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
    return list(set(tickers))


def build_twitter_context(portfolio_symbols: list[str] = None) -> str:
    """
    Tüm hesapları 2 API çağrısında çeker:
    1. Öncelikli hesaplar (piyasa rejimi sinyalleri)
    2. Portföy sembolü geçen tweetler
    """
    if not RAPIDAPI_KEY:
        return "=== TWITTER === RapidAPI key bulunamadı.\n"

    print("[Twitter] Tweetler çekiliyor...")

    sym_set    = set(s.upper() for s in (portfolio_symbols or []))
    all_tweets = []

    # Çağrı 1: Öncelikli hesaplar
    priority_tweets = get_combined_tweets(PRIORITY_ACCOUNTS, limit=8)
    all_tweets.extend(priority_tweets)

    # Çağrı 2: Diğer hesaplar
    other_accounts = [a for a in TWITTER_ACCOUNTS if a not in PRIORITY_ACCOUNTS]
    other_tweets   = get_combined_tweets(other_accounts[:5], limit=6)

    # Portföy sembolü geçenleri işaretle
    for t in other_tweets:
        tickers = extract_tickers_from_tweet(t["tweet"])
        if any(tk in sym_set for tk in tickers):
            t["portfoy_eslesmesi"] = [tk for tk in tickers if tk in sym_set]
            all_tweets.append(t)

    if not all_tweets:
        return "=== TWITTER === Veri alınamadı.\n"

    # Portföy eşleşmelerini + beğeni sayısını öne al
    all_tweets.sort(key=lambda t: (
        -len(t.get("portfoy_eslesmesi", [])),
        -(t.get("begeni", 0) + t.get("rt", 0) * 3),
    ))

    lines = ["=== TWITTER SİNYALLERİ (SPEKÜLATİF kaynak) ===\n"]
    for t in all_tweets[:10]:
        eslesme = ""
        if t.get("portfoy_eslesmesi"):
            eslesme = f" [PORTFÖYde: {', '.join(t['portfoy_eslesmesi'])}]"
        lines.append(
            f"@{t['hesap']}{eslesme}\n"
            f"  {t['tweet'][:200]}\n"
            f"  ❤️{t['begeni']} 🔄{t['rt']}\n"
        )

    print(f"[Twitter] {len(all_tweets)} tweet işlendi.")
    return "\n".join(lines)
