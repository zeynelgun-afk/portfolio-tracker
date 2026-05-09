#!/usr/bin/env python3
"""
Finzora AI — Sonuç Takip Sistemi
İki görevi otomatik yapar:
  1. BILANÇO TRACKER: bilançodan sonra EPS/gelir gerçekleşen → MD + index güncelle
  2. RADAR TRACKER: haber tespitinden 5 gün sonra fiyat tepkisi → MD + index güncelle

Kullanım:
  python scripts/result_tracker.py           # normal çalıştır
  python scripts/result_tracker.py --dry-run # değişiklik yapma, sadece göster
"""

import os
import sys
import json
import time
import base64
import argparse
import requests
from datetime import datetime, timedelta, timezone, date

# ── Config ──────────────────────────────────────────────────────────────────
FMP_KEY         = os.environ.get("FMP_API_KEY", "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8")
GH_TOKEN        = os.environ.get("GH_TOKEN", "")
BOT_TOKEN       = os.environ.get("TELEGRAM_BOT_TOKEN", "")
PRIVATE_CHAT_ID = os.environ.get("TELEGRAM_PRIVATE_ID", "1403072107")

GH_REPO     = "zeynelgun-afk/portfolio-tracker"
GH_API      = "https://api.github.com"
FMP_BASE    = "https://financialmodelingprep.com/stable"
TG_API      = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Radar haberi için kaç gün sonra fiyat tepkisini kontrol et
RADAR_CHECK_DAYS = 5

# ── Yardımcı ────────────────────────────────────────────────────────────────
def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)

# 10 May 2026 — canonical fmp_client'a migrasyon. Pre-throttle (1.5s sleep) korundu;
# canonical retry mantığı bunun üstüne eklenir. Boş veride [] döner (geri uyum).
import sys as _sys_fmp
from pathlib import Path as _Path_fmp

_AGENT_DIR = _Path_fmp(__file__).resolve().parent.parent / "agent"
if str(_AGENT_DIR) not in _sys_fmp.path:
    _sys_fmp.path.insert(0, str(_AGENT_DIR))

try:
    from fmp_client import fmp_get as _canonical_fmp_get

    def fmp_get(endpoint, params=None):
        """fmp_client wrapper + pre-throttle. Boş veride [] döner."""
        time.sleep(1.5)  # legacy pre-throttle, korundu
        result = _canonical_fmp_get(endpoint, params)
        return result if result else []
except ImportError:
    def fmp_get(endpoint, params=None):
        p = {"apikey": FMP_KEY, **(params or {})}
        try:
            time.sleep(1.5)
            r = requests.get(f"{FMP_BASE}/{endpoint}", params=p, timeout=15)
            if r.status_code == 200 and r.text.strip() and "DNS" not in r.text:
                return r.json()
        except Exception as e:
            log(f"FMP hata ({endpoint}): {e}")
        return []

