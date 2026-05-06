---
name: adil-deger-9-yontem
description: ABD hisse senetleri için kapsamlı adil değer hesaplaması. DUAL-MODE sistem - hızlı büyüyen şirketler için GROWTH modu (sadece büyüme yöntemleri), olgun şirketler için BLENDED modu (ağırlıklı Traditional + Forward + Growth). 13 yöntem, 3 piyasa rejimi (Ayı/Normal/Boğa). PEG, EV/Forward Revenue/EBITDA, Rule of 40, Reverse DCF dahil. AI mega-cap özel preset, otomatik karar matrisi, analist konsensüs entegrasyonu. Tetikleyiciler "X hissesini değerle", "adil değer hesapla", "X için fair value", "X kaç eder", "9 yöntem değerleme". Finzora AI Adil Değer v3.7.2 metodolojisi. Her kullanımda notes klasörü güncellenir.
---

# Adil Değer 9 Yöntem (Finzora AI v3.7.2) - v4.0

## Versiyon Geçmişi

**v4.0 (6 Mayıs 2026)** — Quality/Moat Premium
- ROE ve Net Margin sektör hedeflerine göre kalite primi (1.0-1.50x)
- Sadece çarpan bazlı yöntemlere uygulanır (P/E, EV/X, P/FCF)
- Kalite şirketleri (KO, JNJ, V, MA gibi) için doğru değerleme
- KO testinde başarılı: analist hedefiyle %0.2 fark

**v3.0 (6 Mayıs 2026)** — DUAL-MODE büyüyen vs olgun ayrımı
- 🚀 GROWTH modu: hızlı büyüyen şirketlerde Traditional kullanılmaz
- ⚖️ BLENDED modu: olgun şirketlerde ağırlıklı (Traditional %50-80 + Forward+Growth)
- 5 kriterli otomatik mod tespiti
- Yeni yöntemler: PEG, EV/FWD Revenue, EV/FWD EBITDA, Rule of 40, Reverse DCF

**v2.0 (6 Mayıs 2026)** — Bug fix + iyileştirmeler
- k_e %15 cap, ROE<k_e RIM fallback, CV uyarı, Forward outlier, AI mega-cap, Analist konsensüs

**v1.0 (6 Mayıs 2026)** — İlk sürüm 9 yöntem

## Premium Sistemi (3 Katmanlı)

### 1. Piyasa Rejimi Çarpanı (her yöntemde)
- Ayı: -%25-35
- Normal: %0
- Boğa: +%20-30

### 2. AI Mega-Cap Premium (sadece boğada, semi/tech için)
- Tetikleme: market cap > $300B + 1y +%100+
- Boğa multiplier: 1.40-1.55x
- Bazis: Momentum + sektör

### 3. Quality/Moat Premium (her senaryoda, fundamental)
- Tetikleme: ROE > sektör hedef VEYA Net Margin > sektör hedef
- Multiplier: 1.0-1.50x
- Bazis: Geometrik ortalama (ROE ratio × Margin ratio) ^ 0.5
- Hangi yöntemlere: P/E, Forward P/E, EV/EBIT, EV/EBITDA, EV/Revenue, P/FCF, EV/FWD Rev/EBITDA
- Hangilerine değil: Justified P-B (zaten ROE), Graham, DCF, PEG, Rule of 40 (çift sayım önleme)

## Amaç

Hisse senetleri için 13'e kadar yöntemle adil değer hesaplar, 3 piyasa rejiminde ayrı eder değer üretir, mod bazlı farklı değerleme felsefesi uygular.

## Tetikleme

- "X hissesini değerle"
- "X için adil değer hesapla"
- "X kaç eder"
- "X fair value"

## Kullanım

```bash
python /mnt/skills/user/adil-deger-9-yontem/scripts/adil_deger.py TICKER
python /mnt/skills/user/adil-deger-9-yontem/scripts/adil_deger.py TICKER --json
```

## DUAL-MODE Sistemi (v3 Yeni)

### 🚀 GROWTH MODU
**Tetikleme: ≥3/5 kriter sağlanırsa**
1. Forward growth ratio (EPS_FWD_2Y / EPS_TTM) > 2.0
2. Revenue 3y CAGR > %20
3. Sektör Growth-friendly (semicon_design, tech_software, healthcare_biotech, communication)
4. AI mega-cap aktif
5. 1y fiyat performansı > %50

**Yöntemler (sadece bunlar hesaba katılır):**
- Forward P/E
- DCF (10 yıl + Terminal)
- PEG Ratio
- EV/Forward Revenue
- EV/Forward EBITDA
- Rule of 40 (yazılım/AI uygunluğu)

**Reverse DCF:** Mevcut fiyatın implied büyüme oranını gösterir, hesaba katılmaz.

