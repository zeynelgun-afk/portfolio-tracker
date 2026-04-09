# HAFTALIK RAPOR — PAZAR DEĞERLENDİRMESİ v1.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz.
>
> **zorunlu adımlar:**
> - [ ] ADIM 0 — playbook + piyasa istihbaratı + geçen hafta özeti oku
> - [ ] ADIM 1 — makro veri toplama (endeksler, sektörler, emtia, treasury, VIX)
> - [ ] ADIM 2 — portföy durum + tüm pozisyonlar K-rule kontrolü
> - [ ] ADIM 3 — K-rule otomatik script raporu (k09/k14/k15b/k16/k17/k18/k19/k20)
> - [ ] ADIM 4 — sektör rotasyonu analizi (haftalık RS)
> - [ ] ADIM 5 — balon riski değerlendirmesi (skill: us-market-bubble-detector)
> - [ ] ADIM 6 — portföy rebalancing (K-10 + K-12 + K-17 cross-check)
> - [ ] ADIM 7 — izleme listesi güncelleme (data/watchlist.json)
> - [ ] ADIM 8 — gelecek hafta takvimi ve strateji
> - [ ] RAPOR — bölüm 1-8 eksiksiz yazıldı mı?
> - [ ] GIT — commit + push yapıldı mı?
> - [ ] TELEGRAM — rapor gönderildi mi?

> **versiyon**: 1.0 | **son güncelleme**: 7 nisan 2026
> **çıktı dosyası**: `reports/weekly/WEEKLY_YYYY_MM_DD.md`
> **çalışma zamanı**: pazar günleri, NYSE kapalı
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[HAFTALIK RAPOR] hafta YYYY-MM-DD`

---

## ZAMAN BİLİNCİ

- rapor pazar günü yazılır — cuma NYSE kapanışı baz
- son seans verisi = cuma kapanış (FMP'de kesin)
- VIXY = VIX proxy (doğrudan ^VIX güvenilmez)
- USO = petrol proxy (CLUSD/WTIUSD güvenilmez)

---

## ÇALIŞMA AKIŞI

```
ADIM 0 — PLAYBOOK + PİYASA İSTİHBARATI + GEÇEN HAFTA
  → docs/TRADING_PLAYBOOK.md oku, 17 K kuralını gözden geçir
  → docs/MARKET_INTELLIGENCE.md oku, aktif temaları hatırla
  → reports/weekly/WEEKLY_{geçen_hafta}.md oku, geçen haftanın planı tuttu mu kontrol et
  → data/swing/status.json oku, K-14 drawdown fren durumu aktif mi?

ADIM 1 — MAKRO VERİ TOPLAMA
  → FMP quote: SPY, QQQ, DIA, IWM, VIXY, USO, GCUSD
  → FMP sector-performance-snapshot (son 5 gün)
  → FMP treasury-rates (haftalık değişim)
  → web araması: "weekly market recap {tarih}", "sector rotation week"
  → prediction markets: kalshi + polymarket haftalık değişim

ADIM 2 — PORTFÖY DURUM
  → 3 portföy JSON oku (balanced/aggressive/dividend)
  → her pozisyon için K-rule çapraz kontrol:
    • K-04: SMA50 altında mı? (trend kaybı)
    • K-06: stop mesafe kontrolü (max(2×ATR, %5))
    • K-11: RSI 80+ baskın tetik kontrolü
    • K-12: konsantrasyon limit aşımı (Dengeli %25 / Agresif %20 / Temettü %15 / sektör %40)
    • K-16: earnings 7g içinde mi? (portföy sell-the-news skor)
  → data/swing/active.json + closed.json oku

ADIM 3 — K-RULE OTOMATİK SCRIPT RAPORU
  → scripts/k09_proximity_check.py --quiet (stop yakınlık)
  → scripts/k14_drawdown_track.py (drawdown status)
  → scripts/k20_rs_filter.py --status (10 sektör RS durum)
  → Ana pozisyonlar için:
    • scripts/k17_correlation_check.py SYMBOL --quiet
    • scripts/k18_insider_check.py SYMBOL --quiet (senior sell kontrolü)
  → Tüm alert'ler raporda bölüm 3'te özetlensin

