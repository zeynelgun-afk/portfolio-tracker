# Adil Değer Skill v5.0 — Etap 2 Notu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 2 tamamlandı

## Yapılan Değişiklikler

### A. Sadeleştirme — 4 Yöntem Çıkarıldı

`calculate_methods()` fonksiyonu temizlendi. v5.0 toplam yöntem: **9** (skill ismi ile uyumlu).

**Çıkarılanlar:**
- ❌ **Graham Number** — 1949'dan kalma, modern AI/tech için saçma değerler veriyordu
- ❌ **EV/EBIT** — EV/EBITDA ile tekrar, D&A farkı ihmal edilebilir
- ❌ **Justified P-B (Gordon + RIM)** — Karmaşık, modern büyüme şirketlerinde yanıltıcı
- ❌ **Rule of 40** — Saf SaaS için, portföyde yok

**Kalan 9 Yöntem:**
| # | Yöntem | Kategori |
|---|---|---|
| 1 | Net P/E (TTM) | Traditional |
| 2 | EV/EBITDA | Traditional |
| 3 | EV/Revenue | Traditional |
| 4 | P/FCF (4y normalize) | Traditional |
| 5 | Forward P/E (NTM/2y) | Forward |
| 6 | DCF (10y + Terminal) | Forward |
| 7 | PEG Ratio | Growth |
| 8 | EV/Forward Revenue | Growth |
| 9 | EV/Forward EBITDA | Growth |

Bonus: Reverse DCF (yöntem değil, bilgi notu olarak çıktıda)

### B. FMP Layer Entegrasyonu — Yeni Sinyaller

`analyze()` fonksiyonu sonuna `v5_signals` bloğu eklendi. `format_output()` sonuna **"v5.0 EK SİNYALLER"** bölümü eklendi.

**6 yeni sinyal:**

1. **Risk Skorları (Altman Z + Piotroski)**
   ```
   🛡️ Altman Z: 68.23 → 🟢 GÜVENLİ
   🛡️ Piotroski: 6/9 → 🟡 SAĞLAM
   ```

2. **Analist Sentiment + Momentum**
   ```
   💚 Strong Buy: 2 | Buy: 58 | Hold: 16 | Sell: 3 | Strong Sell: 0
   Konsensüs: Buy
   Son 6 ay: 🔴 DOWNGRADE TRENDI (-6)
   ```

3. **DCF Sanity Check**
   ```
   FMP DCF (unlevered): $247.15
   FMP DCF (levered):   $257.86
   Bizim DCF (normal):  $58.98
   ⚠️ Fark %-76 — varsayımlar farklı, gözden geçir
   ```

4. **Konsantrasyon Riski (Product + Geographic)**
   ```
   Ürün/Segment (2026): 🔴 KRİTİK: Data Center %90
   Coğrafya (2026): 🟠 YÜKSEK: UNITED STATES %69
   ```

5. **Canlı Sektör P/E**
   ```
   Canlı: 62.3x (industry-pe-snapshot)
   Statik (skill içi): 28x
   ⚠️ Statik tablo %+123 sapmış — sektör eskimiş tabloya göre yukarıda
   ```

6. **Dinamik WACC (CAPM)**
   ```
   Canlı: %17.84 (CAPM (Rf %4.38 + Beta 2.244 × ERP %6))
   Statik fallback: %10
   ```

### C. Version + Header Güncellemesi
- Script versiyonu: `4.0` → `5.0`
- fmp_layer + projection_engine modülleri lazy-import (yoksa v4.1 mode fallback)
- HEADERS = User-Agent eklendi (network sandbox 503 fix)

## NVDA Test Çıktısı — Kritik Bulgular

NVDA üzerinde v5.0 test çalıştırıldı. Bulgular:

### 🔴 Mevcut Skill'in Kalibrasyon Sorunları

1. **DCF parametreleri yanlış**
   - Bizim DCF: $59 (statik WACC %10)
   - FMP DCF: $247 (gerçek piyasa parametreleri)
   - Fark: %-76
   - **Sebep**: Statik WACC %10, ama CAPM canlı %17.84 (Beta 2.24 × ERP %6 + Rf %4.38). DCF aşırı düşük çıkıyor.
   - **Çözüm Etap 3'te**: WACC'yi canlı CAPM ile değiştir, fallback olarak statik tut

