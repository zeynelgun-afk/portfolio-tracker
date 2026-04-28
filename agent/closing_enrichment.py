"""
Kapanış raporu zenginleştirme modülü.

5 ek bağlam üretir, kapanış prompt'una inject edilir:

1. GÜN İÇİ İŞLEM AKIŞI         — bugün yapılan tüm alım/satımlar
2. PLAN vs GERÇEKLEŞME          — sabah morning kararları gerçekleşti mi
3. RİSK/PERFORMANS PANOSU       — toplam değer, getiri, konsantrasyon, drawdown
4. ERKEN UYARI RADARI           — gelecek 5 gün earnings + makro takvim
5. SEKTÖR ROTASYON              — sektör ETF'leri performans + portföy ağırlık

Tüm Türkçe, kullanıcı raporu açabilir ve anlayabilir.

Tasarım kuralı: hiçbir veri yoksa o blok atlanır (boş tablo yerine
"veri toplanıyor" yazılır), rapor kalitesi düşmez.

27 Nis 2026 — ilk versiyon.
"""

from __future__ import annotations
import csv
import json
import os
from datetime import datetime, timedelta, date
from pathlib import Path

import pytz

REPO_ROOT = Path(__file__).resolve().parents[1]
TR_TZ     = pytz.timezone("Europe/Istanbul")

PORTFOY_TR = {
    "balanced":   "Dengeli",
    "aggressive": "Agresif",
    "dividend":   "Temettü",
    "swing":      "Swing",
}


# ── 1. GÜN İÇİ İŞLEM AKIŞI ──────────────────────────────────────────────────

