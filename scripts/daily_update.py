#!/usr/bin/env python3
"""
OTOMATIK GÜNLÜK FİYAT GÜNCELLEMESİ
Her gün piyasa kapanışında çalıştırılmalı (NYSE kapanış: TR 23:00)
Tüm portföyleri, swing trade'leri, watchlist'i günceller
"""

import json
import os
import sys
import requests
import sys as _sys
_sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from event_logger import log as _log
    _log.kaynak = "daily_update"
except ImportError:
    class _FallbackLog:
        kaynak = "daily_update"
        def __getattr__(self, n): return lambda *a, **kw: None
    _log = _FallbackLog()
from datetime import datetime, timedelta, timezone
import subprocess
from pathlib import Path

# ====== KONFIGURASYON ======
FMP_API_KEY = os.environ.get("FMP_API_KEY", "")
FMP_BASE = "https://financialmodelingprep.com/stable"
REPO_ROOT = Path(__file__).parent.parent  # portfolio-tracker kök dizini

# Dosya yolları
BALANCED_JSON = REPO_ROOT / "data/portfolios/balanced.json"
AGGRESSIVE_JSON = REPO_ROOT / "data/portfolios/aggressive.json"
DIVIDEND_JSON = REPO_ROOT / "data/portfolios/dividend.json"
SWING_ACTIVE_JSON = REPO_ROOT / "data/swing/active.json"
WATCHLIST_JSON = REPO_ROOT / "data/watchlist.json"
SUMMARY_JSON = REPO_ROOT / "data/summary.json"
LOG_FILE = REPO_ROOT / "logs/daily_update.log"

# ====== YARDIMCI FONKSİYONLAR ======

def log(message):
    """Log mesajını hem konsola hem dosyaya yaz"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{timestamp}] {message}"
    print(log_msg)
    
    # Log klasörünü oluştur
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_msg + '\n')


def fmp_get(endpoint, params=None):
    """FMP API'den veri çek"""
    if params is None:
        params = {}
    params['apikey'] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if isinstance(data, dict) and 'Error Message' in data:
            log(f"❌ FMP Error: {data['Error Message']}")
            return None
        
        return data
    except requests.exceptions.RequestException as e:
        log(f"❌ Request failed for {endpoint}: {e}")
        return None


def get_batch_quotes(symbols):
    """Birden fazla sembol için fiyat çek"""
    symbols_str = ','.join(symbols)
    log(f"📊 Batch quote çekiliyor: {len(symbols)} sembol")
    
    quotes = fmp_get("batch-quote", {"symbols": symbols_str})
    
    if not quotes:
        log("❌ Batch quote başarısız!")
        return {}
    
    # Dict'e dönüştür (sembol -> quote)
    quote_dict = {q['symbol']: q for q in quotes}
    log(f"✅ {len(quote_dict)} sembol fiyatı alındı")
    
    return quote_dict


def load_json(filepath):
    """JSON dosyasını yükle"""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        log(f"⚠️  Dosya bulunamadı: {filepath}")
        return None
    except json.JSONDecodeError as e:
        log(f"❌ JSON parse hatası {filepath}: {e}")
        return None


def save_json(filepath, data):
    """JSON dosyasını kaydet"""
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        log(f"💾 Kaydedildi: {filepath.name}")
        return True
    except Exception as e:
        log(f"❌ Kaydetme hatası {filepath}: {e}")
        return False


# ====== 3 FAZLI PORTFÖY STOP KONFİGURASYONU ======
# Faz 1: Giriş tamponu (geniş ATR stop — tez kanıtlanana kadar)
# Faz 2: Başa baş (breakeven) — yeterli kâr sonrası stop = maliyet_baz
# Faz 3: İzleyen (trailing) — MA veya chandelier ile trend takibi
STOP_CONFIG = {
    "dengeli": {
        "faz1_katsayi":      3.0,
        "atr_period":        21,
        "faz2_tetik_pct":    5.0,   # %5 kârda başa baş geçiş
        "max_kayip_pct":     0.12,  # Stop asla girişin %12'sinden aşağı gidemez (ATR şişmesi koruması)
        "faz3_yontem":       "sma",
        "faz3_sma_period":   50,
        "faz3_sma_buffer":   0.98,
    },
    "agresif": {
        "faz1_katsayi":      3.0,
        "atr_period":        21,
        "faz2_tetik_pct":    7.0,   # %7 kârda başa baş geçiş
        "max_kayip_pct":     0.18,  # Stop asla girişin %18'inden aşağı gidemez
        "faz3_yontem":       "chandelier",
        "faz3_chan_period":  20,
        "faz3_chan_katsayi": 3.5,
    },
    "temettü": {
        "faz1_katsayi":      2.5,
        "atr_period":        21,
        "faz2_tetik_pct":    4.0,   # %4 kârda başa baş geçiş
        "max_kayip_pct":     0.10,  # Stop asla girişin %10'undan aşağı gidemez
        "faz3_yontem":       "sma",
        "faz3_sma_period":   100,
        "faz3_sma_buffer":   0.985,
    }
}

