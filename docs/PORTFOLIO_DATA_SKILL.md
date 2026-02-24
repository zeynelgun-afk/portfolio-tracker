# PORTFOLIO TRACKER — VERİ YAPISI VE GÜNCELLEME KURALLARI

> **Repo**: https://github.com/zeynelgun-afk/portfolio-tracker  
> **Son doğrulama**: Şubat 2026  
> **Amaç**: Tüm JSON dosyalarının tutarlı ve doğru güncellenmesi için tek referans kaynak

---

## ⚠️ KRİTİK GENEL KURALLAR

1. **Türkçe zorunlu** — Tüm alan adları, açıklamalar ve commit mesajları Türkçe
2. **Hiçbir alan atlanamaz** — Her pozisyon açılış/kapanışında ZORUNLU alanlar tam doldurulur
3. **Hesaplama tutarlılığı** — `yatirim = adet × maliyet_baz`, `guncel_deger = adet × guncel_fiyat`, `kar_zarar = guncel_deger - yatirim`
4. **Nakit dengesi** — Her alış/satıştan sonra `nakit.miktar` güncellenir
5. **Tarih formatı** — ISO 8601: `"2026-02-20"` (tarih) veya `"2026-02-20T19:41:06.665367"` (timestamp)
6. **Her değişiklikten sonra** → git commit + push

---

## 1. PORTFÖY DOSYALARI ŞEMASI

### Dosya Yolları
| Portföy | Dosya |
|---------|-------|
| Dengeli ($100K) | `data/portfolios/balanced.json` |
| Agresif Büyüme ($100K) | `data/portfolios/aggressive.json` |
| Değer + Temettü ($100K) | `data/portfolios/dividend.json` |
| Sektör Rotasyonu ($100K) | `data/portfolios/rotation.json` |

### Portföy JSON Şeması (Tam Yapı)

```json
{
  "portfoy_adi": "Portföy Adı",
  "baslangic_sermaye": 100000,
  "nakit": {
    "miktar": 12345.67,
    "para_birimi": "USD"
  },
  "pozisyonlar": [...],
  "son_guncelleme": "2026-02-20T19:41:06.665367",
  "toplam_deger": 105000.00,
  "toplam_getiri_yuzde": 5.0,
  "transactions": [...],
  "notes": [...]
}
```

### Pozisyon Şeması (her `pozisyonlar[]` elemanı)

```json
{
  "sembol": "SM",
  "isim": "SM Energy Company",
  "sektor": "Enerji",
  "adet": 1040,
  "maliyet_baz": 20.67,
  "guncel_fiyat": 24.005,
  "yatirim": 21496.80,
  "guncel_deger": 24965.20,
  "kar_zarar": 3468.40,
  "kar_zarar_yuzde": 16.13,
  "gunluk_degisim_yuzde": 2.58547,
  "son_guncelleme": "2026-02-20T19:41:06.665367",
  "giris_tarihi": "2026-02-17",
  "giris_fiyati": 20.67,
  "giris_nedeni": "Başlangıç pozisyonu - Oil & gas E&P, düşük maliyetli üretici",
  "agirlik_yuzde": 23.68
}
```

### Pozisyon Alanları — Hesaplama Kuralları

| Alan | Türü | Hesaplama / Kural |
|------|------|-------------------|
| `sembol` | string | Büyük harf ticker (örn. "SM") |
| `isim` | string | Şirketin tam resmi adı |
| `sektor` | string | Türkçe sektör adı (bkz. sektör listesi) |
| `adet` | int | Hisse adedi |
| `maliyet_baz` | float | Ortalama alış fiyatı (USD) |
| `guncel_fiyat` | float | FMP API'den gelen güncel kapanış fiyatı |
| `yatirim` | float | `adet × maliyet_baz` |
| `guncel_deger` | float | `adet × guncel_fiyat` |
| `kar_zarar` | float | `guncel_deger - yatirim` |
| `kar_zarar_yuzde` | float | `(kar_zarar / yatirim) × 100` |
| `gunluk_degisim_yuzde` | float | FMP `changesPercentage` alanından |
| `son_guncelleme` | datetime | Her güncellemede `datetime.now().isoformat()` |
| `giris_tarihi` | date | `"YYYY-MM-DD"` formatında |
| `giris_fiyati` | float | İlk alış fiyatı (ortalama değil) |
| `giris_nedeni` | string | Türkçe, detaylı giriş tezi |
| `agirlik_yuzde` | float | `(guncel_deger / toplam_deger) × 100` |

