# KARAR ÇERÇEVESİ — v1.0

> **son güncelleme**: 6 nisan 2026
> **amaç**: her trade kararında tutarlı, önyargısız, gerekçeli düşünme süreci sağlamak
> **kullanım**: seans promptu AŞAMA 3'te her karar öncesi, sabah raporunda plan yazarken

---

## 1. PRE-TRADE GO/NO-GO (giriş öncesi 10 soru)

her yeni pozisyon açmadan önce bu 10 soruyu sırasıyla geç.
**tek bir "hayır" = giriş iptal** (istisna: gerekçeyle açıkça belirtilirse override edilebilir).

```
□ 1. sinyal var mı?
     ichimoku 4/4, kumo kırılımı, kijun bounce veya portföy tezine uygun tetikleyici
     → sinyal yoksa giriş yok (FOMO girişi yasak)

□ 2. stop tanımlı mı?
     chandelier (3×ATR) veya portföy stop seviyesi hesaplandı mı?
     stop mesafesi ≥%5 mi? (aksi halde R:R bozulur)

□ 3. R:R ≥ 2:1 mi?
     hedef fiyat / stop mesafesi oranı en az 2:1
     → 1.5:1 bile olsa giriş yapma

□ 4. VIX uygun mu? (K-13 v4.1)
     kriz tipine göre sektör kontrolü:
     - faydalanıcı sektör → VIX 28'e kadar tam pozisyon
     - duyarlı sektör → VIX 22'den itibaren yarım
     - VIX >35 → hiç giriş yok

□ 5. insider temiz mi? (K-17/K-18)
     FMP insider-trading endpoint kontrolü
     son 90 günde büyük satış (>$5M) var mı?

□ 6. earnings riski var mı?
     5 gün içinde earnings açıklaması var mı?
     varsa: binary risk, K-11 erken uygula veya bekle

□ 7. korelasyon uygun mu?
     aynı alt sektörde 3'ten fazla pozisyon olacak mı? (3 portföy + swing toplam)
     sektör exposure %30'u aşacak mı?

□ 8. nakit yeterli mi?
     giriş sonrası nakit oranı %5 altına düşecek mi?
     düşecekse: acil fırsat değilse giriş yapma

□ 9. sabah planında var mı?
     plan dışı giriş → ekstra gerekçe zorunlu
     "seansta gördüm, güzel görünüyor" yeterli değil

□ 10. karşıt argüman düşündüm mü?
      bu pozisyonun kötüye gidebileceği en muhtemel senaryo ne?
      → cevap yoksa giriş yapma (kırmızı takım testi bölüm 3'e bak)
```

---

## 2. DÜŞÜNCE ZİNCİRİ ZORUNLULUĞU (chain-of-thought)

her AL veya SAT kararından önce **3 adımlı gerekçe** yazılmalıdır.
bu gerekçe chat'te gösterilir, rapor dosyasına yazılmaz.

### format:

```
KARAR: [AL/SAT/TUT/İZLE] — [SEMBOL]

1. VERİ: [somut veri noktası — fiyat, RSI, hacim, haber, teknik seviye]
   örnek: "COHR RSI 68, kumo üstü, tenkan>kijun, hacim 1.4x ortalama"

2. KURAL: [hangi playbook kuralı veya sistem sinyali bu kararı destekliyor]
   örnek: "ichimoku 4/4 bullish, chandelier stop %6.2 mesafede, K-13 uygun (optik = faydalanıcı)"

3. KARŞIT: [bu kararın neden yanlış olabileceği]
   örnek: "earnings 8 gün sonra, VIX hala 26 seviyesinde, sektör RS son 3 günde zayıflıyor"

→ SONUÇ: [kararı uygula / ertele / vazgeç]
```

### ne zaman uygulanır:
- her yeni pozisyon girişinde (swing + portföy)
- her satış kararında (stop hariç — stop otomatik, gerekçe gereksiz)
- her kısmi kâr alma kararında (K-11)
- her pozisyon büyütme kararında

### ne zaman UYGULANMAz:
- fiyat güncellemesi (rutin)
- trailing stop yukarı çekme (mekanik)
- watchlist ekleme/çıkarma

---

## 3. KIRMIZI TAKIM TESTİ (red team)

her yeni pozisyon açılışında zorunlu. amaç: onay yanlılığını (confirmation bias) kırmak.

### format:

```
KIRMIZI TAKIM — [SEMBOL]

senaryo 1 (en muhtemel risk): [ne olabilir]
  tetikleyici: [hangi olay/veri bu senaryoyu başlatır]
  etki: [fiyat tahmini, stop tetiklenir mi?]
  savunma: [ne yaparsın — stop zaten korur mu, yoksa ek aksiyon gerek mi?]

senaryo 2 (sektörel risk): [sektör seviyesinde ne ters gidebilir]
  tetikleyici: [...]
  etki: [...]

senaryo 3 (makro risk): [genel piyasa seviyesinde ne ters gidebilir]
  tetikleyici: [...]
  etki: [...]
```