# Temettü kesintisi ve kritik haber anahtar kelimeleri
TEMETTÜ_KESINTI_KW = [
    "dividend cut", "cuts dividend", "reduces dividend", "suspends dividend",
    "eliminates dividend", "dividend suspension", "dividend reduction",
    "cuts its dividend", "slashes dividend", "halves dividend",
    "dividend eliminated", "dividend suspended", "reduced its dividend",
    "suspend its dividend", "eliminate its dividend",
]
KRITIK_HABER_KW = [
    "bankruptcy", "bankrupt", "fraud", "sec investigation", "going concern",
    "class action", "accounting irregularity", "delist", "delisted",
    "restatement", "material weakness",
]


def calculate_atr21(symbol, period=21):
    """ATR(period) — historical OHLCV'den manuel hesap. FMP endpoint bağımsız.
    limit=period+20 ile yeterli veri garanti altında; from_date kullanılmaz
    (from+limit birlikte FMP'de bazen beklenenden az kayıt döndürür).
    """
    data = fmp_get("historical-price-eod/full", {
        "symbol": symbol,
        "limit": period + 20,   # 21+20=41 — hafta sonu/tatil tampon dahil
    })
    if not data or not isinstance(data, list) or len(data) < period + 1:
        return None
    # FMP yeniden eskiye sıralar → ters çevir (eskiden yeniye)
    data_asc = sorted(data, key=lambda x: x.get("date", ""))
    true_ranges = []
    for i in range(1, len(data_asc)):
        c = data_asc[i]
        p = data_asc[i - 1]
        hi = c.get("high") or 0
        lo = c.get("low") or 0
        pc = p.get("close") or 0
        if not (hi and lo and pc):
            continue
        tr = max(hi - lo, abs(hi - pc), abs(lo - pc))
        true_ranges.append(tr)
    if len(true_ranges) >= period:
        return round(sum(true_ranges[-period:]) / period, 4)
    return None


def get_sma_value(symbol, period):
    """SMA(period) — FMP technical indicator, son değer."""
    data = fmp_get("technical-indicators/sma", {
        "symbol": symbol,
        "periodLength": period,
        "timeframe": "1day",
    })
    if data and isinstance(data, list) and data:
        return data[0].get("sma")
    return None


def _portfoy_turu(filepath):
    """Dosya adından portföy türünü döndür."""
    name = Path(filepath).stem  # balanced / aggressive / dividend
    return {"balanced": "dengeli", "aggressive": "agresif", "dividend": "temettü"}.get(name)


