#!/usr/bin/env python3
"""
Portföy Adil Değer Entegrasyon Scripti — Finzora AI

7 entegrasyon adımı:
  1. Portföy + watchlist adil değer taraması → sabah raporu bölümü
  2. Market cycle filtresi (SPY SMA200 + VIX)
  3. Karar matrisi puanı (+3 / 0 / -3)
  4. Swing giriş filtresi (PAHALI → red)
  5. Açık pozisyon dinamik çıkış sinyali
  6. Agresif v2 tedarik zinciri taraması
  7. Pozisyon büyüklük önerisi (iskonto × limit)

Kullanım:
  python3 scripts/portfoy_adil_deger.py                    # tam rapor
  python3 scripts/portfoy_adil_deger.py --hizli            # sadece tablo
  python3 scripts/portfoy_adil_deger.py --tedarik          # v2 tezi tarama
  python3 scripts/portfoy_adil_deger.py --swing NVDA MSFT  # swing filtresi
  python3 scripts/portfoy_adil_deger.py --telegram         # Telegram gönder
  python3 scripts/portfoy_adil_deger.py --rapor            # MD dosyasına yaz
"""

import sys, os, json, math, argparse, subprocess
from datetime import datetime

REPO   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "scripts"))

import requests
FMP_KEY   = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE  = "https://financialmodelingprep.com/stable"
TG_TOKEN  = "8749931249:AAGTLVKLHx5grcGlJhuodg-DbFDkFYjpCcI"
TG_CHAT   = "-1003827034395"

# Agresif v2 tedarik zinciri evreni
TEDARIK_ZINCIRI = {
    "Ekipman":        ["ASML","AMAT","LRCX","KLAC","CAMT","ONTO"],
    "Kimya/Malzeme":  ["ENTG","MKSI","PLAB"],
    "Optik":          ["COHR","LITE","GLW","AAOI"],
    "Güç Altyapısı":  ["POWL","VRT","ETN","PWR"],
    "Soğutma":        ["TT","JCI"],
    "Veri Merkezi":   ["DLR","EQIX"],
    "Enerji":         ["COP","XOM"],
    "Nadir Toprak":   ["MP","FCX"],
}

# ── Yardımcılar ───────────────────────────────────────────────

def fmp(e, p=None):
    if p is None: p = {}
    p["apikey"] = FMP_KEY
    try:
        r = requests.get(f"{FMP_BASE}/{e}", params=p, timeout=20)
        if r.status_code == 429:
            import time; time.sleep(62); r = requests.get(f"{FMP_BASE}/{e}", params=p, timeout=20)
        r.raise_for_status()
        d = r.json()
        return None if isinstance(d,dict) and "Error" in d else d
    except: return None

def safe(v, d=None):
    try:
        f = float(v); return d if (math.isnan(f) or math.isinf(f)) else f
    except: return d

def tg(msg):
    try:
        requests.post(f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage",
                      json={"chat_id": TG_CHAT, "text": msg,
                            "parse_mode": "HTML"}, timeout=10)
    except: pass

def hesapla_sembol(sym):
    """adil_deger_calculator.hesapla() çağrısı — import ile."""
    try:
        from adil_deger_calculator import hesapla
        return hesapla(sym.upper(), sessiz=True)
    except Exception as ex:
        print(f"  [{sym}] hata: {ex}")
        return None


# ═══════════════════════════════════════════════════════════════
# ADIM 2 — Market Cycle Filtresi
# ═══════════════════════════════════════════════════════════════

