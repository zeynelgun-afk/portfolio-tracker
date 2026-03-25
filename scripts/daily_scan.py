#!/usr/bin/env python3
"""
Finzora AI — Günlük Swing Trade Tarama Scripti
--------------------------------------------------
Çalışma: Her iş günü piyasa kapanışı sonrası (21:30 UTC / 00:30 TR)
Yöntem : EP (Episodic Pivot) + Flag/Base Breakout — Qullamaggie metodolojisi
Çıktı  : data/swing/daily_scan.json
"""

import requests
import json
import os
import subprocess
from datetime import datetime, timedelta, timezone

# ─── Yapılandırma ────────────────────────────────────────────────────────────
FMP_API_KEY = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
FMP_BASE    = "https://financialmodelingprep.com/stable"

# Filtre parametreleri
EP_MIN_DEGISIM_YZD  = 7.5      # % — minimum EP hareketi
EP_MIN_DOLAR_HACIM  = 100e6    # $100M — minimum dollar volume
EP_MAX_PIYASA_DEG   = 1e9      # $1B — minimum market cap
BREAKOUT_MIN_HACIM  = 500_000  # minimum ortalama günlük hacim
BREAKOUT_VOL_KATSAYI= 1.5      # breakout günü hacim çarpanı
BREAKOUT_BAKIN_GUN  = 50       # n günlük yüksek kırılımı
MIN_FIYAT           = 10       # minimum hisse fiyatı
MAX_ADAY            = 8        # her kategoride maksimum aday sayısı

VIX_UYARI_ESIGI     = 25       # VIX bu seviyenin üzerindeyse uyarı
VIX_KRITIK_ESIGI    = 30       # VIX bu seviyenin üzerindeyse EP skip öner

# ─── Yardımcı Fonksiyonlar ───────────────────────────────────────────────────
def fmp_get(endpoint, params=None):
    if params is None:
        params = {}
    params["apikey"] = FMP_API_KEY
    url = f"{FMP_BASE}/{endpoint}"
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json()
        if isinstance(data, dict) and "Error Message" in data:
            print(f"  ⚠ FMP hata [{endpoint}]: {data['Error Message']}")
            return None
        return data
    except Exception as e:
        print(f"  ✗ İstek hatası [{endpoint}]: {e}")
        return None

def guvenli_float(deger, varsayilan=0.0):
    try:
        return float(deger) if deger is not None else varsayilan
    except:
        return varsayilan

def piyasa_kapali_mi(quotes):
    """batch-quote'ta tüm hisseler %0 değişim dönüyorsa piyasa kapalıdır."""
    if not quotes or len(quotes) < 3:
        return True
    sifir_sayisi = sum(1 for q in quotes if guvenli_float(q.get("changesPercentage")) == 0)
    return sifir_sayisi == len(quotes)

# ─── Piyasa Bağlamı ──────────────────────────────────────────────────────────
def piyasa_baglamini_al():
    print("→ Piyasa bağlamı alınıyor...")
    endeks_quotes = fmp_get("batch-quote", {"symbols": "SPY,QQQ,IWM"})
    vix_quote     = fmp_get("quote", {"symbol": "^VIX"})

    endeks = {}
    if endeks_quotes:
        for q in endeks_quotes:
            sym = q.get("symbol", "")
            endeks[sym] = {
                "fiyat"  : guvenli_float(q.get("price")),
                "degisim": guvenli_float(q.get("changesPercentage")),
                "hacim"  : guvenli_float(q.get("volume")),
            }

    vix = 0.0
    if vix_quote and isinstance(vix_quote, list) and len(vix_quote) > 0:
        vix = guvenli_float(vix_quote[0].get("price"))

    # Piyasa kapalı kontrolü
    kapali = piyasa_kapali_mi(endeks_quotes)

    return {
        "spy_degisim"  : endeks.get("SPY", {}).get("degisim", 0),
        "qqq_degisim"  : endeks.get("QQQ", {}).get("degisim", 0),
        "iwm_degisim"  : endeks.get("IWM", {}).get("degisim", 0),
        "spy_fiyat"    : endeks.get("SPY", {}).get("fiyat", 0),
        "qqq_fiyat"    : endeks.get("QQQ", {}).get("fiyat", 0),
        "vix"          : vix,
        "piyasa_kapali": kapali,
        "vix_uyarisi"  : vix >= VIX_UYARI_ESIGI,
        "vix_kritik"   : vix >= VIX_KRITIK_ESIGI,
    }