### Portföy-Seviyesi Hesaplamalar

```
toplam_deger = sum(pozisyon.guncel_deger) + nakit.miktar
toplam_getiri_yuzde = ((toplam_deger - baslangic_sermaye) / baslangic_sermaye) × 100
nakit.miktar = baslangic_sermaye - sum(pozisyon.yatirim) + realized_pnl
agirlik_yuzde = (guncel_deger / toplam_deger) × 100  [her pozisyon için]
```

### Transaction Şeması (portföy içi `transactions[]`)

```json
{
  "tarih": "2026-02-20",
  "islem_tipi": "ALIŞ",
  "sembol": "SM",
  "adet": 1040,
  "fiyat": 20.67,
  "tutar": 21496.80,
  "aciklama": "Başlangıç pozisyonu - Dengeli portföy - Oil & gas E&P"
}
```

| Alan | Değerler | Kural |
|------|---------|-------|
| `islem_tipi` | `"ALIŞ"` veya `"SATIŞ"` | Türkçe, büyük harf |
| `tutar` | float | `adet × fiyat` |
| `aciklama` | string | Türkçe, portföy adı + neden içermeli |

### Notes Şeması (portföy içi `notes[]`)

```json
{
  "date": "2026-02-20T19:41:06.665367",
  "type": "entry",
  "content": "Türkçe not içeriği"
}
```

| `type` değerleri | Kullanım |
|-----------------|---------|
| `"entry"` | Yeni pozisyon girişi |
| `"exit"` | Pozisyon çıkışı |
| `"rebalance"` | Portföy yeniden dengeleme |
| `"format_fix"` | Teknik düzeltme |
| `"market_note"` | Piyasa gözlemi |

---

## 2. SWING TRADE DOSYALARI ŞEMASI

### 2a. `data/swing/active.json` — Açık Pozisyonlar

```json
{
  "son_guncelleme": "2026-02-20T16:36:55.511599",
  "not": "SWING TRADE SADECE SİMÜLASYON - Sadece % kazanç/kayıp takibi (MAX: 10 pozisyon)",
  "aktif_pozisyonlar": [
    {
      "id": "SWING-001",
      "sembol": "NEM",
      "giris_tarihi": "2026-02-12",
      "giris_fiyati": 118.12,
      "guncel_fiyat": 124.97,
      "guncel_kar_zarar_yuzde": 5.80,
      "hedef_fiyat": 129.93,
      "stop_loss": 112.21,
      "tutulan_gun": 7,
      "giris_nedeni": "Güçlü momentum, altın madenciliği lideri, güvenli liman talebi",
      "katalizor": "Altın fiyat gücü, malzeme sektörü rotasyonu",
      "tez": "Dünyanın en büyük altın üreticisi, emtia gücü",
      "zaman_cercevesi": "7-10 gün",
      "risk": "Altın fiyat dönüşü, dolar güçlenmesi",
      "durum": "Normal aralıkta",
      "tarama_yontemi": "RSI oversold / momentum",
      "son_guncelleme": "2026-02-20T19:41:14.015574",
      "partial_exit_plan": {
        "hedef_ulasildiginda": {
          "aksiyon": "%50 POZİSYONU SAT",
          "satis_fiyati": 129.93,
          "sebep": "Kar garantiye al"
        },
        "kalan_50_icin": {
          "aksiyon": "TRAİLİNG STOP AKTİF",
          "baslangic_trailing_stop": 123.43,
          "trailing_yuzde": 5,
          "aciklama": "Zirveden -%5 düşünce sat"
        },
        "durum": "Hedef bekleniyor"
      }
    }
  ]
}
```

