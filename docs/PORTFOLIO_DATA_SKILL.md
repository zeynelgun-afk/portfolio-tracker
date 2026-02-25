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

## 2. SWING TRADE

> **Swing trade ile ilgili tüm kurallar, dosya şemaları ve stratejiler tek bir yerde:**
> 📄 **`docs/SWING_TRADE_RULES.md`**
>
> Bu dosya şunları içerir:
> - Hisse seçim kriterleri (beta, ATR%, hacim filtreleri)
> - 5 giriş stratejisi (RSI oversold, breakout, pullback, earnings momentum, sektör rotasyonu)
> - ATR tabanlı dinamik stop-loss yönetimi
> - Kademeli çıkış planı (3 aşamalı)
> - Pozisyon boyutlandırma (%1 risk kuralı)
> - `active.json`, `closed.json`, `watchlist.json` dosya şemaları
> - Tarama yöntemleri ve performans takibi

### Dosya Yolları
| Dosya | Açıklama |
|-------|----------|
| `data/swing/active.json` | Açık pozisyonlar (max 10) |
| `data/swing/closed.json` | Kapanmış pozisyonlar |
| `data/swing/watchlist.json` | İzleme listesi |
| `docs/SWING_TRADE_RULES.md` | Tüm kurallar ve şemalar |

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

## 7. GIT COMMIT FORMAT

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

## 8. SIKÇA YAPILAN HATALAR (YAPMA!)

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