def market_cycle():
    """
    SPY SMA200 ve VIX kontrolü.
    Dönüş: ('RISK_ON' | 'DIKKATLI' | 'RISK_OFF', detay_str)
    """
    # SPY fiyat ve SMA200
    spy_q   = fmp("quote", {"symbol": "SPY"})
    spy_sma = fmp("technical-indicators/sma",
                  {"symbol": "SPY", "periodLength": 200, "timeframe": "1day"})
    spy_p   = safe(spy_q[0].get("price")) if spy_q else None
    sma200  = safe(spy_sma[0].get("sma")) if spy_sma else None

    # VIX — web search ile
    try:
        r = requests.get("https://query1.finance.yahoo.com/v8/finance/chart/%5EVIX",
                         headers={"User-Agent":"Mozilla/5.0"}, timeout=8)
        vix = r.json()["chart"]["result"][0]["meta"]["regularMarketPrice"]
    except:
        vix = None

    # SPY SMA21 (kısa trend)
    spy_sma21 = fmp("technical-indicators/sma",
                    {"symbol": "SPY", "periodLength": 21, "timeframe": "1day"})
    sma21 = safe(spy_sma21[0].get("sma")) if spy_sma21 else None

    # Karar
    detay_parts = []
    if spy_p and sma200:
        spy_vs_200 = (spy_p / sma200 - 1) * 100
        detay_parts.append(f"SPY ${spy_p:.1f} | SMA200 ${sma200:.1f} ({spy_vs_200:+.1f}%)")
    if sma21:
        detay_parts.append(f"SMA21 ${sma21:.1f}")
    if vix:
        detay_parts.append(f"VIX {vix:.1f}")

    # Durum belirleme
    spy_above_200 = spy_p and sma200 and spy_p > sma200
    spy_above_21  = spy_p and sma21  and spy_p > sma21
    vix_sakin     = (vix or 99) < 22
    vix_yuksek    = (vix or 0) > 28

    if spy_above_200 and spy_above_21 and vix_sakin:
        durum = "RISK_ON"
        emoji = "🟢"
    elif vix_yuksek or (not spy_above_200):
        durum = "RISK_OFF"
        emoji = "🔴"
    else:
        durum = "DIKKATLI"
        emoji = "🟡"

    detay = " | ".join(detay_parts) if detay_parts else "veri yok"
    return durum, f"{emoji} {durum}: {detay}"


# ═══════════════════════════════════════════════════════════════
# ADIM 3 — Karar Matrisi Puanı
# ═══════════════════════════════════════════════════════════════

def karar_puani(res, cycle):
    """
    Adil değer sinyaline göre karar matrisi puanı.
    cycle: 'RISK_ON' | 'DIKKATLI' | 'RISK_OFF'
    """
    if not res: return 0, "hesap yok"
    fark  = res.get("fark_pct") or 0
    guven = res.get("guven") or 0
    q     = res.get("quality_skor") or 0
    q_mult= res.get("quality_mult", 1.0)
    fark_ham = res.get("fark_ham") or fark

    # Haklı prim tespiti
    hakli_prim = fark_ham > 20 and q_mult > 1.0 and (fark_ham - fark) > 5

    if hakli_prim:
        puan = 1; aciklama = f"HAKLI PRİM 🏆 (ham:{fark_ham:+.0f}% kalite:{q})"
    elif fark < -20 and guven >= 70:
        puan = 3; aciklama = f"UCUZ 🟢 güçlü (güven {guven})"
    elif fark < -20 and guven >= 50:
        puan = 2; aciklama = f"UCUZ 🟢 orta (güven {guven})"
    elif fark < -10 and guven >= 60:
        puan = 1; aciklama = f"UCUZ-ADİL sınırı"
    elif fark > 20 and guven >= 70:
        puan = -3; aciklama = f"PAHALI 🔴 güçlü (güven {guven})"
    elif fark > 20 and guven >= 50:
        puan = -2; aciklama = f"PAHALI 🔴 orta (güven {guven})"
    elif -10 <= fark <= 10:
        puan = 0; aciklama = "ADİL 🟡"
    elif 10 < fark <= 20:
        puan = -1; aciklama = f"Hafif primli ({fark:+.0f}%)"
    elif fark > 20:
        # Pahalı ama düşük güven — yine de negatif
        puan = -1; aciklama = f"PAHALI ({fark:+.0f}%) düşük güven:{guven} — dikkat"
    elif fark < -10:
        puan = 0; aciklama = f"Hafif ucuz ({fark:+.0f}%) — izle"
    else:
        puan = 0; aciklama = "Bant içi"

    # Market cycle düzeltmesi
    if cycle == "RISK_OFF" and puan > 0:
        puan = max(0, puan - 1)
        aciklama += " [cycle -1]"

    return puan, aciklama


