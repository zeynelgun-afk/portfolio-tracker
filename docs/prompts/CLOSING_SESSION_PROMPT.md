# SEANS KAPANIŞ PROMPT — v1.0

> **versiyon**: 1.0 | **oluşturma**: 24 şubat 2026
> **çalışma zamanı**: NYSE kapandıktan sonra (TR 00:00+), after-hours verisi yerleştikten sonra
> **ön koşul**: o günün sabah raporu + seans içi güncelleme yapılmış olmalı
> **perspektif**: GÜNÜN DEĞERLENDİRMESİ + YARIN İÇİN HAZIRLIK
> **fiyat verisi**: kapanış fiyatları (kesinleşmiş, final)
> **çıktı**: JSON final güncelleme + günlük log + git push
> **dil**: küçük harf türkçe, teknik terimler ingilizce kalabilir
> **kaynak atfı**: sadece "finzora ai" kullan

---

## 3 PROMPT — BİR GÜNÜN AKIŞI

```
TR 09:00-15:00  →  SABAH RAPORU (DAILY_REPORT_PROMPT.md)
                    analiz + plan, dünün kapanışıyla

TR 18:00-18:30  →  SEANS İÇİ AKSİYON (SESSION_ACTION_PROMPT.md)
                    canlı fiyat, karar + uygulama

TR 00:00-01:00  →  SEANS KAPANIŞ (bu prompt)
                    final güncelleme + değerlendirme + yarın hazırlık
```

---

## ÇALIŞTIRMA KOMUTU

kullanıcı şunlardan birini söylediğinde:
- "piyasa kapandı"
- "kapanış güncellemesi"
- "gün sonu"
- "final güncelleme"

---

## ANA AKIŞ (4 AŞAMA)

```
AŞAMA 1: FİNAL VERİ TOPLAMA (kapanış fiyatları)
    │
AŞAMA 2: JSON FİNAL GÜNCELLEME (tüm dosyalar)
    │
AŞAMA 3: GÜNÜN DEĞERLENDİRMESİ
    │
AŞAMA 4: YARIN HAZIRLIK + GİT PUSH
```

---

# AŞAMA 1 — FİNAL VERİ TOPLAMA

## 1a. kapanış fiyatları

```python
# tüm portföy + swing sembollerini birleştir
all_symbols = benzersiz_sembol_listesi()

# batch quote — kapanış fiyatları kesinleşmiş
quotes = fmp_get("batch-quote", {"symbols": ",".join(all_symbols)})

# endeksler
indices = fmp_get("batch-quote", {"symbols": "SPY,QQQ,DIA,IWM"})

# emtia + forex
gold = fmp_get("quote", {"symbol": "GCUSD"})
oil = fmp_get("quote", {"symbol": "CLUSD"})
usdtry = fmp_get("quote", {"symbol": "USDTRY"})
```

## 1b. sektör kapanış performansı

```python
sectors = fmp_get("sector-performance-snapshot", {"date": TODAY})
```

## 1c. after-hours hareketler (önemli olanlar)

```python
# portföy hisselerinde after-hours hareket var mı?
for symbol in critical_symbols:
    ah = fmp_get("aftermarket-quote", {"symbol": symbol})
    # after-hours'ta %2+ hareket varsa → not düş
```

## 1d. AMC earnings sonuçları

**websearch** (1-2 arama):
```
- "{DATE} after hours earnings results"
- varsa spesifik: "NVDA earnings results" gibi
```

portföy veya swing hisselerinin AMC earnings'leri varsa → sonucu kaydet, yarın sabah raporuna not

## toplam API bütçesi (aşama 1)

| kaynak | çağrı sayısı |
|--------|-------------|
| batch quote (portföy + swing) | ~1 |
| endeksler + emtia + forex | ~5 |
| sektör performansı | ~1 |
| after-hours (kritik olanlar) | ~3-5 |
| **FMP toplam** | **~10-12** |
| **websearch** | **1-2** |

