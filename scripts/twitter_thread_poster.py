#!/usr/bin/env python3
"""
Twitter Thread Poster - API v2
Finzora AI Portfolio Management System

Rapor PDF'sinden tweet thread'i oluştur ve paylaş.
Kullanım: python3 scripts/twitter_thread_poster.py --pdf path/to/report.pdf --mode thread
"""

import os
import sys
import json
import time
import argparse
import requests
from typing import List, Optional
from pathlib import Path

# Twitter API v2 endpoint
TWITTER_API_URL = "https://api.twitter.com/2/tweets"

class TwitterThreadPoster:
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.headers = {
            "Authorization": f"Bearer {bearer_token}",
            "Content-Type": "application/json",
        }
    
    def post_tweet(self, text: str, reply_to_id: Optional[str] = None) -> dict:
        """
        Tek bir tweet at.
        
        Args:
            text: Tweet metni (max 280 char)
            reply_to_id: Thread'de reply atıyorsa önceki tweet'in ID'si
        
        Returns:
            API response (tweet ID içerir)
        """
        payload = {
            "text": text,
        }
        
        if reply_to_id:
            payload["reply"] = {
                "in_reply_to_tweet_id": reply_to_id
            }
        
        response = requests.post(
            TWITTER_API_URL,
            json=payload,
            headers=self.headers,
        )
        
        if response.status_code != 201:
            raise Exception(
                f"Tweet atma hatası: {response.status_code}\n"
                f"Cevap: {response.text}"
            )
        
        return response.json()
    
    def post_thread(self, tweets: List[str], delay: float = 1.0) -> List[str]:
        """
        Tweet thread'i sırayla at.
        
        Args:
            tweets: Tweet metinlerinin listesi (sırayla)
            delay: Her tweet arası bekleme süresi (saniye)
        
        Returns:
            Posted tweet ID'leri
        """
        tweet_ids = []
        
        for i, tweet_text in enumerate(tweets):
            print(f"[{i+1}/{len(tweets)}] Atılıyor: {tweet_text[:50]}...")
            
            reply_to_id = tweet_ids[-1] if tweet_ids else None
            response = self.post_tweet(tweet_text, reply_to_id=reply_to_id)
            
            tweet_id = response["data"]["id"]
            tweet_ids.append(tweet_id)
            
            print(f"✓ Tweet atıldı (ID: {tweet_id})")
            
            # Rate limit'i aşmamak için bekleme (opsiyonel)
            if i < len(tweets) - 1:
                time.sleep(delay)
        
        return tweet_ids
    
    def validate_tweets(self, tweets: List[str]) -> bool:
        """
        Tweet'lerin geçerliliğini kontrol et (max 280 char).
        """
        for i, tweet in enumerate(tweets):
            if len(tweet) > 280:
                print(f"⚠️  Tweet {i+1} çok uzun ({len(tweet)} char, max 280)")
                return False
        return True


class TwitterThreadGenerator:
    """
    Rapor yada config'den Twitter thread'i oluştur.
    """
    
    @staticmethod
    def load_threads_from_file(filepath: str) -> List[str]:
        """
        JSON dosyasından thread'i yükle.
        
        Format:
        {
            "threads": [
                "Tweet 1 metni...",
                "Tweet 2 metni..."
            ]
        }
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("threads", [])
    
    @staticmethod
    def load_threads_from_markdown(filepath: str) -> List[str]:
        """
        Markdown dosyasından thread'i yükle.
        Format: ## TWEET N
        """
        tweets = []
        current_tweet = []
        
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith("## TWEET"):
                    if current_tweet:
                        tweets.append("\n".join(current_tweet).strip())
                        current_tweet = []
                elif line.strip() and not line.startswith("#"):
                    current_tweet.append(line.rstrip())
        
        if current_tweet:
            tweets.append("\n".join(current_tweet).strip())
        
        return tweets


def main():
    parser = argparse.ArgumentParser(
        description="Twitter thread'i paylaş"
    )
    parser.add_argument(
        "--source",
        type=str,
        required=True,
        help="Thread kaynağı (JSON veya Markdown dosyası)"
    )
    parser.add_argument(
        "--format",
        type=str,
        choices=["json", "markdown"],
        default="json",
        help="Dosya formatı"
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Tweet'ler arası bekleme süresi (saniye)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Gerçekten atmadan önce preview göster"
    )
    
    args = parser.parse_args()
    
    # Bearer token'ı environment'tan al
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    if not bearer_token:
        print("❌ TWITTER_BEARER_TOKEN environment variable'ı bulunamadı")
        sys.exit(1)
    
    # Thread'i yükle
    generator = TwitterThreadGenerator()
    if args.format == "json":
        tweets = generator.load_threads_from_file(args.source)
    else:
        tweets = generator.load_threads_from_markdown(args.source)
    
    if not tweets:
        print("❌ Tweet bulunamadı")
        sys.exit(1)
    
    print(f"✓ {len(tweets)} tweet yüklendi\n")
    
    # Geçerlilik kontrol
    poster = TwitterThreadPoster(bearer_token)
    if not poster.validate_tweets(tweets):
        print("❌ Bazı tweet'ler çok uzun. Lütfen düzenle.")
        sys.exit(1)
    
    # Preview göster
    print("=" * 60)
    print("THREAD PREVIEW")
    print("=" * 60)
    for i, tweet in enumerate(tweets, 1):
        print(f"\n[{i}/{len(tweets)}] ({len(tweet)} char)")
        print("-" * 60)
        print(tweet)
    print("\n" + "=" * 60)
    
    if args.dry_run:
        print("✓ Dry-run modunda. Tweet'ler atılmadı.")
        sys.exit(0)
    
    # Thread'i at
    response = input("\nThread'i Twitter'a atmak istediğine emin misin? (y/n): ")
    if response.lower() != 'y':
        print("İptal edildi.")
        sys.exit(0)
    
    print("\n" + "=" * 60)
    print("THREAD ATILIYOR...")
    print("=" * 60)
    
    try:
        tweet_ids = poster.post_thread(tweets, delay=args.delay)
        print("\n" + "=" * 60)
        print(f"✓ {len(tweet_ids)} tweet başarıyla atıldı!")
        print("=" * 60)
        
        # İlk tweet'in URL'sini yazdır
        first_tweet_id = tweet_ids[0]
        print(f"\n🔗 Thread URL: https://twitter.com/zeynelgun01/status/{first_tweet_id}")
        
    except Exception as e:
        print(f"\n❌ Hata: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