# ═══════════════════════════════════════════════════════════════
# ADIM 4 — Swing Giriş Filtresi
# ═══════════════════════════════════════════════════════════════

def swing_filtre(sym, res, cycle):
    """
    Adil değer bazlı swing bilgi notu.

    MİMARİ KARAR: Bu fonksiyon YASAKLAMAZ.
    Gerçek yasaklar K-kurallarının görevi (K-04, K-18, K-19 vb.)
    Adil değer → pozisyon boyutunu etkiler, girişi engellemez.

    Dönüş: ('DESTEKLI' | 'NOTR' | 'DIKKAT', mesaj)
    """
    if not res:
        return "NOTR", "adil değer hesaplanamadı — K-kuralları geçerli"

    fark     = res.get("fark_pct") or 0
    guven    = res.get("guven") or 0
    q        = res.get("quality_skor") or 0
    q_mult   = res.get("quality_mult", 1.0)
    fark_ham = res.get("fark_ham") or fark
    hakli_prim = fark_ham > 20 and q_mult > 1.0 and (fark_ham - fark) > 5

    # DESTEKLI: Adil değer girişi güçlendiriyor
    if fark < -20 and guven >= 70:
        return "DESTEKLI", f"UCUZ {fark:+.0f}% güven:{guven} — güçlü değer desteği, tam lot"
    if fark < -20 and guven >= 50:
        return "DESTEKLI", f"UCUZ {fark:+.0f}% güven:{guven} — değer desteği, normal lot"
    if hakli_prim:
        return "DESTEKLI", f"HAKLI PRİM Q{q} — kalite prim hak ediyor, normal lot"
    if cycle == "RISK_OFF" and fark < -10:
        return "DESTEKLI", f"RISK_OFF ama UCUZ {fark:+.0f}% — defansif değer, küçük lot"

    # DIKKAT: Adil değer risk ekliyor — girebilirsin, boyutu küçült
    if fark > 30 and guven >= 60 and not hakli_prim:
        return "DIKKAT", f"Primli {fark:+.0f}% güven:{guven} — lot küçük tut, stop sıkı"
    if fark > 20 and guven >= 50 and not hakli_prim:
        return "DIKKAT", f"Hafif primli {fark:+.0f}% — normal lot ama stop yakın"
    if cycle == "RISK_OFF":
        return "DIKKAT", f"RISK_OFF ortamı — lot küçük tut"

    # NOTR: Adil değer nötr
    return "NOTR", f"ADİL bölge ({fark:+.0f}%) — K-kuralları belirleyici"


