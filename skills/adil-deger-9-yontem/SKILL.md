---
name: adil-deger-9-yontem
description: ABD hisse senetleri için 9 yöntemli kapsamlı adil değer hesaplaması yapar (Net P/E, Forward P/E, EV/EBIT, EV/EBITDA, EV/Revenue, P/FCF, ROE/Justified P-B, Graham, DCF). Ayı/Normal/Boğa olmak üzere 3 piyasa rejiminde ayrı eder değer üretir. Tetikleyiciler: "X hissesini değerle", "adil değer hesapla", "X için fair value", "X kaç eder", "9 yöntem değerleme", "AMKR değerlemesi yap", "MSFT eder fiyatı". Finzora AI sisteminin Adil Değer v3.7.2 metodolojisini uygular. Her kullanımda notes/usage_log.csv ve notes/learnings.md güncellenir.
---

# Adil Değer 9 Yöntem (Finzora AI v3.7.2)

## Amaç

Bir ABD hissesi için **9 farklı yöntemle** adil değer hesaplar ve **3 piyasa rejimi** (Ayı/Normal/Boğa) için ayrı eder değer aralıkları üretir. Mevcut fiyatla karşılaştırır, ucuz/dengeli/pahalı kararı verir.

## Tetikleme

Kullanıcı şunları söylediğinde:
- "X hissesini değerle"
- "X için adil değer hesapla"
- "X kaç eder"
- "X fair value"
- "9 yöntem değerleme"
- "AMKR değerlemesi yap"

## İş Akışı

### Adım 1: Veri Toplama (FMP API)

`scripts/adil_deger.py` betiğini çalıştır. Bu betik FMP'den şunları çeker:

**Profile & Quote:**
- Şirket adı, sektör, endüstri
- Mevcut fiyat, market cap, beta, 52H aralık
- Ortalama hacim, 50/200 SMA

