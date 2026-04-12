#!/usr/bin/env python3
"""
Finzora AI — Claude Haber Analiz Ajanı (Otonom)
================================================
Portföy hisselerinin haberlerini çeker, Claude API ile tez analizi yapar
ve otomatik karar uygular. SEN KARAR VER kuralı geçerli.

Aksiyonlar:
  HOLD          — Tez bozulmamış, dokunma
  IZLE          — Belirsiz/tek kaynak, takip et
  STOP_SIKIŞTIR — stop_faz=0 → bir sonraki daily_update daha sıkı stop kurar
  KISMI_CIKIS   — Pozisyonun %25 veya %50'sini sat
  TAM_CIKIS     — Tüm pozisyonu kapat

Kullanım:
  python3 scripts/claude_haber_ajan.py            # tüm portföyler
  python3 scripts/claude_haber_ajan.py --dry-run  # uygulama, sadece göster
  python3 scripts/claude_haber_ajan.py --saat 48  # son 48 saatin haberleri
"""

import json
import os
import sys
import csv
import argparse
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from datetime import datetime, timedelta, timezone

# ── Yollar ──────────────────────────────────────────────────────────────────
BASE            = Path(__file__).parent.parent
BALANCED_JSON   = BASE / "data/portfolios/balanced.json"
AGGRESSIVE_JSON = BASE / "data/portfolios/aggressive.json"
DIVIDEND_JSON   = BASE / "data/portfolios/dividend.json"
TRANSACTIONS    = BASE / "data/transactions.csv"
LOG_FILE        = BASE / "logs/claude_haber_ajan.log"

# ── API ──────────────────────────────────────────────────────────────────────
FMP_KEY         = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
FMP_BASE        = "https://financialmodelingprep.com/stable"
CLAUDE_MODEL    = "claude-sonnet-4-6"
ANTHROPIC_URL   = "https://api.anthropic.com/v1/messages"
ANTHROPIC_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")

PORTFOY_DOSYALARI = {
    "dengeli":  BALANCED_JSON,
    "agresif":  AGGRESSIVE_JSON,
    "temettü":  DIVIDEND_JSON,
}


# ══════════════════════════════════════════════════════════════════════════════
# YARDIMCI FONKSİYONLAR
# ══════════════════════════════════════════════════════════════════════════════

def log(msg: str):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{ts}] {msg}"
    print(line)
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def fmp_get(endpoint: str, params: dict = None):
    if params is None:
        params = {}
    params["apikey"] = FMP_KEY
    qs = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{FMP_BASE}/{endpoint}?{qs}"
    try:
        with urllib.request.urlopen(url, timeout=20) as r:
            data = json.loads(r.read())
        if isinstance(data, dict) and "Error Message" in data:
            return None
        return data
    except Exception as e:
        log(f"  FMP hata ({endpoint}): {e}")
        return None


