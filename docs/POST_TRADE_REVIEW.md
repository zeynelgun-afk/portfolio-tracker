---
title: Post-Trade Review
description: Trade kapanış sonrası analiz akışı. trade_feedback otomatik ders çıkarır.
tags:
  - trading
  - lessons
  - review
related:
  - "[[Index]]"
  - "[[K_RULES_BACKTEST_DERSLER]]"
  - "[[EPISODIC_MEMORY]]"
  - "[[SELF_IMPROVEMENT_SYSTEM]]"
---

# POST-TRADE REVIEW ÇERÇEVESİ — v1.0

> **son güncelleme**: 6 nisan 2026
> **amaç**: her kapanan trade'den maksimum öğrenme çıkarmak, sistem seviyesinde iyileştirme sağlamak
> **kullanım**: kapanış raporunda (BÖLÜM 5), closed.json kaydında, haftalık raporda

---

## 1. PROCESS vs OUTCOME AYRIMI

### temel prensip

kârlı trade ≠ iyi trade. zararlı trade ≠ kötü trade.

```
                    İYİ SÜREÇ           KÖTÜ SÜREÇ
                  ┌─────────────────┬─────────────────┐
   KÂRLI SONUÇ    │  ✅ İDEAL       │  ⚠️ ŞANS        │
                  │  tekrarla       │  tekrarlama!     │
                  │  sistem çalışıyor│  kural ihlali   │
                  ├─────────────────┼─────────────────┤
   ZARARLI SONUÇ  │  📊 NORMAL      │  ❌ HATA         │
                  │  kabul et       │  ders çıkar      │
                  │  stop çalıştı   │  playbook'a ekle │
                  └─────────────────┴─────────────────┘
```

### süreç skoru nasıl verilir (1-5):

```
5 = MÜKEMMEL SÜREÇ
    - tüm giriş kriterleri sağlanmış (GO/NO-GO 10/10)
    - kırmızı takım testi yapılmış
    - pozisyon boyutu kurallara uygun
    - stop/hedef önceden tanımlı ve uyulmuş
    - çıkış mekanik (stop veya hedef) veya gerekçeli

4 = İYİ SÜREÇ
    - giriş kriterleri büyük ölçüde sağlanmış (8-9/10)
    - stop/hedef tanımlı, uyulmuş
    - küçük sapma var ama kontrollü (örn: tam yerine yarım pozisyon)

3 = ORTALAMA SÜREÇ
    - giriş gerekçesi var ama checklist tam uygulanmamış
    - stop tanımlı ama çıkış biraz geç veya erken
    - duygusal etki belirgin değil ama sezgisel karar var

2 = ZAYIF SÜREÇ
    - giriş impulsif veya FOMO bazlı
    - stop override edilmiş (K-06 ihlali)
    - plan dışı pozisyon, yetersiz analiz
    - korelasyon kontrolü yapılmamış

1 = KÖTÜ SÜREÇ
    - tamamen duygusal karar (panik satış, FOMO alış)
    - stop yok veya sürekli aşağı çekilmiş
    - kural ihlali açık ve kasıtlı
    - pozisyon boyutu aşırı
```

---

## 2. YAPILANDIRILMIŞ POST-TRADE REVIEW

her kapanan trade için (swing + portföy) aşağıdaki format uygulanır.

### closed.json zorunlu alanlar (mevcut + YENİ):

```json
{
  "id": "SWG-XXX",
  "sembol": "XXXX",
  "giris_tarihi": "2026-XX-XX",
  "giris_fiyati": 0.00,
  "cikis_tarihi": "2026-XX-XX",
  "cikis_fiyati": 0.00,
  "adet": 0,
  "kar_zarar": 0.00,
  "kar_zarar_yuzde": 0.00,
  "tutulan_gun": 0,
  "cikis_nedeni": "stop-loss / hedef / tez bozulması / süre",
  "sonuc": "kazanc / kayip",
  "tarama_yontemi": "ichimoku_kirilan / kijun_bounce / momentum / earnings",

  "// --- YENİ ALANLAR ---": "",
  "process_score": 0,
  "process_notu": "kısa açıklama — süreç neden bu skoru aldı",
  "root_cause": "hazırlık / uygulama / boyutlandırma / duygusal / harici",
  "corrective_action": "bir sonraki döngüde test edilecek somut davranış",
  "bias_detected": "yok / anchoring / disposition / FOMO / overconfidence / sunk_cost",

  "lessons": "serbest metin — bu trade'den ne öğrendim"
}
```

### root_cause kategorileri:

```
HAZIRLIK
  giriş analizi yetersizdi, sinyal yanlış yorumlandı, earnings kontrolü atlandı,
  insider check yapılmadı, sektör RS kontrol edilmedi

UYGULAMA
  giriş zamanlaması kötüydü (ilk 15dk'da giriş, gap chase),
  çıkış geç/erken yapıldı, stop takip edilmedi

BOYUTLANDIRMA
  pozisyon çok büyük/küçük, VIX kuralı uygulanmadı,
  nakit oranı yetersiz kaldı, korelasyon riski ihmal edildi

DUYGUSAL
  FOMO girişi, panik çıkışı, stop override, "geri dönecek" beklentisi,
  kalabalığı takip etme, son trade'in etkisiyle aşırı güven

HARİCİ
  beklenmeyen makro olay, jeopolitik gelişme, earnings sürprizi,
  sektör çapında satış — kontrol dışı faktör
```

