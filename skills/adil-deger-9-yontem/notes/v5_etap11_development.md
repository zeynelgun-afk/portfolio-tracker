# Adil Değer Skill v5.0 — Etap 11 Notu (Research Tracker)

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 11 tamamlandı

## Yapılan Değişiklikler

### A. scripts/research_tracker.py (Yeni)

Tüm aktif v5.0 analizlerinin **gerçekleşme takibi**:

```bash
python3 scripts/research_tracker.py --daily     # Günlük güncelleme + Telegram durum uyarıları
python3 scripts/research_tracker.py --weekly    # Pazar Telegram DM özeti
python3 scripts/research_tracker.py --status    # Debug: aktif takip tablosu
```

**Mantık (--daily):**

`data/research/index.json` 'analizler' dizisindeki **aktif_izleme** durumundaki her entry için:

1. FMP'den güncel fiyat çek (`/quote`)
2. `gerceklesen` alanını güncelle:
   - `simdiki_fiyat`
   - `fiyat_tepkisi_pct` = (simdiki - tespit) / tespit × 100
   - `gun_sayisi` (analiz_tarihi'nden bugüne)
   - `son_kontrol` (timestamp)
3. Stop/hedef kontrolü:
   - `simdiki <= stop_loss` → `tez_tuttu=False`, `durum=kapandi`, `ders="Stop kırıldı..."`
   - `simdiki >= hedef_2` → `tez_tuttu=True`, `durum=kapandi`, `ders="Boğa hedefi tutturuldu..."`
   - `simdiki >= hedef_1` → `tez_tuttu=True`, `durum=kapandi`, `ders="Baz hedef..."`
   - `gun_sayisi > 180` → `tez_tuttu="belirsiz"`, `ders="180 gün geçti, ne hedef ne stop..."`
4. Durum değişikliği varsa Telegram DM'e uyarı

**Mantık (--weekly):**

Son 30 günde üretilmiş v5.0 analizlerinin istatistikleri:

- Toplam analiz / Aktif / Kapanmış sayıları
- **Hit rate** (kapananlar içinde tutturulan oranı)
- Ortalama getiri %
- Mod dağılımı (GROWTH vs BLENDED)
- AL kararı ortalama getirisi
- Başarılar (en yüksek 5)
- Başarısızlıklar (stop kırılanlar) + ders metni
- Confidence kalibrasyonu (YÜKSEK confidence hit rate'i)
- Bekleyenler (henüz takipte değil)

Telegram **DM'e** gönderilir (GROUP'a değil — sistem mesajı, kullanıcı kuralı).

### B. .github/workflows/research_tracker.yml (Yeni)

GitHub Actions workflow (sadece workflow_dispatch — schedule yok, çünkü Railway tek scheduler):

```yaml
inputs:
  mode: daily | weekly | status
```

Adımlar:
1. Repo checkout
2. Python 3.11 + requests
3. `research_tracker.py --$mode --verbose`
4. **index.json değişikliği varsa otomatik commit + push**

`PAT_TOKEN` veya `GITHUB_TOKEN` ile yetkilendirme.

### C. Railway Scheduler Entegrasyonu (telegram_bot.py)

`_GH_ZAMANLAMALAR` tablosuna iki yeni satır:

```python
(23, 35, "research_tracker.yml", {"mode":"daily"},  False, False, "Research Tracker Günlük"),    # her gün 23:35
(14,  0, "research_tracker.yml", {"mode":"weekly"}, False, True,  "Research Tracker Haftalık"), # Pazar 14:00
```

**Neden 23:35 (23:30 değil)**: Mevcut `result_tracker.yml` 23:30'da tetikleniyor, bunun bitişini beklemek için 5 dakika kaydırıldı. Aynı anda iki workflow tetiklemenin pratik bir anlamı yok ve GitHub Actions queue'sunu rahatlatır.

**Neden Pazar 14:00**: Mevcut `agent.yml --mode=weekly` Pazar 12:00'de çalışıyor. Skill performans özeti weekly raporundan sonra anlamlı olur (haftalık raporda hangi pozisyonların tutturulduğu, hangilerinin stop kırdığı görünür hale gelir).

### D. Print Log Güncellemesi

Bot başlangıcında scheduler özet log'una iki yeni satır:
```
[Bot]   23:35 TR (Gün) → Research Tracker Günlük (v5.0)
[Bot]   14:00 TR (Pzr) → Research Tracker Haftalık DM Özet (v5.0)
```

## Test (Lokal Sandbox)

```bash
$ python3 scripts/research_tracker.py --status
📊 v5.0 takipteki analizler: 1
NVDA  2026-05-11  aktif_izleme  🟢 AL  None  %+0.0  —  —

$ python3 scripts/research_tracker.py --daily --verbose
📊 Günlük güncelleme: 5 aktif analiz
  📌 TEM: durum değişti → hedef_1
✅ 5 analiz güncellendi, 1 durum değişikliği

$ python3 scripts/research_tracker.py --status (tekrar)
NVDA  2026-05-11  aktif_izleme  🟢 AL  $218.21  %+1.4  0  —
```

Daily çağrı:
- NVDA fiyatı $215.22 → $218.21 (+%1.4) güncellendi ✅
- TEM eski bilanço analizinde "hedef_1" tetiklendi (eski v7 üretimi entry, fiyat hareketi yakalandı) ✅
- Telegram DM'e durum değişikliği bildirimi gönderildi ✅

## Şema Genişletmeleri

`index.json` entry'sinde `gerceklesen` artık şu alanları içerir:

```json
"gerceklesen": {
  "tespit_fiyati": 215.22,
  "simdiki_fiyat": 218.21,         ← her gün güncellenir
  "fiyat_tepkisi_pct": 1.4,         ← her gün güncellenir
  "gun_sayisi": 0,                  ← her gün güncellenir
  "son_kontrol": "2026-05-11 22:30",← her gün güncellenir
  "tez_tuttu": null,                ← hedef/stop tetiklenince güncellenir
  "ders": null                      ← hedef/stop tetiklenince yazılır
}
```

`tez_tuttu` değerleri:
- `null` — henüz sonuç yok (aktif takip)
- `True` — hedef tutturuldu
- `False` — stop kırıldı
- `"belirsiz"` — 180 gün ne hedef ne stop tetiklendi

## Akış (Tam Pipeline, v5.0 Final)

```
[Gün 0]  /deger NVDA → Skill v5.0 → markdown + index.json + git push
   ↓
[Gün 1-180]  Her gün 23:35 → research_tracker.py --daily
   ↓ (FMP fiyat çek)
   ↓ (gerceklesen güncelle)
   ↓ (hedef/stop tetiklenirse → DM uyarı + durum: kapandi)
   ↓
[Pazar 14:00]  research_tracker.py --weekly
   ↓ (son 30 gün istatistikleri)
   ↓ (hit rate, ortalama getiri, başarı/başarısızlıklar, confidence kalibrasyonu)
   ↓ (Telegram DM özet)
   ↓
[Sürekli]  Hit rate verisi birikiyor → skill self-correction
```

## Faydası (Somut)

**1. Kalibrasyon ölçümü:**

Şimdiye kadar "skill iyi çalışıyor mu?" sorusunun cevabı yoktu. Etap 11 sonrası örnek 8 hafta sonra:

```
📊 v5.0 Performans (Mart-Mayıs 2026):
  Toplam analiz: 48
  Hit rate: %62 (29 tuttu / 47 kapandı)
  AL kararı ortalama getirisi: %18.3
  GÜÇLÜ AL ortalama: %26.7 (n=8)
  GEÇ kararı doğruluğu: %75 (12/16 gerçekten düştü)
  YÜKSEK confidence: %78 hit rate (n=18)
  Quality Premium >1.30: ortalama +%22 getiri
```

**2. Otomatik post-mortem:**

Stop kıran her pozisyon için `ders` alanı yazılır:
```
"Stop $187.24 kırıldı 23. günde, fiyat $182.50 (-%15.2)"
```

Aylık review'de bu derslerden pattern çıkarılabilir.

**3. Sürekli izleme yükü ortadan kalkıyor:**

Eskiden 12 aktif analizden hangilerinin hedef tutturduğunu manuel takip ediyordun. Şimdi otomatik DM:
```
🔔 Durum Değişiklikleri
🟢 NVDA — BAZ HEDEF TUTTURULDU
   Fiyat: $260.50 (%+21.0, 12 gün)
   "Baz hedef $259.25 12. günde tutturuldu..."
```

## Etap 12+ İçin Bırakılanlar

1. **Confidence overrride** — YÜKSEK confidence hit rate %78 ise, ORTA confidence %55 ise → Quality Premium katsayısını real-data ile kalibre et
2. **Karar matrisi ayarlama** — GEÇ kararı doğruluğu düşükse karar eşiklerini gevşet
3. **Aylık otomatik rapor** — Her ayın 1'i kapsamlı performans dökümü (Pazar weekly özetinden daha derin)
4. **Sektör bazlı hit rate** — semicon vs consumer staples vs biotech ayrı analiz
5. **Karar gecikme analizi** — Hedef tutturmaya kaç gün gerekti (AL kararı 30 günde mi 90 günde mi tutuyor?)

Kaynak: finzora ai
