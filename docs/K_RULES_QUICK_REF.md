---
title: K-Rules Hızlı Referans
description: Tüm K-rule'ların (K-04...K-23) kısa açıklaması. Sabah ve seans promptlarında kullanılan tek kaynak.
tags:
  - k-rules
  - trading
  - reference
related:
  - "[[Index]]"
  - "[[TRADING_PLAYBOOK]]"
  - "[[DECISION_FRAMEWORK]]"
  - "[[K_RULES_BACKTEST_DERSLER]]"
  - "[[STOP_MANAGEMENT_V2]]"
---

# K-RULES HIZLI REFERANS — tek kaynak özet

> bu dosya tüm seans ve sabah promptlarında K-kural referansı olarak kullanılır.
> detaylar için → [[TRADING_PLAYBOOK]] ilgili bölüm.
> amaç: prompt'larda K-kural tekrarını önlemek ve tek kaynak tutmak.

---

## 🎯 AKTİF K-KURALLARI — MASTER TABLO (28 Nis 2026)

| Kod | Tetik | Aksiyon | Otomatik mi? | Backtest |
|-----|-------|---------|--------------|----------|
| **K-02** | kriz/şok başlangıcı | momentum sektörlerine 3 iş günü yeni giriş yok | manuel | — |
| **K-04** | SMA50+SMA200 altı | giriş yok (RSI<30 istisnası hariç) | manuel | — |
| **K-05** | swing pozisyonu earnings ≤2 iş günü | TAM çıkış, exception yok | otomatik | ✅ 5g -%5.12, 20g -%8.68 — GÜÇLÜ |
| **K-06** | stop tetiklendi | %100 çık, override YASAK | otomatik | ⚠️ 5g -%1.79, 20g +%5.86 — marjinal |
| **K-06 giriş stop** | ilk giriş | `max(2×ATR(14), %5)` mesafe | otomatik | — |
| **K-07** | chandelier trailing tetik | %100 çık | otomatik | — |
| **K-07 kâr kilidi** | pozisyon kârda | kâr <%7→3×ATR, %7-15→2×ATR, %15+→1.5×ATR | otomatik | — |
| **K-09** | fiyat stop'a <%2 | 4 kontrol (RSI/hacim/SPY+VIX/sektör) | otomatik | ⚠️ 5g +%3.25 (az veri) |
| **K-10** | VIX bandı | min savunmacı + nakit eşiği | otomatik | — |
| **K-11 katman 1** | RSI 70+ VE kâr %15+ | kâr kilidi aktif | otomatik | ✅ 5g +%2.30, 20g -%3.52 — kısmi çıkış doğru |
| **K-11 katman 2** | RSI 80+ veya (75+ + negatif div) | %25-30 kısmi sat | otomatik | ✅ |
| **K-11 katman 3** | 50SMA altı veya chandelier | tam çık | otomatik | ✅ |
| **K-12 Dengeli** | tek hisse >%25 | küçült | otomatik | — |
| **K-12 Agresif** | tek hisse >%20 (max 6 poz, tema 9'da %25) | küçült | otomatik | — |
| **K-12 Temettü** | tek hisse >%15 (max 6 poz) | küçült | otomatik | — |
| **K-12 sektör/tema** | toplam >%40 (tema 9 + RS+%5'te %60) | en zayıfı kes | otomatik | — |
| **K-12 v2** ⭐ | tema güç değişimi 9→6/4/2 | %25/%50/%100 azalt | otomatik | — |
| **K-13 v4.1** | VIX bantları × sektör | 4×2 matrisi (faydalanıcı/duyarlı) | otomatik | — |
| **K-13b** | VIX 28+ duyarlı sektör | ichimoku 4/4 şartı, çeyrek pozisyon | otomatik | — |
| **K-15a** | RSI<35 oversold | 1 gün teyit bekle | manuel | — |
| **K-15b** | momentum + P/E neg/>50 | `k15b_dilution_check.py` zorunlu | otomatik | — |
| **K-15c** ⭐ | tema alımı 15+ gün | kâr +%5+ → %50 çıkış, 20g+ negatif → tam çıkış | otomatik | ✅ Tema 5g +%7.45, 20g -%0.86 |
| **K-16** | portföy earnings 7g öncesi | skor 2-3 → %25, 4-5 → %50 | otomatik | — |
| **K-17** | korelasyon + tema çakışma | 3 soru testi, tema %40 limit | otomatik | — |
| **K-19** | XLP swing girişi | YASAK | otomatik | — |
| **K-20** | sektör RS dead cat bounce | son 3g negatif → bounce yanıltıcı | otomatik | — |
| **K-21** ⭐ | VIX 5g'de %20+ sıçradı | swing girişi YOK (1 gün) | otomatik | ✅ Crisis rally KTOS -%32 ders |
| **K-22** ⭐ | nakit oranı >%10 | portföy tipine göre dağıtım önerisi | otomatik | — |
| **K-24** 🆕 | swing girişi öncesi VCP kalite kontrol | STRONG → tam poz, WEAK → yarım, NONE → geç | otomatik | 13 May 2026 Minervini metodu |
| **K-ZST** ⭐ | swing 10. gün | kâr +%5+ → pik penceresi uyarısı | otomatik | ✅ Tema 10g +%6.39 |
| **K-EVR** | swing aday tarama | beta(1Y)<0.7 elendi | otomatik | — |
| **K-ATR** | giriş stop kurulumu | <2×ATR(14) ise yarım poz veya yasak | otomatik | — |

⭐ = 28 Nisan 2026'da backtest verisinden eklenen yeni kurallar.

**Kaldırılan kurallar:**
- K-01 (7 nisan 2026 — K-05 ile çakışma)
- K-03 (içerik K-13 v4.1'e taşındı)
- K-08 (K-07 chandelier zaten kapsıyor)
- K-14 (11 nisan 2026 — psikoloji testi ile değiştirildi)
- K-18 (11 nisan 2026 — geriye dönük test başarısız, ters çalışıyor)

**SWING SİSTEM REFORMU v2 (28 Nis 2026 — devreye alındı):**

Yeni filtreler (`scripts/swing_entry_engine.py`):
1. **Volume strength**: Bugünkü hacim son 20g ortalamasıyla — rasyo <0.7 ceza
2. **Sector strength**: Sektör ETF vs SPY 10g — underperform <-%2 ceza
3. **Market regime**: SPY 21SMA durumu — risk-off ceza

**Kompozit kalite skoru** (0-100):
- Sinyal türü/sayısı: 40p (tenkan/ichimoku 25, oversold 8)
- Ichimoku konum: 20p (4/4=20)
- Hacim teyidi: 15p
- Sektör gücü: 15p  
- Piyasa rejimi: 10p

Karar:
- **Skor ≥70**: GÜÇLÜ → 2x convicted bet
- **Skor 55-70**: ORTA → 1.5x
- **Skor 40-55**: ZAYIF → 1.0x
- **Skor <40**: GEÇERSİZ → giriş YOK

**Akıllı trailing** (yaş bazlı ATR çarpanı, `agent/swing_manager.py`):
- <5g: 3.0×ATR (whipsaw önle)
- 5-10g: 2.5×ATR (pik penceresi)
- 10-15g: 2.0×ATR (sıkılaşma)
- 15g+: 1.5×ATR (K-15c'ye yakın)
- Break-even floor: kar >%5 → stop maliyetin altına inmez

**Druckenmiller convicted bet** çarpanları:
| Sinyal | Çarpan | Backtest |
|--------|--------|----------|
| tenkan_bounce | 1.5x | +%8.23 (10g) ✅ |
| ichimoku | 1.5x | +%7.90 (10g) ✅ |
| kumo_kirilim | 1.5x | klasik güç |
| consolidation_breakout | 1.2x | — |
| sma50_bounce | 1.0x | — |
| nr7_sikisma | 1.0x | volatilite |
| kijun_bounce_v2 | 1.0x | orta |
| oversold_bounce | 0.5x | -%6.28 (20g) 🔴 |

Multi-sinyal +0.25x bonus (max 2.5x) | 4/4 ichimoku +0.25x bonus

---

## 💪 K-12 v2 DİNAMİK SEKTÖR LİMİTİ (28 Nis 2026 — devreye alındı)

Mevcut K-12 sabit %40 — **çok güçlü temalarda fırsat kaybı**. Druckenmiller felsefesi: "convicted bet, when conviction is high, bet big."

**Dinamik yumuşama (`scripts/k12_dynamic_limits.py`):**

| Tema Skor | RS vs SPY | Sektör Toplam Limit | Tek Pozisyon Limit |
|-----------|-----------|---------------------|--------------------|
| 9-10 | >+%5 | %40 → **%60** | Aggressive %20 → **%25** |
| 8 | >+%2 | %40 → **%50** | Standart |
| 7 | >0 | %40 → **%45** | Standart |
| ≤6 | — | **%40** standart | Standart |

**İptal koşulları (yumuşama uygulanmaz):**
- VIX > 28 → standart %40
- K-23 drawdown ≥ DEFANSIF → standart %40 (yada azalt)
- Tema skoru ardışık 2 hafta düşüyorsa → standart %40

**Otomatik AZALT trigger (tema güç değişimi):**

| Tema skor düşüşü | Aksiyon |
|------------------|---------|
| 9 → 6 (-3) | %25 azalt |
| 9 → 4 (-5) | %50 azalt |
| 9 → 2 (-7) | tam çıkış |

**Convicted bet bonus (`cash_deployment_engine.py`):**
- Tema 9 GUCLU + RS +%5+ → carpan +0.3 (max 2.5x)
- UEC örnek: 1.7x → **2.0x** (uranyum tema 9), pozisyon $77K → $96K

**Test sonuç (28 Nis 2026):**
- AI/Yari-iletken aggressive'de %12.9 / **%60** limit (+%47 alan)
- Uranyum nukleer aggressive'de **0%** / %60 (yeni $173K alabilir)
- Defansif temalar (savunma, sağlık, altın) yumuşama yok — standart %40

Bu reform **AI tema 9 iken aggressive'in %50-60'ı AI/uranyum** olabilir, ama tema 9'dan 6'ya düşerse sistem **otomatik %25 azalt**. Druckenmiller mantığı + risk koruma.

---

## 🩺 TEZ BOZULMA ALARMI (28 Nis 2026 — devreye alındı)

Memory: "tez bozulması olunca pozisyon kapat" — manuel kuraldı, otomatikleşti.

Her pozisyona tez sağlamlık skoru (0-100):

| Sinyal | Etki |
|--------|------|
| Tema skoru ZAYIF (<5) | +30 |
| Tema ORTA (5-6) | +15 |
| Tema güç düşüşü (5+ puan) | +25 |
| Sektör RS underperform (<-5%) | +25 |
| Sektör RS underperform (<-3%) | +20 |
| Fiyat 50SMA altı (>%5) | +20 |
| Fiyat 50SMA altı | +15 |
| VIX > 30 (CRISIS) | +15 |
| VIX > 25 (risk-off) | +10 |
| Earnings MISS son 60g | +20 |
| Earnings BEAT son 60g | -5 |

**Karar matrisi:**
- ≥70: 🔴 **TEZ_TAMAMEN_BOZULDU** → kapat
- 50-69: 🟠 **TEZ_AGIR_HASAR** → %50 azalt
- 30-49: 🟡 **TEZ_HAFIF_HASAR** → izle, sıkı stop
- <30: ✅ **TEZ_SAGLAM** → tut

**Entegrasyon:**
- `agent/risk_engine.build_risk_context` → morning prompt'a "TEZ BOZULMA ALARMI" bloğu (Discovery'den önce)
- `agent/orchestrator.run_morning` sonu → skor ≥50 pozisyonlar **DM uyarı**
- `data/session_state.json:thesis_erosion` her sabah güncel

**İlk üretim sonucu (28 Nis):**
- ABBV skor 75 🔴 → KAPAT (Iran tezi çürüdü, Healthcare RS -%7.3)
- CL skor 70 🔴 → KAPAT (XLP tema 2 ZAYIF)
- MO skor 65 🟠 → %50 AZALT (zaten K-05 earnings öncesi çıkış)
- NEM skor 50 🟠 → %50 AZALT (altın tema 1)

---



Mevcut k_engine kural-tabanlı, **bağlamı görmez**. Çelişkili durumlarda LLM'e sorar.

**3 katmanlı sistem (`agent/exit_judgement.py`):**

1. **KURAL** — `k_engine.run_exit_checks()` — hızlı, deterministik
2. **CONTEXT** — pozisyon için zengin bağlam:
   - Tema gücü (`theme_scores.json`)
   - Sektör RS vs SPY
   - Earnings 14g içinde mi?
   - K-23 drawdown durumu
   - Pozisyon yaşı + kar/zarar
3. **CONFLICT DETECTOR** — kural ↔ context çelişiyor mu?
4. **LLM JUDGEMENT** — sadece çelişki varsa Anthropic API çağrısı

**Çelişki senaryoları:**
- K-09/K-11 EXIT/PARTIAL ama **tema GUCLU + earnings yok** → LLM sor
- K-ZST WARN ama tema 8+ + sektor outperform + kar artıyor → LLM sor
- K-15c PARTIAL ama momentum güçlü → LLM sor
- HOLD ama drawdown HEDGE+ → LLM sor (ters çelişki)

**LLM cevap formatı:**
```
ACTION: HOLD / EXIT_NOW / PARTIAL_25 / PARTIAL_50 / TIGHTEN
CONFIDENCE: yuksek / orta / dusuk
REASONING: 3-5 cümle gerekçe (KESİN/MUHTEMEL/SPEKÜLATİF)
RISK: bear case
```

**K-06 stop kesin tetikse LLM'e gitmiyoruz** — direkt EXIT (maliyet kontrolü).

**Log:** her judgement `logs/exit_judgement.jsonl`'a kaydedilir, post-mortem analiz için `python scripts/judgement_review.py`.

**Beklenen etki:** Kural sistemi tek başına yanlış zamanlama yapan durumları (örn MU tema 9 GUCLU iken erken kar al) LLM'in reasoning'i ile düzeltir.

---

## ⚠️ RAPOR YAZARKEN KIRMIZI ÇİZGİLER (26 nisan 2026 post-mortem)

> bu bölüm haftalık/günlük rapor yazan AI için zorunlu okuma.
> her madde geçmişte gerçekleşmiş hataya dayanır.

### 1. K-05 ile K-16'yı karıştırma

| Pozisyon türü | Earnings yaklaşınca hangi kural? |
|--------------|----------------------------------|
| **Swing trade** | **K-05** — 2+ iş günü önce TAM çıkış, exception yok |
| **Portföy pozisyonu** | **K-16** — 7 gün önce skor hesapla, skora göre %0/%25/%50 |

**K-05'i portföy pozisyonuna ASLA uygulama.**  
**K-16'yı swing pozisyonuna ASLA uygulama.**  
K-05 "%30 azalt" demez — FULL EXIT demektir.

### 2. stop_loss ile hedef_fiyat'ı karıştırma

JSON'daki alan isimleri:

```
"stop_loss":    ← her zaman güncel fiyatın ALTINDA olmalı
"hedef_fiyat":  ← her zaman güncel fiyatın ÜSTÜNDE olmalı (long pozisyon)
```

"MU stop $470 → $478" gibi bir ifade yazacaksan önce JSON'u oku:
- `stop_loss` = mevcut stop
- `hedef_fiyat` = hedef — stop ile aynı değil!

**Rapora yazmadan önce:** `stop < güncel_fiyat < hedef` kontrolünü her pozisyon için yap.

### 3. K-11 atlama

Kazanç ≥%15 olan her pozisyon için:
1. RSI(14) canlı çek
2. RSI ≥ 70 → Tier1 tetiklendi → **aksiyon listesine ekle**
3. RSI ≥ 80 → Tier2 tetiklendi → daha agresif

"Hedef aşıldı" notu yazmak yetmez — **aksiyon listesine eklemek zorunlu.**

### 4. Makro verileri hallüsine yapma

**Yasak:** İşsizlik oranını, CPI rakamını, NFP tahminini hafızadan yazmak.

**Zorunlu:** Rapordan önce `scripts/weekly_pre_check.py` çalıştır.  
Çıktıdaki `macro` bölümünü oku, oradan yaz.

Makro takvim kuralları (değişmez):
- **NFP:** O ayın **ilk Cuması** (Mayıs 2026 = 1 Mayıs)
- **CPI:** Ayın **~10-15'i** arası (BLS takvimi — hallüsine yapma)
- **PCE:** Ayın **son iş günü** civarı (~30-31)

### 5. Haftalık rapor yazma sırası (zorunlu)

```
1. scripts/weekly_pre_check.py çalıştır
2. data/weekly_pre_check.json dosyasını oku
3. Sadece o dosyadaki sayıları rapora yaz
4. Hallüsine rakam = sıfır tolerans
```

---

## kaldırılanlar
- **K-01**: kaldırıldı (7 nisan 2026) — K-05 ile çakışma
- **K-03**: kaldırıldı — içerik K-13 v4.1'e taşındı
- **K-08**: kaldırıldı — K-07 chandelier zaten kapsıyor
- **K-14**: kaldırıldı (11 nisan 2026) — psikoloji testi ile değiştirildi. Her giriş öncesi: "Bu girişi yarın tekrar inceleseydim, tüm kuralları tam uyguladım mı?" Drawdown geçmişi `data/swing/status.json`'da kayıtlı.
- **K-18**: kaldırıldı (11 nisan 2026) — geriye dönük test sonucu: $5M+ insider satışı sonrası hisseler ortalama +2.1% kazandı, kazanma oranı %60. Kural ters çalışıyor. İnsiderlar çoğunlukla rutin sebeplerle satar (10b5-1 planı, vergi, çeşitlendirme) ve piyasa bunu fiyatlıyor. `scripts/k18_insider_check.py` devre dışı bırakıldı.

---

## aktif kurallar (18 kural)

### giriş filtreleri

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-02** | kriz/şok başlangıcı | momentum sektörlerine 3 iş günü yeni giriş yok |
| **K-04** | SMA50+SMA200 altı | giriş yok (RSI<30 istisnası hariç), SMA50+SMA200 altı + insider yoğun → mutlak yasak |
| **K-05** | swing pozisyonu için earnings ≤2 iş günü | tam çıkış, exception yok, binary risk alma |
| **K-13** v4.1 | VIX bantları × sektör kategorisi | 4 bant × 2 kategori matrisi (faydalanıcı/duyarlı) — altta tam tablo |
| **K-13b** | VIX 28+ duyarlı sektör | ichimoku 4/4 şartıyla çeyrek pozisyon istisnası, stop chandelier 3×ATR (%5 taban yok — VIX yüksek olduğu için geniş stop gerekli) |
| **K-15a** | RSI<35 oversold | 1 gün teyit bekle (mevcut pozisyon için değil, sadece yeni giriş) |
| **K-15b** | momentum hisse (3ay >%30 + P/E neg/>50) | `scripts/k15b_dilution_check.py SYMBOL` zorunlu |
| **K-17** | korelasyon + tema çakışması | `scripts/k17_correlation_check.py SYMBOL` — 3 soru testi, tema %40 limit |
| **K-19** | XLP swing girişi | yasak — düşük volatilite (std 3.6% vs momentum 6.3%) swing hedef fiyatına ulaşmayı engeller; sadece portföy pozisyonu olarak alınabilir |
| **K-20** | sektör RS dead cat bounce | `scripts/k20_rs_filter.py` — son 3g RS negatif + bounce yanıltıcı |
| **K-ZST** | swing pozisyon 10. gün | RSI yönü + hacim + RS → 2/3 negatifse çık (bekleme yok) |
| **K-EVR** | swing aday tarama | beta(1Y) < 0.7 olan hisseyi evrenden ele; swing %10 hedefe ulaşamaz |
| **K-ATR** | giriş stop kurulumu | stop mesafesi < 2×ATR(14) ise pozisyon yarıya indir veya girme |

### çıkış disiplini

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-06** | stop tetiklendi | %100 çık, override YASAK, duygusal karar yok, K-09 ile sıralı |
| **K-06 giriş stop** | ilk giriş | `max(2×ATR(14), %5)` — sabit %5 tek başına yetersiz, K-13b modunda chandelier 3×ATR (sabit %5 taban yok) |
| **K-07** | chandelier trailing tetiklendi | %100 çık, sadece yukarı çekilir — matematik tek yön |
| **K-07 kâr kilidi** | pozisyon kârda | kâr <%7 → 3×ATR / %7-15 → 2×ATR / %15+ → 1.5×ATR |
| **K-09** | fiyat stop'a <%2 | `scripts/k09_proximity_check.py` — 4 kontrol (RSI/hacim/SPY+VIX/sektör) → 3+ negatif=EXIT_NOW, 2=WAIT, 0-1=TUT |

### portföy yönetimi

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-10** | VIX bandına göre | min savunmacı + nakit eşiği (statik alt sınır), K-13 paralel çalışır |
| **K-11 katman 1** | RSI 70+ VE kâr %15+ | kâr kilidi aktif: max(2×ATR, 20SMA altı) — K-07'ye göre öncelikli (sıkı 20SMA) |
| **K-11 katman 2** | RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) | %25-30 kısmi sat |
| **K-11 katman 3** | 50SMA altı kapanış VEYA chandelier trailing | tam çık |
| **K-12 Dengeli** | tek hisse > %25 | küçült |
| **K-12 Agresif** | tek hisse > %20 (max 6 poz) | küçült |
| **K-12 Temettü** | tek hisse > %15 (max 6 poz) | küçült |
| **K-12 sektör/tema** | toplam $600K bazlı > %40 | en zayıfı kes |
| **K-16** | portföy pozisyonu earnings 7g öncesi | `scripts/k16_sell_the_news_score.py` — skor 2-3 → %25, skor 4-5 → %50 |

---

## K-13 v4.1 sektör bazlı VIX matrisi

### sektör kategorileri (aktif kriz: jeopolitik/savaş — iran)

**faydalanıcı sektörler** (VIX'e karşı dayanıklı):
- enerji: XOM, CVX, COP, OXY, EOG, SLB
- savunma: LMT, RTX, GD, NOC, LHX, KTOS, RKLB
- altın/gümüş: GLD, SLV, NEM, GOLD, RGLD, AEM
- defansif REIT: O, WELL, VICI
- tütün/staples: MO, PM, PG, KO, PEP, CL (K-19 nedeniyle sadece portföy)

**duyarlı sektörler** (VIX'e karşı zayıf):
- tech momentum: NVDA, AMD, MRVL, AVGO, CRDO
- consumer discretionary: AMZN, TSLA, NKE, HD, LOW
- küçük/orta cap growth: IWM, MDY
- high-beta: biotech, fintech, clean energy

### VIX bant × sektör matrisi

| VIX bandı | faydalanıcı | duyarlı |
|---|---|---|
| **<22** | tam pozisyon | tam pozisyon |
| **22-28** | tam pozisyon | yarım pozisyon |
| **28-35** | yarım pozisyon | giriş yok (K-13b istisna: ichimoku 4/4 → çeyrek) |
| **35+** | çeyrek pozisyon | giriş yok |

### kriz tipi değişirse
kriz tipi değiştiğinde (pandemi/finansal/ticaret/enflasyon) faydalanıcı ve duyarlı listeleri güncellenir. `docs/TRADING_PLAYBOOK.md` K-13 bölümünde geçiş protokolü var.

---

## otomatik script'ler (K-rule)

| script | ne yapar | ne zaman çalıştır |
|---|---|---|
| `scripts/k09_proximity_check.py SYMBOL` | stop yakınlık 4 kontrol | fiyat stop'a <%2 kala |
| `scripts/k15b_dilution_check.py SYMBOL` | momentum hisse dilüsyon skoru | yeni momentum giriş öncesi |
| `scripts/k16_sell_the_news_score.py SYMBOL` | earnings 7g öncesi skor | portföy pozisyonu earnings öncesi |
| `scripts/k17_correlation_check.py SYMBOL` | sektör + tema çakışması | her yeni giriş öncesi |
| `scripts/k19_xlp_filter.py SCAN_FILE` | XLP swing elemesi | swing tarama çıktısı üzerinde |
| `scripts/k20_rs_filter.py SCAN_FILE` | dead cat bounce elemesi | swing tarama çıktısı üzerinde |

not: script'ler `_QUIET_MODE=True` varsayılanı ile çalışır. info severity telegram'a gitmez, warning/critical kritik gider. `send_k_alert(force=True)` override eder.

---


---

## K-ZST 10. gün momentum protokolü

10. günde 3 kontrol yap, 2/3 negatifse çık:

| kontrol | negatif sinyal |
|---|---|
| RSI yönü | 10. gün RSI < giriş günü RSI |
| Hacim trendi | son 3g ort. hacim < ilk 3g ort. hacim |
| Relative Strength | hisse son 5g SPY'dan zayıf (RS negatif) |

→ 2/3 negatif = **ÇIK** | 1/3 negatif = izle | 0/3 = tut

**Kanıt:** GOOGL(23g→+7.8%), XOM(15g→+5.5%), LMT(18g→+1.4%), GE(13g→+1.7%) — 4 trade'de erken çıkış optimal olurdu.

## K-EVR swing evreni beta filtresi

Beta(1Y) < 0.7 olan hisseler swing evrenine giremez.

**Evrenden çıkarılanlar (örnekler):**
- Telekom: VZ, T, TMUS
- Kamu hizmetleri: DUK, NEE, SO, EXC
- Defensif sağlık: DVA, HUM, UHS
- Büyük defensif perakende: WMT, TGT, COST
- Defensif REIT (swing): AMT, O, VICI

Bu hisseler dengeli/temettü portföyüne gönderilir.

**Kanıt:** WMT(-3.5%), T(-5.5%), DUK(+1.5%), DVA(+1.1%) — 4 trade, ortalama puan 2.25/10.

## K-ATR giriş stop mesafesi zorunlu kontrolü

```
stop_mesafe  = giris_fiyati − stop_fiyati
min_mesafe   = 2 × ATR(14)

eğer stop_mesafe < min_mesafe:
    → pozisyonu yarıya indir
    → veya girme
```

**Kanıt:** AMT(-3.4%, %1.7 mesafe), ZS(+2.5%, dar trailing), NEM(+2.1%, ATR önerisi) — 3 trade.

## kural hiyerarşisi (çakışma durumunda)

1. **K-06 stop tetiği** → her şeyin üstünde, override yasak
2. **K-07 kâr kilidi** > K-11 katman 2 (kazançlı pozisyonda K-11 sıkı, kazançsız K-07 gevşek)
3. **K-13 v4.1** > K-02 (kriz şok kuralı artık K-13 v4.1 matrisinde)
5. **K-10 portföy seviyesi alt sınır** paralel çalışır, K-13 sektör seçer
6. **K-17 tema** > K-12 sektör (anlatı tema daha dar tanım)

---

> son güncelleme: 12 nisan 2026 | finzora ai | K-14 kaldırıldı (psikoloji testi); K-18 kaldırıldı (backtest); K-ZST/K-EVR/K-ATR eklendi (3+ trade kanıtı)

---

## YENİ DÖKÜMANLAR (11 Nisan 2026)

| Döküman | İçerik |
|---------|--------|
| `docs/THEMATIC_SYSTEM.md` | Tema bazlı portföy rotasyonu, TEMA_PUANI sistemi, 7 ana tema |
| `docs/SECTOR_AGENTS.md` | Araştırma ajanları, supply chain haritası, conviction scorer |
| `docs/STOP_MANAGEMENT_V2.md` | Stepped ATR trailing, VIX bazlı çarpan, confluence stop |
| `docs/DECISION_ARCHITECTURE_V2.md` | 3 katmanlı karar sistemi, rejim adaptasyonu, bias korumaları |

## HEDEFLER (11 Nisan 2026 itibaren)

| Portföy | Sermaye | Max Poz | Hedef |
|---------|---------|---------|-------|
| Dengeli | 00K | **6** | **%50+/yıl** |
| Agresif | 00K | **6** | **%80+/yıl** |
| Temettü | 00K | **6** | **%25+/yıl + temettü** |
| Swing | Ayrı | 5 | Aylık pozitif beklenti |

## FMP API LİMİTİ DÜZELTMESİ

~~Günlük 2,500 call~~ **YANLIŞ** — Gerçek limit: **Dakikada 2,500 call, günlük limitsiz.**
Bu kritik bir düzeltmedir — API kullanımını gereksiz kısıtlamak zorunda değiliz.

> değişiklik gerektiren güncellemeler doğrudan `docs/TRADING_PLAYBOOK.md`'de yapılır, bu dosya senkron tutulur.

---

## 📊 K-kural performans analizi (11 nisan 2026)

**22 trade üzerinde otomatik analiz — `scripts/k_rule_performance.py`**

### kural uyumunun sayısal etkisi

| metrik | kural ihlali olan (8 trade) | kural uyumlu (14 trade) |
|---|---|---|
| ortalama PnL | -1.1% | +1.0% |
| win rate | %50 | %64 |
| **avantaj** | — | **+2.1% PnL farkı** |

### en sık ihlal edilen kurallar

| kural | ihlal sayısı | ana hata |
|---|---|---|
| K-zaman (15 gün) | 6 trade | GOOGL(23g), T(22g), DVA(27g), DUK(28g) |
| K-evren (swing evreni) | 7 trade | VZ, WMT, AMT, T, DUK, DVA — düşük beta |
| K-13 (VIX matrisi) | 1 trade | AROC — VIX>27'de duyarlı sektör girişi |
| K-stop (ATR mesafesi) | 1 trade | AMT — %1.7 mesafe, ATR kullanılmamış |

### onaylı sistem değişiklikleri

> aşağıdakiler veri destekli — tek kaynak bu bölüm.

**SWING EVRENİ'NDEN ÇIKARILAN:** VZ, T, TMUS, DUK, NEE, SO, DVA, WMT, TGT, COST, AMT  
(düşük beta, swing %10 hedefe ulaşamaz, temettü/değer portföyüne gönder)

**K-06 GİRİŞ STOP güçlendirildi:** min. stop mesafesi = `max(2×ATR(14), %5)` — %1.7 gibi dar mesafelerde pozisyon yarıya indir veya girme.

**K-21 KRİZ RALLİSİ YASAĞI** (28 Nis 2026 backtest dersi — devreye alındı):
- Tetik: Son 5 işgününde VIX %20'den fazla sıçradıysa
- Etki: O gün swing girişi YOK
- T+1: Sadece RSI<35 + ichimoku 3/4 ile devam
- Kanıt: 2 Mart 2026 Iran krizi günü açılan HAL/KTOS/CEG, 20 gün sonra ortalama -%4.87. KTOS tek başına -%32.3.
- Uygulama: `scripts/swing_entry_engine.py:_detect_crisis_rally()`

**K-15c TEMA 15G ZORUNLU ÇIKIŞ** (28 Nis 2026 backtest dersi — devreye alındı):
- Tetik: Tema-bazlı alım pozisyonu (giriş_nedeni'nde "tema" veya "taram") 15+ gün tutuldu ve kâr +%5+
- Etki: %50 kısmi çıkış (kâr realize)
- 20+ gün ve negatif kâr ise: %100 tam çıkış
- Kanıt: 8 tema alımda 5g +%7.45, 10g +%6.39, **20g -%0.86** — 15. günden sonra getiri negatife dönüyor
- Uygulama: `agent/orchestrator.py:_check_portfolio_exits()` — her FAZ'da tetiklenir

**K-22 NAKİT KULLANIM** (28 Nis 2026 — devreye alındı):
- Tetik: Portföy nakit oranı %10'u aşıyorsa
- Hedef: Nakit %5'e indirilmeli
- AGGRESSIVE: Önce swing sinyalleri (backtest +%8 olanlar), sonra tema, VIX>22 ise inverse ETF
- BALANCED: Önce tema, VIX>22 ise defansif rotasyon, VIX<22 + tema yok ise SPY/QQQ
- DIVIDEND: Önce tema, slot dolu ise en iyi pozisyonu büyüt (HEDGE YASAK)
- Filtre: Bekleyen ÇIKIŞ kararları olan semboller exclude
- Uygulama: `scripts/cash_deployment_engine.py` — her morning session_state'e yazılır

### zeynel onayı bekleyen kural adayları

| kod | açıklama | kanıt |
|---|---|---|
| **K-ZST** | 10. günde momentum kontrol protokolü | 4 trade (GOOGL, XOM, LMT, GE) |
| **K-EVR** | Beta>0.7 swing evren zorunlu filtresi | 4 trade (WMT, T, DUK, DVA) |
| **K-ATR** | Giriş stop mesafesi ≥ 2×ATR(14) zorunlu | 3 trade (ZS, AMT, NEM) |
| **K-KRZ** | Kriz gün-1 giriş yasağı (1 gün cooling) | 1 trade (RTX, LMT, HAL genel) |
| **K-JEO** | Jeopolitik trade'de çıkış tetikleyicisi zorunlu | 1 trade (HAL) |

**K-24 VCP SETUP KALİTE FİLTRESİ** (13 May 2026 — prototip, backtest bekliyor):
- Tetik: Swing girişi öncesi (Ichimoku 4/4 + K-19/K-20 geçen aday için zorunlu son filtre)
- Yöntem: Mark Minervini Volatility Contraction Pattern — algoritmik tespit
- Algoritma: Son 120 günde zigzag pivot (%3+ swing) → ardışık daralan kontraksyon zinciri → her birinde hacim azalması → pivot yakınlığı → SMA50>SMA200 trend filtresi
- Skor (0-100): zincir uzunluğu (30p) + daralma sırası (25p) + hacim kuruması (20p) + pivot yakınlığı (15p) + trend (10p)
- Karar:
  - **STRONG** (≥70): Tam pozisyon ($8-10K)
  - **WEAK** (40-69): Yarım pozisyon ($5K) veya izleme
  - **NONE** (<40): Giriş YOK
- Setup-bozuldu güvenliği: Pivot'tan %5+ aşağıdaki hisse STRONG verilemez (max WEAK), %10+ aşağıda max NONE
- Uygulama: `agent/vcp_detector.py:detect_vcp(symbol)` — FMP historical-price-eod/full
- Kanıt: backtest bekliyor — son 6 ay swing trade'lerinde VCP ✅ olanların ortalama getiri farkı ölçülecek

**K-24 örnek tarama** (13 May 2026 watchlist üzerinde test):
- CAT: WEAK 68 (pivot $931, -2.06% uzak, 2 ardışık daralan) → izlemede tut
- LMT: WEAK 75 (VCP zinciri güçlü ama pivot -18% bozuk) → setup geçti, geçmiş fırsat
- MRK: WEAK 75 (VCP güçlü ama pivot -9% bozuk) → setup geçti
- NVDA, AAPL, WDC, KLAC, AMAT, MU, PLTR: VCP zinciri yok veya pivot bozuk
- STRONG çıkan yok — Minervini doktrini: STRONG VCP nadir, bu beklenen sonuç
> `scripts/k_rule_performance.py --all` → tam rapor + backtest sonuçları güncelleme