#### Aktif Pozisyon — Zorunlu Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `id` | string | `"SWING-NNN"` formatında sıralı ID |
| `sembol` | string | Büyük harf ticker |
| `giris_tarihi` | date | `"YYYY-MM-DD"` |
| `giris_fiyati` | float | Giriş fiyatı |
| `guncel_fiyat` | float | Güncel kapanış fiyatı |
| `guncel_kar_zarar_yuzde` | float | `((guncel - giris) / giris) × 100` |
| `hedef_fiyat` | float | %10 hedef (min) |
| `stop_loss` | float | %5 stop (max) |
| `tutulan_gun` | int | Giriş tarihinden itibaren geçen gün |
| `giris_nedeni` | string | Türkçe, detaylı neden |
| `katalizor` | string | Türkçe, tetikleyici olay |
| `tez` | string | Türkçe, yatırım tezi |
| `zaman_cercevesi` | string | Örn: `"7-10 gün"` |
| `risk` | string | Türkçe, ana riskler |
| `durum` | string | Güncel durum açıklaması |
| `tarama_yontemi` | string | Tarama yöntemi (bkz. yöntemler) |
| `son_guncelleme` | datetime | Her güncellemede yenile |

#### Tarama Yöntemleri (`tarama_yontemi` değerleri)
- `"RSI oversold"` — RSI < 30 veya aşırı satım
- `"earnings momentum"` — Kazanç sürprizi sonrası ivme
- `"breakout"` — Direnç kırılımı
- `"sektor liderligi"` — Sektör rotasyonunda öncü
- `"momentum"` — Fiyat + hacim momentum taraması

---

### 2b. `data/swing/closed.json` — Kapanmış Pozisyonlar

```json
{
  "son_guncelleme": "2026-02-20",
  "kapatilan_pozisyonlar": [
    {
      "id": "SWING-001",
      "sembol": "GOOGL",
      "giris_tarihi": "2026-01-02",
      "cikis_tarihi": "2026-02-03",
      "giris_fiyati": 315.15,
      "cikis_fiyati": 339.71,
      "kar_zarar_yuzde": 7.79,
      "tutulan_gun": 23,
      "cikis_nedeni": "Hedefe yakın, kar reali edildi",
      "sonuc": "KAZANÇ",
      "ders": "Momentum devam stratejisi çalıştı."
    }
  ]
}
```

#### Kapanmış Pozisyon — Zorunlu Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `cikis_tarihi` | date | `"YYYY-MM-DD"` |
| `cikis_fiyati` | float | Çıkış fiyatı |
| `kar_zarar_yuzde` | float | `((cikis - giris) / giris) × 100` |
| `tutulan_gun` | int | Giriş → çıkış arası gün |
| `cikis_nedeni` | string | Türkçe, neden çıkıldı |
| `sonuc` | string | `"KAZANÇ"` veya `"ZARAR"` |
| `ders` | string | Türkçe, bu trade'den çıkarılan ders |

---

### 2c. `data/swing/watchlist.json` — İzleme Listesi

```json
{
  "son_guncelleme": "2026-02-20T16:48:07.288589",
  "not": "Bir sonraki işlemler için potansiyel swing adayları",
  "izleme_listesi": [
    {
      "sembol": "SPG",
      "guncel_fiyat": 202.01,
      "momentum_5gun": 2.9,
      "sektor": "REITs - Alışveriş Merkezleri",
      "notlar": "AVM REIT'i, perakende toparlanma oyunu",
      "urgency": "medium",
      "ekleme_tarihi": "2026-02-20",
      "son_kontrol": null,
      "hedef_giris": "195-200",
      "hedef_fiyat": 220.0,
      "stop_loss": 190.0
    }
  ],
  "haric_tutulanlar": [
    {
      "sembol": "GOOGL",
      "neden": "Negatif momentum -6.7%, tech zayıflığı devam ediyor"
    }
  ]
}
```

#### Watchlist Aday — Alanlar

| Alan | Türü | Açıklama |
|------|------|---------|
| `sembol` | string | Ticker |
| `guncel_fiyat` | float | Güncel fiyat |
| `momentum_5gun` | float | 5 günlük % değişim |
| `sektor` | string | Türkçe sektör |
| `notlar` | string | Türkçe gözlemler |
| `urgency` | string | `"high"` / `"medium"` / `"low"` |
| `ekleme_tarihi` | date | Watchlist'e eklenme tarihi |
| `son_kontrol` | date/null | Son kontrol tarihi veya null |
| `hedef_giris` | string | Fiyat aralığı (örn. `"195-200"`) |
| `hedef_fiyat` | float | Hedef çıkış fiyatı |
| `stop_loss` | float | Stop seviyesi |