**Traditional yöntemler (Net P/E, EV/EBIT vs) sadece "Margin of Safety Zemini" olarak gösterilir, ana karar bu yöntemlerden çıkmaz.**

### ⚖️ BLENDED MODU
**Tetikleme: GROWTH kriterlerinin <3'ü sağlanırsa**

**Ağırlıklandırma (forward growth ratio bazlı):**

| Forward Growth | Traditional | Forward+Growth |
|---|---|---|
| > 1.5x | %50 | %50 |
| 1.2-1.5x | %65 | %35 |
| < 1.2x | %80 | %20 |

**Yöntemler (tüm 13'ü hesaba katılır, ağırlıklandırılır):**
- 7 Traditional (TTM bazlı)
- 2 Forward (Forward P/E + DCF)
- 4 Growth (PEG, EV/FWD x2, Rule of 40)

## 13 Yöntem Listesi

### Traditional (TTM Bazlı, 7 Yöntem)
1. Net P/E
2. EV/EBIT
3. EV/EBITDA
4. EV/Revenue
5. P/FCF (4 yıl normalize)
6. Justified P-B (Gordon veya RIM fallback)
7. Graham Number

### Forward (Beklenti Bazlı, 2 Yöntem)
8. Forward P/E (2 yıl ileri EPS)
9. DCF (10 yıl + Terminal)

### Growth (Yeni v3, 4 Yöntem)
10. PEG Ratio (PEG target × growth)
11. EV/Forward Revenue
12. EV/Forward EBITDA
13. Rule of 40 (revenue growth + FCF margin)

### Bonus
- Reverse DCF (implied growth rate, hesaba katılmaz)

## Piyasa Rejimleri

| Rejim | Tespit | Çarpan Düzeltme |
|---|---|---|
| Ayı | VIX > 28 veya SPY < 200SMA -%5 | -%25-35 |
| Normal | VIX 15-22, baseline | %0 |
| Boğa | VIX < 16, SPY > 200SMA +%5 | +%20-30 |

AI Mega-Cap istisnası: Boğa multiplier 1.40-1.55x (semi/tech, $300B+, 1y +%100+)

## CV Uyarı Seviyeleri

| CV | Renk | Anlam |
|---|---|---|
| < %20 | 🟢 | Yöntemler hizalı, güvenilir |
| %20-35 | 🟡 | Normal dağılım |
| %35-50 | 🟠 | Tutarsızlık var |
| ≥ %50 | 🔴 | KRİTİK: Model güvenilir değil |

## Otomatik Karar Matrisi

| Mevcut Fiyat | Öneri |
|---|---|
| ≤ Ayı medyan | 🟢 GÜÇLÜ AL |
| ≤ Normal medyan | 🟢 AL |
| ≤ Normal P75 | 🟡 İZLE / KÜÇÜK POZİSYON |
| ≤ Boğa medyan | 🟡 İZLE |
| ≤ Boğa P75 | 🟠 PAHALI / İZLE |
| ≤ Boğa P75 × 1.20 | 🟠 ÇOK PAHALI |
| > Boğa P75 × 1.20 | 🔴 GEÇ / KAÇIN |

## Veri Kaynakları (FMP Stable API)

- `/profile`, `/quote`, `/income-statement` (annual + quarterly)
- `/cash-flow-statement`, `/balance-sheet-statement`
- `/analyst-estimates` (Forward EPS, Revenue, EBITDA)
- `/price-target-consensus` (Analist hedef fiyat)
- `^VIX`, SPY (Piyasa rejimi)

## Doğrulanmış Test Vakaları

| Ticker | Mod | Quality Premium | Boğa Medyan | Mevcut | Karar | Analist | Doğruluk |
|---|---|---|---|---|---|---|---|
| AMD | 🚀 GROWTH (4/5) | 1.0x | $382 | $413 | PAHALI/İZLE | $401 | ✅ |
| AMKR | ⚖️ BLENDED %65/%35 | 1.0x | $48 | $77 | GEÇ | $66 | ✅ |
| KO | ⚖️ BLENDED %80/%20 | ⭐ 1.40x | $69 | $78 | PAHALI/İZLE | $85 | ✅ (v4'te düzeltildi) |

## Bilinen Limitasyon (v4'e)

**KO testinde keşfedildi:** Sektör lideri/kalite şirketleri (KO, PEP, MCD, JNJ, V, MA, gibi) tarihsel olarak medyan çarpanlarının üstünde işlem görür. Skill bunu yakalayamıyor.

**v4 çözüm önerisi:** ROE ve Net Margin bazlı "Quality Premium" multiplier ekle.

## Önemli Kurallar (Memory'den)

- Tüm metinler Türkçe (rapor, log, notlar)
- Em dash yok, cümleler büyük harfle başlar
- Kaynak: "finzora ai"
- FMP "stable" endpoint, `epsAvg` kullan
- `^VIX` çalışıyor (VIXY proxy kullanma)