def cikis_sinyali(pozisyon, res):
    """
    Mevcut bir pozisyon için adil değer bazlı çıkış değerlendirmesi.
    pozisyon: {'sembol','maliyet_baz','adet','stop_loss','guncel_fiyat'}
    """
    if not res: return None

    sym        = pozisyon.get("sembol","?")
    maliyet    = pozisyon.get("maliyet_baz", 0)
    guncel     = res.get("price") or pozisyon.get("guncel_fiyat", 0)
    stop       = pozisyon.get("stop_loss", 0)
    fark       = res.get("fark_pct") or 0
    guven      = res.get("guven") or 0
    fark_ham   = res.get("fark_ham") or fark
    q_mult     = res.get("quality_mult", 1.0)
    hakli_prim = fark_ham > 20 and q_mult > 1.0

    kar_yuzde  = (guncel / maliyet - 1) * 100 if maliyet > 0 else 0
    sinyaller  = []

    # Tam çıkış sinyalleri
    if fark > 30 and guven >= 70 and not hakli_prim:
        sinyaller.append(("TAM_CIK", f"⚠️  PAHALI {fark:+.0f}% güven:{guven} — döngü tamamlandı, tam çık"))

    # K-11 kâr alma (PAHALI + kâr)
    if fark > 20 and kar_yuzde > 15 and guven >= 60 and not hakli_prim:
        sinyaller.append(("KISMI_SAT", f"💰 PAHALI {fark:+.0f}% + kâr %{kar_yuzde:.0f} — K-11 kâr kilit aktif"))

    # ADİL → PAHALI geçişi (giriş UCUZ'dan yapılmışsa)
    if -5 < fark < 20 and kar_yuzde > 20:
        sinyaller.append(("IZLE", f"📊 ADİL değere geldi (giriş UCUZ'dan), %{kar_yuzde:.0f} kâr — kâr kilidi düşün"))

    # Değer artık ADİL ama UCUZ'dan çok uzaklaştı
    if fark > 15 and guven >= 65:
        sinyaller.append(("STOP_SIKISTIR", f"🔒 Adil değer {fark:+.0f}% üstüne geçti — trailing stop sıkılaştır"))

    return sinyaller if sinyaller else [("BEKLE", "✓ Pozisyon adil değer bandında — hold devam")]


# ═══════════════════════════════════════════════════════════════
# ADIM 7 — Pozisyon Büyüklük Önerisi
# ═══════════════════════════════════════════════════════════════

def pozisyon_buyuklugu(res, portfoy_tipi="dengeli"):
    """
    Adil değer iskontosuna göre pozisyon büyüklüğü (max limitin yüzdesi).
    portfoy_tipi: dengeli=25%, agresif=20%, temettu=15%
    """
    if not res: return 0, "hesap yok"

    fark  = res.get("fark_pct") or 0
    guven = res.get("guven") or 0
    q     = res.get("quality_skor") or 0
    fark_ham = res.get("fark_ham") or fark

    limitler = {"dengeli": 25, "agresif": 20, "temettu": 15}
    max_limit = limitler.get(portfoy_tipi, 20)

    # Güven filtresi
    if guven < 40:
        return 0, f"güven çok düşük ({guven}) — geç"

    # İskonto bazlı oran
    if fark < -30:
        oran = 1.00  # tam limit
        not_ = f"UCUZ {fark:+.0f}% — tam pozisyon"
    elif fark < -20:
        oran = 0.70
        not_ = f"UCUZ {fark:+.0f}% — %70 pozisyon"
    elif fark < -10:
        oran = 0.45
        not_ = f"Hafif ucuz {fark:+.0f}% — %45 pozisyon"
    elif fark < 5:
        oran = 0.25
        not_ = f"ADİL {fark:+.0f}% — %25 pozisyon (izle)"
    else:
        # Pahalı görünse de giriş yasak değil — K-kuralları ve teknik belirleyici
        oran = 0.20
        not_ = f"Primli {fark:+.0f}% — küçük lot (%20 limit), K-kuralları belirleyici"

    # Kalite ayarı (+%10 bonus kaliteli hisselerde)
    if q >= 70 and oran > 0:
        oran = min(oran * 1.10, 1.0)
        not_ += f" [kalite Q{q} +10%]"

    # Güven ayarı (50-60 arası: -%20)
    if 40 <= guven < 60 and oran > 0:
        oran *= 0.80
        not_ += f" [güven {guven} -%20]"

    hedef_pct = round(max_limit * oran, 1)
    return hedef_pct, not_


# ═══════════════════════════════════════════════════════════════
# ADIM 1 — Portföy Taraması + Rapor
# ═══════════════════════════════════════════════════════════════