def send_telegram(msg):
    if not BOT_TOKEN:
        return
    try:
        requests.post(
            f"{TG_API}/sendMessage",
            json={"chat_id": PRIVATE_CHAT_ID, "text": msg,
                  "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=10,
        )
    except Exception:
        pass

# ── GitHub Dosya İşlemleri ───────────────────────────────────────────────────
def gh_read(path):
    """GitHub'dan dosyayı oku. (içerik, sha) döndür."""
    if not GH_TOKEN:
        return None, None
    r = requests.get(
        f"{GH_API}/repos/{GH_REPO}/contents/{path}",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        timeout=10,
    )
    if r.status_code == 200:
        data = r.json()
        return base64.b64decode(data["content"]).decode(), data["sha"]
    return None, None

def gh_write(path, content, message, sha=None, dry_run=False):
    """GitHub'a dosya yaz."""
    if dry_run:
        log(f"  [DRY] {path}")
        return True
    if not GH_TOKEN:
        log("GH_TOKEN eksik")
        return False
    payload = {
        "message": message,
        "content": base64.b64encode(content.encode()).decode(),
        "committer": {"name": "Finzora AI", "email": "zeynelgun@users.noreply.github.com"},
    }
    if sha:
        payload["sha"] = sha
    r = requests.put(
        f"{GH_API}/repos/{GH_REPO}/contents/{path}",
        headers={"Authorization": f"token {GH_TOKEN}", "Accept": "application/vnd.github+json"},
        json=payload, timeout=15,
    )
    return r.status_code in [200, 201]

# ── FMP Veri Çekimi ──────────────────────────────────────────────────────────
def get_eps_actual(ticker, tarih_str):
    """Bilanço tarihine yakın EPS gerçekleşen ve gelir verisini FMP'den çek."""
    try:
        d = datetime.strptime(tarih_str, "%Y-%m-%d")
        from_d = (d - timedelta(days=3)).strftime("%Y-%m-%d")
        to_d   = (d + timedelta(days=3)).strftime("%Y-%m-%d")
    except Exception:
        return None

    data = fmp_get("earnings-calendar", {"from": from_d, "to": to_d})
    if not isinstance(data, list):
        return None

    for item in data:
        if item.get("symbol") == ticker and item.get("epsActual") is not None:
            return {
                "eps_actual":      round(float(item["epsActual"]), 2),
                "eps_estimated":   round(float(item.get("epsEstimated") or 0), 2),
                "revenue_actual":  round(float(item.get("revenueActual") or 0) / 1e6, 1),
                "revenue_est":     round(float(item.get("revenueEstimated") or 0) / 1e6, 1),
            }
    return None

def get_price_on(ticker, tarih_str):
    """Belirli tarihteki kapanış fiyatını çek."""
    try:
        d   = datetime.strptime(tarih_str, "%Y-%m-%d")
        frm = (d - timedelta(days=5)).strftime("%Y-%m-%d")
        to  = (d + timedelta(days=2)).strftime("%Y-%m-%d")
    except Exception:
        return None

    data = fmp_get("historical-price-eod/full", {"symbol": ticker, "from": frm, "to": to})
    if not isinstance(data, list) or not data:
        return None

    # En yakın tarihi bul
    target = datetime.strptime(tarih_str, "%Y-%m-%d").date()
    best   = None
    for item in data:
        try:
            item_d = datetime.strptime(item["date"][:10], "%Y-%m-%d").date()
            if item_d <= target + timedelta(days=2):
                if best is None or abs((item_d - target).days) < abs((best[0] - target).days):
                    best = (item_d, float(item.get("close", 0)))
        except Exception:
            continue
    return best[1] if best else None

def get_current_price(ticker):
    """Anlık fiyat çek."""
    data = fmp_get("batch-quote", {"symbols": ticker})
    if isinstance(data, list) and data:
        return float(data[0].get("price", 0))
    return None

# ── MD Güncelleyici ──────────────────────────────────────────────────────────
def update_md_bilanco(md_content, gerceklesen):
    """Bilanço sonuçları tablosunu MD içinde güncelle."""
    eps_a   = gerceklesen.get("eps")
    eps_e   = gerceklesen.get("eps_beklenti")
    surp    = gerceklesen.get("surpriz_pct")
    gelir_a = gerceklesen.get("gelir_m")
    gelir_e = gerceklesen.get("gelir_beklenti_m")
    tepki   = gerceklesen.get("fiyat_tepkisi_pct")
    senaryo = gerceklesen.get("senaryo", "—")
    dogru   = gerceklesen.get("dogru_tahmin")
    ders    = gerceklesen.get("ders", "—")

    surp_str   = f"%{surp:+.1f}" if surp is not None else "—"
    tepki_str  = f"%{tepki:+.1f}" if tepki is not None else "—"
    dogru_str  = "✅ Evet" if dogru else ("❌ Hayır" if dogru is False else "—")

    yeni_tablo = f"""## Bilanço Sonrası Güncelleme

| Alan | Beklenti | Gerçekleşen | Fark |
|---|---|---|---|
| EPS | ${eps_e or '—'} | ${eps_a or '—'} | {surp_str} |
| Gelir | ${gelir_e or '—'}M | ${gelir_a or '—'}M | — |
| Fiyat Tepkisi | — | {tepki_str} | — |
| Senaryo | — | {senaryo} | — |
| Doğru Tahmin | — | {dogru_str} | — |
| Ders | {ders} | | |"""

    # Eski "Bilanço Sonrası Güncelleme" bölümünü bul ve değiştir
    if "## Bilanço Sonrası Güncelleme" in md_content:
        idx = md_content.index("## Bilanço Sonrası Güncelleme")
        md_content = md_content[:idx] + yeni_tablo + "\n\n---\n\n*Finzora AI tarafından üretilmiştir. Yatırım tavsiyesi değildir.*"
    else:
        md_content = md_content.rstrip() + "\n\n" + yeni_tablo

    return md_content

def update_md_radar(md_content, gerceklesen, ticker):
    """Radar fiyat tepkisi tablosunu MD içinde güncelle."""
    tespit  = gerceklesen.get("tespit_fiyati")
    simdiki = gerceklesen.get("simdiki_fiyat")
    degisim = gerceklesen.get("fiyat_tepkisi_pct")
    tuttu   = gerceklesen.get("tez_tuttu")
    ders    = gerceklesen.get("ders", "—")

    degisim_str = f"%{degisim:+.1f}" if degisim is not None else "—"
    tuttu_str   = "✅ Tuttu" if tuttu else ("❌ Tutmadı" if tuttu is False else "⏳ İzleniyor")

    yeni_tablo = f"""| Alan | Değer |
|---|---|
| Tespit Fiyatı | ${tespit or '—'} |
| Şimdiki Fiyat ({datetime.now().strftime('%d %b')}) | ${simdiki or '—'} |
| Fiyat Değişimi | {degisim_str} |
| Tez Tuttu mu | {tuttu_str} |
| Ders | {ders} |"""

    eski = """| Alan | Değer |
|---|---|
| Tespit Fiyatı | — |
| Fiyat Tepkisi | — |
| Tez Tuttu mu | — |
| Ders | — |"""

    if eski in md_content:
        md_content = md_content.replace(eski, yeni_tablo)
    elif "> *Fiyat tepkisi ve gelişmeler buraya eklenecek*" in md_content:
        md_content = md_content.replace(
            "> *Fiyat tepkisi ve gelişmeler buraya eklenecek*\n\n" + eski,
            f"> *{datetime.now().strftime('%d %b %Y')} tarihinde otomatik güncellendi*\n\n" + yeni_tablo
        )

    return md_content

# ── Ana Mantık: Bilanço Tracker ──────────────────────────────────────────────
def track_bilancolar(analizler, dry_run):
    """bilanco_tarihi geçmiş ve durum=='beklemede' olan analizleri güncelle."""
    bugun = date.today()
    degisiklik = []

    for analiz in analizler:
        if analiz.get("analiz_turu") != "bilanço_oncesi":
            continue
        if analiz.get("durum") not in ["beklemede"]:
            continue

        bilanco_str = analiz.get("bilanco_tarihi") or analiz.get("bülançö_tarihi")
        if not bilanco_str:
            continue

        try:
            bilanco_d = datetime.strptime(bilanco_str, "%Y-%m-%d").date()
        except Exception:
            continue

        if bilanco_d > bugun:
            log(f"  {analiz['ticker']}: bilançosu henüz gelmedi ({bilanco_str})")
            continue

        ticker = analiz["ticker"]
        log(f"  {ticker}: bilanço geçti ({bilanco_str}), veri çekiliyor...")

        # EPS gerçekleşen
        eps_data = get_eps_actual(ticker, bilanco_str)
        if not eps_data:
            log(f"  {ticker}: EPS verisi bulunamadı, atlanıyor")
            continue

        eps_a = eps_data["eps_actual"]
        eps_e = eps_data["eps_estimated"] or analiz.get("on_beklenti", {}).get("eps_konsensus", 0)
        surp  = round((eps_a - eps_e) / abs(eps_e) * 100, 1) if eps_e else None

        # Fiyat tepkisi: bilanço günü kapanış vs ertesi gün kapanış
        fiyat_bilanco = get_price_on(ticker, bilanco_str)
        ertesi_str    = (bilanco_d + timedelta(days=1)).strftime("%Y-%m-%d")
        fiyat_ertesi  = get_price_on(ticker, ertesi_str)
        tepki_pct     = None
        if fiyat_bilanco and fiyat_ertesi and fiyat_bilanco > 0:
            tepki_pct = round((fiyat_ertesi - fiyat_bilanco) / fiyat_bilanco * 100, 1)

        # Beat / Miss / In-Line
        if surp is not None:
            if surp >= 3:
                durum = "beat"
            elif surp <= -3:
                durum = "miss"
            else:
                durum = "in_line"
        else:
            durum = "guncellendi"

        # Senaryo eşleştir
        on = analiz.get("on_beklenti", {})
        senaryo = "—"
        if tepki_pct is not None:
            a_pct = on.get("senaryo_a_olasilik", 0)
            b_pct = on.get("senaryo_b_olasilik", 0)
            if surp and surp >= 5 and tepki_pct >= 4:
                senaryo = "A — Beat & Raise"
            elif surp and surp >= 0 and tepki_pct >= 0:
                senaryo = "B — In-Line Beat"
            else:
                senaryo = "C — Miss / Düşük"

        dogru_tahmin = None
        if durum == "beat" and on.get("senaryo_a_olasilik", 0) >= 0.35:
            dogru_tahmin = True
        elif durum == "miss" and on.get("senaryo_c_olasilik", 0) <= 0.3:
            dogru_tahmin = False

        ders = f"{'Beat' if durum=='beat' else 'Miss'} | Sürpriz {surp:+.1f}% | Fiyat {tepki_pct:+.1f}%" if surp and tepki_pct else "Veri eksik"

        # index güncelle
        analiz["durum"] = durum
        analiz["gerceklesen"] = {
            "eps":               eps_a,
            "eps_beklenti":      eps_e,
            "surpriz_pct":       surp,
            "gelir_m":           eps_data.get("revenue_actual"),
            "gelir_beklenti_m":  eps_data.get("revenue_est"),
            "fiyat_tepkisi_pct": tepki_pct,
            "senaryo":           senaryo,
            "dogru_tahmin":      dogru_tahmin,
            "ders":              ders,
        }

        # MD güncelle
        md_path = analiz.get("dosya")
        if md_path:
            md_content, md_sha = gh_read(md_path)
            if md_content:
                yeni_md = update_md_bilanco(md_content, analiz["gerceklesen"])
                ok = gh_write(
                    md_path, yeni_md,
                    f"[TRACKER] {ticker} bilanço sonuçları: {durum.upper()} | EPS {surp:+.1f}%",
                    sha=md_sha, dry_run=dry_run,
                )
                log(f"  {ticker} MD: {'OK' if ok else 'HATA'}")

        emoji = "✅" if durum == "beat" else ("❌" if durum == "miss" else "➡️")
        degisiklik.append(
            f"{emoji} <b>{ticker} — {durum.upper()}</b>\n"
            f"EPS: ${eps_a} vs ${eps_e} ({surp:+.1f}%)\n"
            f"Fiyat Tepkisi: {tepki_pct:+.1f}%\n"
            f"Senaryo: {senaryo}"
        )

        log(f"  {ticker}: {durum} | EPS sürpriz {surp:+.1f}% | Fiyat {tepki_pct:+.1f}%")

    return degisiklik

# ── Ana Mantık: Radar Tracker ────────────────────────────────────────────────
def track_radar(analizler, dry_run):
    """Haber radarı tespitlerinde 5 gün sonra fiyat tepkisini kontrol et."""
    bugun = date.today()
    degisiklik = []

    for analiz in analizler:
        if analiz.get("analiz_turu") != "haber_radar":
            continue
        if analiz.get("gerceklesen", {}).get("fiyat_tepkisi_pct") is not None:
            continue  # zaten güncellendi

        analiz_str = analiz.get("analiz_tarihi", "")
        if not analiz_str:
            continue

        try:
            analiz_d = datetime.strptime(analiz_str, "%Y-%m-%d").date()
        except Exception:
            continue

        gecen_gun = (bugun - analiz_d).days
        if gecen_gun < RADAR_CHECK_DAYS:
            log(f"  Radar {analiz['id']}: {gecen_gun} gün geçti, {RADAR_CHECK_DAYS} bekleniyor")
            continue

        ticker = analiz.get("ticker", "")
        if not ticker or ticker == "RADAR":
            continue

        log(f"  Radar {ticker}: {gecen_gun} gün geçti, fiyat kontrol ediliyor...")

        # Tespit günü fiyatı
        tespit_fiyat = get_price_on(ticker, analiz_str)
        # Şimdiki fiyat
        simdiki = get_current_price(ticker)

        degisim = None
        tez_tuttu = None

        if tespit_fiyat and simdiki and tespit_fiyat > 0:
            degisim = round((simdiki - tespit_fiyat) / tespit_fiyat * 100, 1)
            # Yon bullish ise pozitif fiyat = tez tuttu
            yon = analiz.get("etiketler", [])
            if "bullish" in yon:
                tez_tuttu = degisim >= 2
            elif "bearish" in yon:
                tez_tuttu = degisim <= -2

        ders = f"{gecen_gun} günde {degisim:+.1f}%" if degisim is not None else "Veri eksik"

        analiz["gerceklesen"] = {
            "tespit_fiyati":      round(tespit_fiyat, 2) if tespit_fiyat else None,
            "simdiki_fiyat":      round(simdiki, 2) if simdiki else None,
            "fiyat_tepkisi_pct":  degisim,
            "tez_tuttu":          tez_tuttu,
            "ders":               ders,
        }

        # MD güncelle
        md_path = analiz.get("dosya")
        if md_path:
            md_content, md_sha = gh_read(md_path)
            if md_content:
                yeni_md = update_md_radar(md_content, analiz["gerceklesen"], ticker)
                ok = gh_write(
                    md_path, yeni_md,
                    f"[TRACKER] {ticker} radar tepkisi: {degisim:+.1f}% ({gecen_gun}g)",
                    sha=md_sha, dry_run=dry_run,
                )
                log(f"  {ticker} MD: {'OK' if ok else 'HATA'}")

        emoji = "✅" if tez_tuttu else ("❌" if tez_tuttu is False else "➡️")
        degisiklik.append(
            f"{emoji} <b>{ticker} Radar Güncellemesi</b>\n"
            f"Tespit: ${tespit_fiyat:.2f} → Şimdi: ${simdiki:.2f}\n"
            f"{gecen_gun} gün sonra: {degisim:+.1f}%"
        )

        log(f"  {ticker}: {degisim:+.1f}% ({gecen_gun} gün) | Tez: {'✓' if tez_tuttu else '✗'}")

    return degisiklik

# ── index.json Güncelle ──────────────────────────────────────────────────────
def guncelle_istatistikler(index):
    """Doğru tahmin oranını ve sayaçları güncelle."""
    tahminler = [
        a for a in index["analizler"]
        if a.get("gerceklesen", {}).get("dogru_tahmin") is not None
    ]
    if tahminler:
        dogru = sum(1 for a in tahminler if a["gerceklesen"]["dogru_tahmin"])
        index["dogru_tahmin_orani"] = round(dogru / len(tahminler), 2)

    index["beat_tahmin"]   = sum(1 for a in index["analizler"] if a.get("durum") == "beat")
    index["miss_tahmin"]   = sum(1 for a in index["analizler"] if a.get("durum") == "miss")
    index["beklemede"]     = sum(1 for a in index["analizler"] if a.get("durum") == "beklemede")
    index["aktif_izleme"]  = sum(1 for a in index["analizler"] if a.get("durum") == "aktif_izleme")
    index["son_guncelleme"] = date.today().strftime("%Y-%m-%d")
    return index

# ── Main ─────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    log("=== Finzora Sonuç Takip Sistemi başlıyor ===")

    # index.json oku
    idx_path = "data/research/index.json"
    idx_raw, idx_sha = gh_read(idx_path)
    if not idx_raw:
        log("HATA: index.json okunamadı")
        return

    index = json.loads(idx_raw)
    analizler = index.get("analizler", [])
    log(f"Toplam analiz: {len(analizler)}")

    tum_degisiklikler = []

    # 1. Bilanço tracker
    log("── Bilanço Tracker ──")
    bilanco_deg = track_bilancolar(analizler, args.dry_run)
    tum_degisiklikler.extend(bilanco_deg)

    # 2. Radar tracker
    log("── Radar Tracker ──")
    radar_deg = track_radar(analizler, args.dry_run)
    tum_degisiklikler.extend(radar_deg)

    if not tum_degisiklikler:
        log("Güncellenecek analiz yok.")
        return

    # 3. index.json kaydet
    index = guncelle_istatistikler(index)
    ok = gh_write(
        idx_path,
        json.dumps(index, ensure_ascii=False, indent=2),
        f"[TRACKER] Sonuçlar güncellendi — {date.today()}",
        sha=idx_sha,
        dry_run=args.dry_run,
    )
    log(f"index.json: {'OK' if ok else 'HATA'}")

    # 4. Telegram DM
    tarih_str = datetime.now().strftime("%d %b %Y")
    msg = f"📊 <b>Sonuç Takip — {tarih_str}</b>\n\n" + "\n\n".join(tum_degisiklikler)
    if not args.dry_run:
        send_telegram(msg)
        log("Telegram DM gönderildi ✓")
    else:
        print("\n── DRY RUN — Telegram mesajı ──")
        print(msg)

    log("=== Tamamlandı ===")

if __name__ == "__main__":
    main()