---

## 3. ÖZET DOSYASI — `data/summary.json`

```json
{
  "son_guncelleme": "2026-02-20",
  "simulasyon_donemi": "17 Şubat 2026 - 20 Şubat 2026",
  "islem_gunleri": 4,
  "toplam_sermaye": 400000.0,
  "toplam_deger": 416637.99,
  "toplam_kar_zarar": 16637.99,
  "toplam_kar_zarar_yuzde": 4.16,
  "benchmark_spy": 0.0,
  "alpha": 4.16,
  "portfolyolar": {
    "dengeli": {
      "isim": "Dengeli Portföy",
      "deger": 105419.58,
      "maliyet": 100000.0,
      "kar_zarar": 5419.58,
      "kar_zarar_yuzde": 5.42,
      "pozisyon_sayisi": 6,
      "nakit": {
        "miktar": 9613.20,
        "para_birimi": "USD"
      },
      "durum": "BAŞARILI"
    },
    "agresif": {...},
    "temettü": {...},
    "rotasyon": {...},
    "swing_trade": {
      "isim": "Swing Trade (Simülasyon)",
      "pozisyon_sayisi": 5,
      "ortalama_getiri_yuzde": 2.5,
      "bos_slot": 5,
      "durum": "5/10 pozisyon aktif"
    }
  },
  "son_islemler": ["İşlem özeti satırları"],
  "onemli_dersler": ["Önemli ders satırları"]
}
```

### Summary Hesaplama Kuralları

```
toplam_deger = dengeli.deger + agresif.deger + temettü.deger + rotasyon.deger
toplam_kar_zarar = toplam_deger - toplam_sermaye
toplam_kar_zarar_yuzde = (toplam_kar_zarar / toplam_sermaye) × 100
alpha = toplam_kar_zarar_yuzde - benchmark_spy
```

---

## 4. TRANSACTIONS CSV — `data/transactions.csv`

### Format

```
date,action,symbol,shares,price,total,reason
2026-02-17,BUY,SM,1040,20.67,21496.80,"Başlangıç pozisyonu - Dengeli portföy - Oil & gas E&P"
2026-02-19,SELL,FCX,132,60.17,7943.10,"Zayıf performans - Çin talebi riski - P/E 40x"
```

| Sütun | Değerler | Kural |
|-------|---------|-------|
| `date` | `YYYY-MM-DD` | ISO tarih |
| `action` | `BUY` veya `SELL` | İngilizce (CSV standardı) |
| `symbol` | büyük harf | Ticker |
| `shares` | int | Adet |
| `price` | float | Hisse fiyatı |
| `total` | float | `shares × price` |
| `reason` | string (Türkçe) | Neden alındı/satıldı - portföy adı + neden |

---

## 5. SEKTÖR İSİMLERİ STANDARDI (Türkçe)

| Türkçe | Kullanım Bağlamı |
|--------|-----------------|
| `"Enerji"` | E&P, majör petrol şirketleri |
| `"Enerji ETF"` | XLE gibi ETF'ler (Dengeli portföyde) |
| `"Temel Tüketim"` | Savunmacı tüketim |
| `"Tütün"` | MO, PM gibi |
| `"Telekomünikasyon"` | T, VZ gibi |
| `"Sağlık"` | Sağlık hizmeti, sigorta |
| `"Teknoloji"` | Yazılım, yarı iletken |
| `"Savunma"` | Savunma sanayi |
| `"Endüstriyel"` | XLI, CAT gibi |
| `"Emtia"` | FCX, RGLD gibi |
| `"Finans"` | Bankalar, sigorta |
| `"REITs"` | Gayrimenkul yatırım ortaklıkları |
| `"Kamu Hizmetleri"` | Utilities |
| `"İletişim"` | Communication services |
| `"Tüketim Döngüsel"` | Consumer cyclical |

---