⚠️ günlük toplam: sabah ~100 + seans içi ~88 + kapanış ~12 = **~200 / 2,500** = **%8** (güvenli)

---

# AŞAMA 2 — JSON FİNAL GÜNCELLEME

bu aşama en önemlisi — tüm verilerin kapanış fiyatıyla tutarlı güncellenmesi.

## 2a. portföy JSON'ları (`data/portfolios/*.json`)

her 4 portföy için:

```python
for portfolio in [balanced, aggressive, dividend, rotation]:
    for pozisyon in portfolio['pozisyonlar']:
        pozisyon['guncel_fiyat'] = quote['price']
        pozisyon['gunluk_degisim_yuzde'] = quote['changesPercentage']
        pozisyon['guncel_deger'] = pozisyon['adet'] * pozisyon['guncel_fiyat']
        pozisyon['kar_zarar'] = pozisyon['guncel_deger'] - pozisyon['yatirim']
        pozisyon['kar_zarar_yuzde'] = (pozisyon['kar_zarar'] / pozisyon['yatirim']) * 100
        pozisyon['son_guncelleme'] = datetime.now().isoformat()
    
    # portföy toplamları
    portfolio['toplam_deger'] = sum(p['guncel_deger'] for p in pozisyonlar) + nakit['miktar']
    portfolio['toplam_getiri_yuzde'] = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) * 100
    portfolio['son_guncelleme'] = datetime.now().isoformat()
    
    # ağırlık yüzdeleri yeniden hesapla
    for pozisyon in portfolio['pozisyonlar']:
        pozisyon['agirlik_yuzde'] = (pozisyon['guncel_deger'] / portfolio['toplam_deger']) * 100
```

## 2b. swing active.json (`data/swing/active.json`)

```python
for pozisyon in aktif_pozisyonlar:
    pozisyon['guncel_fiyat'] = quote['price']
    pozisyon['guncel_kar_zarar_yuzde'] = ((guncel - giris) / giris) * 100
    pozisyon['tutulan_gun'] = (today - giris_tarihi).days
    pozisyon['son_guncelleme'] = datetime.now().isoformat()
    
    # trailing stop güncelle (sadece yukarı)
    if pozisyon has partial_exit_plan:
        zirve_fiyat = max(pozisyon['guncel_fiyat'], önceki_zirve)
        yeni_trailing = zirve_fiyat * 0.95
        if yeni_trailing > mevcut_trailing:
            pozisyon['partial_exit_plan']['kalan_50_icin']['baslangic_trailing_stop'] = yeni_trailing
```

## 2c. summary.json (`data/summary.json`)

```python
summary['son_guncelleme'] = TODAY
summary['toplam_deger'] = dengeli + agresif + temettü + rotasyon
summary['toplam_kar_zarar'] = toplam_deger - 400000
summary['toplam_kar_zarar_yuzde'] = (toplam_kar_zarar / 400000) * 100

# SPY benchmark güncelle
summary['benchmark_spy'] = SPY_degisim_baslangictan_beri
summary['alpha'] = toplam_kar_zarar_yuzde - benchmark_spy

# her portföy alt özeti güncelle
for portfolio_key in ['dengeli', 'agresif', 'temettü', 'rotasyon']:
    summary['portfolyolar'][key] = {
        'deger': portfolio.toplam_deger,
        'kar_zarar': portfolio.toplam_deger - 100000,
        'kar_zarar_yuzde': ...,
        'pozisyon_sayisi': len(pozisyonlar),
        'nakit': nakit
    }

# swing özeti
summary['portfolyolar']['swing_trade'] = {
    'pozisyon_sayisi': aktif_count,
    'ortalama_getiri_yuzde': ortalama_kz,
    'bos_slot': 10 - aktif_count
}
```

## 2d. doğrulama kontrolleri

güncelleme sonrası şu kontrolleri yap:

```
✓ her pozisyonda yatirim = adet × maliyet_baz (sabit, değişmemeli)
✓ her pozisyonda guncel_deger = adet × guncel_fiyat
✓ her pozisyonda kar_zarar = guncel_deger - yatirim
✓ nakit.miktar değişmedi (trade olmadıysa)
✓ toplam_deger = sum(guncel_deger) + nakit
✓ agirlik_yuzde toplamı + nakit ağırlığı ≈ %100
✓ summary toplam_deger = 4 portföy toplamı
✓ swing trailing stop'lar sadece yukarı gitmiş (aşağı inmemiş)
✓ tüm son_guncelleme timestamp'leri bugünün tarihi
```

hata bulursan → düzelt, commit mesajında belirt

---

# AŞAMA 3 — GÜNÜN DEĞERLENDİRMESİ

## 3a. gün performansı

```
bugün ne oldu?
- piyasa: SPY %X, QQQ %X
- en iyi/en kötü sektör
- VIX değişimi
- önemli haberler/gelişmeler
```

## 3b. portföy bazında günlük değişim

```
her portföy için:
- bugünkü toplam değişim ($, %)
- en iyi/en kötü performans gösteren pozisyon
- sabah planındaki aksiyonlar uygulandı mı?
- beklenmeyen gelişme oldu mu?
```

## 3c. swing trade günlük özet

```
- bugün trade yapıldı mı? (giriş/çıkış)
- trailing stop güncellenen pozisyonlar
- yarın stop'a en yakın pozisyon (acil dikkat)
- yarın hedefe en yakın pozisyon (kar alma hazırlığı)
```

## 3d. sabah planı değerlendirmesi

sabah raporundaki aksiyon planını gözden geçir:

```
🔴 acil aksiyonlar → yapıldı mı? sonuç ne oldu?
🟡 izlenenler → tetiklendi mi? ne oldu?
🟢 fırsatlar → değerlendirildi mi?

yapılmayan aksiyonlar → neden yapılmadı? yarına mı kaldı?
```

## 3e. bugünün dersleri

bugün öğrenilen bir şey var mı?
- doğru karar verilen trade → neden doğruydu?
- yanlış karar → neden yanlıştı? bir dahaki sefere ne farklı yapılmalı?
- kaçırılan fırsat → fark edildi mi? neden girilmedi?
- risk yönetimi → stop'lar çalıştı mı? trailing doğru mu ayarlanmıştı?

---

# AŞAMA 4 — YARIN HAZIRLIK + GİT PUSH

## 4a. yarın izlenecekler

```
earnings:
- yarın BMO raporlayanlar (portföy/swing hisselerimiz varsa → acil)
- yarın AMC raporlayanlar
- bu hafta kalan önemli earnings

makro:
- yarınki ekonomik veriler (CPI, PMI, FOMC, consumer confidence vb.)
- merkez bankası konuşmaları

teknik:
- SMA kırılımı yakın olan pozisyonlar
- RSI aşırı bölgede olanlar (>75 veya <30)
- stop'a yakın swing pozisyonları

strateji:
- yarın açılışta yapılacak ilk iş ne?
- bekleyen alış/satış kararları
- watchlist'te tetiklenmeyi bekleyen seviyeler
```

## 4b. günlük log (isteğe bağlı)

eğer günde önemli olay olduysa `data/logs/DAILY_{DATE}.md` oluştur:

```markdown
# {DATE} günlük log

## piyasa
- SPY: $XXX (±%X)
- önemli gelişmeler

## portföy
- toplam değer: $XXX (±%X)
- yapılan trade'ler (varsa)

## swing
- giriş/çıkış (varsa)
- trailing güncellemeleri

## notlar
- bugünün dersi
- yarın dikkat edilecekler
```

sıradan bir gün olduysa (trade yok, önemli gelişme yok) → log oluşturmaya gerek yok, sadece JSON güncellemesi yeterli

## 4c. git commit + push