def _gunluk_islemler(seans_tarihi: str) -> list[dict]:
    """transactions.csv'den belirli günün işlemlerini oku."""
    tx_path = REPO_ROOT / "data" / "transactions.csv"
    if not tx_path.exists():
        return []
    rows = []
    with open(tx_path, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            if r.get("date") == seans_tarihi:
                rows.append(r)
    return rows


def islem_akisi_blogu(seans_tarihi: str) -> str:
    """Gün içi işlem akışı tablosu (1.5 numaralı bölüm)."""
    islemler = _gunluk_islemler(seans_tarihi)
    if not islemler:
        return ""

    lines = []
    lines.append("## 1.5 GÜN İÇİ İŞLEM AKIŞI")
    lines.append("")
    lines.append(f"Bugün **{len(islemler)} işlem** yapıldı:")
    lines.append("")
    lines.append("| Tip | Sembol | Adet | Fiyat | Tutar | Sebep |")
    lines.append("|-----|--------|------|-------|-------|-------|")

    toplam_alim = 0.0
    toplam_satim = 0.0
    for r in islemler:
        try:
            adet = float(r["shares"])
            fiyat = float(r["price"])
            tutar = float(r["total"])
        except (ValueError, KeyError):
            continue

        action = r.get("action", "")
        emoji = "🟢" if action == "BUY" else "🔴"
        tip_tr = "ALIŞ" if action == "BUY" else "SATIŞ"
        sebep = r.get("reason", "")[:65]

        if action == "BUY":
            toplam_alim += tutar
        else:
            toplam_satim += tutar

        adet_fmt = f"{adet:.0f}" if adet == int(adet) else f"{adet:.2f}"
        lines.append(
            f"| {emoji} {tip_tr} | {r['symbol']} | {adet_fmt} | ${fiyat:,.2f} | ${tutar:,.0f} | {sebep} |"
        )

    net_akis = toplam_satim - toplam_alim
    yon_emoji = "💵 nakit girişi" if net_akis > 0 else ("💸 nakit çıkışı" if net_akis < 0 else "denge")
    lines.append("")
    lines.append(f"**Net nakit hareketi:** ${abs(net_akis):,.0f} {yon_emoji} "
                 f"(alış toplamı ${toplam_alim:,.0f}, satış toplamı ${toplam_satim:,.0f})")
    lines.append("")
    return "\n".join(lines)


# ── 2. PLAN vs GERÇEKLEŞME ──────────────────────────────────────────────────

def _morning_plan_oku(seans_tarihi: str) -> list[dict] | None:
    """O günün morning raporundan kararları oku.

    Morning kararları logs/events.jsonl'da type=decision mode=morning olarak
    kaydedilir. claude_call_id ile aynı sabah çağrısına bağlıdır.
    """
    events_path = REPO_ROOT / "logs" / "events.jsonl"
    if not events_path.exists():
        return None

    morning_kararlar = []
    try:
        with open(events_path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                if e.get("type") != "decision":
                    continue
                if e.get("mode") != "morning":
                    continue
                ts = e.get("ts", "")
                # Tarih eşleşmesi
                if not ts.startswith(seans_tarihi):
                    continue
                morning_kararlar.append(e)
    except Exception:
        return None

    return morning_kararlar


def plan_gerceklesme_blogu(seans_tarihi: str) -> str:
    """Sabah Claude kararlarının gerçekleşip gerçekleşmediği analizi."""
    plan = _morning_plan_oku(seans_tarihi)
    if not plan:
        return ""  # Sabah planı yok (ilk gün veya morning çalışmadı)

    islemler = _gunluk_islemler(seans_tarihi)
    yapilan_semboller = {(r.get("symbol"), r.get("action")) for r in islemler}

    lines = []
    lines.append("## 5.1 SABAH PLANI vs GERÇEKLEŞME")
    lines.append("")

    yapilan = []
    yapilmayan = []
    for k in plan:
        sym = k.get("sembol", "?")
        tip = k.get("tip", "?")
        # ÇIK/EKLE/BÜYÜT/STOP_GÜNCELLE/İZLE → action mapping
        if tip in ("EKLE", "BÜYÜT"):
            beklenen_action = "BUY"
        elif tip in ("ÇIK", "KÜÇÜLT"):
            beklenen_action = "SELL"
        else:
            # STOP_GÜNCELLE, İZLE — işlem gerektirmez, atla
            continue

        gerceklesti = (sym, beklenen_action) in yapilan_semboller
        if gerceklesti:
            yapilan.append((sym, tip, k.get("neden", "")))
        else:
            yapilmayan.append((sym, tip, k.get("neden", ""), k.get("aciliyet", "")))

    toplam_aksiyon = len(yapilan) + len(yapilmayan)
    if toplam_aksiyon == 0:
        lines.append("Sabah planında somut alım/satım kararı yoktu (sadece izleme/stop güncelleme).")
        lines.append("")
        return "\n".join(lines)

    skor = (len(yapilan) / toplam_aksiyon * 100) if toplam_aksiyon else 0

    lines.append(f"**Tutarlılık skoru: %{skor:.0f}** ({len(yapilan)}/{toplam_aksiyon} sabah kararı uygulandı)")
    lines.append("")

    if yapilan:
        lines.append("### ✅ Yapıldı")
        for sym, tip, neden in yapilan:
            lines.append(f"- **{sym}** {tip} — {neden[:80]}")
        lines.append("")

    if yapilmayan:
        lines.append("### ❌ Atlandı")
        for sym, tip, neden, aciliyet in yapilmayan:
            ac_str = f" ({aciliyet})" if aciliyet else ""
            lines.append(f"- **{sym}** {tip}{ac_str} — {neden[:80]}")
        lines.append("")
        lines.append("> ⚠️ Atlanan kararlar varsa: ya kural beklenenden farklı tetiklendi, "
                     "ya FAZ_2 penceresinde fiyat hedefini bulmadı, ya kapasite doluydu. "
                     "Yarın morning'de gerekçe sorgulanmalı.")
        lines.append("")

    return "\n".join(lines)


# ── 3. RİSK/PERFORMANS PANOSU ───────────────────────────────────────────────

PERF_HISTORY_PATH = REPO_ROOT / "data" / "performance_history.jsonl"

def _gunluk_snapshot_yaz(toplam_deger: float, seans_tarihi: str):
    """Bugünün toplam portföy değerini history dosyasına yaz (idempotent)."""
    PERF_HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Aynı gün için duplicate yazma
    if PERF_HISTORY_PATH.exists():
        try:
            with open(PERF_HISTORY_PATH, encoding="utf-8") as f:
                for line in f:
                    if seans_tarihi in line:
                        return  # Zaten var
        except Exception:
            pass
    kayit = {
        "tarih": seans_tarihi,
        "toplam_deger": round(toplam_deger, 2),
        "yazim_zamani": datetime.now(TR_TZ).isoformat(),
    }
    with open(PERF_HISTORY_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")


def _history_oku() -> list[dict]:
    """Tarihsel günlük portföy değerleri."""
    if not PERF_HISTORY_PATH.exists():
        return []
    rows = []
    try:
        with open(PERF_HISTORY_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except Exception:
                        continue
    except Exception:
        return []
    return sorted(rows, key=lambda r: r.get("tarih", ""))


def risk_panosu_blogu(portfolios: dict, seans_tarihi: str) -> str:
    """Risk + performans özeti — her zaman gösterilir."""
    # Toplam değer
    toplam = sum(p.get("toplam_deger", 0) for p in portfolios.values())
    baslangic = 600000  # $100K balanced + $400K aggressive + $100K dividend
    getiri_pct = (toplam - baslangic) / baslangic * 100 if baslangic else 0

    # Tarihsel snapshot yaz (bugün için)
    _gunluk_snapshot_yaz(toplam, seans_tarihi)

    # Tarihsel kıyaslama
    history = _history_oku()
    dunki = None
    yedi_g = None
    otuz_g = None
    if len(history) >= 2:
        for h in reversed(history[:-1]):  # bugün hariç
            if dunki is None:
                dunki = h
                continue
            try:
                dt = datetime.strptime(h["tarih"], "%Y-%m-%d").date()
                bd = datetime.strptime(seans_tarihi, "%Y-%m-%d").date()
                gap = (bd - dt).days
            except Exception:
                continue
            if yedi_g is None and gap >= 5:
                yedi_g = h
            if otuz_g is None and gap >= 25:
                otuz_g = h

    # Pozisyon konsantrasyonu (top-3)
    pozisyonlar = []
    for pf_name, pf in portfolios.items():
        for poz in pf.get("pozisyonlar", []):
            sym = poz.get("sembol")
            if sym in (None, "_template"):
                continue
            adet = poz.get("adet", 0) or 0
            cf = poz.get("guncel_fiyat", 0) or 0
            deger = adet * cf
            if deger > 0:
                pozisyonlar.append((sym, deger, pf_name))
    pozisyonlar.sort(key=lambda x: -x[1])
    top3_deger = sum(d for _, d, _ in pozisyonlar[:3])
    top3_pct = (top3_deger / toplam * 100) if toplam else 0
    top3_isim = ", ".join(s for s, _, _ in pozisyonlar[:3])

    # Sektör konsantrasyon
    sektor_dagilim = {}
    for pf in portfolios.values():
        for poz in pf.get("pozisyonlar", []):
            sym = poz.get("sembol")
            if sym in (None, "_template"):
                continue
            adet = poz.get("adet", 0) or 0
            cf = poz.get("guncel_fiyat", 0) or 0
            deger = adet * cf
            if deger <= 0:
                continue
            sek = poz.get("sektor", "Bilinmiyor")
            sektor_dagilim[sek] = sektor_dagilim.get(sek, 0) + deger
    en_buyuk_sektor = max(sektor_dagilim.items(), key=lambda x: x[1]) if sektor_dagilim else ("yok", 0)
    en_buyuk_sektor_pct = (en_buyuk_sektor[1] / toplam * 100) if toplam else 0

    # Drawdown — tarihsel zirveye göre
    if history:
        zirve = max(h.get("toplam_deger", 0) for h in history + [{"toplam_deger": toplam}])
        drawdown = (toplam - zirve) / zirve * 100 if zirve else 0
    else:
        drawdown = 0

    # Çıktı
    lines = []
    lines.append("## 0. PORTFÖY ÖZETİ (PANO)")
    lines.append("")
    lines.append("| Gösterge | Bugün | Dün | 7 gün önce | 30 gün önce |")
    lines.append("|----------|-------|-----|-----------|-------------|")

    def fmt_d(d):
        return f"${d['toplam_deger']:,.0f}" if d else "—"

    lines.append(f"| Toplam değer | ${toplam:,.0f} | {fmt_d(dunki)} | {fmt_d(yedi_g)} | {fmt_d(otuz_g)} |")

    # Değişimler
    if dunki:
        delta_dun = toplam - dunki["toplam_deger"]
        delta_dun_pct = delta_dun / dunki["toplam_deger"] * 100 if dunki["toplam_deger"] else 0
        lines.append(f"| Dünden değişim | **{delta_dun:+,.0f} ({delta_dun_pct:+.2f}%)** | — | — | — |")

    lines.append(f"| Başlangıçtan getiri | **{getiri_pct:+.2f}%** | — | — | — |")
    lines.append(f"| Zirveden geri çekilme | {drawdown:+.2f}% | — | — | — |")
    lines.append(f"| Toplam pozisyon sayısı | {len(pozisyonlar)} | — | — | — |")
    lines.append(f"| En büyük 3 pozisyon ağırlık | %{top3_pct:.1f} | — | — | — |")
    lines.append(f"| En yoğun sektör | {en_buyuk_sektor[0]} (%{en_buyuk_sektor_pct:.1f}) | — | — | — |")
    lines.append("")

    # En büyük 3 pozisyon
    lines.append(f"**En yoğun 3 pozisyon:** {top3_isim}")
    lines.append("")

    # Sektör dağılım
    if sektor_dagilim:
        lines.append("**Sektör dağılımı (yatırılı sermaye üzerinden):**")
        sektor_sirali = sorted(sektor_dagilim.items(), key=lambda x: -x[1])
        yatirili_toplam = sum(sektor_dagilim.values())
        for sek, deg in sektor_sirali[:8]:
            pct = deg / yatirili_toplam * 100 if yatirili_toplam else 0
            lines.append(f"- {sek}: %{pct:.1f} (${deg:,.0f})")
        lines.append("")

    # Tarihsel veri yetersiz uyarısı
    if len(history) < 7:
        lines.append(f"> ℹ️  Tarihsel pano daha zenginleşecek: {len(history)} gün verisi var. "
                     f"7 gün dolduğunda haftalık trendler, 30 gün dolduğunda aylık metrikler görünecek.")
        lines.append("")

    return "\n".join(lines)


# ── 4. ERKEN UYARI RADARI ───────────────────────────────────────────────────

def _portfoy_sembolleri(portfolios: dict) -> set[str]:
    syms = set()
    for pf in portfolios.values():
        for poz in pf.get("pozisyonlar", []):
            sym = poz.get("sembol")
            if sym and sym != "_template":
                syms.add(sym)
    return syms


def erken_uyari_blogu(portfolios: dict, seans_tarihi: str) -> str:
    """Gelecek 5 işlem günü için earnings ve risk yoğunluğu."""
    import requests

    portfoy_syms = _portfoy_sembolleri(portfolios)
    if not portfoy_syms:
        return ""

    fmp_key = os.environ.get("FMP_API_KEY", "")
    if not fmp_key:
        return ""  # Veri çekilemez, atla

    # FMP earnings calendar
    today = datetime.strptime(seans_tarihi, "%Y-%m-%d").date()
    end = today + timedelta(days=5)
    url = (f"https://financialmodelingprep.com/stable/earnings-calendar"
           f"?from={today.isoformat()}&to={end.isoformat()}&apikey={fmp_key}")

    try:
        r = requests.get(url, timeout=15)
        if r.status_code != 200:
            return ""
        data = r.json()
        if not isinstance(data, list):
            return ""
    except Exception:
        return ""

    # Portföydeki semboller için filtrele
    portfoy_earnings = [d for d in data if d.get("symbol") in portfoy_syms]
    if not portfoy_earnings:
        return ""

    # Tarihe göre grupla
    gunluk = {}
    for e in portfoy_earnings:
        ed = e.get("date", "")
        if not ed:
            continue
        gunluk.setdefault(ed, []).append(e)

    lines = []
    lines.append("## 6.5 ERKEN UYARI RADARI (gelecek 5 işlem günü)")
    lines.append("")

    gunler_tr = ["Pazartesi", "Salı", "Çarşamba", "Perşembe", "Cuma", "Cumartesi", "Pazar"]
    aylar_tr = {1:"Oca", 2:"Şub", 3:"Mar", 4:"Nis", 5:"May", 6:"Haz",
                7:"Tem", 8:"Ağu", 9:"Eyl", 10:"Eki", 11:"Kas", 12:"Ara"}

    yogun_gun = None
    yogun_sayi = 0
    for ed in sorted(gunluk.keys()):
        try:
            dt = datetime.strptime(ed, "%Y-%m-%d").date()
        except Exception:
            continue
        gap = (dt - today).days
        if gap < 0 or gap > 5:
            continue

        gun_str = gunler_tr[dt.weekday()]
        ay_str = aylar_tr.get(dt.month, str(dt.month))
        baslik = f"### {dt.day} {ay_str} {gun_str}"
        if gap == 0:
            baslik += " — BUGÜN"
        elif gap == 1:
            baslik += " — yarın"
        else:
            baslik += f" — {gap} gün sonra"
        lines.append(baslik)
        for e in gunluk[ed]:
            sym = e.get("symbol", "?")
            eps_est = e.get("epsEstimated")
            time_h = e.get("time", "")  # bmo/amc
            time_str = "açılış öncesi" if time_h == "bmo" else ("kapanış sonrası" if time_h == "amc" else "saat belirsiz")
            eps_str = f" — beklenen EPS ${eps_est}" if eps_est else ""
            lines.append(f"- **{sym}** earnings ({time_str}){eps_str}")
        lines.append("")

        if len(gunluk[ed]) > yogun_sayi:
            yogun_sayi = len(gunluk[ed])
            yogun_gun = (dt, gunluk[ed])

    if yogun_gun and yogun_sayi >= 3:
        d, _items = yogun_gun
        lines.append(f"**⚠️ PİK YOĞUNLUK:** {d.day} {aylar_tr.get(d.month, '?')} — "
                     f"{yogun_sayi} earnings aynı gün. Bu günden önce pozisyon küçültme değerlendirilmeli.")
        lines.append("")

    return "\n".join(lines)


# ── 5. SEKTÖR ROTASYON ──────────────────────────────────────────────────────

# 11 ana SPDR sektör ETF'i + bonus
SEKTOR_ETF = {
    "XLK":  "Teknoloji",
    "XLV":  "Sağlık",
    "XLF":  "Finans",
    "XLY":  "Tüketici (Lüks)",
    "XLP":  "Tüketici (Defansif)",
    "XLE":  "Enerji",
    "XLI":  "Sanayi",
    "XLB":  "Hammadde",
    "XLU":  "Kamu Hizmeti",
    "XLRE": "Gayrimenkul",
    "XLC":  "İletişim",
    "GLD":  "Altın",
    "ITA":  "Savunma",
}


def sektor_rotasyon_blogu(portfolios: dict) -> str:
    """Sektör ETF performansı vs portföy ağırlığı."""
    import requests
    fmp_key = os.environ.get("FMP_API_KEY", "")
    if not fmp_key:
        return ""

    # FMP /stable/quote multi-sembol BOŞ liste döner — tek tek sorgu
    quote_map = {}
    for etf in SEKTOR_ETF.keys():
        try:
            url = f"https://financialmodelingprep.com/stable/quote?symbol={etf}&apikey={fmp_key}"
            r = requests.get(url, timeout=8)
            if r.status_code == 200:
                d = r.json()
                if isinstance(d, list) and d:
                    quote_map[etf] = d[0]
        except Exception:
            continue

    if not quote_map:
        return ""

    # Portföy sektör ağırlığı (yatırılı sermaye üzerinden)
    sektor_deger = {}
    yatirili_toplam = 0
    for pf in portfolios.values():
        for poz in pf.get("pozisyonlar", []):
            sym = poz.get("sembol")
            if sym in (None, "_template"):
                continue
            adet = poz.get("adet", 0) or 0
            cf = poz.get("guncel_fiyat", 0) or 0
            deger = adet * cf
            if deger <= 0:
                continue
            sek = poz.get("sektor", "")
            sektor_deger[sek] = sektor_deger.get(sek, 0) + deger
            yatirili_toplam += deger

    # FMP sektör → portföy sektör eşleşmesi (yaklaşık)
    fmp_to_pf = {
        "Teknoloji":         ["Technology", "AI Networking / Switching", "AI Bellek / DRAM", "Tech"],
        "Sağlık":            ["Healthcare", "Saglik Sigortasi"],
        "Finans":            ["Financial Services", "Banks"],
        "Tüketici (Lüks)":   ["Consumer Cyclical"],
        "Tüketici (Defansif)":["Consumer Defensive", "Tütün"],
        "Enerji":            ["Energy", "Enerji / Doğalgaz Pipeline"],
        "Sanayi":            ["Industrials"],
        "Hammadde":          ["Basic Materials", "Materials"],
        "Kamu Hizmeti":      ["Utilities"],
        "Gayrimenkul":       ["Real Estate"],
        "İletişim":          ["Communication Services"],
    }

    def pf_agirlik_for(fmp_sek_tr: str) -> float:
        adlar = fmp_to_pf.get(fmp_sek_tr, [])
        toplam = sum(sektor_deger.get(a, 0) for a in adlar)
        return (toplam / yatirili_toplam * 100) if yatirili_toplam else 0

    lines = []
    lines.append("## 1.2 SEKTÖR ROTASYON")
    lines.append("")
    lines.append("| Sektör | Bugün | Fiyat | Portföy Ağırlık | Yorum |")
    lines.append("|--------|-------|-------|----------------|-------|")

    rows = []
    for etf, sek_tr in SEKTOR_ETF.items():
        q = quote_map.get(etf)
        if not q:
            continue
        price = q.get("price", 0) or 0
        prev = q.get("previousClose", 0) or 0
        chg = ((price - prev) / prev * 100) if prev else 0
        # GLD/ITA sektörel ağırlık olarak portföye eşlenmez, ayrı kategoriler
        if etf in ("GLD", "ITA"):
            pf_w = 0
        else:
            pf_w = pf_agirlik_for(sek_tr)
        rows.append((sek_tr, etf, chg, price, pf_w))

    # En güçlü → en zayıf sırala
    rows.sort(key=lambda x: -x[2])

    for sek_tr, etf, chg, price, pf_w in rows:
        chg_str = f"{chg:+.2f}%"
        if chg > 0.5:
            yorum_emoji = "🟢"
        elif chg < -0.5:
            yorum_emoji = "🔴"
        else:
            yorum_emoji = "⚪"

        if pf_w > 25:
            yorum = "yüksek ağırlık — kâr al sinyali olabilir"
        elif pf_w > 15:
            yorum = "normal ağırlık"
        elif pf_w > 5:
            yorum = "düşük ağırlık"
        elif pf_w > 0:
            yorum = "minimal maruziyet"
        else:
            yorum = "—"

        pf_str = f"%{pf_w:.1f}" if pf_w > 0 else "—"
        lines.append(f"| {sek_tr} ({etf}) | {yorum_emoji} {chg_str} | ${price:.2f} | {pf_str} | {yorum} |")

    lines.append("")
    return "\n".join(lines)


# ── ANA FONKSİYON: tüm zenginleştirme ───────────────────────────────────────

def kapanis_zenginlestirici(portfolios: dict, seans_tarihi: str | None = None) -> str:
    """Tüm 5 ek bağlamı tek metinde birleştir.

    Closing prompt'una doğrudan yapıştırılabilir.
    seans_tarihi None ise bugün (TR) kullanılır.
    """
    if seans_tarihi is None:
        now_tr = datetime.now(TR_TZ)
        if now_tr.hour < 6:
            seans_tarihi = (now_tr - timedelta(days=1)).strftime("%Y-%m-%d")
        else:
            seans_tarihi = now_tr.strftime("%Y-%m-%d")

    bloklar = []

    # 3 — Risk panosu (her zaman, history yazımı için kritik)
    try:
        b = risk_panosu_blogu(portfolios, seans_tarihi)
        if b:
            bloklar.append(b)
    except Exception as e:
        print(f"[ClosingEnrichment] risk_panosu hata: {e}")

    # 5 — Sektör rotasyon
    try:
        b = sektor_rotasyon_blogu(portfolios)
        if b:
            bloklar.append(b)
    except Exception as e:
        print(f"[ClosingEnrichment] sektor_rotasyon hata: {e}")

    # 1 — İşlem akışı
    try:
        b = islem_akisi_blogu(seans_tarihi)
        if b:
            bloklar.append(b)
    except Exception as e:
        print(f"[ClosingEnrichment] islem_akisi hata: {e}")

    # 2 — Plan vs gerçekleşme
    try:
        b = plan_gerceklesme_blogu(seans_tarihi)
        if b:
            bloklar.append(b)
    except Exception as e:
        print(f"[ClosingEnrichment] plan_gerceklesme hata: {e}")

    # 4 — Erken uyarı
    try:
        b = erken_uyari_blogu(portfolios, seans_tarihi)
        if b:
            bloklar.append(b)
    except Exception as e:
        print(f"[ClosingEnrichment] erken_uyari hata: {e}")

    if not bloklar:
        return ""

    return "\n---\n\n".join(bloklar) + "\n"


if __name__ == "__main__":
    # Manuel test
    import sys
    portfolios = {}
    for p in ["balanced", "aggressive", "dividend"]:
        path = REPO_ROOT / "data" / "portfolios" / f"{p}.json"
        if path.exists():
            portfolios[p] = json.load(open(path, encoding="utf-8"))

    if "--gun" in sys.argv:
        idx = sys.argv.index("--gun")
        seans = sys.argv[idx+1]
    else:
        seans = None

    print(kapanis_zenginlestirici(portfolios, seans))