# ─── Seviye Hesaplama ────────────────────────────────────────────────────────
def seviyeleri_hesapla(giris, stop):
    """Giriş ve stop fiyatından R hedeflerini hesapla."""
    if giris <= 0 or stop <= 0 or stop >= giris:
        return None
    r         = giris - stop
    risk_yuzde = round((r / giris) * 100, 1)
    return {
        "giris"      : round(giris, 2),
        "stop"       : round(stop, 2),
        "r_dolar"    : round(r, 2),
        "risk_yuzde" : risk_yuzde,
        "hedef_2r"   : round(giris + 2 * r, 2),
        "hedef_3r"   : round(giris + 3 * r, 2),
        "rr_orani"   : "2:1",
    }

# ─── EP (Episodic Pivot) Taraması ────────────────────────────────────────────
def ep_tara():
    """
    Episodic Pivot adayları:
    1. biggest-gainers listesinden başla
    2. Filtrele: % >= 7.5, dollar_volume >= 100M, market_cap >= 1B, price >= 10
    3. Teyit: close_today > high_yesterday (son 5 günlük OHLCV)
    4. Skora göre sırala
    """
    print("→ EP (Episodic Pivot) taranıyor...")
    adaylar = []

    # 1) En büyük kazananlar
    gainers = fmp_get("biggest-gainers", {"limit": 60})
    if not gainers:
        print("  ✗ biggest-gainers verisi alınamadı")
        return []

    # 2) Ön filtre: price, değişim, dollar_volume
    on_filtre = []
    for g in gainers:
        fiyat     = guvenli_float(g.get("price"))
        degisim   = guvenli_float(g.get("changesPercentage"))
        hacim     = guvenli_float(g.get("volume"))
        dol_hacim = fiyat * hacim

        if (degisim  >= EP_MIN_DEGISIM_YZD and
            dol_hacim >= EP_MIN_DOLAR_HACIM and
            fiyat     >= MIN_FIYAT):
            g["dollar_volume"] = dol_hacim
            on_filtre.append(g)

    if not on_filtre:
        print("  — Ön filtreden geçen EP adayı yok")
        return []

    print(f"  ✓ Ön filtreden {len(on_filtre)} aday geçti, tarihsel veri alınıyor...")

    # 3) Her aday için son 5 günlük OHLCV — close > high_yesterday kontrolü
    sembolleri = [g["symbol"] for g in on_filtre]

    # batch-quote ile ek bilgi al (marketCap, avgVolume, priceAvg50, priceAvg200)
    batch = fmp_get("batch-quote", {"symbols": ",".join(sembolleri)})
    batch_map = {}
    if batch:
        for q in batch:
            batch_map[q.get("symbol", "")] = q

    for g in on_filtre:
        sym    = g.get("symbol", "")
        fiyat  = guvenli_float(g.get("price"))
        degisim= guvenli_float(g.get("changesPercentage"))
        bq     = batch_map.get(sym, {})

        market_cap = guvenli_float(bq.get("marketCap"))
        avg_volume = guvenli_float(bq.get("avgVolume"))
        price_50ma = guvenli_float(bq.get("priceAvg50"))
        price_200ma= guvenli_float(bq.get("priceAvg200"))
        year_high  = guvenli_float(bq.get("yearHigh"))
        year_low   = guvenli_float(bq.get("yearLow"))
        prev_close = guvenli_float(bq.get("previousClose"))

        # Market cap filtresi
        if market_cap > 0 and market_cap < EP_MAX_PIYASA_DEG:
            continue

        # Son 5 günlük OHLCV — close > high_yesterday
        tarih_gecmis = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
        tarih_bugun  = datetime.now().strftime("%Y-%m-%d")
        hist = fmp_get("historical-price-eod/full", {
            "symbol": sym, "from": tarih_gecmis, "to": tarih_bugun
        })

        close_gt_yest_high = False
        onceki_gun_high    = 0.0
        bugun_low          = 0.0

        if hist and len(hist) >= 2:
            # hist[0] = bugün, hist[1] = dün (en yeni önce)
            bugun_close        = guvenli_float(hist[0].get("close"))
            bugun_low          = guvenli_float(hist[0].get("low"))
            onceki_gun_high    = guvenli_float(hist[1].get("high"))
            close_gt_yest_high = bugun_close > onceki_gun_high

        # Skoru hesapla (0-100)
        skor = _ep_skoru_hesapla(
            degisim, g["dollar_volume"], close_gt_yest_high,
            avg_volume, hacim=guvenli_float(g.get("volume")),
            price_200ma=price_200ma, fiyat=fiyat
        )

        # Seviyeler: giriş = today close, stop = today low
        giris = fiyat * 1.005  # %0.5 yukarısından konfirmasyon girişi
        stop  = bugun_low * 0.99 if bugun_low > 0 else fiyat * 0.92
        seviyeler = seviyeleri_hesapla(giris, stop)

        # 52 haftalık konumu
        yw_konum = ""
        if year_high > 0 and year_low > 0:
            konum_yuzde = ((fiyat - year_low) / (year_high - year_low)) * 100
            yw_konum = f"52h yüksek: %{round(konum_yuzde)}"

        # Uyarılar
        uyarilar = []
        if not close_gt_yest_high:
            uyarilar.append("⚠ close > dünkü high doğrulanamadı")
        if avg_volume > 0 and guvenli_float(g.get("volume")) < avg_volume * 1.5:
            uyarilar.append("⚠ hacim 1.5x ortalamanın altında")
        if market_cap < 2e9:
            uyarilar.append("⚠ küçük cap — volatil olabilir")

        aday = {
            "sembol"            : sym,
            "isim"              : g.get("name", sym),
            "setup_tipi"        : "EP",
            "fiyat"             : round(fiyat, 2),
            "degisim_yuzde"     : round(degisim, 2),
            "hacim"             : int(guvenli_float(g.get("volume"))),
            "ort_hacim"         : int(avg_volume),
            "hacim_katsayi"     : round(guvenli_float(g.get("volume")) / avg_volume, 1) if avg_volume > 0 else 0,
            "dollar_hacim_M"    : round(g["dollar_volume"] / 1e6, 1),
            "piyasa_deger_B"    : round(market_cap / 1e9, 2) if market_cap > 0 else 0,
            "onceki_gun_high"   : round(onceki_gun_high, 2),
            "bugun_low"         : round(bugun_low, 2),
            "close_gt_dunku_high": close_gt_yest_high,
            "sma50_uzerinde"    : fiyat > price_50ma if price_50ma > 0 else None,
            "sma200_uzerinde"   : fiyat > price_200ma if price_200ma > 0 else None,
            "52h_konum"         : yw_konum,
            "ep_skoru"          : skor,
            "seviyeler"         : seviyeler,
            "uyarilar"          : uyarilar,
        }
        adaylar.append(aday)

    # Skora göre sırala, en iyileri al
    adaylar.sort(key=lambda x: x["ep_skoru"], reverse=True)
    return adaylar[:MAX_ADAY]