def portfoy_tara(hizli=False):
    """Tüm portföy ve watchlist'i tarar, sonuçları döndürür."""
    # Portföy dosyaları
    portfoyler = {}
    for ad, dosya in [("dengeli","balanced"),("agresif","aggressive"),("temettu","dividend")]:
        p = os.path.join(REPO, "data", "portfolios", f"{dosya}.json")
        try:
            d = json.load(open(p))
            aktif = [poz for poz in d.get("pozisyonlar",[])
                     if (poz.get("adet",0) or 0) > 0]
            if aktif: portfoyler[ad] = aktif
        except: pass

    # Watchlist (üst 8 aday)
    wl_syms = []
    try:
        wl = json.load(open(os.path.join(REPO,"data","watchlist.json")))
        items = wl.get("izleme_listesi", [])
        # skora göre sırala
        items_s = sorted([i for i in items if isinstance(i,dict) and i.get("sembol")],
                         key=lambda x: x.get("skor",0), reverse=True)
        wl_syms = [i["sembol"] for i in items_s[:8]]
    except: pass

    # Tüm sembolleri topla — çakışan semboller (MO gibi) ayrı kayıt tutar
    portfoy_syms = {}  # sym → [(portfoy_adi, poz), ...]
    for ad, pozlar in portfoyler.items():
        for poz in pozlar:
            sym = poz["sembol"]
            if sym not in portfoy_syms:
                portfoy_syms[sym] = []
            portfoy_syms[sym].append((ad, poz))

    tum_syms = list(portfoy_syms.keys()) + [s for s in wl_syms if s not in portfoy_syms]

    # Tarama
    sonuclar = {}
    for sym in tum_syms:
        print(f"  ⟳ {sym}...", flush=True, end=" ")
        res = hesapla_sembol(sym)
        sonuclar[sym] = res
        if res:
            fark = res.get("fark_pct") or 0
            guven = res.get("guven") or 0
            sinyal = "🟢UCUZ" if fark<-20 else "🔴PAHALI" if fark>20 else "🟡ADİL"
            print(f"{sinyal} {fark:+.0f}% güven:{guven}")
        else:
            print("veri yok")

    return portfoyler, portfoy_syms, wl_syms, sonuclar