def hesapla_portfoy_stop(pos, portfoy_turu, current_price):
    """
    3 Fazlı stop hesaplama.
    Döndürür: (yeni_stop_loss, yeni_faz) | (None, None) hata durumunda.
    Stop asla aşağı çekilmez — sadece yukarı.
    """
    cfg = STOP_CONFIG.get(portfoy_turu)
    if not cfg:
        return None, None

    sembol       = pos["sembol"]
    maliyet      = pos.get("maliyet_baz", 0)
    mevcut_stop  = pos.get("stop_loss", 0) or 0
    mevcut_faz   = pos.get("stop_faz", 0)   # 0 = henüz hesaplanmamış

    if not maliyet or not current_price:
        return None, None

    pnl_pct = ((current_price - maliyet) / maliyet) * 100

    # ── FAZ 1 İLK KURULUM ──────────────────────────────────────────────────
    # Faz 0: Mevcut P&L'e göre doğru faza doğrudan gir.
    # Önemli: Uzun süredir tutulmuş pozisyonlar zaten Faz 2/3 eşiğini geçmiş olabilir.
    # max_kayip_pct: kriz ATR şişmesini önler (COHR ATR$22 → stop %30 aşağı gibi durumlar).
    if mevcut_faz == 0:
        atr = calculate_atr21(sembol, cfg["atr_period"])
        if not atr:
            return mevcut_stop, 0   # ATR çekilemedi — değiştirme

        # P&L yeterince yüksekse Faz 2/3'e atla
        if pnl_pct >= cfg["faz2_tetik_pct"]:
            # Floor: maliyet_baz ve eski manuel stop'un en iyisi (stop hiç gerilememeli)
            floor = max(round(maliyet, 2), mevcut_stop)
            # Faz 3: izleyen stop ile başla
            if cfg["faz3_yontem"] == "sma":
                sma = get_sma_value(sembol, cfg["faz3_sma_period"])
                if sma:
                    trailing = round(sma * cfg["faz3_sma_buffer"], 2)
                    return max(trailing, floor), 3
            elif cfg["faz3_yontem"] == "chandelier":
                zirve = max(pos.get("zirve_fiyat", current_price), current_price)
                katsayi = cfg["faz3_chan_katsayi"]
                if pnl_pct >= 30:
                    katsayi = 2.5
                trailing = round(zirve - atr * katsayi, 2)
                return max(trailing, floor), 3
            # SMA/chandelier verisi yoksa başa baş ile Faz 2'de başla
            return floor, 2

        # Normal Faz 1: ATR stop + cap
        faz1_stop_atr = round(maliyet - atr * cfg["faz1_katsayi"], 2)
        min_stop      = round(maliyet * (1 - cfg["max_kayip_pct"]), 2)
        faz1_stop     = max(faz1_stop_atr, min_stop)
        return round(faz1_stop, 2), 1

    # ── FAZ 2 TETİK: yeterli kâr → başa baş ───────────────────────────────
    if mevcut_faz == 1 and pnl_pct >= cfg["faz2_tetik_pct"]:
        basbas = round(maliyet, 2)
        return max(basbas, mevcut_stop), 2

    # ── FAZ 1: Stop sabit kal (sadece yukarı gidebilir, orijinal ATR stop) ─
    if mevcut_faz == 1:
        return mevcut_stop, 1

    # ── FAZ 3: İzleyen stop ────────────────────────────────────────────────
    if mevcut_faz >= 2:
        if cfg["faz3_yontem"] == "sma":
            sma = get_sma_value(sembol, cfg["faz3_sma_period"])
            if sma:
                trailing = round(sma * cfg["faz3_sma_buffer"], 2)
                return max(trailing, mevcut_stop), 3

        elif cfg["faz3_yontem"] == "chandelier":
            atr = calculate_atr21(sembol, cfg["atr_period"])
            zirve = max(pos.get("zirve_fiyat", current_price), current_price)
            if atr:
                katsayi = cfg["faz3_chan_katsayi"]
                if pnl_pct >= 30:    # K-11 v3 Tier 1 uyumu
                    katsayi = 2.5
                trailing = round(zirve - atr * katsayi, 2)
                return max(trailing, mevcut_stop), 3

        return mevcut_stop, mevcut_faz  # Veri yoksa mevcut stop'u koru

    return mevcut_stop, mevcut_faz


# ====== TEMELTTü KESİNTİSİ VE KRİTİK HABER İZLEME ======

def send_telegram_direct(message, severity="warning"):
    """Telegram'a direkt bildirim gönder (telegram_notify.py üzerinden).
    severity: 'critical' → --type alert, 'warning'/'info' → --type custom
    """
    try:
        notify_script = Path(__file__).parent / "telegram_notify.py"
        t_type = "alert" if severity == "critical" else "custom"
        result = subprocess.run(
            ["python3", str(notify_script), "--type", t_type, "--msg", message],
            timeout=15, capture_output=True, text=True
        )
        if result.returncode != 0:
            log(f"  ⚠️  Telegram script hata kodu {result.returncode}: {result.stderr[:200]}")
    except Exception as e:
        log(f"  ⚠️  Telegram gönderim hatası: {e}")