```bash
# ana commit — her gün yapılacak
git add data/portfolios/ data/swing/ data/summary.json
git commit -m "[GÜNCELLEME] {tarih} kapanış fiyatları — SPY ±%X, toplam $XXXk (±%X)"

# trade varsa ayrı commit (seans içinde yapılmamışsa)
git commit -m "[ALIŞ/SATIŞ] ..."

# log varsa
git add data/logs/
git commit -m "[LOG] {tarih} günlük log"

git push
```

---

# KULLANICIYA ÖZET FORMAT

```markdown
## 📊 kapanış güncellemesi — {tarih}

### piyasa kapanışı
SPY: $XXX (±%X) | QQQ: $XXX (±%X) | VIX: XX (±%X)
altın: $X,XXX | petrol: $XX | USD/TRY: XX.XX

### portföy kapanışı
| portföy | değer | günlük | toplam k/z | durum |
|---------|-------|--------|-----------|-------|
| dengeli | $XXX,XXX | ±%X | ±%X | ✅/⚠️ |
| agresif | $XXX,XXX | ±%X | ±%X | ... |
| temettü | $XXX,XXX | ±%X | ±%X | ... |
| rotasyon | $XXX,XXX | ±%X | ±%X | ... |
| **toplam** | **$XXX,XXX** | **±%X** | **±%X** | |

### bugün yapılanlar
- [trade'ler, trailing güncellemeleri, watchlist değişiklikleri]
- veya: "trade yok, sadece fiyat güncellemesi"

### swing durumu
aktif: X/10 | ortalama k/z: ±%X
⚠️ dikkat: [stop'a yakın veya hedefe yakın pozisyonlar]

### yarın dikkat
- 🔴 [acil: earnings, stop kontrolü]
- 🟡 [izle: makro veri, teknik seviye]
- 🟢 [fırsat: watchlist tetiklenmesi, dip alım]

### after-hours (varsa)
- AMC earnings sonuçları
- after-hours'ta önemli hareket eden hisseler

✅ tüm JSON dosyaları güncellendi, git push yapıldı
```

---

# ÖNEMLİ KURALLAR

## kapanış güncellemesi zorunlulukları
- her iş günü kapanışta JSON'lar güncellenmeli (trade olmasa bile)
- summary.json her gün yenilenecek
- trailing stop'lar kontrol edilecek (sadece yukarı güncelleme)
- doğrulama kontrolleri yapılacak

## kapanış güncellemesinde yapılmayacaklar
- yeni pozisyon açma (piyasa kapalı, yarın sabah değerlendir)
- panik kararları (after-hours %5 düşse bile, yarın sabah analiz et)
- after-hours fiyatıyla JSON güncelleme (sadece normal seans kapanış fiyatı kullan)

## after-hours hareket kuralı
- after-hours'ta portföy hissesinde > %3 hareket varsa → not düş, yarın sabah raporu için flag
- after-hours'ta swing hissesinde > %5 hareket varsa → acil not, yarın açılışta ilk iş
- after-hours fiyatı JSON'lara YAZILMAz (sadece normal kapanış fiyatı geçerli)

---

# 3 PROMPT TOPLU BAKIŞ

| prompt | dosya | zaman (TR) | amaç | çıktı |
|--------|-------|-----------|------|-------|
| sabah raporu | `DAILY_REPORT_PROMPT.md` | 09:00-15:00 | analiz + plan | .md rapor |
| seans içi | `SESSION_ACTION_PROMPT.md` | 18:00-23:30 | karar + uygulama | trade + JSON |
| kapanış | `CLOSING_SESSION_PROMPT.md` | 00:00-01:00 | değerlendirme + final | JSON final + log |

**günlük API bütçesi**:
```
sabah:   ~100 FMP + 7-11 websearch
seans:   ~88 FMP  + 4-7 websearch
kapanış: ~12 FMP  + 1-2 websearch
toplam:  ~200 FMP + 12-20 websearch = %8 günlük limit (güvenli)
```

---

> son güncelleme: 24 şubat 2026 | finzora ai