def _ep_skoru_hesapla(degisim, dol_hacim, close_gt_high, avg_vol, hacim, price_200ma, fiyat):
    skor = 0
    # Değişim büyüklüğü (0-30 puan)
    if degisim >= 20:      skor += 30
    elif degisim >= 15:    skor += 24
    elif degisim >= 10:    skor += 18
    elif degisim >= 7.5:   skor += 12
    # Dollar volume (0-25 puan)
    if dol_hacim >= 500e6:   skor += 25
    elif dol_hacim >= 250e6: skor += 20
    elif dol_hacim >= 100e6: skor += 15
    # close > dünkü high (0-25 puan) — önemli teyit
    if close_gt_high:        skor += 25
    # Hacim katsayısı vs ortalama (0-20 puan)
    if avg_vol > 0:
        kat = hacim / avg_vol
        if kat >= 5:    skor += 20
        elif kat >= 3:  skor += 15
        elif kat >= 2:  skor += 10
        elif kat >= 1.5:skor += 5
    # SMA200 üzerinde mi (0-10 puan) — uzun vadeli trend filtresi
    if price_200ma > 0 and fiyat > price_200ma:
        skor += 10
    return min(skor, 100)

# ─── Breakout (Flag/Base) Taraması ──────────────────────────────────────────
def breakout_tara():
    """
    Flag/Base breakout adayları:
    1. most-actives listesinden başla
    2. batch-quote ile ek bilgi al
    3. Filtre: price >= 15, avgVolume >= 500K, priceAvg50 üzerinde
    4. 60 günlük OHLCV — last 50 günün higherini kırdı mı + base kalitesi
    5. Skora göre sırala
    """
    print("→ Breakout (Flag/Base) taranıyor...")
    adaylar = []

    # 1) En çok işlem gören hisseler
    actives = fmp_get("most-actives", {"limit": 50})
    if not actives:
        print("  ✗ most-actives verisi alınamadı")
        return []

    # Semboller listesi
    sembolleri = [a.get("symbol", "") for a in actives if a.get("symbol")]

    # 2) batch-quote ile detaylı bilgi
    batch = fmp_get("batch-quote", {"symbols": ",".join(sembolleri)})
    batch_map = {}
    if batch:
        for q in batch:
            batch_map[q.get("symbol", "")] = q

    # 3) Ön filtre
    on_filtre = []
    for sym in sembolleri:
        bq = batch_map.get(sym, {})
        fiyat      = guvenli_float(bq.get("price"))
        avg_volume = guvenli_float(bq.get("avgVolume"))
        hacim      = guvenli_float(bq.get("volume"))
        price_50ma = guvenli_float(bq.get("priceAvg50"))
        market_cap = guvenli_float(bq.get("marketCap"))

        if (fiyat >= MIN_FIYAT and
            avg_volume >= BREAKOUT_MIN_HACIM and
            hacim >= avg_volume * BREAKOUT_VOL_KATSAYI and
            market_cap >= EP_MAX_PIYASA_DEG):
            on_filtre.append(sym)

    if not on_filtre:
        print("  — Ön filtreden geçen breakout adayı yok")
        return []

    print(f"  ✓ Ön filtreden {len(on_filtre)} aday geçti, {BREAKOUT_BAKIN_GUN} günlük OHLCV alınıyor...")

    # 4) Her aday için 60 günlük OHLCV
    tarih_gecmis = (datetime.now() - timedelta(days=80)).strftime("%Y-%m-%d")
    tarih_bugun  = datetime.now().strftime("%Y-%m-%d")

    for sym in on_filtre[:20]:  # maksimum 20 API çağrısı
        hist = fmp_get("historical-price-eod/full", {
            "symbol": sym, "from": tarih_gecmis, "to": tarih_bugun
        })
        if not hist or len(hist) < BREAKOUT_BAKIN_GUN:
            continue

        bq = batch_map.get(sym, {})
        fiyat      = guvenli_float(bq.get("price"))
        avg_volume = guvenli_float(bq.get("avgVolume"))
        hacim      = guvenli_float(bq.get("volume"))
        price_50ma = guvenli_float(bq.get("priceAvg50"))
        price_200ma= guvenli_float(bq.get("priceAvg200"))
        market_cap = guvenli_float(bq.get("marketCap"))
        year_high  = guvenli_float(bq.get("yearHigh"))
        year_low   = guvenli_float(bq.get("yearLow"))
        prev_close = guvenli_float(bq.get("previousClose"))
        name       = bq.get("name", sym)

        # hist[0] = bugün, en yeni önce
        bugun     = hist[0]
        bugun_high = guvenli_float(bugun.get("high"))
        bugun_low  = guvenli_float(bugun.get("low"))
        bugun_close= guvenli_float(bugun.get("close"))
        bugun_vol  = guvenli_float(bugun.get("volume"))

        # Önceki N gün (bugün hariç)
        onceki_n_gun = hist[1:BREAKOUT_BAKIN_GUN + 1]
        if len(onceki_n_gun) < BREAKOUT_BAKIN_GUN:
            continue

        n_gun_high = max(guvenli_float(d.get("high")) for d in onceki_n_gun)
        n_gun_low  = min(guvenli_float(d.get("low")) for d in onceki_n_gun)

        # 20 günlük ortalama hacim (gerçek hesaplama)
        son20_vol  = [guvenli_float(d.get("volume")) for d in hist[1:21]]
        avg20_vol  = sum(son20_vol) / len(son20_vol) if son20_vol else 0

        # Breakout kontrolü: bugün N günlük highi kırdı mı?
        kiriyor  = bugun_high > n_gun_high or bugun_close > n_gun_high * 0.995
        # Hacim teyidi
        hacim_katsayisi = bugun_vol / avg20_vol if avg20_vol > 0 else 0
        hacim_teyidi    = hacim_katsayisi >= 1.5

        if not (kiriyor and hacim_teyidi):
            continue

        # Base kalitesi: son 20 günde fiyat aralığı daralmış mı?
        son20_highs = [guvenli_float(d.get("high")) for d in hist[1:21]]
        son20_lows  = [guvenli_float(d.get("low")) for d in hist[1:21]]
        base_genislik = 0
        if son20_highs and son20_lows:
            base_max = max(son20_highs)
            base_min = min(son20_lows)
            base_genislik = ((base_max - base_min) / base_max) * 100

        # Trend kalitesi: 50MA > 200MA?
        trend_yukari = price_50ma > price_200ma if (price_50ma > 0 and price_200ma > 0) else None

        # Seviyeler: giriş = kırılım seviyesi, stop = base alt
        giris    = n_gun_high * 1.005
        stop_raw = n_gun_low * 0.98
        # Stop mantıksal kontrol
        if stop_raw >= giris:
            stop_raw = giris * 0.92
        seviyeler = seviyeleri_hesapla(giris, stop_raw)

        skor = _breakout_skoru_hesapla(
            hacim_katsayisi, base_genislik, trend_yukari,
            fiyat, price_200ma, bugun_close, n_gun_high
        )

        # 52h konumu
        yw_konum = ""
        if year_high > 0 and year_low > 0:
            konum_yuzde = ((fiyat - year_low) / (year_high - year_low)) * 100
            yw_konum = f"52h yüksek: %{round(konum_yuzde)}"

        uyarilar = []
        if base_genislik > 25:
            uyarilar.append("⚠ base çok geniş — temiz değil")
        if not trend_yukari:
            uyarilar.append("⚠ SMA50 < SMA200 — trend sorunlu")
        if hacim_katsayisi < 2.0:
            uyarilar.append("⚠ hacim 2x'in altında")
        if market_cap < 2e9:
            uyarilar.append("⚠ küçük cap")

        aday = {
            "sembol"           : sym,
            "isim"             : name,
            "setup_tipi"       : "BREAKOUT",
            "fiyat"            : round(fiyat, 2),
            "degisim_yuzde"    : round(guvenli_float(bq.get("changesPercentage")), 2),
            "hacim"            : int(bugun_vol),
            "ort_hacim_20g"    : int(avg20_vol),
            "hacim_katsayi"    : round(hacim_katsayisi, 1),
            "dollar_hacim_M"   : round(fiyat * bugun_vol / 1e6, 1),
            "piyasa_deger_B"   : round(market_cap / 1e9, 2),
            "n_gun_high"       : round(n_gun_high, 2),
            "n_gun_low"        : round(n_gun_low, 2),
            "base_genislik_yuzde": round(base_genislik, 1),
            "sma50_uzerinde"   : fiyat > price_50ma if price_50ma > 0 else None,
            "sma200_uzerinde"  : fiyat > price_200ma if price_200ma > 0 else None,
            "trend_yukari"     : trend_yukari,
            "52h_konum"        : yw_konum,
            "bakin_gun"        : BREAKOUT_BAKIN_GUN,
            "breakout_skoru"   : skor,
            "seviyeler"        : seviyeler,
            "uyarilar"         : uyarilar,
        }
        adaylar.append(aday)

    adaylar.sort(key=lambda x: x["breakout_skoru"], reverse=True)
    return adaylar[:MAX_ADAY]