def rapor_olustur(portfoyler, portfoy_syms, wl_syms, sonuclar, cycle, cycle_detay, hizli=False):
    """Markdown formatında tam rapor üretir."""
    simdi = datetime.now().strftime("%d.%m.%Y %H:%M")
    satirlar = []
    satirlar.append(f"\n## Adil Değer Paneli — {simdi}\n")

    # Market cycle
    satirlar.append(f"**Market Cycle:** {cycle_detay}\n")
    if cycle == "RISK_OFF":
        satirlar.append("> ⚠️ **UYARI:** RISK_OFF — UCUZ sinyalleri susturuldu. Sadece PAHALI uyarıları aktif.\n")

    # ── Portföy pozisyonları ──────────────────────────────────
    satirlar.append("### Portföy Pozisyonları\n")
    satirlar.append("| Sembol | Portföy | Maliyet | Fiyat | Adil Değer | Fark% | Güven | Sinyal | K.Puanı | Çıkış? |")
    satirlar.append("|--------|---------|---------|-------|------------|-------|-------|--------|---------|--------|")

    for sym, kayitlar in portfoy_syms.items():
      for (portfoy_adi, poz) in kayitlar:
        res = sonuclar.get(sym)
        if not res:
            satirlar.append(f"| {sym} | {portfoy_adi} | - | - | - | - | - | ❓ | - | - |")
            continue

        maliyet  = poz.get("maliyet_baz", 0)
        fiyat    = res.get("price") or 0
        adil     = res.get("adil_deger") or 0
        fark     = res.get("fark_pct") or 0
        guven    = res.get("guven") or 0
        fark_ham = res.get("fark_ham") or fark
        q_mult   = res.get("quality_mult", 1.0)
        hakli    = fark_ham > 20 and q_mult > 1.0

        if hakli:
            sinyal = "🏆HAK.PRİM"
        elif fark < -20:
            sinyal = "🟢UCUZ"
        elif fark > 20:
            sinyal = "🔴PAHALI"
        else:
            sinyal = "🟡ADİL"

        puan, puan_ac = karar_puani(res, cycle)
        puan_str = f"{puan:+d}" if puan != 0 else "0"

        # Çıkış sinyali
        cikis = cikis_sinyali(poz, res)
        cikis_str = cikis[0][0] if cikis else "-"
        if cikis_str == "BEKLE": cikis_str = "✓"
        elif cikis_str == "TAM_CIK": cikis_str = "⚠️TAM ÇIK"
        elif cikis_str == "KISMI_SAT": cikis_str = "💰KISMI SAT"
        elif cikis_str == "STOP_SIKISTIR": cikis_str = "🔒STOP"

        satirlar.append(
            f"| **{sym}** | {portfoy_adi} | ${maliyet:.2f} | ${fiyat:.2f} | "
            f"${adil:.2f} | {fark:+.1f}% | {guven}/100 | {sinyal} | {puan_str} | {cikis_str} |"
        )

    # ── Watchlist ─────────────────────────────────────────────
    if wl_syms:
        satirlar.append("\n### Watchlist Adil Değer\n")
        satirlar.append("| Sembol | Fiyat | Adil Değer | Fark% | Güven | Q.Skor | Sinyal | K.Puanı | Pos.Büy% |")
        satirlar.append("|--------|-------|------------|-------|-------|--------|--------|---------|----------|")
        for sym in wl_syms:
            if sym in portfoy_syms: continue
            res = sonuclar.get(sym)
            if not res: continue
            fark  = res.get("fark_pct") or 0
            guven = res.get("guven") or 0
            q     = res.get("quality_skor") or 0
            fark_ham = res.get("fark_ham") or fark
            q_mult = res.get("quality_mult", 1.0)
            hakli  = fark_ham > 20 and q_mult > 1.0

            if hakli:            sinyal = "🏆HAK.PRİM"
            elif fark < -20:     sinyal = "🟢UCUZ"
            elif fark > 20:      sinyal = "🔴PAHALI"
            else:                sinyal = "🟡ADİL"

            puan, _ = karar_puani(res, cycle)
            puan_str = f"{puan:+d}" if puan != 0 else "0"

            # Portföy tipi tahmin (watchlist'te hedef_portfoy varsa kullan)
            pb, _ = pozisyon_buyuklugu(res, "dengeli")
            satirlar.append(
                f"| **{sym}** | ${res.get('price',0):.2f} | ${res.get('adil_deger',0):.2f} | "
                f"{fark:+.1f}% | {guven}/100 | Q{q} | {sinyal} | {puan_str} | %{pb} |"
            )

    # ── Swing filtre özeti ────────────────────────────────────
    satirlar.append("\n### Swing Giriş Filtresi (Watchlist)\n")
    for sym in wl_syms[:6]:
        res = sonuclar.get(sym)
        durum, msg = swing_filtre(sym, res, cycle)
        emoji = {"DESTEKLI":"💚","NOTR":"⚪","DIKKAT":"⚠️"}.get(durum,"?")
        satirlar.append(f"- **{sym}**: {emoji} {durum} — {msg}")

    # ── Pozisyon önerileri özeti ──────────────────────────────
    satirlar.append("\n### Pozisyon Büyüklük Önerileri (Dengeli)\n")
    oneri_listesi = []
    for sym in list(portfoy_syms.keys()) + wl_syms:
        res = sonuclar.get(sym)
        if not res: continue
        pb, not_ = pozisyon_buyuklugu(res, "dengeli")
        if pb > 0:
            oneri_listesi.append((pb, sym, not_))

    oneri_listesi.sort(reverse=True)
    for pb, sym, not_ in oneri_listesi[:8]:
        satirlar.append(f"- **{sym}**: max %{pb:.1f} limit — {not_}")

    satirlar.append(f"\n---\n*Finzora AI · {simdi}*\n")
    return "\n".join(satirlar)


