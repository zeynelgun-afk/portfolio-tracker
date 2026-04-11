# KARAR MİMARİSİ v2.0 — ÇOK KATMANLI KARAR SİSTEMİ
> **oluşturulma**: 11 nisan 2026
> **kaynak**: MarketDash AI Swing Trading Guide 2026, FactSet thematic research, institutional multi-agent frameworks

---

## FELSEFİ TEMEL

**v1 sorunu:** 10 soruluk checklist + chain-of-thought yeterliydi ama düz sıralı. Öncelik sırası yoktu, çakışma çözümü yoktu, piyasa rejimi adaptasyonu yoktu.

**v2 prensibi:** Üç katmanlı hiyerarşik karar. Her katman bir üst katmanı geçmeden devreye giremiyor. Rejim-adaptif: trendsiz piyasada momentum stratejisi bekletilir, trendli piyasada daha agresif.

---

## KATMAN 1: MAKRO REJİM FİLTRESİ (Master Switch)

Hiçbir bireysel trade kararı bu katmanı atlatamaz.

```
REJİM TESPİTİ (günlük, sabah):

GÜÇLÜ BULL (en iyi ortam):
  SPY > 21EMA + eğim ↗ + VIX <20 + TEMA_PUANI >55
  → Tüm stratejiler tam gaz | Swing + portföy açık | Tam pozisyon

ZAYIF BULL (dikkatli):
  SPY > 21EMA + eğim → veya ↘ + VIX 20-28
  → Swing temkinli | Yeni portföy girişi seçici | K-13 yarım

NÖTR/YAN TREND (strateji bekle):
  SPY ± 21EMA | VIX 22-30 salınım
  → Swing: sadece A-kalite 4/4 | Portföy: mevcut koru, yeni giriş az
  → Momentum stratejileri düşük beklenti: "chop modunda beklenti düşür" (araştırma: momentum 0.4R→-0.1R choppy piyasada)

ZAYIF BEAR (savunma):
  SPY < 21EMA + eğim ↘ + VIX 28-35
  → Swing: K-14 kademeli fren | Portföy: K-11 hızlandırılmış kâr
  → K-13b istisnası değerlendirilebilir (faydalanıcı sektörler)

GÜÇLÜ BEAR (nakit):
  SPY << 21EMA + VIX >35
  → Swing: DUR (K-14 tam stop) | Portföy: savunmacı rotasyon
  → Sadece çeyrek pozisyon, yüksek temettü/beta<1 hisseler
```

---

## KATMAN 2: TEMA UYUMU (Günlük Dinamik)

Katman 1 geçildikten sonra tema kararı sorgulanır.

```
TEMA_PUANI >55 → Açık sinyaller değerlendirilir
TEMA_PUANI 35-55 → Seçici: sadece tier-1 hisseler
TEMA_PUANI <35 → Yeni giriş yapma, mevcut pozisyonları koru
TEMA DÖNÜŞÜMÜ → Nakit bekle (yeni tema için araştırma ajanı çalışsın)
```

**Tema-portföy eşleştirme kontrolleri:**
- Girilecek hisse doğru temadan mı?
- Bu temadan kaç pozisyon zaten var? (K-17 tema limiti %40)
- Hangi katmandan? (Tier 1 → tam poz, Tier 2 → dikkatli, Tier 3 → sadece agresif)

---

## KATMAN 3: BİREYSEL HİSSE KARARI (Micro)

Her iki üst katmanı geçtikten sonra hisse seviyesinde analiz.

### 3A. TEKNİK SİNYAL KALİTE SKORU (0-100)

```
Ichimoku uyumu      (0-30): 4/4=30, 3/4=15, <3=0
Hacim teyidi        (0-20): 2x+=20, 1.5x=15, 1.2x=10, <1.2x=0
RSI bölgesi         (0-20): 45-65=20, 40-70=15, 70-80=8, >80 veya <35=0
SMA pozisyonu       (0-15): SMA50 üstü=15, altı=0
Tema momentum uyumu (0-15): RS20>+3%=15, 0-3%=10, negatif=0
```

| Skor | Karar |
|------|-------|
| 80-100 | A-kalite → Tam pozisyon |
| 60-79 | B-kalite → Yarım pozisyon |
| 40-59 | C-kalite → Sadece Agresif, çeyrek pozisyon |
| <40 | GEÇ |

### 3B. DÜŞÜNCE ZİNCİRİ (Her karar öncesi zorunlu)