### kalite kontrolü:
- 3 senaryo da "fiyat düşer" olmamalı — farklı risk tipleri olmalı
- en az 1 senaryo tezin temelini sorgulmalı (sektör hikayesi bozulur, talep azalır vb.)
- "risk yok" kabul edilmez — her pozisyonun riski vardır

---

## 4. BİLİŞSEL ÖNYARGI KONTROL LİSTESİ (genişletilmiş)

mevcut self-validation'a ek olarak bu önyargıları kontrol et.
özellikle karar anında "dur ve düşün" tetikleyicileri:

### her kararda kontrol et:

```
□ ONAY YANLILIĞI (confirmation bias)
  "sadece tezimi destekleyen bilgilere mi baktım?"
  → en az 1 ayı (bearish) argüman bul ve değerlendir

□ ÇIPA ETKİSİ (anchoring bias)
  "bu hisse X dolardı, şimdi ucuz" diye mi düşünüyorum?
  → geçmiş fiyat referans noktası değil, mevcut değerleme ve teknik yapı önemli
  → tetikleyici: "eskiden şu kadardı" cümlesini kuruyorsan, çıpa etkisi var

□ KAYIP KAÇINMASI (loss aversion / disposition effect)
  "kazananı erken satıp kaybedeni tutma" eğilimim mi var?
  → stop'a yakın hisseyi "biraz daha bekleyeyim" diye tutuyorsan, disposition effect
  → K-06 kuralı: stop override = zarar biriktirme

□ BATIK MALİYET (sunk cost fallacy)
  "bu kadar zarar ettim, şimdi satamam, geri dönecek" mi düşünüyorum?
  → soru: "bu hisseyi bugün sıfırdan alır mıydım?" hayır ise → çık

□ YAKINLIK YANLILIĞI (recency bias)
  "dünkü büyük düşüş/yükseliş yüzünden aşırı tepki mi veriyorum?"
  → tek günlük hareket = gürültü olabilir, 1./2./3. derece etki zinciri düşün

□ SÜRÜ PSİKOLOJİSİ (herding / FOMO)
  "herkes alıyor/satıyor, ben de yapmalıyım" mı düşünüyorum?
  → twitter'da herkesin konuştuğu hisse = geç kalmış olabilirsin
  → soru: "bu fırsatı 2 gün önce görmüş olsaydım alır mıydım?"

□ AŞIRI GÜVEN (overconfidence)
  "kesin yükselir/düşer" diye mi düşünüyorum?
  → kesinlik yok, olasılık var — hedef belirsizliği kalibre et (KESİN/MUHTEMEL/SPEKÜLATİF)
  → son 3 trade'in hepsi kârlıysa, aşırı güven riski yüksek

□ SONUÇ YANLILIĞI (outcome bias)
  "son trade kârlıydı, demek ki strateji doğru" mu düşünüyorum?
  → kârlı ama kötü süreçli trade = şans, tekrarlanmaz
  → bkz: POST_TRADE_REVIEW.md process vs outcome ayrımı
```

---

## 5. SEKTÖR EXPOSURE TABLOSU

her seansta (en az FAZ 2'de) tüm portföylerin sektör dağılımını hesapla.

### format:

```
SEKTÖR EXPOSURE — {tarih}

| sektör | dengeli | agresif | temettü | swing | TOPLAM $ | TOPLAM % | UYARI |
|--------|---------|---------|---------|-------|----------|----------|-------|
| enerji | $XX,XXX | $0 | $XX,XXX | $0 | $XX,XXX | XX% | |
| teknoloji | $0 | $XX,XXX | $0 | $XX,XXX | $XX,XXX | XX% | ⚠️>30% |
| ... | | | | | | | |

TOPLAM: $XXX,XXX

kurallar:
- tek sektör > %30 → ⚠️ yoğunlaşma uyarısı
- tek sektör > %40 → 🔴 acil rebalance değerlendir
- 2 sektör toplamı > %60 → ⚠️ çeşitlendirme yetersiz
```

### ne zaman hesaplanır:
- sabah raporunda (BÖLÜM 2 sonunda)
- seans içinde yeni pozisyon açılmadan önce (GO/NO-GO soru 7)
- haftalık raporda (zorunlu)

---

## ENTEGRASYON REFERANSLARI

bu dosya şu promptlardan referans alınır:
- `SESSION_ACTION_PROMPT.md` → AŞAMA 3 karar matrisi öncesi
- `DAILY_PART1_SABAH.md` → ADIM 6 plan yazarken
- `DAILY_PART2_CLOSING.md` → ADIM 4 bölüm 5 değerlendirme

tetikleyici cümle: "→ docs/DECISION_FRAMEWORK.md uygula"