## 6. GÜNLÜK GÜNCELLEME AKIŞI

### Fiyat Güncellemesi (Her gün piyasa kapanışında)

1. FMP `batch-quote` ile tüm sembolleri çek
2. Her pozisyon için güncelle:
   - `guncel_fiyat` = `price`
   - `gunluk_degisim_yuzde` = `changesPercentage`
   - `guncel_deger` = `adet × guncel_fiyat`
   - `kar_zarar` = `guncel_deger - yatirim`
   - `kar_zarar_yuzde` = `(kar_zarar / yatirim) × 100`
   - `agirlik_yuzde` yeniden hesapla
   - `son_guncelleme` = `datetime.now().isoformat()`
3. Portföy toplamlarını yeniden hesapla
4. `summary.json` güncelle
5. Swing trade'lerde `tutulan_gun` artır, stop/hedef kontrol et
6. Git commit + push

### Yeni Pozisyon Açılışı

1. Portföy JSON'unda `pozisyonlar[]` dizisine ekle (tam şema)
2. `nakit.miktar -= adet × fiyat`
3. Portföy `transactions[]` listesine ekle
4. `data/transactions.csv` dosyasına satır ekle
5. `summary.json` güncelle
6. Git commit: `"[ALIŞ] PORTFÖY_ADI - SEMBOL @FIYAT - NEDEN"`

### Pozisyon Kapatma (Satış)

1. `pozisyonlar[]` listesinden kaldır
2. `nakit.miktar += adet × satis_fiyati`
3. Portföy `transactions[]` listesine ekle
4. `data/transactions.csv` dosyasına satır ekle
5. Swing ise `data/swing/closed.json`'a ekle (tüm zorunlu alanlar)
6. `summary.json` güncelle
7. Git commit: `"[SATIŞ] PORTFÖY_ADI - SEMBOL @FIYAT - NEDEN"`

---

## 7. SWING TRADE KURALLARI (Sayısal Sınırlar)

| Kural | Değer |
|-------|-------|
| Max eşzamanlı pozisyon | 10 |
| Stop-loss | %5 |
| Kar hedefi | %10 |
| Min R:R oranı | 2:1 |
| Tavsiye tutma süresi | 7-10 gün (kesin üst limit yok, trailing stop ile yönetilir) |

---

## 8. GIT COMMIT FORMAT

```
[TİP] PORTFÖY - SEMBOL @FİYAT - AÇIKLAMA

Örnekler:
[ALIŞ] Dengeli - SM @20.67 - Oil & gas başlangıç pozisyonu
[SATIŞ] Agresif - AMD @199.39 - Stop-loss tetiklendi -%10.8
[GÜNCELLEME] Tüm portföyler - 20 Şubat kapanış fiyatları
[SWING-GİRİŞ] NEM @118.12 - Altın momentum breakout
[SWING-ÇIKIŞ] CAT @775.00 - Hedef tutturuldu +12%
[REBALANCE] Rotasyon - Tech'ten Enerji+Endüstriye rotasyon
```

---

## 9. SIKÇA YAPILAN HATALAR (YAPMA!)

| Hata | Doğrusu |
|------|---------|
| `kar_zarar_yuzde` = `kar_zarar / baslangic_sermaye` | `kar_zarar / yatirim × 100` |
| `agirlik_yuzde` güncellenmeden bırakmak | Her fiyat güncellemesinde yeniden hesapla |
| `nakit` güncellenmeden bırakmak | Alış/satışta mutlaka güncelle |
| İngilizce `islem_tipi` (`"BUY"`) | Türkçe: `"ALIŞ"` / `"SATIŞ"` |
| CSV'de Türkçe `action` (`"ALIŞ"`) | CSV'de İngilizce: `"BUY"` / `"SELL"` |
| Swing ID sıralı değil | `"SWING-010"` → `"SWING-011"` → sıralı gitmeli |
| `summary.json`'ı güncellemeyi unutmak | Her portföy değişikliğinde summary güncelle |
| `giris_nedeni` İngilizce bırakmak | Türkçe ve detaylı olmalı |
| Timestamp yerine sadece tarih yazmak | `son_guncelleme` datetime, `giris_tarihi` date |