```
VERİ:    [Somut sayı — RSI, hacim oranı, ATR, teknik seviye]
KURAL:   [Hangi K-kuralı bu kararı destekliyor]
TEMA:    [Tema puanı, hissenin tema içindeki konumu]
KARŞIT:  [Bu kararın neden yanlış olabileceği — en az 1 senaryo]
POZİSYON: [Hangi portföy, kaç hisse, stop seviyesi, hedef]
```

### 3C. KIRMIZI TAKIM (Yüksek riskli kararlarda zorunlu)

Şu durumlarda kırmızı takım testi zorunlu:
- Pozisyon büyütme (mevcut % limit'in %50'sini aşacaksa)
- Tema değişimi sırasında yeni giriş
- K-13b istisnası kullanılıyorsa
- 3+ gün peşpeşe kayıp sonrası ilk yeni giriş

```
KIRMIZI TAKIM [SEMBOL]

Senaryo 1 — Tema riski: [Tema neden çökebilir?]
Senaryo 2 — Hisse riski: [Şirkete özgü ne ters gidebilir?]
Senaryo 3 — Makro riski: [Piyasa seviyesinde ne değişebilir?]

Her senaryo için: Tetikleyici → Etki → Savunma
```

---

## KARAR HİYERARŞİSİ (Çakışma çözümü)

```
1. K-06 STOP TETİĞİ          → HER ŞEYIN ÜSTÜNDE, tartışmasız
2. K-14 DRAWDOWN FRENI        → Swing girişini engeller
3. MAKRO REJİM (Katman 1)     → Tema ve hisse kararını çerçeveler
4. TEMA_PUANI (Katman 2)      → Hisse seçimini filtreler
5. K-13 VIX MATRİSİ          → Pozisyon boyutunu belirler
6. TEKNİK SİNYAL (Katman 3)  → Giriş zamanlamasını belirler
7. K-17 KORELASYON           → Portföy konsantrasyonunu sınırlar
8. K-12 POZİSYON LİMİTİ     → Son kontrol, boyutu sınırlar
```

---

## BİLİŞSEL ÖNYARGI KORUMALARI (Geliştirilmiş)

Araştırma: Combining multiple confirmation signals reduces false positives by 40-60%. Tek göstergeye güvenmek temel hata.

```
□ TEMA FOMO: "Bu tema çok iyi görünüyor, hızlı girmem lazım"
  → Kontrol: TEMA_PUANI >55 mi? Teknik sinyal A-kalite mi?
  → Değilse: bekle

□ TREND EMPATİSİ: Kârdaki pozisyonu "mutlaka tutalım" hissi
  → Kontrol: Stop seviyesi nerede? Tema puanı düşüyor mu?
  → Kural: K-11 stepped ATR bir duygu değil, matematiktir

□ KAYIP ÖNYARGISI: Stop yakınken "biraz daha bekleyeyim"
  → Kural: K-09 protokolü çalıştır. 3+ negatif → çık.
  → Override yasak (K-06)

□ TEMA KÖRÜ: Aktif temaya her hisseyi sokmak
  → Kontrol: Hisse gerçekten tier-1 mi? Conviction skoru nedir?
  → Minimum skor 60 yoksa GEÇ

□ YENİ TEMA HEYECANİ: Rotasyon sırasında aceleyle yeni temaya girmek
  → Protokol: Araştırma ajanı çalışsın → Supply chain haritası hazır mı?
  → Yeni temadan ilk giriş yarım pozisyon, 2-3 gün bekle
```

---

## SEANS İÇİ KARAR KALİTESİ

Her FAZ sonunda Claude şunu kendine sorar:

```
FAZ 1 sonu: "Acil kararlar netlik ve kural uyumlu muydu?"
FAZ 2 sonu: "Kararlarımın kaçı önceden planlanmıştı, kaçı reaktifti?"
FAZ 3 sonu: "Bugün kapanırken açık kalan riskler neler?"

Kalite metrikleri (haftalık takip):
- Plan dışı giriş oranı (hedef: <%20)
- Kırmızı takım testi atlama oranı (hedef: %0)
- K-kural ihlali oranı (hedef: %0)
- Tema puanı <35 iken yapılan giriş sayısı (hedef: 0)
```

---

## PORTFÖY BAZLI KARAR FARKLARI

| | Dengeli | Agresif | Temettü |
|---|---|---|---|
| Min teknik skor | 60 | 50 (riskli ama fırsat odaklı) | 65 |
| Tema uyumu | Zorunlu | Zorunlu | Zorunlu |
| Kırmızı takım | Büyük giriş | Her girişte | Seçici |
| Pozisyon büyütme | Skor >70 | Skor >60 | Skor >75 |
| Seans içi yeni giriş | Temkinli | Açık | Hayır (portföy kararlı) |

---

*finzora ai | karar mimarisi v2.0 | 11 nisan 2026*