def load_json(fp: Path):
    try:
        with open(fp, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def save_json(fp: Path, data: dict):
    with open(fp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def telegram_gonder(msg: str, severity: str = "custom"):
    """telegram_notify.py üzerinden mesaj gönder."""
    try:
        script = BASE / "scripts/telegram_notify.py"
        t_type = "alert" if severity == "alert" else "custom"
        result = subprocess.run(
            ["python3", str(script), "--type", t_type, "--msg", msg],
            timeout=15, capture_output=True, text=True
        )
        if result.returncode != 0:
            log(f"  Telegram hata {result.returncode}: {result.stderr[:200]}")
    except Exception as e:
        log(f"  Telegram gönderilemedi: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 1. PORTFÖY BAĞLAM OLUŞTURMA
# ══════════════════════════════════════════════════════════════════════════════

def portfoy_ozeti() -> tuple[list[dict], dict]:
    """
    Tüm portföy pozisyonlarını yükler.
    Döndürür: (pozisyon_listesi, sembol→pozisyon_map)
    """
    pozisyonlar = []
    sembol_map = {}   # "MO:temettü" → pos dict referansı

    for tur, fp in PORTFOY_DOSYALARI.items():
        d = load_json(fp)
        if not d:
            continue
        for pos in d.get("pozisyonlar", []):
            ozet = {
                "sembol":       pos["sembol"],
                "portfoy":      tur,
                "portfoy_fp":   str(fp),
                "isim":         pos.get("isim", ""),
                "sektor":       pos.get("sektor", ""),
                "adet":         pos.get("adet", 0),
                "maliyet_baz":  pos.get("maliyet_baz", 0),
                "guncel_fiyat": pos.get("guncel_fiyat", 0),
                "pnl_pct":      pos.get("kar_zarar_yuzde", 0),
                "stop_loss":    pos.get("stop_loss", 0),
                "stop_faz":     pos.get("stop_faz", 0),
                "giris_tarihi": pos.get("giris_tarihi", ""),
                "giris_nedeni": pos.get("giris_nedeni", pos.get("tez", "")),
            }
            pozisyonlar.append(ozet)
            sembol_map[f"{pos['sembol']}:{tur}"] = pos  # portföy JSON referansı
    return pozisyonlar, sembol_map


# ══════════════════════════════════════════════════════════════════════════════
# 2. HABER ÇEKİMİ
# ══════════════════════════════════════════════════════════════════════════════

def haberleri_cek(semboller: list[str], saat_siniri: int = 24) -> list[dict]:
    """FMP'den son N saatin haberlerini çeker, tarih sıralar."""
    if not semboller:
        return []
    log(f"\n📰 Haber çekiliyor: {', '.join(sorted(semboller))} (son {saat_siniri}s)")
    data = fmp_get("news/stock", {"symbols": ",".join(semboller), "limit": 80})
    if not data:
        return []

    sinir = datetime.now(timezone.utc) - timedelta(hours=saat_siniri)
    guncel = []
    for h in data:
        try:
            pub = h.get("publishedDate", "")
            if "T" in pub:
                dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
            else:
                dt = datetime.strptime(pub[:19], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if dt < sinir:
                continue
            h["_dt"] = dt
        except Exception:
            continue
        guncel.append(h)

    guncel.sort(key=lambda x: x["_dt"], reverse=True)
    log(f"  {len(guncel)} haber bulundu (son {saat_siniri} saat)")
    return guncel


# ══════════════════════════════════════════════════════════════════════════════
# 3. CLAUDE API — TEZ ANALİZİ
# ══════════════════════════════════════════════════════════════════════════════

SISTEM_TALIMATI = """Sen Finzora AI'ın otonom portföy yönetim motorusun.
Portföy pozisyonlarını etkileyen haberleri analiz eder, TEZ BOZULMASI değerlendirmesi
yapar ve otomatik olarak uygulanacak kararlar üretirsin.

## TEMEL KARAR KURALLARI

### Tez Bozulması Testi
Bir karar üretmeden önce şu soruyu sor:
"Bu haber, bu pozisyonu almak için gerekli temel tezi doğrudan yanlışlıyor mu?"
- Yanıt EVET → KISMI_CIKIS veya TAM_CIKIS
- Yanıt HAYIR → HOLD veya IZLE

### Doğrulama Eşiği
- Resmi açıklama/8-K/şirket basın bülteni → YUKSEK güven
- Reuters/Bloomberg/WSJ → ORTA güven
- Tek kaynak, blog, sosyal medya → DUSUK güven → IZLE

### Portföy Bazlı Zorunlu Çıkışlar
- Temettü portföyü, temettü kesintisi/dondurması onaylandı → TAM_CIKIS (HEMEN)
- Herhangi portföy, iflas/Chapter 11 başvurusu → TAM_CIKIS (HEMEN)
- Herhangi portföy, SEC fraud soruşturması açıldı → TAM_CIKIS (HEMEN)
- Herhangi portföy, delisting kararı → TAM_CIKIS (HEMEN)

### Kısmi Çıkış Koşulları
- Kazanç kılavuzu ciddi düşüş (>%15) → KISMI_CIKIS %50
- Ana müşteri kaybı / büyük sözleşme iptali → KISMI_CIKIS %25
- Yönetim değişikliği + strateji belirsizliği → KISMI_CIKIS %25

### Stop Sıkıştırma Koşulları
- Olumsuz ama tezi bozmuyor, belirsizlik arttı → STOP_SIKIŞTIR
- Sektörde olumsuz gelişme ama şirkete özgü değil → STOP_SIKIŞTIR

### Habersiz Karar Yok
Listede haber bulunmayan semboller için HOLD ver. Asla haber olmaksızın CIKIS verme.

## ÇIKTI FORMATI
SADECE ve YALNIZCA geçerli JSON döndür. Açıklama, markdown, başlık YASAK.
JSON dışında tek bir karakter bile yazma.
"""

def prompt_olustur(pozisyonlar: list[dict], haberler: list[dict]) -> str:
    """Claude'a gönderilecek kullanıcı promptunu oluştur."""

    # Pozisyon özeti
    poz_blok = []
    for p in pozisyonlar:
        faz_ad = {0: "init", 1: "giriş tamponu", 2: "başa baş", 3: "izleyen"}.get(p["stop_faz"], "?")
        poz_blok.append(
            f"- {p['sembol']} [{p['portfoy']}] {p['isim']}"
            f" | Sektör: {p['sektor']}"
            f" | P&L: {p['pnl_pct']:+.1f}%"
            f" | Stop: ${p['stop_loss']:.2f} ({faz_ad})"
            f" | Giriş tezi: {p['giris_nedeni'][:120]}"
        )

    # Haber özeti (sembol bazlı grupla, max 5 haber/sembol)
    haber_sembol: dict[str, list] = {}
    for h in haberler:
        sym = h.get("symbol", "GENEL")
        if sym not in haber_sembol:
            haber_sembol[sym] = []
        if len(haber_sembol[sym]) < 5:
            haber_sembol[sym].append(h)

    haber_blok = []
    for sym, hs in sorted(haber_sembol.items()):
        for h in hs:
            dt = h.get("_dt", datetime.now(timezone.utc))
            yas = int((datetime.now(timezone.utc) - dt).total_seconds() / 3600)
            haber_blok.append(
                f"[{sym} — {yas}s önce]\n"
                f"  Başlık: {h.get('title','')}\n"
                f"  Kaynak: {h.get('site','')}\n"
                f"  Özet: {(h.get('text') or '')[:300]}"
            )

    semboller = [p["sembol"] for p in pozisyonlar]

    prompt = f"""## PORTFÖY POZİSYONLARI ({len(pozisyonlar)} pozisyon)

{chr(10).join(poz_blok)}

## SON HABERLER ({len(haberler)} haber)

{chr(10).join(haber_blok) if haber_blok else "Son 24 saatte haber bulunamadı."}

## GÖREV

Yukarıdaki her portföy pozisyonu için haber bazlı karar üret.
Haber olmayan semboller için HOLD ver.
Sadece aşağıdaki JSON formatında yanıt ver:

{{
  "analiz_tarihi": "ISO datetime",
  "genel_degerlendirme": "Tüm haberler hakkında 2-3 cümle Türkçe özet",
  "kararlar": [
    {{
      "sembol": "TIKR",
      "portfoy": "dengeli|agresif|temettü",
      "aksiyon": "HOLD|IZLE|STOP_SIKIŞTIR|KISMI_CIKIS_25|KISMI_CIKIS_50|TAM_CIKIS",
      "guven": "YUKSEK|ORTA|DUSUK",
      "aciliyet": "HEMEN|KAPANIS|IZLE",
      "tez_bozuldu_mu": true|false,
      "neden": "Türkçe, max 3 cümle: hangi haber neden bu kararı tetikledi",
      "tetikleyen_haber": "Tetikleyen haberin başlığı veya boş string"
    }}
  ]
}}

Karar üretilmesi gereken semboller: {', '.join(semboller)}
"""
    return prompt


def claude_analiz(pozisyonlar: list[dict], haberler: list[dict]) -> dict | None:
    """Claude API'yi çağır, yapılandırılmış karar döndür."""
    if not ANTHROPIC_KEY:
        log("❌ ANTHROPIC_API_KEY bulunamadı — analiz atlandı")
        return None

    prompt = prompt_olustur(pozisyonlar, haberler)
    payload = json.dumps({
        "model":      CLAUDE_MODEL,
        "max_tokens": 2000,
        "system":     SISTEM_TALIMATI,
        "messages":   [{"role": "user", "content": prompt}]
    }).encode("utf-8")

    req = urllib.request.Request(
        ANTHROPIC_URL,
        data=payload,
        headers={
            "Content-Type":      "application/json",
            "x-api-key":         ANTHROPIC_KEY,
            "anthropic-version": "2023-06-01",
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
        raw = data["content"][0]["text"].strip()

        # JSON temizle (markdown blok varsa soy)
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        raw = raw.strip()

        result = json.loads(raw)
        log(f"  ✅ Claude analizi tamamlandı — {len(result.get('kararlar',[]))} karar")
        return result

    except urllib.error.HTTPError as e:
        log(f"  ❌ Claude API HTTP {e.code}: {e.read().decode()[:300]}")
        return None
    except json.JSONDecodeError as e:
        log(f"  ❌ JSON parse hatası: {e}\n  Ham cevap: {raw[:400]}")
        return None
    except Exception as e:
        log(f"  ❌ Claude API hatası: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 4. KARAR UYGULAMA
# ══════════════════════════════════════════════════════════════════════════════

def transaction_yaz(tarih: str, aksiyon: str, sembol: str,
                    adet: int, fiyat: float, neden: str):
    """transactions.csv'ye kayıt ekle."""
    total = round(adet * fiyat, 2)
    row = [tarih, aksiyon, sembol, adet, fiyat, total, neden]
    header = ["date", "action", "symbol", "shares", "price", "total", "reason"]
    yeni = not TRANSACTIONS.exists()
    with open(TRANSACTIONS, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if yeni:
            w.writerow(header)
        w.writerow(row)
    log(f"    📝 Transaction: {aksiyon} {adet} {sembol} @ ${fiyat:.2f} = ${total:,.2f}")


def portfoy_json_guncelle(portfoy_fp: str, sembol: str,
                          aksiyon: str, pct: float = 0.0) -> tuple[int, float, float]:
    """
    Portföy JSON'ını güncelle.
    Döndürür: (satılan_adet, fiyat, nakit_artis)
    """
    fp = Path(portfoy_fp)
    d = load_json(fp)
    if not d:
        return 0, 0, 0

    pozisyonlar = d.get("pozisyonlar", [])
    hedef = next((p for p in pozisyonlar if p["sembol"] == sembol), None)
    if not hedef:
        return 0, 0, 0

    fiyat       = hedef.get("guncel_fiyat", hedef.get("maliyet_baz", 0))
    mevcut_adet = hedef.get("adet", 0)

    if aksiyon == "TAM_CIKIS":
        satilan  = mevcut_adet
        d["pozisyonlar"] = [p for p in pozisyonlar if p["sembol"] != sembol]
    else:
        satilan = max(1, round(mevcut_adet * pct))
        hedef["adet"] = mevcut_adet - satilan
        hedef["guncel_deger"] = round(hedef["adet"] * fiyat, 2)
        hedef["yatirim"]      = round(hedef["adet"] * hedef["maliyet_baz"], 2)
        hedef["kar_zarar"]    = round(hedef["guncel_deger"] - hedef["yatirim"], 2)
        hedef["kar_zarar_yuzde"] = round(
            (hedef["kar_zarar"] / hedef["yatirim"] * 100) if hedef["yatirim"] else 0, 2
        )

    nakit_artis = round(satilan * fiyat, 2)
    if "nakit" in d:
        d["nakit"]["miktar"] = round(d["nakit"].get("miktar", 0) + nakit_artis, 2)

    save_json(fp, d)
    return satilan, fiyat, nakit_artis


def stop_sikiştir(portfoy_fp: str, sembol: str):
    """stop_faz=0 yap → bir sonraki daily_update sıfırdan hesaplar."""
    fp = Path(portfoy_fp)
    d = load_json(fp)
    if not d:
        return
    for pos in d.get("pozisyonlar", []):
        if pos["sembol"] == sembol:
            eski = pos.get("stop_faz", "?")
            pos["stop_faz"] = 0
            log(f"    🔧 {sembol} stop_faz {eski}→0 (sıfırla)")
            break
    save_json(fp, d)


def karar_uygula(karar: dict, sembol_map: dict,
                 dry_run: bool = False) -> dict:
    """
    Tek bir kararı uygular.
    Döndürür: uygulama sonuç dict'i
    """
    sembol   = karar["sembol"]
    portfoy  = karar["portfoy"]
    aksiyon  = karar["aksiyon"]
    neden    = karar.get("neden", "")
    guven    = karar.get("guven", "ORTA")
    aciliyet = karar.get("aciliyet", "IZLE")

    sonuc = {
        "sembol":  sembol,
        "portfoy": portfoy,
        "aksiyon": aksiyon,
        "guven":   guven,
        "neden":   neden,
        "uygulandi": False,
        "detay":   "",
    }

    # HOLD / IZLE — uygulama yok
    if aksiyon in ("HOLD", "IZLE"):
        sonuc["uygulandi"] = True
        sonuc["detay"] = "Uygulama gerekmez"
        return sonuc

    # DUSUK güven → hiçbir yıkıcı işlem yapma
    if guven == "DUSUK" and aksiyon not in ("STOP_SIKIŞTIR", "HOLD", "IZLE"):
        log(f"  ⚠️  {sembol}: Güven DUSUK → {aksiyon} uygulanmadı, IZLE'ye düşürüldü")
        sonuc["aksiyon"] = "IZLE"
        sonuc["uygulandi"] = True
        sonuc["detay"] = "Güven DUSUK — aksiyon uygulanmadı"
        return sonuc

    # Portföy JSON referansını bul
    anahtar = f"{sembol}:{portfoy}"
    pos_ref = sembol_map.get(anahtar)
    if not pos_ref:
        # portfoy adı eşleşmeyebilir — tüm portföylerde ara
        for k, v in sembol_map.items():
            if k.startswith(f"{sembol}:"):
                pos_ref = v
                portfoy_fp = PORTFOY_DOSYALARI.get(k.split(":")[1], None)
                if portfoy_fp:
                    portfoy = k.split(":")[1]
                break

    portfoy_fp = str(PORTFOY_DOSYALARI.get(portfoy, ""))
    if not portfoy_fp:
        sonuc["detay"] = "Portföy dosyası bulunamadı"
        return sonuc

    tarih = datetime.now().strftime("%Y-%m-%d")

    if aksiyon == "STOP_SIKIŞTIR":
        if not dry_run:
            stop_sikiştir(portfoy_fp, sembol)
        sonuc["uygulandi"] = True
        sonuc["detay"] = "stop_faz=0, bir sonraki güncellemede yeniden hesaplanır"

    elif aksiyon in ("KISMI_CIKIS_25", "KISMI_CIKIS_50"):
        pct = 0.25 if "25" in aksiyon else 0.50
        if not dry_run:
            satilan, fiyat, nakit = portfoy_json_guncelle(portfoy_fp, sembol, "KISMI_CIKIS", pct)
            if satilan > 0:
                transaction_yaz(tarih, "SELL_PARTIAL", sembol, satilan, fiyat,
                                f"Claude Haber Ajanı: {neden[:100]}")
                sonuc["detay"] = f"{satilan} hisse @ ${fiyat:.2f} satıldı (nakit +${nakit:,.2f})"
            else:
                sonuc["detay"] = "Satış gerçekleşmedi (adet=0)"
        else:
            fiyat = pos_ref.get("guncel_fiyat", 0) if pos_ref else 0
            adet  = pos_ref.get("adet", 0) if pos_ref else 0
            satilan = max(1, round(adet * pct))
            sonuc["detay"] = f"[DRY-RUN] {satilan} hisse @ ${fiyat:.2f} satılacaktı"
        sonuc["uygulandi"] = True

    elif aksiyon == "TAM_CIKIS":
        if not dry_run:
            satilan, fiyat, nakit = portfoy_json_guncelle(portfoy_fp, sembol, "TAM_CIKIS")
            if satilan > 0:
                transaction_yaz(tarih, "SELL", sembol, satilan, fiyat,
                                f"Claude Haber Ajanı TAM_CIKIS: {neden[:100]}")
                sonuc["detay"] = f"{satilan} hisse @ ${fiyat:.2f} TAM satıldı (nakit +${nakit:,.2f})"
            else:
                sonuc["detay"] = "Satış gerçekleşmedi"
        else:
            fiyat = pos_ref.get("guncel_fiyat", 0) if pos_ref else 0
            adet  = pos_ref.get("adet", 0) if pos_ref else 0
            sonuc["detay"] = f"[DRY-RUN] {adet} hisse @ ${fiyat:.2f} satılacaktı"
        sonuc["uygulandi"] = True

    return sonuc


# ══════════════════════════════════════════════════════════════════════════════
# 5. TELEGRAM RAPORU
# ══════════════════════════════════════════════════════════════════════════════

AKSIYON_EMOJI = {
    "HOLD":           "✅",
    "IZLE":           "👁",
    "STOP_SIKIŞTIR":  "🔧",
    "KISMI_CIKIS_25": "📉",
    "KISMI_CIKIS_50": "📉📉",
    "TAM_CIKIS":      "🔴",
}

def telegram_raporu_olustur(claude_sonuc: dict, uygulama_sonuclari: list[dict],
                             haber_sayisi: int, dry_run: bool) -> str:
    mod = " [DRY-RUN]" if dry_run else ""
    tarih = datetime.now().strftime("%d %b %Y %H:%M")

    # Sadece dikkat gerektiren kararları öne al
    onemli = [s for s in uygulama_sonuclari
              if s["aksiyon"] not in ("HOLD", "IZLE")]
    izle   = [s for s in uygulama_sonuclari if s["aksiyon"] == "IZLE"]

    lines = [
        f"🤖 <b>Finzora AI Haber Ajanı{mod}</b>",
        f"📅 {tarih} | {haber_sayisi} haber tarandı",
        "",
        f"📊 <i>{claude_sonuc.get('genel_degerlendirme','')}</i>",
    ]

    if onemli:
        lines.append("\n<b>— Uygulanan Kararlar —</b>")
        for s in onemli:
            emoji = AKSIYON_EMOJI.get(s["aksiyon"], "•")
            lines.append(
                f"{emoji} <b>{s['sembol']}</b> [{s['portfoy']}] → {s['aksiyon']}"
                f"\n   {s['neden'][:120]}"
                f"\n   {s['detay']}"
            )
    else:
        lines.append("\n✅ Kritik aksiyon gerektiren haber yok.")

    if izle:
        lines.append("\n<b>— İzleme Listesine Eklendi —</b>")
        for s in izle:
            lines.append(f"👁 {s['sembol']}: {s['neden'][:100]}")

    return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 6. GIT COMMIT
# ══════════════════════════════════════════════════════════════════════════════

def git_push(mesaj: str):
    try:
        import subprocess as sp
        os.chdir(BASE)
        sp.run(["git", "add", "."], check=True, capture_output=True)
        r = sp.run(["git", "commit", "-m", mesaj], capture_output=True, text=True)
        if "nothing to commit" in r.stdout:
            log("  ℹ️  Git: değişiklik yok")
            return
        if r.returncode != 0:
            log(f"  ❌ Git commit: {r.stderr[:200]}")
            return
        sp.run(["git", "push"], check=True, capture_output=True)
        log("  ✅ Git push OK")
    except Exception as e:
        log(f"  ❌ Git hatası: {e}")


# ══════════════════════════════════════════════════════════════════════════════
# 7. ANA FONKSİYON
# ══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Finzora AI — Claude Haber Ajanı")
    parser.add_argument("--dry-run",  action="store_true",
                        help="Kararları uygulama, sadece göster")
    parser.add_argument("--saat",    type=int, default=24,
                        help="Kaç saatlik haberleri tara (varsayılan: 24)")
    parser.add_argument("--no-push", action="store_true",
                        help="Git push yapma")
    args = parser.parse_args()

    log("\n" + "=" * 60)
    log(f"🤖 CLAUDE HABER AJANI BAŞLATILDI"
        + (" [DRY-RUN]" if args.dry_run else ""))
    log("=" * 60)

    # ── 1. Portföy yükle ────────────────────────────────────────────────────
    pozisyonlar, sembol_map = portfoy_ozeti()
    if not pozisyonlar:
        log("❌ Portföy pozisyonu yüklenemedi.")
        return
    log(f"📂 {len(pozisyonlar)} pozisyon yüklendi")

    # ── 2. Haber çek ────────────────────────────────────────────────────────
    semboller = list({p["sembol"] for p in pozisyonlar})
    haberler  = haberleri_cek(semboller, saat_siniri=args.saat)

    if not haberler:
        log("ℹ️  Son 24 saatte haber bulunamadı — ajan çıkıyor.")
        return

    # ── 3. Claude analizi ───────────────────────────────────────────────────
    log("\n🧠 Claude analizi başlıyor...")
    claude_sonuc = claude_analiz(pozisyonlar, haberler)

    if not claude_sonuc:
        log("❌ Claude analizi başarısız — ajan çıkıyor.")
        return

    kararlar = claude_sonuc.get("kararlar", [])
    log(f"\n📋 Claude {len(kararlar)} karar üretti:")

    # ── 4. Kararları uygula ─────────────────────────────────────────────────
    uygulama_sonuclari = []
    for karar in kararlar:
        sym = karar.get("sembol", "?")
        aks = karar.get("aksiyon", "HOLD")
        guv = karar.get("guven", "?")
        log(f"  {sym}: {aks} ({guv}) — {karar.get('neden','')[:80]}")

        sonuc = karar_uygula(karar, sembol_map, dry_run=args.dry_run)
        if sonuc.get("detay"):
            log(f"    → {sonuc['detay']}")
        uygulama_sonuclari.append({**karar, **sonuc})

    # ── 5. Telegram ────────────────────────────────────────────────────────
    rapor = telegram_raporu_olustur(
        claude_sonuc, uygulama_sonuclari, len(haberler), args.dry_run
    )
    onemli_aksiyon = any(
        s["aksiyon"] in ("TAM_CIKIS", "KISMI_CIKIS_25", "KISMI_CIKIS_50")
        for s in uygulama_sonuclari
    )
    seviye = "alert" if onemli_aksiyon else "custom"
    telegram_gonder(rapor, severity=seviye)
    log("\n📤 Telegram raporu gönderildi")

    # ── 6. Sonucu kaydet (log amaçlı) ───────────────────────────────────────
    sonuc_fp = BASE / f"logs/haber_ajan_{datetime.now().strftime('%Y%m%d_%H%M')}.json"
    try:
        with open(sonuc_fp, "w", encoding="utf-8") as f:
            json.dump({
                "tarih":    datetime.now().isoformat(),
                "dry_run":  args.dry_run,
                "haberler": len(haberler),
                "claude":   claude_sonuc,
                "uygulama": uygulama_sonuclari,
            }, f, ensure_ascii=False, indent=2, default=str)
    except Exception:
        pass

    # ── 7. Git ──────────────────────────────────────────────────────────────
    if not args.dry_run and not args.no_push:
        islemler = [s for s in uygulama_sonuclari
                    if s["aksiyon"] not in ("HOLD", "IZLE")]
        if islemler:
            ozet = ", ".join(f"{s['sembol']} {s['aksiyon']}" for s in islemler)
            mesaj = f"[AJAN] Claude haber kararları: {ozet} — {datetime.now().strftime('%d %b %Y')}"
        else:
            mesaj = f"[AJAN] Haber taraması — aksiyon yok — {datetime.now().strftime('%d %b %Y')}"
        git_push(mesaj)

    log("\n" + "=" * 60)
    log("✅ CLAUDE HABER AJANI TAMAMLANDI")
    log("=" * 60 + "\n")


if __name__ == "__main__":
    main()