ADIM 4 — SEKTÖR ROTASYONU
  → 11 SPDR sektör ETF haftalık performans tablosu
  → RS hesabı (sektör - SPY)
  → rotasyon yönü: risk-on / risk-off / karışık
  → K-20 dead cat bounce patern kontrol (scripts/k20_rs_filter.py --status)

ADIM 5 — BALON RİSKİ
  → skill kullan: us-market-bubble-detector (minsky-kindleberger framework v2.1)
  → put/call ratio, VIX, margin debt, breadth, IPO
  → mekanik skor → risk seviyesi (yeşil/sarı/kırmızı)
  → K-13 v4.1 ile entegrasyon (VIX bandı + balon skoru birlikte karar)

ADIM 6 — PORTFÖY REBALANCING
  → K-10 VIX bazlı savunmacı allokasyon kontrolü ($600K bazlı)
  → K-12 tek hisse + sektör + tema limit aşım taraması
  → K-17 anlatı tema yoğunluk kontrolü
  → aşım varsa aksiyon planı (ADIM 8'de)

ADIM 7 — İZLEME LİSTESİ GÜNCELLEME
  → data/watchlist.json oku
  → mevcut adayların fiyatları + K-rule filtreleri uygula:
    • scripts/k19_xlp_filter.py (XLP eleme)
    • scripts/k20_rs_filter.py (RS dead cat eleme)
    • scripts/k18_insider_check.py (senior sell eleme)
  → yeni aday ekle (agresif v2 AI tedarik zinciri katmanları + temettü skorları)
  → güncel olmayan adayları haric_tutulanlar'a taşı (neden ile)

ADIM 8 — GELECEK HAFTA STRATEJİ
  → ekonomik takvim (tradingeconomics + web)
  → kazanç takvimi (FMP earnings-calendar, portföy kesişimi)
  → senaryo planlaması (A/B/C) zorunlu
  → aksiyon planı (hemen / izle / pasif)
  → risk senaryoları (what-if)

RAPOR YAZ (bölüm 1-8) → git commit + push → telegram
```

---

## RAPOR FORMATI

```markdown
# haftalık piyasa değerlendirmesi - {tarih}

**rapor dönemi**: {pazartesi} - {cuma}
**hazırlanma tarihi**: pazar, {tarih}

---

## özet: {3-5 kelime tema}

{3-4 paragraf — haftanın ana gelişmeleri, portföy performansı, kritik karar noktaları}

---

## 1. makro göstergeler

### endeks performansı ({cuma} kapanış)

| endeks | fiyat | haftalık | YTD | RSI(14) | SMA50 | SMA200 | teknik durum |
|--------|-------|----------|-----|---------|-------|--------|---------------|
| SPY | $XXX.XX | ±X.X% | ±X.X% | XX.X | ✅/❌ | ✅/❌ | [durum] |
| QQQ | ... | | | | | | |
| DIA | ... | | | | | | |
| IWM | ... | | | | | | |

### emtia + makro

| varlık | fiyat | haftalık | not |
|--------|-------|----------|-----|
| WTI (USO proxy) | $XX.XX | ±X% | |
| altın | $X,XXX | ±X% | |
| 10Y treasury | %X.XX | ±bps | |
| dolar (DXY) | XX.X | ±X% | |
| VIX (VIXY proxy) | XX | ±X% | |

### prediction markets haftalık değişim

- Fed rate cut 2026: %XX → %XX (±%X)
- [gündem olayı]: %XX → %XX (±%X)
- aksiyon: [ne demeye geliyor]

---

## 2. portföy performansı

### genel bakış

| portföy | başlangıç | şu an | haftalık | toplam | alpha vs SPY |
|---------|-----------|-------|----------|--------|--------------|
| dengeli | $100K | $XXX | ±X% | ±X% | ±X% |
| agresif | $400K | $XXX | ±X% | ±X% | ±X% |
| temettü | $100K | $XXX | ±X% | ±X% | ±X% |
| **toplam** | **$600K** | **$XXX** | **±X%** | **±X%** | **±X%** |

### K-rule durum kontrolü (3 portföy toplamı)

**K-10 VIX allokasyon**:
- VIX bandı: [sakin/dikkatli/gergin/panik]
- Min savunmacı + nakit eşiği: %XX
- Mevcut: %XX → [✓ sağlanıyor / ❌ eksik]

**K-12 konsantrasyon**:
- Hisse limitleri (portföy bazlı): [tüm pozisyonlar kontrol edildi]
- Sektör limit (%40): [en yüksek sektör %XX]
- Tema limit (%40): [en yüksek tema %XX]

**K-17 korelasyon**:
- En yoğun anlatı tema: [tema] %XX
- Cross-portföy aynı hisse: [varsa liste]

### portföy detayları

[dengeli / agresif / temettü için tablolar]

---

## 3. swing trade durumu + K-rule alert'leri

### aktif swing pozisyonları

| id | sembol | giriş | cuma | k/z% | chandelier stop | gün | durum |
|----|--------|-------|------|------|-----------------|-----|-------|

### K-14 DRAWDOWN DURUMU

data/swing/status.json:
- aktif_durum: [normal / K14_DRAWDOWN_FREN]
- peak-to-trough: %XX.XX
- ortam testi: VIX/SPY SMA50 [sağlandı / sağlanmadı]
- yeni giriş: [izinli / yasak (A-kalite istisna)]

### K-14 fren kaldırma kriterleri (haftalık değerlendirme)

> fren sonsuza kadar aktif kalmasın diye her pazar teker teker kontrol edilir

| koşul | hedef | mevcut | durum |
|---|---|---|---|
| VIX (VIXY proxy) | <22 | XX.X | ✓/✗ |
| SPY fiyat vs SMA50 | üstü | $XXX vs $XXX | ✓/✗ |
| 11 sektörden SPY'yi haftalık geçen sayısı | ≥6 | X/11 | ✓/✗ |
| Son swing ardışık zarar serisi bitti mi | evet | [son trade W/L] | ✓/✗ |
| **karar** | 4/4 → fren kalkar | X/4 | [KALKAR / DEVAM] |

**fren kaldırılırsa**: data/swing/status.json `aktif_durum` → "normal", değişiklik rapora ve playbook'a işlenir, commit edilir.
**fren devamsa**: haftalık raporda hangi koşulların karşılanmadığı açıkça belirtilir, ek bekleme süresi tahmini verilir.

### K-rule script raporu (haftalık özet)

**K-09 stop yakınlık (tüm portföy + swing)**: X alert
**K-14 drawdown**: [normal / 2 ardışık zarar / drawdown fren]
**K-17 korelasyon uyarıları**: X sembol
**K-18 insider alerts**: X sembol (senior sell)
**K-20 dead cat sektörler**: [varsa liste]

---

## 4. sektör rotasyonu analizi

### 11 SPDR sektör ETF haftalık performans

| sektör ETF | haftalık | RS vs SPY | yorum |
|------------|----------|-----------|-------|
| XLK (tech) | ±X.X% | ±X.X% | |
| XLC (iletişim) | ... | | |
| XLY (döngüsel tüketim) | ... | | |
| XLI (endüstri) | ... | | |
| XLF (finans) | ... | | |
| XLV (sağlık) | ... | | |
| XLE (enerji) | ... | | |
| XLB (malzeme) | ... | | |
| XLRE (gayrimenkul) | ... | | |
| XLU (utilities) | ... | | |
| XLP (temel tüketim) | ... | | |

### K-20 dead cat bounce paterni (RS20<0 + RS10>0)

**Dead cat sektörler (swing girişi yasak)**: [liste]

### rotasyon yönü

- risk-on / risk-off / karışık
- öncü sektörler: [liste]
- zayıf sektörler: [liste]
- portföy etkisi: [bizim pozisyonlarımız nasıl etkileniyor]

---

## 5. balon riski değerlendirmesi

> skill: us-market-bubble-detector (minsky-kindleberger framework v2.1)

### mekanik skor tablosu

| gösterge | değer | skor |
|----------|-------|------|
| put/call ratio | X.XX | X/5 |
| VIX | XX | X/5 |
| margin debt | $XB | X/5 |
| breadth (%above 200SMA) | %XX | X/5 |
| IPO aktivitesi | [seviye] | X/5 |

**toplam balon skoru**: X/25 → [yeşil/sarı/kırmızı]

### yorum

- mevcut safha: [kindleberger 5 aşama hangisi]
- K-13 ile entegrasyon: VIX bandı + balon skoru → [karar]
- portföy konumu: [savunmacı / nötr / agresif]

---

## 6. portföy rebalancing kararı

### aşım kontrolü

| kural | eşik | mevcut | durum | aksiyon |
|-------|------|--------|-------|---------|
| K-12 Dengeli tek hisse | %25 | %XX | ✓/⚠ | |
| K-12 Agresif tek hisse | %20 | %XX | ✓/⚠ | |
| K-12 Temettü tek hisse | %15 | %XX | ✓/⚠ | |
| K-12 GICS sektör | %40 | %XX | ✓/⚠ | |
| K-12 anlatı tema | %40 | %XX | ✓/⚠ | |
| K-10 VIX savunmacı min | %XX | %XX | ✓/⚠ | |

### rebalancing aksiyonları

- [varsa kısmi satış/alış planı]
- [K-14 drawdown fren varsa: sadece rebalance, yeni giriş yok]

---

## 7. izleme listesi güncellemesi

### data/watchlist.json değişiklikleri

**eklenen adaylar** (X):
- SEMBOL — hedef portföy — giriş eşiği — R:R — urgency
- [K-18 insider temiz, K-17 korelasyon OK, K-20 sektör OK]

**çıkarılan adaylar** (X):
- SEMBOL — neden (K-XX ihlali / fırsat geçti / tez bozuldu)

### agresif v2 AI tedarik zinciri izleme

| katman | hisse | durum | K-rule filtre sonucu |
|--------|-------|-------|----------------------|
| çip tasarımı | NVDA | ... | ... |
| ekipman | ASML | ... | ... |
| kimya | ENTG | ... | ... |
| optik | COHR | ... | ... |
| güç | POWL | ... | ... |
| soğutma | VRT | ... | ... |
| DC | DLR | ... | ... |

---

## 8. gelecek hafta strateji ve takvim

### ekonomik takvim

| tarih | saat (TR) | veri | beklenti | önem |
|-------|-----------|------|----------|------|

### kazanç takvimi (portföy/watchlist kesişimi)

| tarih | sembol | timing | beklenti | K-16 skor |
|-------|--------|--------|----------|-----------|

### senaryo planlaması (A/B/C)

**senaryo A (%XX)**: [en olası] → aksiyon
**senaryo B (%XX)**: [alternatif] → aksiyon
**senaryo C (%XX)**: [tail risk] → aksiyon

### aksiyon planı

🔴 **hemen** (pazartesi açılış):
1. [aksiyon] — [sebep + K-rule referansı]

🟡 **izle** (hafta boyunca):
2. [koşul] → [aksiyon]

🟢 **pasif** (seviye bekle):
3. [sembol + koşul]

### risk senaryoları

- [risk 1] → [mitigation]
- [risk 2] → [mitigation]

---

## sonuç ve anahtar mesajlar

1. [anahtar mesaj 1]
2. [anahtar mesaj 2]
3. [anahtar mesaj 3]

**bir sonraki güncelleme**: pazartesi sabah raporu

---

*finzora ai | fmp api | hafta {tarih} kapandı*
```

---

## KALİTE KONTROL

rapor tamamlandığında kontrol et:

- [ ] tüm 8 bölüm yazıldı mı?
- [ ] 17 K kuralı raporda açıkça değerlendirildi mi?
- [ ] k09/k14/k15b/k16/k17/k18/k19/k20 scriptleri çalıştı mı?
- [ ] K-14 drawdown status kontrol edildi mi?
- [ ] K-10/K-12 aşım tablosu var mı?
- [ ] Balon riski mekanik skor hesaplandı mı?
- [ ] Senaryo planlaması A/B/C yapıldı mı?
- [ ] Aksiyon planı net ve uygulanabilir mi?
- [ ] Git commit + push yapıldı mı?
- [ ] Telegram raporu gönderildi mi?

---

## JSON/CSV GÜNCELLEME

weekly prompt'ta JSON fiyat güncellemesi yapılmaz (cuma kapanış pazartesi günlük raporda yansır).
SADECE şu güncellemeler yapılabilir:
- data/watchlist.json (yeni/çıkarılan adaylar)
- data/swing/status.json (K-14 durum güncellenmiş ise)

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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

---

> son güncelleme: 7 nisan 2026 v1.0 | finzora ai
