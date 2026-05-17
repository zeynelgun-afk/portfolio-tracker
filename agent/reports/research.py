#!/usr/bin/env python3
"""
Adil Değer Skill v5.0 — Research Tracker (Etap 11)
=====================================================

data/research/index.json içindeki aktif 'analizler' için:
1. Günlük (23:30): FMP'den güncel fiyat çek, 'gerceklesen' alanını güncelle
2. Haftalık (Pazar 14:00): Skill performans özeti Telegram DM'e gönder

Çalışma:
    python3 scripts/research_tracker.py --daily        # Günlük güncelleme (sessiz)
    python3 scripts/research_tracker.py --weekly       # Haftalık özet (Telegram DM)
    python3 scripts/research_tracker.py --status       # Mevcut durum dump (debug)

Railway scheduler entegrasyonu:
    - Günlük 23:30 result_tracker slotunda: --daily çağrısı
    - Pazar 14:00 yeni slot: --weekly çağrısı

v5.0 — 11 Mayıs 2026
finzora ai
"""

import os
import sys
import json
import requests
from datetime import datetime, timedelta
from pathlib import Path

API_KEY = os.environ.get("FMP_API_KEY", "")
BASE = "https://financialmodelingprep.com/stable"
HEADERS = {"User-Agent": "finzora-research-tracker/5.0"}

REPO_ROOT = Path(__file__).resolve().parents[2]
INDEX_PATH = REPO_ROOT / "data" / "research" / "index.json"

# Telegram (optional)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN") or os.environ.get("TELEGRAM_TOKEN", "")
PRIVATE_CHAT = os.environ.get("TELEGRAM_DM_CHAT_ID") or os.environ.get("TELEGRAM_PRIVATE_CHAT", "")  # Zeynel DM


def fetch_quote(ticker):
    """FMP'den güncel fiyat al."""
    try:
        r = requests.get(
            f"{BASE}/quote",
            params={"symbol": ticker, "apikey": API_KEY},
            headers=HEADERS,
            timeout=15,
        )
        if r.status_code != 200:
            return None
        data = r.json()
        if isinstance(data, list) and data:
            return data[0]
    except Exception as e:
        print(f"⚠️ {ticker} fiyat alınamadı: {e}", file=sys.stderr)
    return None


def tg_send_dm(text, parse_mode="HTML"):
    """Telegram DM'e gönder."""
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                "chat_id": PRIVATE_CHAT,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True,
            },
            timeout=15,
        )
        if r.status_code == 200:
            return True
        print(f"⚠️ Telegram gönderim başarısız: {r.status_code} {r.text[:200]}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Telegram hata: {e}", file=sys.stderr)
    return False


# ============================================================================
# GÜNLÜK TAKİP
# ============================================================================