**Ratios TTM & Key Metrics TTM:**
- P/E TTM, P/B, P/S, P/FCF
- EV/EBITDA, EV/Sales
- ROE, ROA, ROIC
- Marjlar (gross, operating, net)
- Borç oranları (D/E, Net Debt/EBITDA)
- Graham Number (FMP'den hazır)

**Income Statement (5 yıl annual + 5 çeyrek):**
- Revenue, Gross Profit, Operating Income, Net Income, EBITDA, EPS

**Cash Flow Statement (5 yıl annual):**
- Operating CF, CapEx, Free Cash Flow

**Balance Sheet (Latest):**
- Cash, Total Debt, Net Debt, Stockholders' Equity

**Analyst Estimates (Forward 4 yıl):**
- Revenue, EBITDA, Net Income, EPS

**Historical Price (90 gün):**
- RSI(14), MA20, son performans

### Adım 2: Sektör Tespit ve Medyan Yükleme

`references/sektor-medyanlari.md` dosyasından şirketin endüstrisine uygun çarpan presetlerini yükle.

**8 Sektör Preseti:**
1. Technology (Software, Hardware)
2. Semiconductors (özel preset, OSAT vs Fabless ayrımı)
3. Financials (Banks, Insurance)
4. Healthcare (Pharma, Biotech)
5. Consumer (Discretionary + Staples)
6. Industrials & Energy
7. REITs
8. Utilities

**Auto-detection mantığı:**
```
profile.sector == "Technology" AND profile.industry contains "Semiconductors"
  → Semiconductors preset
profile.sector == "Financial Services" AND industry contains "Bank"
  → Banks preset
... (tam kural seti referans dosyasında)
```

### Adım 3: Piyasa Rejimi Belirleme

`references/piyasa-rejimleri.md`'den 3 senaryo için çarpan ayarları:

**Mevcut piyasa rejimini tespit et:**
- VIX < 16 ve SPY 200SMA üstünde → **BOĞA** (Bull)
- VIX 16-22 ve SPY 200SMA çevresinde → **NORMAL** (Neutral)
- VIX > 22 veya SPY 200SMA altında → **AYI** (Bear)

VIX ve SPY verisini de FMP'den çek, log'a kaydet. Ama hesap her durumda **3 senaryo** üretir.

### Adım 4: 9 Yöntem Hesaplama

Her yöntem için 3 senaryoda hesapla. Detaylı formüller `references/9-yontem-formuller.md`'de.

| # | Yöntem | Girdiler | Notlar |
|---|---|---|---|
| 1 | Net P/E | EPS TTM × hedef P/E | Sektör medyanı |
| 2 | Forward P/E | EPS 2 yıl forward × hedef P/E | Beklenti baz |
| 3 | EV/EBIT | EBIT × hedef → EV → Equity → /share | Sermaye yapısı bağımsız |
| 4 | EV/EBITDA | EBITDA × hedef → EV → Equity → /share | Capital intensive için iyi |
| 5 | EV/Revenue | Revenue × hedef → EV → Equity → /share | Marjı bozulan firmalar için |
| 6 | P/FCF | (Normalize 4 yıl FCF) × hedef P/FCF | Capex normalize edilir |
| 7 | ROE / Justified P-B | (ROE-g)/(k-g) × BVPS | Bankalar ve ROE-driven firmalar |
| 8 | Graham Number | sqrt(22.5 × EPS × BVPS) | Defansif değer çapası |
| 9 | DCF | 10 yıl FCF projeksiyonu + Terminal | Detaylı, %10 WACC default |

**Pure Forward auto-trigger:** Eğer TTM net income negatif veya marj < %3 ise yöntemler 1, 4, 6, 7'yi forward EPS/EBITDA/FCF ile hesapla, başlığa "(Forward)" ekle.

### Adım 5: 3 Senaryolu Sonuç

Her yöntem için 3 sütun üret:

| Yöntem | Ayı Piyasası | Normal Piyasa | Boğa Piyasası |
|---|---|---|---|
| Net P/E | $X | $Y | $Z |
| ... | ... | ... | ... |

**Ortalama hesabı:** Her senaryoda 9 yöntemin ortalamasını al (CV ≥ %30 ise yöntemleri ayrı not et, ortalama güvenilirliği düşük).

### Adım 6: Final Çıktı Formatı

```markdown
# [TICKER] Adil Değer Raporu (9 Yöntem)

**Tarih:** [date] | **Mevcut Fiyat:** $[price]
**Sektör:** [sector] / [industry]
**Tespit edilen piyasa rejimi:** [BOĞA/NORMAL/AYI]
**Pure Forward modu:** [aktif / pasif]

## 1. Veri Özeti
[Temel metrikler tablosu]

## 2. 9 Yöntem × 3 Senaryo Adil Değer Tablosu
[Detaylı tablo]

## 3. Senaryo Bazlı Eder Değer Aralıkları

### 🐻 Ayı Piyasası Eder: $A.AA – $B.BB
**Açıklama:** Resesyon/risk-off dönemde piyasa bu seviyeyi adil görür.
**Mevcut fiyata göre:** %X pahalı / ucuz

### ⚖️ Normal Piyasa Eder: $C.CC – $D.DD
**Açıklama:** Tarihsel ortalama çarpanlarla. En referans alınması gereken aralık.
**Mevcut fiyata göre:** %Y pahalı / ucuz

### 🐂 Boğa Piyasası Eder: $E.EE – $F.FF
**Açıklama:** Risk-on dönemde momentum primi dahil edildiğinde.
**Mevcut fiyata göre:** %Z pahalı / ucuz

## 4. Karar
[GİR / İZLE / GEÇ + Druckenmiller çarpanı 0.5-2.5x]

## 5. Notlar
[Edge case'ler, model varsayımları, riskler]

**Kaynak:** finzora ai | FMP API | Adil Değer v3.7.2
```

### Adım 7: Log ve Öğrenme Kaydı (ZORUNLU)

Her kullanımda **mutlaka** şu iki dosyayı güncelle:

#### A) `notes/usage_log.csv`
Yeni satır ekle:
```csv
date,ticker,price,bear_low,bear_high,normal_low,normal_high,bull_low,bull_high,decision,sector,market_regime,notes_id
```

#### B) `notes/learnings.md`
Eğer analizi sırasında şunlardan biri yaşandıysa kaydet:
- Sektör medyanları yetersiz kaldı (yöntem CV ≥ %30)
- Pure Forward tetiklendi
- Bir yöntem aşırı sapma verdi (median ± %50 üstü)
- Yeni edge case (negatif NI, asimetrik bilanço, vb.)
- Fiyat geri test (önceden değerlenmiş hisse şimdi ne durumda)

Format:
```markdown
## YYYY-MM-DD - [TICKER]
**Bağlam:** [kısa]
**Gözlem:** [skill nasıl davrandı]
**Düzeltme önerisi:** [skill'e ne eklenmeli]
```

## Kullanım Örneği

Kullanıcı: "AMKR'ı değerle"

1. `python /mnt/skills/user/adil-deger-9-yontem/scripts/adil_deger.py AMKR` çalıştır
2. JSON çıktıyı parse et
3. Format'a göre rapor üret
4. usage_log.csv'ye satır ekle
5. Eğer yeni öğrenme varsa learnings.md'ye not ekle

## Önemli Kurallar (Memory'den)

- Tüm metinler Türkçe (rapor, log, notlar)
- Em dash (—) yok
- Cümleler büyük harfle başlar
- Kaynak: "finzora ai"
- AI kokusu olmayan profesyonel ton
- Türkçe terim öncelik, parantez içinde İngilizce
- Hesaplamada FMP "stable" endpoint kullan
- `changesPercentage` yerine manuel hesapla (memory dersi)
- `epsAvg` (estimatedEpsAvg değil)

## Rejim Tespitinde VIX Kontrolü

VIX `^VIX` sembolü FMP'de **çalışıyor** (memory doğrulaması). VIXY proxy kullanma, contango bozar.

## Sektör Auto-Detection Kuralları

`references/sektor-medyanlari.md`'de detaylı kurallar var. Belirsizse Technology / Generic preset kullan ve learnings.md'ye not düş.

## Skill Geliştirme Döngüsü

Her N kullanımdan sonra (örn. 10):
1. `notes/usage_log.csv`'yi incele
2. Geri test yap: Önceki değerlemeler bugünkü fiyatla nasıl uyumlu?
3. Sektör medyanları güncellenmeli mi?
4. Yeni preset gerekli mi (örn. AI tedarik zinciri için ayrı semicon alt-preset)?
5. SKILL.md'yi ve referansları güncelle, GitHub'a commit et.