# ═══════════════════════════════════════════════════════════════
# ADIM 6 — Tedarik Zinciri Taraması
# ═══════════════════════════════════════════════════════════════

def tedarik_tara(cycle, telegram=False):
    """Agresif v2 AI tedarik zinciri evrenini tarar."""
    print(f"\n{'═'*68}")
    print("  AGRESİF v2 TEDARİK ZİNCİRİ TARASI")
    print(f"  Market Cycle: {cycle}")
    print(f"{'═'*68}\n")

    tum = []
    for kategori, semboller in TEDARIK_ZINCIRI.items():
        print(f"\n  [{kategori}]")
        for sym in semboller:
            print(f"    {sym}...", end=" ", flush=True)
            res = hesapla_sembol(sym)
            if not res:
                print("veri yok"); continue
            fark  = res.get("fark_pct") or 0
            guven = res.get("guven") or 0
            q     = res.get("quality_skor") or 0
            puan, ac = karar_puani(res, cycle)
            tum.append((puan, sym, fark, guven, q, ac, kategori))

            sinyal = "🟢" if fark<-20 else "🔴" if fark>20 else "🟡"
            print(f"{sinyal} {fark:+.0f}% güven:{guven} Q{q} puan:{puan:+d}")

    # Özet — sadece UCUZ veya güçlü sinyal
    print(f"\n{'─'*68}")
    print("  ARAŞTIR LİSTESİ (UCUZ + güven≥50):\n")
    ucuz = [(p,s,f,g,q,a,k) for p,s,f,g,q,a,k in sorted(tum,reverse=True) if f<-20 and g>=50]
    if ucuz:
        for p,s,f,g,q,a,k in ucuz:
            print(f"  🟢 {s:<6} [{k}] fark:{f:+.0f}% güven:{g} Q{q} — {a}")
    else:
        print("  (Şu an evrende güven≥50 UCUZ sinyal yok)")

    if telegram:
        msg = "🔍 <b>Agresif v2 Tedarik Zinciri Tarası</b>\n\n"
        msg += f"Market: {cycle}\n\n"
        if ucuz:
            msg += "<b>ARAŞTIR:</b>\n"
            for _,s,f,g,q,a,k in ucuz:
                msg += f"🟢 {s} [{k}] {f:+.0f}% güven:{g}\n"
        else:
            msg += "Şu an güçlü UCUZ sinyal yok."
        tg(msg)
        print("\n  Telegram'a gönderildi.")