def update_entry_realized(entry, quote):
    """Tek entry için 'gerceklesen' alanını güncelle.
    
    Returns: (updated, status_change_label)
        updated: bool — değişiklik yapıldı mı
        status_change_label: str | None — durum değişti mi
    """
    simdiki_fiyat = quote.get("price")
    if not simdiki_fiyat:
        return False, None
    
    tespit_fiyati = entry.get("analiz_fiyati")
    if not tespit_fiyati or tespit_fiyati <= 0:
        return False, None
    
    tepki_pct = (simdiki_fiyat - tespit_fiyati) / tespit_fiyati * 100
    
    # Gün sayısı
    try:
        analiz_dt = datetime.strptime(entry.get("analiz_tarihi", ""), "%Y-%m-%d")
        gun_sayisi = (datetime.now() - analiz_dt).days
    except ValueError:
        gun_sayisi = None
    
    # Hedef/Stop kontrolü
    giris = entry.get("giris_plani", {}) or {}
    stop = giris.get("stop_loss")
    hedef_1 = giris.get("hedef_1")
    hedef_2 = giris.get("hedef_2")
    
    on = entry.get("on_beklenti", {})
    bear_hedef = on.get("senaryo_ayi", {}).get("fiyat_hedef")
    bull_hedef = on.get("senaryo_boga", {}).get("fiyat_hedef")
    
    tez_tuttu = entry.get("gerceklesen", {}).get("tez_tuttu")  # mevcut durum
    ders = entry.get("gerceklesen", {}).get("ders")
    status_change = None
    
    if tez_tuttu is None or tez_tuttu == "belirsiz":
        # Henüz sonuçlanmamış — kontrol et
        if stop and simdiki_fiyat <= stop:
            tez_tuttu = False
            ders = f"Stop ${stop:.2f} kırıldı {gun_sayisi}. günde, fiyat ${simdiki_fiyat:.2f} (-%{abs(tepki_pct):.1f})"
            status_change = "stop_kirildi"
        elif hedef_2 and simdiki_fiyat >= hedef_2:
            tez_tuttu = True
            ders = f"Boğa hedefi ${hedef_2:.2f} {gun_sayisi}. günde tutturuldu, fiyat ${simdiki_fiyat:.2f} (+%{tepki_pct:.1f})"
            status_change = "hedef_2"
        elif hedef_1 and simdiki_fiyat >= hedef_1:
            tez_tuttu = True
            ders = f"Baz hedef ${hedef_1:.2f} {gun_sayisi}. günde tutturuldu, fiyat ${simdiki_fiyat:.2f} (+%{tepki_pct:.1f})"
            status_change = "hedef_1"
        elif gun_sayisi and gun_sayisi > 180:
            tez_tuttu = "belirsiz"
            ders = f"180 gün geçti, fiyat %{tepki_pct:+.1f} (${simdiki_fiyat:.2f}). Ne hedef ne stop tetiklendi — tez yavaş gelişiyor veya yanılmış"
            status_change = "180gun_belirsiz"
    
    # Güncelle
    g = entry.setdefault("gerceklesen", {})
    g["simdiki_fiyat"] = round(simdiki_fiyat, 2)
    g["fiyat_tepkisi_pct"] = round(tepki_pct, 1)
    g["gun_sayisi"] = gun_sayisi
    g["son_kontrol"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    g["tez_tuttu"] = tez_tuttu
    if ders:
        g["ders"] = ders
    
    # Durum değişikliği
    if status_change in ("stop_kirildi", "hedef_1", "hedef_2"):
        entry["durum"] = "kapandi"
    
    return True, status_change


def daily_update(verbose=False):
    """Tüm aktif analizler için günlük güncelleme."""
    if not INDEX_PATH.exists():
        print(f"❌ {INDEX_PATH} bulunamadı")
        return
    
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    aktif_analizler = [a for a in index_data.get("analizler", [])
                       if a.get("durum") in ("aktif_izleme", None)
                       and a.get("analiz_turu") == "adil_deger_hesabi"]
    
    if not aktif_analizler:
        if verbose:
            print("Aktif analiz yok")
        return
    
    print(f"📊 Günlük güncelleme: {len(aktif_analizler)} aktif analiz", file=sys.stderr)
    
    status_changes = []
    updated_count = 0
    
    for entry in aktif_analizler:
        ticker = entry.get("ticker")
        if not ticker:
            continue
        
        quote = fetch_quote(ticker)
        if not quote:
            if verbose:
                print(f"  ⚠️ {ticker}: fiyat alınamadı")
            continue
        
        updated, status_change = update_entry_realized(entry, quote)
        if updated:
            updated_count += 1
        
        if status_change:
            status_changes.append({
                "ticker": ticker,
                "change": status_change,
                "entry": entry,
            })
            if verbose:
                print(f"  📌 {ticker}: durum değişti → {status_change}")
    
    # Üst seviye sayaçları güncelle
    index_data["aktif_izleme"] = sum(1 for a in index_data["analizler"]
                                      if a.get("durum") in ("aktif_izleme", None))
    
    # Yaz
    with open(INDEX_PATH, "w", encoding="utf-8") as f:
        json.dump(index_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ {updated_count} analiz güncellendi, {len(status_changes)} durum değişikliği", file=sys.stderr)
    
    # Önemli durum değişikliklerini DM'e bildir
    if status_changes:
        send_status_alerts(status_changes)
    
    return status_changes


def send_status_alerts(changes):
    """Stop/hedef tetiklendiyse Telegram DM'e uyarı."""
    lines = []
    lines.append("<b>🔔 Adil Değer Takip — Durum Değişiklikleri</b>")
    lines.append("")
    
    for c in changes:
        ticker = c["ticker"]
        change = c["change"]
        entry = c["entry"]
        g = entry.get("gerceklesen", {})
        simdiki = g.get("simdiki_fiyat", 0)
        tepki = g.get("fiyat_tepkisi_pct", 0)
        gun = g.get("gun_sayisi", 0)
        
        emoji = {
            "stop_kirildi": "🔴",
            "hedef_1": "🟢",
            "hedef_2": "🚀",
            "180gun_belirsiz": "🟡",
        }.get(change, "ℹ️")
        
        label = {
            "stop_kirildi": "STOP KIRILDI",
            "hedef_1": "BAZ HEDEF TUTTURULDU",
            "hedef_2": "BOĞA HEDEF TUTTURULDU",
            "180gun_belirsiz": "180 GÜN — BELİRSİZ",
        }.get(change, change)
        
        lines.append(f"{emoji} <b>{ticker}</b> — {label}")
        lines.append(f"   Fiyat: ${simdiki:.2f}  (%{tepki:+.1f}, {gun} gün)")
        lines.append(f"   <i>{g.get('ders', '')}</i>")
        lines.append("")
    
    tg_send_dm("\n".join(lines))


# ============================================================================
# HAFTALIK ÖZET
# ============================================================================

def weekly_summary():
    """Pazar günü skill performansı özet Telegram DM'e."""
    if not INDEX_PATH.exists():
        print(f"❌ {INDEX_PATH} bulunamadı")
        return
    
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    today = datetime.now()
    bir_hafta_once = today - timedelta(days=7)
    otuz_gun_once = today - timedelta(days=30)
    
    analizler = [a for a in index_data.get("analizler", [])
                 if a.get("analiz_turu") == "adil_deger_hesabi"
                 and a.get("v5_sinyaller")]  # sadece v5.0 üretimi
    
    if not analizler:
        tg_send_dm("📊 <b>Adil Değer Skill — Haftalık Özet</b>\n\nHenüz v5.0 üretiminden analiz yok.")
        return
    
    def parse_date(s):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except (ValueError, TypeError):
            return None
    
    # Son 30 gün kaydedilenler
    son_30 = [a for a in analizler if parse_date(a.get("analiz_tarihi"))
              and parse_date(a["analiz_tarihi"]) >= otuz_gun_once]
    
    if not son_30:
        tg_send_dm("📊 <b>Adil Değer Skill — Haftalık Özet</b>\n\nSon 30 günde v5.0 üretiminden analiz yok.")
        return
    
    # İstatistikler
    toplam = len(son_30)
    aktif = sum(1 for a in son_30 if a.get("durum") in ("aktif_izleme", None))
    kapanmis = sum(1 for a in son_30 if a.get("durum") == "kapandi")
    
    hedef_tutturanlar = [a for a in son_30 if a.get("gerceklesen", {}).get("tez_tuttu") is True]
    stop_kiranlar = [a for a in son_30 if a.get("gerceklesen", {}).get("tez_tuttu") is False]
    belirsiz = [a for a in son_30 if a.get("gerceklesen", {}).get("tez_tuttu") == "belirsiz"]
    bekleyenler = [a for a in son_30 if a.get("gerceklesen", {}).get("tez_tuttu") is None]
    
    # Hit rate (kapanmış analizler içinde)
    kapanmis_set = hedef_tutturanlar + stop_kiranlar
    hit_rate = (len(hedef_tutturanlar) / len(kapanmis_set) * 100) if kapanmis_set else None
    
    # Ortalama getiri
    getiriler = [a.get("gerceklesen", {}).get("fiyat_tepkisi_pct")
                 for a in son_30 if a.get("gerceklesen", {}).get("fiyat_tepkisi_pct") is not None]
    ortalama_getiri = sum(getiriler) / len(getiriler) if getiriler else 0
    
    # Karar bazlı analiz
    al_kararlari = [a for a in son_30 if "AL" in (a.get("karar", "") or "").upper()]
    gec_kararlari = [a for a in son_30 if "GEÇ" in (a.get("karar", "") or "").upper() or "KAÇIN" in (a.get("karar", "") or "").upper()]
    
    al_avg_getiri = (sum(a.get("gerceklesen", {}).get("fiyat_tepkisi_pct", 0) for a in al_kararlari) / len(al_kararlari)) if al_kararlari else 0
    
    # Mod bazlı
    growth_count = sum(1 for a in son_30 if (a.get("adil_deger", {}) or {}).get("mod") == "GROWTH")
    blended_count = sum(1 for a in son_30 if (a.get("adil_deger", {}) or {}).get("mod") == "BLENDED")
    
    # Confidence bazlı
    yuksek_conf = [a for a in son_30 if (a.get("adil_deger", {}) or {}).get("confidence") == "YUKSEK"]
    
    # Mesaj kur
    lines = []
    lines.append("<b>📊 Adil Değer Skill v5.0 — Haftalık Performans</b>")
    lines.append(f"<i>{bir_hafta_once.strftime('%d %b')} → {today.strftime('%d %b %Y')}</i>")
    lines.append("")
    
    lines.append("<b>📈 SON 30 GÜN ÖZET:</b>")
    lines.append(f"  Toplam analiz: {toplam}")
    lines.append(f"  • Aktif izleme: {aktif}")
    lines.append(f"  • Kapanmış: {kapanmis}")
    lines.append(f"  • Hedef tutturanlar: {len(hedef_tutturanlar)}")
    lines.append(f"  • Stop kıranlar: {len(stop_kiranlar)}")
    lines.append(f"  • Belirsiz (180+ gün): {len(belirsiz)}")
    
    if hit_rate is not None:
        lines.append(f"  • <b>Hit rate: %{hit_rate:.0f}</b> ({len(hedef_tutturanlar)}/{len(kapanmis_set)})")
    
    lines.append(f"  • Ortalama getiri: %{ortalama_getiri:+.1f}")
    lines.append("")
    
    # Mod dağılımı
    lines.append("<b>🎭 Mod Dağılımı:</b>")
    lines.append(f"  GROWTH: {growth_count}  |  BLENDED: {blended_count}")
    if al_kararlari:
        lines.append(f"  AL kararı ortalama getirisi: %{al_avg_getiri:+.1f} ({len(al_kararlari)} hisse)")
    lines.append("")
    
    # Başarılar
    if hedef_tutturanlar:
        lines.append("<b>🟢 BAŞARILAR:</b>")
        sorted_succ = sorted(hedef_tutturanlar,
                             key=lambda a: a.get("gerceklesen", {}).get("fiyat_tepkisi_pct", 0),
                             reverse=True)[:5]
        for a in sorted_succ:
            ticker = a.get("ticker")
            g = a.get("gerceklesen", {})
            gun = g.get("gun_sayisi", 0)
            tepki = g.get("fiyat_tepkisi_pct", 0)
            karar = a.get("karar", "")
            lines.append(f"  {karar} <b>{ticker}</b>: {gun}g → %{tepki:+.1f}")
        lines.append("")
    
    # Başarısızlıklar
    if stop_kiranlar:
        lines.append("<b>🔴 BAŞARISIZLIKLAR:</b>")
        for a in stop_kiranlar[:5]:
            ticker = a.get("ticker")
            g = a.get("gerceklesen", {})
            gun = g.get("gun_sayisi", 0)
            tepki = g.get("fiyat_tepkisi_pct", 0)
            karar = a.get("karar", "")
            lines.append(f"  {karar} <b>{ticker}</b>: {gun}g → %{tepki:+.1f}")
            ders = g.get("ders", "")
            if ders:
                lines.append(f"    <i>{ders[:100]}</i>")
        lines.append("")
    
    # Confidence kalibrasyonu
    if yuksek_conf:
        yk_tutturan = sum(1 for a in yuksek_conf if a.get("gerceklesen", {}).get("tez_tuttu") is True)
        yk_kapanmis = sum(1 for a in yuksek_conf if a.get("gerceklesen", {}).get("tez_tuttu") in (True, False))
        if yk_kapanmis > 0:
            yk_rate = yk_tutturan / yk_kapanmis * 100
            lines.append("<b>🎯 Confidence Kalibrasyonu:</b>")
            lines.append(f"  YÜKSEK confidence: {yk_tutturan}/{yk_kapanmis} tutturdu (%{yk_rate:.0f})")
            lines.append("")
    
    # Bekleyenler (henüz takip başlamamış)
    if bekleyenler:
        lines.append(f"<i>📋 {len(bekleyenler)} analiz henüz takipte değil (yeni eklendi)</i>")
        lines.append("")
    
    lines.append("<i>Kaynak: research_tracker.py — Pazar 14:00 Railway scheduler</i>")
    lines.append("<i>finzora ai — Adil Değer Skill v5.0</i>")
    
    msg = "\n".join(lines)
    
    if len(msg) > 4096:
        msg = msg[:4090] + "\n..."
    
    print(f"📤 Haftalık özet gönderiliyor (chat_id={PRIVATE_CHAT})", file=sys.stderr)
    success = tg_send_dm(msg)
    print(f"   Gönderim: {'✅' if success else '❌'}", file=sys.stderr)


# ============================================================================
# DEBUG STATUS
# ============================================================================

def status_dump():
    """Mevcut takip durumunu göster (debug)."""
    if not INDEX_PATH.exists():
        print(f"❌ {INDEX_PATH} bulunamadı")
        return
    
    with open(INDEX_PATH, "r", encoding="utf-8") as f:
        index_data = json.load(f)
    
    analizler = [a for a in index_data.get("analizler", [])
                 if a.get("analiz_turu") == "adil_deger_hesabi"
                 and a.get("v5_sinyaller")]
    
    print(f"\n📊 v5.0 takipteki analizler: {len(analizler)}\n")
    print(f"{'Ticker':<8}{'Tarih':<14}{'Durum':<15}{'Karar':<25}{'Mevcut':<10}{'Tepki%':<10}{'Gün':<6}{'Sonuç':<15}")
    print("-" * 110)
    
    for a in analizler:
        ticker = a.get("ticker", "?")
        tarih = a.get("analiz_tarihi", "?")
        durum = a.get("durum", "?")
        karar = a.get("karar", "?")[:23]
        g = a.get("gerceklesen", {})
        simdiki = g.get("simdiki_fiyat", "—")
        tepki = g.get("fiyat_tepkisi_pct", "—")
        gun = g.get("gun_sayisi", "—")
        sonuc = g.get("tez_tuttu", "—")
        sonuc_str = {True: "✅ tuttu", False: "❌ tutmadı", "belirsiz": "🟡 belirsiz", None: "—"}.get(sonuc, str(sonuc))
        
        simdiki_str = f"${simdiki:.2f}" if isinstance(simdiki, (int, float)) else str(simdiki)
        tepki_str = f"%{tepki:+.1f}" if isinstance(tepki, (int, float)) else str(tepki)
        
        print(f"{ticker:<8}{tarih:<14}{durum:<15}{karar:<25}{simdiki_str:<10}{tepki_str:<10}{str(gun):<6}{sonuc_str:<15}")


# ============================================================================
# CLI
# ============================================================================

def main():
    if len(sys.argv) < 2:
        print("Kullanım:")
        print("  python3 research_tracker.py --daily    # Günlük fiyat güncelleme + durum kontrolü")
        print("  python3 research_tracker.py --weekly   # Pazar Telegram DM özeti")
        print("  python3 research_tracker.py --status   # Mevcut durumu listele (debug)")
        sys.exit(1)
    
    cmd = sys.argv[1]
    verbose = "--verbose" in sys.argv or "-v" in sys.argv
    
    if cmd == "--daily":
        daily_update(verbose=verbose)
    elif cmd == "--weekly":
        weekly_summary()
    elif cmd == "--status":
        status_dump()
    else:
        print(f"Bilinmeyen komut: {cmd}")
        sys.exit(1)


if __name__ == "__main__":
    main()