---

## 3. KAPANIŞ RAPORUNDA REVIEW FORMATI

bölüm 5 (günün değerlendirmesi) içinde kapanan trade varsa:

```markdown
### kapanan trade review

**[SEMBOL]** — [kazanç ✅ / kayıp ❌] %X.XX ($XXX)

| alan | değer |
|------|-------|
| süreç skoru | X/5 |
| sonuç | kazanç/kayıp |
| matris konumu | ✅ ideal / ⚠️ şans / 📊 normal / ❌ hata |
| kök neden | [hazırlık/uygulama/boyutlandırma/duygusal/harici] |
| tespit edilen önyargı | [yok/anchoring/FOMO/...] |
| düzeltici aksiyon | [somut davranış] |

**ders**: [1-2 cümle]
```

---

## 4. HAFTALIK SİSTEM META-REVIEW

her pazar (haftalık raporda) aşağıdaki bölüm eklenir:

### format:

```markdown
## sistem performansı — hafta {tarih aralığı}

### swing v2.3 istatistikleri

| metrik | bu hafta | son 4 hafta | toplam |
|--------|----------|-------------|--------|
| toplam trade | X | X | X |
| kazanç oranı | %XX | %XX | %XX |
| ortalama kazanç | %X.X | %X.X | %X.X |
| ortalama kayıp | -%X.X | -%X.X | -%X.X |
| profit factor | X.XX | X.XX | X.XX |
| ortalama tutma süresi | X gün | X gün | X gün |
| ortalama süreç skoru | X.X/5 | X.X/5 | X.X/5 |

### yöntem bazlı başarı

| tarama yöntemi | trade sayısı | kazanç oranı | ort. k/z | not |
|----------------|-------------|--------------|---------|-----|
| kumo kırılımı | X | %XX | %X.X | [yorum] |
| kijun bounce | X | %XX | %X.X | |
| momentum | X | %XX | %X.X | |
| earnings | X | %XX | %X.X | |

### süreç kalitesi trendi

| süreç skoru | trade sayısı | kazanç oranı | ort. k/z |
|-------------|-------------|--------------|---------|
| 5 (mükemmel) | X | %XX | %X.X |
| 4 (iyi) | X | %XX | %X.X |
| 3 (ortalama) | X | %XX | %X.X |
| 2 (zayıf) | X | %XX | %X.X |
| 1 (kötü) | X | %XX | %X.X |

→ korelasyon: süreç skoru yükseldikçe kazanç oranı artıyor mu?

### kök neden dağılımı (kayıplar)

| kök neden | kayıp sayısı | toplam kayıp $ | en sık önyargı |
|-----------|-------------|----------------|----------------|
| hazırlık | X | $XXX | [anchoring/FOMO/...] |
| uygulama | X | $XXX | |
| boyutlandırma | X | $XXX | |
| duygusal | X | $XXX | |
| harici | X | $XXX | |

### düzeltici aksiyonlar takibi

| tarih | aksiyon | uygulandı mı | sonuç |
|-------|---------|-------------|-------|
| [önceki haftadan] | [aksiyon] | evet/hayır | [etki] |

### bu haftanın odak noktası

en sık tekrarlanan hata: [...]
bu hafta test edilecek düzeltici aksiyon: [...]
```

---

## 5. PUT/CALL RATIO + ANALYST CONSENSUS

### sabah raporuna eklenecek veri noktaları:

```
SENTIMENT VERİLERİ:

1. CBOE put/call ratio (web aramasıyla):
   → websearch: "CBOE put call ratio today"
   - < 0.7: aşırı iyimserlik (contrarian ayı sinyali)
   - 0.7 - 1.0: normal aralık
   - > 1.0: aşırı kötümserlik (contrarian boğa sinyali)
   - > 1.2: panik seviyesi (tarihsel olarak dip yakın)

2. analyst consensus değişimleri (FMP ile):
   → FMP: upgrades-downgrades (portföy hisseleri, limit 20)
   → FMP: grades-consensus (portföy hisseleri)
   - consensus kötüleşiyorsa (strongBuy azalıyor) → dikkat
   - consensus iyileşiyorsa (buy artıyor) → teyit
   - son 7 günde 2+ downgrade → sektör sorunu olabilir
```

---

## ENTEGRASYON REFERANSLARI

bu dosya şu promptlardan referans alınır:
- `DAILY_PART2_CLOSING.md` → ADIM 4 bölüm 5 değerlendirme, ADIM 5 playbook güncelleme
- `SESSION_ACTION_PROMPT.md` → AŞAMA 4 trade işlemleri (closed.json kaydı)
- haftalık rapor → sistem performansı bölümü

tetikleyici cümle: "→ docs/POST_TRADE_REVIEW.md uygula"