# ═══════════════════════════════════════════════════════════════
# ANA FONKSİYON
# ═══════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser(description="Portföy Adil Değer Entegrasyonu")
    ap.add_argument("--hizli",    action="store_true", help="Sadece tablo, detaysız")
    ap.add_argument("--tedarik",  action="store_true", help="v2 tezi tedarik zinciri tarama")
    ap.add_argument("--swing",    nargs="+", metavar="SYM", help="Semboller için swing filtresi")
    ap.add_argument("--telegram", action="store_true", help="Telegram'a gönder")
    ap.add_argument("--rapor",    action="store_true", help="MD dosyasına yaz")
    args = ap.parse_args()

    print(f"\n{'═'*68}")
    print("  PORTFÖY ADİL DEĞER ENTEGRASYONu — Finzora AI")
    print(f"  {datetime.now().strftime('%d.%m.%Y %H:%M')}")
    print(f"{'═'*68}\n")

    # Adım 2: Market cycle
    print("  ⟳ Market cycle kontrol ediliyor...")
    cycle, cycle_detay = market_cycle()
    print(f"  {cycle_detay}\n")

    # --swing: sadece swing filtresi
    if args.swing:
        print(f"  SWING GİRİŞ FİLTRESİ\n  {'─'*40}")
        for sym in args.swing:
            res = hesapla_sembol(sym)
            durum, msg = swing_filtre(sym, res, cycle)
            emoji = {"ONAY":"✅","RED":"❌","DIKKAT":"⚠️"}.get(durum,"?")
            print(f"\n  {emoji} {sym}: {durum}")
            print(f"     {msg}")
            if res:
                print(f"     Adil değer: ${res.get('adil_deger',0):.2f} | "
                      f"Fark: {res.get('fark_pct',0):+.1f}% | "
                      f"Güven: {res.get('guven',0)}/100 | "
                      f"Q:{res.get('quality_skor',0)}")
        return

    # --tedarik: tedarik zinciri taraması
    if args.tedarik:
        tedarik_tara(cycle, telegram=args.telegram)
        return

    # Adım 1: Portföy taraması
    print("  ⟳ Portföy ve watchlist taranıyor...\n")
    portfoyler, portfoy_syms, wl_syms, sonuclar = portfoy_tara(args.hizli)

    # Adım 3: Karar puanları + Adım 5: Çıkış sinyalleri
    print(f"\n{'─'*68}")
    print("  PORTFÖY ÖZETİ\n")
    for sym, kayitlar in portfoy_syms.items():
      for (portfoy_adi, poz) in kayitlar:
        res = sonuclar.get(sym)
        if not res: continue
        puan, puan_ac = karar_puani(res, cycle)
        cikis = cikis_sinyali(poz, res)
        pb, pb_not = pozisyon_buyuklugu(res, portfoy_adi)

        fark  = res.get("fark_pct") or 0
        guven = res.get("guven") or 0
        q     = res.get("quality_skor") or 0
        adil  = res.get("adil_deger") or 0

        print(f"  {sym:<6} [{portfoy_adi}] ${res.get('price',0):.2f} → adil ${adil:.2f} "
              f"({fark:+.1f}%) güven:{guven} Q{q}")
        print(f"         Karar puanı: {puan:+d} | {puan_ac}")
        if cikis and cikis[0][0] != "BEKLE":
            for tip, msg in cikis:
                print(f"         Çıkış: {msg}")
        print()

    # Rapor üret
    rapor_md = rapor_olustur(portfoyler, portfoy_syms, wl_syms, sonuclar,
                              cycle, cycle_detay, args.hizli)
    print(rapor_md)

    # Dosyaya yaz
    if args.rapor:
        tarih = datetime.now().strftime("%Y-%m-%d")
        dosya = os.path.join(REPO,"reports","daily",f"DAILY_ADIL_DEGER_{tarih}.md")
        os.makedirs(os.path.dirname(dosya), exist_ok=True)
        with open(dosya,"w") as f:
            f.write(rapor_md)
        print(f"  → {dosya}")

    # Telegram
    if args.telegram:
        # Kısa özet gönder
        msg = f"📊 <b>Adil Değer Paneli</b>\n{cycle_detay}\n\n"
        for sym, kayitlar in portfoy_syms.items():
            res = sonuclar.get(sym)
            if not res: continue
            fark = res.get("fark_pct") or 0
            g    = res.get("guven") or 0
            ikon = "🟢" if fark<-20 else "🔴" if fark>20 else "🟡"
            msg += f"{ikon} {sym}: {fark:+.1f}% güven:{g}\n"
        ucuz_wl = [s for s in wl_syms
                   if sonuclar.get(s) and (sonuclar[s].get("fark_pct") or 0) < -20
                   and (sonuclar[s].get("guven") or 0) >= 60]
        if ucuz_wl:
            msg += f"\n🟢 Watchlist UCUZ: {', '.join(ucuz_wl)}"
        tg(msg)
        print("  Telegram'a gönderildi.")


if __name__ == "__main__":
    main()