2. **Sektör P/E tablosu eskimiş**
   - Statik semicon P/E: 28x
   - Canlı Semiconductors industry P/E: 62.3x
   - Fark: %+123
   - **Sebep**: SECTOR_MULTIPLES tablosu 2025 başında yazıldı, AI sektörü o günden beri sürekli yeni zirve görüyor.
   - **Çözüm Etap 3'te**: Canlı sector-pe öncelik, statik fallback

3. **Konsantrasyon riski rapora girmiyordu**
   - NVDA gelirinin %90'ı Data Center segmentinden
   - ABD'den %69 gelir
   - Bunu hiç görmüyorduk — şimdi otomatik tespit ediliyor
   - **Etki**: NVDA gibi mega-cap için bile **müşteri/segment konsantrasyon** sinyali kritik

4. **Analist downgrade trendi yakalandı**
   - NVDA için son 6 ayda **-6 net rating düşüşü**
   - Konsensüs hâlâ Buy, ama yön zayıflıyor
   - **Etki**: Erken uyarı sinyali — momentum değişiyor

### 🟢 v5.0 Sinyallerinin Değeri

Bu sinyaller olmasa NVDA için "AL" diyordu ve eski parametrelerle de doğru sonuçtu. Ama v5.0 ile:
- Risk skorlarıyla **iflas riski 🟢 net görünüyor**
- Konsantrasyon riskiyle **Data Center bağımlılığı** gözüküyor
- Downgrade momentum'la **dikkat sinyali** var
- DCF sanity check ile bizim hesabımızın bozuk olduğunu **fark ediyoruz** (eskiden $59 yazıyor ve emin oluyorduk)

## Test Durumu

| Test | Sonuç |
|---|---|
| NVDA full pipeline | ✅ Çalışıyor, 9 yöntem + v5 sinyalleri |
| 4 yöntem çıkarma | ✅ Temiz silindi (kalan referans: 0) |
| Syntax check | ✅ OK (1341 satır) |
| Backward compat | ✅ v5.0 modülleri yoksa v4.1 mode fallback |

## Etap 3'te Yapılacaklar

### Yüksek Öncelik (Kalibrasyon Düzeltmeleri)
1. **DCF içine canlı CAPM WACC entegrasyonu** — dcf_calculate'ta statik WACC yerine v5_signals['dynamic_wacc'] kullan
2. **Net P/E'de canlı sektör P/E kullanımı** — calculate_methods'ta SECTOR_MULTIPLES['pe'] yerine v5_signals['live_pe']['value']
3. **Forward P/E'de de canlı sektör P/E** (aynı şekilde)

### Orta Öncelik (Projection Entegrasyonu)
4. **`--projection` flag default ON** — analyze() içinde projection_engine çağrısı, çıktıya "Bölüm 12: 5y Projeksiyon" ekle
5. **Pre-IPO modu** — `--pre-ipo` flag + JSON input, FMP olmadan manuel girdiyle akış
6. **Markdown rapor şablonu** — `reports/research/TICKER_ADIL_DEGER_DATE.md` için 12 bölüm

### Düşük Öncelik (Kozmetik + Doc)
7. SKILL.md v5.0 olarak güncelle
8. references/sektor-margin-profilleri.md ekle
9. references/fmp-endpoint-rehberi.md ekle
10. notes/learnings.md güncelle (NVDA dersleri)
11. Geniş test: CBRS, AMD, KO, TEM, FLYW

## Kod İstatistikleri

| Metrik | v4.1 | v5.0 Etap 2 |
|---|---|---|
| adil_deger.py satır | 1259 | 1341 |
| Aktif yöntem | 13 | 9 |
| Modül sayısı | 1 | 3 (adil_deger + fmp_layer + projection_engine) |
| FMP endpoint kullanımı | 7 | 20 (13 yeni) |
| Statik tablo | 1 (SECTOR_MULTIPLES) | 1 + canlı fallback |

**Kaynak**: finzora ai