def _breakout_skoru_hesapla(hacim_kat, base_genislik, trend_yukari,
                              fiyat, sma200, bugun_close, n_gun_high):
    skor = 0
    # Hacim katsayısı (0-30 puan)
    if hacim_kat >= 4:    skor += 30
    elif hacim_kat >= 3:  skor += 24
    elif hacim_kat >= 2:  skor += 18
    elif hacim_kat >= 1.5:skor += 12
    # Base kalitesi: dar base daha iyi (0-20 puan)
    if base_genislik <= 8:    skor += 20
    elif base_genislik <= 12: skor += 15
    elif base_genislik <= 18: skor += 10
    elif base_genislik <= 25: skor += 5
    # Trend (0-20 puan)
    if trend_yukari is True:  skor += 20
    elif trend_yukari is None:skor += 10
    # SMA200 üzerinde (0-15 puan) — uzun vadeli trend filtresi
    if sma200 > 0 and fiyat > sma200:  skor += 15
    # Kırılım gücü: kapanış ne kadar üzerinde (0-15 puan)
    if n_gun_high > 0:
        kiriim_yuzde = ((bugun_close - n_gun_high) / n_gun_high) * 100
        if kiriim_yuzde >= 3:   skor += 15
        elif kiriim_yuzde >= 2: skor += 12
        elif kiriim_yuzde >= 1: skor += 8
        elif kiriim_yuzde >= 0: skor += 4
    return min(skor, 100)