def temettu_ve_kritik_haber_kontrolu(portfoy_semboller):
    """
    Tüm portföy hisselerinin son 48 saatlik haberlerini tara.
    Temettü kesintisi veya kritik olumsuz haber varsa Telegram'a gönder.
    Günlük otomatik güncelleme sırasında çalışır.

    Dedup: işlenmiş haber URL'leri data/news_seen.json'a kaydedilir,
    aynı haber iki kez Telegram'a düşmez (sabah + kapanış run'larında).
    """
    if not portfoy_semboller:
        return

    log(f"\n📰 Haber taraması: {', '.join(sorted(portfoy_semboller))}")
    symbols_str = ",".join(portfoy_semboller)
    haberler = fmp_get("news/stock", {"symbols": symbols_str, "limit": 60})

    if not haberler:
        log("  ⚠️  FMP haber çekilemedi")
        return

    sinir_dt = datetime.now(timezone.utc) - timedelta(hours=48)

    # İşlenmiş haber cache'i — URL hash'leri
    seen_path = REPO_ROOT / "data" / "news_seen.json"
    seen = {"urls": [], "updated": ""}
    if seen_path.exists():
        try:
            seen = json.loads(seen_path.read_text(encoding="utf-8"))
        except Exception:
            seen = {"urls": [], "updated": ""}
    seen_set = set(seen.get("urls", []))

    uyarilar = []
    for h in haberler:
        # Tarih filtresi
        try:
            pub_str = h.get("publishedDate", "")
            if "T" in pub_str:
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            else:
                pub_dt = datetime.strptime(pub_str[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if pub_dt < sinir_dt:
                continue
        except Exception:
            continue

        url = h.get("url", "") or ""
        # Dedup — bu URL daha önce işlendiyse atla
        if url and url in seen_set:
            continue

        baslik    = (h.get("title", "") or "").lower()
        icerik    = (h.get("text", "") or "")[:600].lower()
        tam_metin = baslik + " " + icerik
        sembol    = h.get("symbol", "")
        tetiklendi = False   # Bir haber için tek uyarı gönder

        # Temettü kesintisi — öncelikli kontrol
        for kw in TEMETTÜ_KESINTI_KW:
            if kw in tam_metin:
                uyarilar.append({
                    "sembol": sembol, "tur": "TEMETTÜ KESİNTİSİ",
                    "baslik": h.get("title", "")[:200],
                    "url": url, "severity": "critical",
                })
                if url:
                    seen_set.add(url)
                tetiklendi = True
                break

        # Kritik haber — temettü uyarısı verildiyse atla (çift mesaj önleme)
        if not tetiklendi:
            for kw in KRITIK_HABER_KW:
                if kw in tam_metin:
                    uyarilar.append({
                        "sembol": sembol, "tur": "KRİTİK HABER",
                        "baslik": h.get("title", "")[:200],
                        "url": url, "severity": "warning",
                    })
                    if url:
                        seen_set.add(url)
                    break

    # Cache'i güncelle — sadece son 500 URL tut (dosya büyümesin)
    seen["urls"]    = list(seen_set)[-500:]
    seen["updated"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    try:
        seen_path.write_text(json.dumps(seen, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        log(f"  ⚠️  news_seen.json yazımı atlandı: {e}")

    if uyarilar:
        for u in uyarilar:
            msg = (
                f"🚨 {u['tur']}: {u['sembol']}\n"
                f"Başlık: {u['baslik']}\n"
                f"Link: {u['url']}"
            )
            log(f"  🚨 {u['tur']} — {u['sembol']}: {u['baslik'][:80]}")
            send_telegram_direct(msg, severity=u["severity"])
    else:
        log(f"  ✅ Yeni kritik haber yok ({len(haberler)} haber tarandı, son 48 saat, dedup aktif)")


def update_portfolio(filepath, quote_dict):
    """Bir portföy dosyasını güncelle"""
    portfolio = load_json(filepath)
    if not portfolio:
        return False
    
    portfolio_name = portfolio.get('portfoy_adi', filepath.stem)
    log(f"\n📂 {portfolio_name} güncelleniyor...")

    now = datetime.now().isoformat()
    updated_count = 0
    p_turu = _portfoy_turu(filepath)   # Döngü dışında bir kez hesapla

    for pos in portfolio.get('pozisyonlar', []):
        symbol = pos['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = pos.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        # Fiyatları güncelle
        pos['guncel_fiyat'] = new_price
        # changesPercentage piyasa dışında 0 döner — manuel hesap öncelikli
        prev_close = quote.get('previousClose', 0)
        if prev_close and prev_close > 0:
            pos['gunluk_degisim_yuzde'] = round(((new_price - prev_close) / prev_close) * 100, 2)
        else:
            pos['gunluk_degisim_yuzde'] = quote.get('changesPercentage', 0)
        
        # Hesaplamaları güncelle
        pos['guncel_deger'] = round(pos['adet'] * new_price, 2)
        pos['yatirim'] = round(pos['adet'] * pos['maliyet_baz'], 2)
        pos['kar_zarar'] = round(pos['guncel_deger'] - pos['yatirim'], 2)
        pos['kar_zarar_yuzde'] = round((pos['kar_zarar'] / pos['yatirim']) * 100, 2)
        pos['son_guncelleme'] = now

        # Zirve fiyat takibi (Faz 3 chandelier için)
        if new_price > pos.get('zirve_fiyat', 0):
            pos['zirve_fiyat'] = new_price

        # ── 3 FAZLI STOP GÜNCELLEMESİ ──────────────────────────────────
        if p_turu:
            eski_stop = pos.get('stop_loss', 0) or 0
            eski_faz  = pos.get('stop_faz', 0)
            yeni_stop, yeni_faz = hesapla_portfoy_stop(pos, p_turu, new_price)
            if yeni_stop is not None:
                pos['stop_loss'] = yeni_stop
                pos['stop_faz']  = yeni_faz
                faz_ad = {1: "Giriş Tamponu", 2: "Başa Baş", 3: "İzleyen"}
                if yeni_faz != eski_faz:
                    log(f"    📍 {symbol} STOP FAZ {eski_faz}→{yeni_faz} "
                        f"({faz_ad.get(yeni_faz,'?')}): ${eski_stop:.2f} → ${yeni_stop:.2f}")
                elif abs(yeni_stop - eski_stop) > 0.01:
                    log(f"    🔄 {symbol} stop: ${eski_stop:.2f} → ${yeni_stop:.2f} (Faz {yeni_faz})")

        # Stop mesafesi ve durum
        aktif_stop = pos.get('stop_loss', 0) or 0
        if aktif_stop > 0 and new_price > 0:
            stop_mesafe = ((new_price - aktif_stop) / new_price) * 100
            pos['stop_mesafe_pct'] = round(stop_mesafe, 2)
            if new_price <= aktif_stop:
                pos['durum'] = "🔴 STOP-LOSS TETİKLENDİ!"
            elif stop_mesafe <= 3:
                pos['durum'] = f"⚠️ Stop yakın ({stop_mesafe:.1f}%)"
            elif pos.get('kar_zarar_yuzde', 0) >= 20:
                pos['durum'] = f"🚀 Güçlü (+{pos['kar_zarar_yuzde']:.1f}%)"
            else:
                pos['durum'] = "✅ Normal"
        # ────────────────────────────────────────────────────────────────

        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        stop_info = f" | stop ${aktif_stop:.2f} Faz{pos.get('stop_faz',0)}" if aktif_stop else ""
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%) | P&L {pos['kar_zarar_yuzde']:+.1f}%{stop_info}")
        updated_count += 1
    
    # Toplam değer hesapla
    total_position_value = sum(pos['guncel_deger'] for pos in portfolio['pozisyonlar'])
    cash = portfolio.get('nakit', {}).get('miktar', 0)
    portfolio['toplam_deger'] = round(total_position_value + cash, 2)
    
    # Toplam getiri hesapla
    starting_capital = portfolio.get('baslangic_sermaye', 100000)
    portfolio['toplam_getiri'] = round(portfolio['toplam_deger'] - starting_capital, 2)
    portfolio['toplam_getiri_yuzde'] = round(
        ((portfolio['toplam_deger'] - starting_capital) / starting_capital) * 100, 2
    )
    
    # Ağırlıkları yeniden hesapla
    for pos in portfolio['pozisyonlar']:
        pos['agirlik_yuzde'] = round(
            (pos['guncel_deger'] / portfolio['toplam_deger']) * 100, 2
        )
    
    # Nakit ağırlığını güncelle
    if 'nakit' in portfolio:
        portfolio['nakit']['agirlik_yuzde'] = round(
            (portfolio['nakit']['miktar'] / portfolio['toplam_deger']) * 100, 2
        )
    
    portfolio['son_guncelleme'] = now
    
    log(f"  💰 Toplam değer: ${portfolio['toplam_deger']:,.2f} ({portfolio['toplam_getiri_yuzde']:+.2f}%)")
    log(f"  📊 {updated_count}/{len(portfolio['pozisyonlar'])} pozisyon güncellendi")
    
    return save_json(filepath, portfolio)


def update_swing_trades(quote_dict):
    """Swing trade pozisyonlarını güncelle"""
    swing = load_json(SWING_ACTIVE_JSON)
    if not swing:
        return False
    
    log(f"\n🎯 Swing Trade güncelleniyor...")
    
    now = datetime.now().isoformat()
    today = datetime.now().date()
    updated_count = 0
    
    for pos in swing.get('aktif_pozisyonlar', []):
        symbol = pos['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = pos.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        # Fiyat güncelle
        pos['guncel_fiyat'] = new_price
        pos['son_fiyat'] = new_price
        
        # Kar/zarar hesapla — giris_fiyat (JSON'daki alan adı)
        entry_price = pos.get('giris_fiyat', pos.get('giris_fiyati', 0))
        pnl_pct = round(((new_price - entry_price) / entry_price) * 100, 2) if entry_price > 0 else 0
        pos['pnl_pct'] = pnl_pct
        
        # Zirve fiyat takibi — chandelier trailing için şart
        if new_price > pos.get('zirve_fiyat', 0):
            pos['zirve_fiyat'] = new_price
        
        # Chandelier stop güncelle: zirve - 3×ATR(14)
        atr14 = pos.get('atr14', 0)
        if atr14 > 0:
            yeni_chandelier = round(pos['zirve_fiyat'] - 3 * atr14, 2)
            eski_chandelier = pos.get('chandelier_stop', 0)
            # Chandelier sadece yukarı çekilir (K-07)
            if yeni_chandelier > eski_chandelier:
                pos['chandelier_stop'] = yeni_chandelier
                pos['chandelier_guncelleme'] = today.isoformat()
        
        # Etkin stop = chandelier_stop ile stop_loss'un büyüğü
        aktif_stop = max(pos.get('chandelier_stop', 0), pos.get('stop_loss', 0))
        
        # Stop mesafesi: (fiyat - stop) / fiyat × 100
        stop_distance = ((new_price - aktif_stop) / new_price) * 100 if new_price > 0 else 999
        target_distance = ((pos['hedef_fiyat'] - new_price) / new_price) * 100 if pos.get('hedef_fiyat') else 999
        
        # Tutulan gün hesapla
        try:
            entry_date = datetime.strptime(pos['giris_tarihi'], '%Y-%m-%d').date()
            pos['tutulan_gun'] = (today - entry_date).days
        except (KeyError, ValueError):
            pass
        
        # Durum güncelle
        if new_price <= aktif_stop:
            pos['durum'] = "🔴 STOP-LOSS TETİKLENDİ!"
        elif pos.get('hedef_fiyat') and new_price >= pos['hedef_fiyat']:
            pos['durum'] = "🎯 HEDEF ULAŞILDI!"
        elif stop_distance < 2:
            pos['durum'] = f"⚠️ Stop yakın ({stop_distance:.1f}%)"
        elif target_distance < 5:
            pos['durum'] = f"🎯 Hedefe yakın ({target_distance:.1f}%)"
        else:
            pos['durum'] = "✅ Normal aralıkta"
        
        pos['son_guncelleme'] = now
        
        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%) | P&L: {pnl_pct:+.2f}% | {pos['durum']}")
        updated_count += 1
    
    swing['son_guncelleme'] = now
    
    log(f"  📊 {updated_count}/{len(swing.get('aktif_pozisyonlar', []))} swing pozisyon güncellendi")
    
    return save_json(SWING_ACTIVE_JSON, swing)


def update_watchlist(quote_dict):
    """Watchlist'i güncelle"""
    watchlist = load_json(WATCHLIST_JSON)
    if not watchlist:
        return False
    
    log(f"\n👁️  Watchlist güncelleniyor...")
    
    now = datetime.now().isoformat()
    updated_count = 0
    
    for candidate in watchlist.get('izleme_listesi', []):
        symbol = candidate['sembol']
        
        if symbol not in quote_dict:
            log(f"  ⚠️  {symbol}: fiyat bulunamadı")
            continue
        
        quote = quote_dict[symbol]
        old_price = candidate.get('guncel_fiyat', 0)
        new_price = quote['price']
        
        candidate['guncel_fiyat'] = new_price
        
        # 5 günlük momentum hesapla
        # changesPercentage piyasa dışında 0 döner — manuel hesap
        prev_close = quote.get('previousClose', 0)
        if prev_close and prev_close > 0:
            candidate['momentum_5gun'] = round(((new_price - prev_close) / prev_close) * 100, 2)
        else:
            candidate['momentum_5gun'] = 0
        
        candidate['son_kontrol'] = datetime.now().strftime('%Y-%m-%d')
        
        change = ((new_price - old_price) / old_price) * 100 if old_price > 0 else 0
        log(f"  ✅ {symbol}: ${old_price:.2f} → ${new_price:.2f} ({change:+.2f}%)")
        updated_count += 1
    
    watchlist['son_guncelleme'] = now
    
    log(f"  📊 {updated_count}/{len(watchlist.get('izleme_listesi', []))} watchlist adayı güncellendi")
    
    return save_json(WATCHLIST_JSON, watchlist)


def update_summary():
    """Summary dosyasını güncelle"""
    log(f"\n📋 Summary güncelleniyor...")
    
    balanced = load_json(BALANCED_JSON)
    aggressive = load_json(AGGRESSIVE_JSON)
    dividend = load_json(DIVIDEND_JSON)
    swing = load_json(SWING_ACTIVE_JSON)
    
    if not all([balanced, aggressive, dividend]):
        log("❌ Portföy dosyaları yüklenemedi!")
        return False

    # swing None olabilir (active.json henüz oluşmamış) — guard
    swing_pozisyonlar = swing.get('aktif_pozisyonlar', []) if swing else []
    # Tek kaynak: agent.swing_manager.SWING_MAX_POSITIONS
    try:
        import sys as _sys
        _sys.path.insert(0, str(REPO_ROOT / "agent"))
        from swing_manager import SWING_MAX_POSITIONS as swing_slot_max
    except Exception:
        swing_slot_max = 5  # fallback

    # Toplam değerleri hesapla
    total_capital = 600000  # $100K + $400K + $100K
    total_value = balanced['toplam_deger'] + aggressive['toplam_deger'] + dividend['toplam_deger']
    total_pnl = total_value - total_capital
    total_pnl_pct = (total_pnl / total_capital) * 100

    summary = {
        "son_guncelleme": datetime.now().strftime('%Y-%m-%d'),
        "toplam_sermaye": total_capital,
        "toplam_deger": round(total_value, 2),
        "toplam_kar_zarar": round(total_pnl, 2),
        "toplam_kar_zarar_yuzde": round(total_pnl_pct, 2),
        "portfolyolar": {
            "dengeli": {
                "isim": "Dengeli Portföy",
                "deger": balanced['toplam_deger'],
                "maliyet": balanced['baslangic_sermaye'],
                "kar_zarar": balanced['toplam_deger'] - balanced['baslangic_sermaye'],
                "kar_zarar_yuzde": balanced['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(balanced['pozisyonlar']),
                "nakit": balanced.get('nakit', {"miktar": 0})
            },
            "agresif": {
                "isim": "Agresif Büyüme Portföyü",
                "deger": aggressive['toplam_deger'],
                "maliyet": aggressive['baslangic_sermaye'],
                "kar_zarar": aggressive['toplam_deger'] - aggressive['baslangic_sermaye'],
                "kar_zarar_yuzde": aggressive['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(aggressive['pozisyonlar']),
                "nakit": aggressive.get('nakit', {"miktar": 0})
            },
            "temettü": {
                "isim": "Değer + Temettü Portföyü",
                "deger": dividend['toplam_deger'],
                "maliyet": dividend['baslangic_sermaye'],
                "kar_zarar": dividend['toplam_deger'] - dividend['baslangic_sermaye'],
                "kar_zarar_yuzde": dividend['toplam_getiri_yuzde'],
                "pozisyon_sayisi": len(dividend['pozisyonlar']),
                "nakit": dividend.get('nakit', {"miktar": 0})
            },
            "swing_trade": {
                "isim": "Swing Trade",
                "pozisyon_sayisi": len(swing_pozisyonlar),
                "bos_slot": swing_slot_max - len(swing_pozisyonlar),
                "durum": f"{len(swing_pozisyonlar)}/{swing_slot_max} pozisyon aktif"
            }
        }
    }
    
    log(f"  💰 Toplam portföy değeri: ${total_value:,.2f} ({total_pnl_pct:+.2f}%)")
    
    return save_json(SUMMARY_JSON, summary)


def git_commit_and_push(message):
    """Git commit ve push yap"""
    log(f"\n🔄 Git commit yapılıyor...")
    
    try:
        os.chdir(REPO_ROOT)
        
        # Git add
        subprocess.run(['git', 'add', '.'], check=True)
        
        # Git commit
        commit_result = subprocess.run(
            ['git', 'commit', '-m', message],
            capture_output=True,
            text=True
        )
        
        if commit_result.returncode == 0:
            log(f"  ✅ Commit başarılı: {message}")
            
            # Git push
            push_result = subprocess.run(
                ['git', 'push'],
                capture_output=True,
                text=True
            )
            
            if push_result.returncode == 0:
                log(f"  ✅ Push başarılı!")
                return True
            else:
                log(f"  ❌ Push hatası: {push_result.stderr}")
                return False
        else:
            # "nothing to commit" durumu
            if "nothing to commit" in commit_result.stdout:
                log(f"  ℹ️  Değişiklik yok, commit atlandı")
                return True
            else:
                log(f"  ❌ Commit hatası: {commit_result.stderr}")
                return False
    
    except subprocess.CalledProcessError as e:
        log(f"  ❌ Git işlemi başarısız: {e}")
        return False


# ====== ANA FONKSİYON ======

def main():
    """Ana güncelleme fonksiyonu"""
    log("\n" + "="*60)
    log("🚀 OTOMATIK FİYAT GÜNCELLEMESİ BAŞLATILIYOR")
    log("="*60)
    
    # Tüm sembolleri topla
    all_symbols = set()
    
    # Portföy sembolleri
    for filepath in [BALANCED_JSON, AGGRESSIVE_JSON, DIVIDEND_JSON]:
        portfolio = load_json(filepath)
        if portfolio:
            all_symbols.update(pos['sembol'] for pos in portfolio.get('pozisyonlar', []))
    
    # Swing trade sembolleri
    swing = load_json(SWING_ACTIVE_JSON)
    if swing:
        all_symbols.update(pos['sembol'] for pos in swing.get('aktif_pozisyonlar', []))
    
    # Watchlist sembolleri
    watchlist = load_json(WATCHLIST_JSON)
    if watchlist:
        all_symbols.update(c['sembol'] for c in watchlist.get('izleme_listesi', []))
    
    log(f"\n📊 Toplam {len(all_symbols)} sembol güncelleniyor:")
    log(f"   {', '.join(sorted(all_symbols))}")
    
    # Batch quote çek
    quote_dict = get_batch_quotes(list(all_symbols))
    
    if not quote_dict:
        log("\n❌ FMP API'den fiyat alınamadı! Güncelleme iptal edildi.")
        sys.exit(1)
    
    # Her şeyi güncelle
    success = True
    success &= update_portfolio(BALANCED_JSON, quote_dict)
    success &= update_portfolio(AGGRESSIVE_JSON, quote_dict)
    success &= update_portfolio(DIVIDEND_JSON, quote_dict)
    success &= update_swing_trades(quote_dict)
    success &= update_watchlist(quote_dict)
    success &= update_summary()

    if not success:
        log("\n⚠️  Bazı dosyalar güncellenemedi!")

    # Git commit + push
    commit_message = f"[GÜNCELLEME] Fiyat + stop güncellemesi - {datetime.now().strftime('%d %b %Y %H:%M')}"
    git_commit_and_push(commit_message)
    
    log("\n" + "="*60)
    log("✅ GÜNCELLEME TAMAMLANDI")
    log("="*60 + "\n")


if __name__ == "__main__":
    main()