# ─── Sektör Bağlamı ──────────────────────────────────────────────────────────
def sektor_performansini_al(tarih):
    sektor_data = fmp_get("sector-performance-snapshot", {"date": tarih})
    if not sektor_data:
        # Bir gün geri git
        onceki = (datetime.strptime(tarih, "%Y-%m-%d") - timedelta(days=1)).strftime("%Y-%m-%d")
        sektor_data = fmp_get("sector-performance-snapshot", {"date": onceki})
    if not sektor_data:
        return {}
    return {s.get("sector", ""): round(guvenli_float(s.get("averageChange")), 2)
            for s in sektor_data}

# ─── Sonuçları Kaydet ────────────────────────────────────────────────────────
def sonuclari_kaydet(baglam, ep_adaylar, breakout_adaylar, sektor_perf):
    tarih_str = datetime.now().strftime("%Y-%m-%d")
    saat_str  = datetime.now().strftime("%H:%M TR")

    # VIX uyarı mesajı
    vix_mesaj = ""
    if baglam["vix_kritik"]:
        vix_mesaj = f"⚠⚠ VIX {baglam['vix']:.1f} — KRİTİK SEVIYE. EP girişleri riskli, pozisyon küçült veya geç."
    elif baglam["vix_uyarisi"]:
        vix_mesaj = f"⚠ VIX {baglam['vix']:.1f} — YÜKSEK OYNAKLLIK. Stop seviyeleri geniş tut, yarım pozisyon düşün."

    sonuc = {
        "tarama_tarihi"   : tarih_str,
        "tarama_saati"    : saat_str,
        "piyasa_durumu"   : "KAPALI" if baglam["piyasa_kapali"] else "AÇIK",
        "piyasa_ozeti": {
            "spy_degisim" : baglam["spy_degisim"],
            "qqq_degisim" : baglam["qqq_degisim"],
            "iwm_degisim" : baglam["iwm_degisim"],
            "vix"         : baglam["vix"],
            "vix_uyarisi" : baglam["vix_uyarisi"],
            "vix_kritik"  : baglam["vix_kritik"],
            "vix_mesaj"   : vix_mesaj,
        },
        "en_iyi_sektorler": sorted(sektor_perf.items(), key=lambda x: x[1], reverse=True)[:5],
        "en_kotu_sektorler": sorted(sektor_perf.items(), key=lambda x: x[1])[:3],
        "ep_adaylari"     : ep_adaylar,
        "breakout_adaylari": breakout_adaylar,
        "ozet": {
            "toplam_ep"       : len(ep_adaylar),
            "toplam_breakout" : len(breakout_adaylar),
            "toplam_aday"     : len(ep_adaylar) + len(breakout_adaylar),
            "tarama_notu"     : _tarama_notu_uret(baglam, ep_adaylar, breakout_adaylar),
        }
    }

    os.makedirs("data/swing", exist_ok=True)
    with open("data/swing/daily_scan.json", "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)

    print(f"\n✅ Tarama tamamlandı → data/swing/daily_scan.json")
    print(f"   EP adayları   : {len(ep_adaylar)}")
    print(f"   Breakout adayları: {len(breakout_adaylar)}")
    print(f"   VIX            : {baglam['vix']:.1f}")

def _tarama_notu_uret(baglam, ep_adaylar, breakout_adaylar):
    notlar = []
    if baglam["vix_kritik"]:
        notlar.append("VIX kritik seviyede — yeni giriş yaparken dikkatli ol")
    if baglam["spy_degisim"] < -1.5:
        notlar.append("SPY güçlü düşüş — momentum bozuk, breakout tuzağı riski")
    elif baglam["spy_degisim"] > 1.5:
        notlar.append("SPY güçlü — trend destekliyor")
    if not ep_adaylar and not breakout_adaylar:
        notlar.append("Bugün temiz aday yok — nakit tut, bekle")
    elif len(ep_adaylar) >= 3:
        notlar.append(f"{len(ep_adaylar)} EP adayı var — seçici ol, en yüksek skorluya odaklan")
    return " | ".join(notlar) if notlar else "Normal tarama günü"

# ─── Git Commit ───────────────────────────────────────────────────────────────
def git_commit_push(tarih_str):
    try:
        subprocess.run(["git", "config", "user.email", "zeynelgun@users.noreply.github.com"], check=True)
        subprocess.run(["git", "config", "user.name", "Finzora AI"], check=True)
        subprocess.run(["git", "pull", "--rebase", "origin", "main"], check=False)
        subprocess.run(["git", "add", "data/swing/daily_scan.json"], check=True)
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            capture_output=True
        )
        if result.returncode != 0:
            subprocess.run(
                ["git", "commit", "-m",
                 f"[TARAMA] Swing adayları güncellendi — {tarih_str}"],
                check=True
            )
            subprocess.run(["git", "push"], check=True)
            print("✅ Git push başarılı")
        else:
            print("— Değişiklik yok, commit atlandı")
    except subprocess.CalledProcessError as e:
        print(f"⚠ Git hatası: {e}")

# ─── Ana Akış ────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print(f"Finzora AI — Günlük Swing Tarama")
    print(f"Zaman: {datetime.now().strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    tarih_str = datetime.now().strftime("%Y-%m-%d")

    # 1) Piyasa bağlamı
    baglam = piyasa_baglamini_al()
    print(f"  SPY: {baglam['spy_degisim']:+.2f}% | QQQ: {baglam['qqq_degisim']:+.2f}% | VIX: {baglam['vix']:.1f}")

    # 2) Sektör performansı
    sektor_perf = sektor_performansini_al(tarih_str)

    # 3) EP taraması
    ep_adaylar = ep_tara()

    # 4) Breakout taraması
    breakout_adaylar = breakout_tara()

    # 5) Kaydet
    sonuclari_kaydet(baglam, ep_adaylar, breakout_adaylar, sektor_perf)

    # 6) Git commit
    git_commit_push(tarih_str)

if __name__ == "__main__":
    main()
