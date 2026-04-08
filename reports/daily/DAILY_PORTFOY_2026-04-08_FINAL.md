# günlük portföy fırsat raporu — 8 nisan 2026, çarşamba (FİNAL)

> finzora ai | bu rapor bugünkü ÜÇÜNCÜ ve SON revizyondur. önceki iki sürüm referans amacıyla saklıdır ama BU RAPOR geçerli karar kaynağıdır.
>
> revize geçmişi:
> - v1 (`DAILY_PORTFOY_2026-04-08.md`): FMP fundamentals hatası ile yalnızca teknik skorlar → 7 EKLE
> - v2 (`DAILY_PORTFOY_2026-04-08_REVIZE.md`): fundamentals düzeltme + manuel niteliksel puanlar → 5 EKLE
> - **v3 FİNAL (bu rapor)**: mekanik skor sistemi `scripts/portfolio_scan_common.py` ile test edildi → 6 EKLE
>
> v2 ile v3 arasındaki fark: v2'de "CMS katalizör +3", "sektör yeni +2" gibi niteliksel bonuslar içeriyordu. v3 bu sübjektif bonusları kaldırdı, sadece ölçülebilir metrikler (P/E, ROIC, momentum, teknik, FCF yield) kullanıyor. Sonuç: 4 karar değişti.

---

## 0. v2 → v3 değişen kararlar

| sembol | v1 | v2 | **v3 final** | sebep |
|--------|:--:|:--:|:------------:|-------|
| **CAT** | EKLE | GEÇ | **EKLE** | mekanik skor 10 (eşik 9), ROIC %11.4 + 6M +%44 + golden cross baskın, tek P/E bakışı yanıltıcıydı |
| **UNH** | EKLE | EKLE | **GEÇ** | mekanik skor 5 (eşik 9 altı), ROIC %8.2 düşük, 6M -%16.8 negatif, CMS katalizör niteliksel bonus sistemde yok |
| **SO** | İZLE | EKLE | **GEÇ** | mekanik skor 2, FCF yield -%3.03 (ağır capex), temettü sürdürülebilirlik riski |
| **UPS** | GEÇ | GEÇ | **EKLE** | mekanik skor 9 (eşik 9 sınırda), yield %6.72 + P/E 14.9 + FCF yield %5.75. v1/v2'de gözden kaçtı |
| **AMAT** | EKLE | İZLE | **EKLE** | K-17 korelasyon KLAC ile var ama limit max 3 ekipman, 2 OK |

**kararı değişmeyenler**: WDC, KLAC, MRK (hepsi 3 sürümde de güçlü sinyal)

---

## 1. final EKLE listesi

### tablo

| portföy | sembol | fiyat | skor | tutar | tez başlık |
|---------|--------|------:|:----:|------:|------------|
| dengeli | **CAT** | $724.44 | 10 | $16,667 | Golden cross + global capex + ROIC %11.4 |
| agresif | **WDC** | $311.96 | **17** | $15,000 | Samsung memory beat, ROIC %25.2 |
| agresif | **KLAC** | $1,548.85 | 14 | $15,480 | Process control monopol, ROIC %36.8 |
| agresif | **AMAT** | $354.31 | 14 | $14,880 | Ekipman lider, ROIC %22.6 |
| temettü | **MRK** | $119.36 | 9 | $6,000 | P/E 16.3, ROIC %20.8, payout %44.8 |
| temettü | **UPS** | $97.58 | 9 | $5,855 | yield %6.72, P/E 14.9, FCF yield %5.75 |

**Toplam yeni alım**: ~$73,882

### mevcut pozisyon aksiyonları

| işlem | portföy | sembol | tutar | koşul |
|-------|---------|--------|------:|-------|
| **DÖNDÜR (SAT)** | temettü | PM (77 hisse) | -$12,127 | ilk 30 dk $160 altı kapanışta çalışır |
| **BÜYÜT** | temettü | MO | +$5,000 | ilk 30 dk SMA50 üstü teyidi şart |

**Sonuç**: PM sermayesi MRK + UPS'e aktarılır. net temettü nakit hareketi ~+$272

---

## 2. aday detayları

### dengeli — CAT

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $724.44 | |
| P/E TTM | 38.1 | pahalı, puan yok (0) |
| ROIC | %11.4 | ✅ +1 (>10) |
| 6M momentum | +%44.3 | ✅ +3 (>20%) |
| 1M momentum | +%6.4 | ✅ +1 (>0) |
| RSI | 54.4 | ✅ +2 (40-60 nötr) |
| SMA50 | ✅ ($714.7) | +2 |
| SMA200 | ✅ ($553.3) | golden cross +1 |
| FCF yield | %3.03 | ✅ +1 (>3%) |
| **SKOR** | **10** | **EKLE** (eşik 9) |

**tez**: Golden cross aktif, 6 aylık +%44 güçlü trend. ROIC %11.4 kalite sağlam, FCF yield %3 pozitif. Data center inşaat patlamasından yararlanıyor. Dengeli portföyde sanayi yok = sektör çeşitlilik. Ateşkes sonrası global risk-on rotasyonu sanayiye olumlu.

**karşıt argüman**: P/E 38 yüksek, döngüsel hisse. Ekonomik yavaşlama riski. Yüksek fiyat ($724) nominal pozisyon büyüklüğü hassas (23 hisse sadece $16,667 için)

**giriş planı**:
- hedef giriş: $715-735 (ilk 30 dk bekle, kovalama yok)
- stop: $695 (-%4.1)
- hedef 1: $790 (+%9.0)
- hedef 2: $850 (+%17.3)
- R:R: 2.2
- pozisyon: 23 hisse × $724 = $16,652 (hedef %16.67 ağırlık)

### agresif — WDC (en yüksek skor)

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $311.96 | |
| P/E TTM | 28.3 | memory sektör orta |
| ROIC | %25.2 | ✅ +3 (>25) |
| 1M momentum | +%27.2 | ✅ +3 (>20) |
| 3M momentum | +%66.2 | ✅ +2 (>15) |
| 6M momentum | +%157.4 | ✅ +3 (>50) |
| RSI | 59.1 | ✅ +2 (50-70) |
| SMA50 | ✅ ($278.4) | +2 |
| golden cross | ✅ | +2 |
| **SKOR** | **17** | **EKLE** (eşik 14) |

**tez**: samsung Q1 operating profit YoY +%755, memory sektörü için pozitif teyit. WDC pure-play NAND/HDD, P/E 28 memory sektöründe kabul edilebilir, ROIC %25.2 güçlü fundamental. 6 aylık +%157 momentum + teknik setup ideal. SNDK (P/E -100) yerine daha güvenli alternatif.

**karşıt argüman**: 6 aylık +%157 ralli hızlı, kar alma baskısı var. Memory cyclical — üretim fazlası riskine duyarlı. K-14 aktif = YARIM POZİSYON zorunlu

**giriş planı**:
- hedef giriş: $300-320 (ilk 30 dk bekle)
- stop: $288 (-%7.7, memory sektörü volatil)
- hedef 1: $360 (+%15.4)
- hedef 2: $420 (+%34.6)
- R:R: 2.0
- pozisyon: **$15,000 YARIM POZ** (normal $30K) → ~48 hisse

### agresif — KLAC

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $1,548.85 | |
| P/E TTM | 44.7 | pahalı ama kalite karşılığı |
| ROIC | **%36.8** | ✅ +3 (>25) — ekipman en yüksek |
| ROE | %95.2 | — |
| 1M | +%15.2 | ✅ +2 |
| 6M | +%45.8 | ✅ +2 |
| RSI | 57.2 | ✅ +2 |
| SMA50/200 | ✅/✅ | +2 + golden cross +2 |
| **SKOR** | **14** | **EKLE** (eşik 14) |

**tez**: yarıiletken process control neredeyse monopol, rakipsiz. ROIC %36.8 ekipman sektörünün EN yüksek getirili şirketi. Samsung memory beat + TSMC foundry capex + AVGO custom ASIC tedarik zinciri yayılımı. P/E 44.7 pahalı görünse de kalite lideri

**karşıt argüman**: P/E 44.7 aşırı pahalı, geleceği fiyatlandırıyor. Capex cycle iptal riski (samsung/TSMC erteleme). Çin ticaret gerilimi. Hisse fiyatı $1,548 nominal büyük (küçük % yanılma büyük dolar zararı)

**giriş planı**:
- hedef giriş: $1,520-1,570
- stop: $1,470 (-%5.1)
- hedef 1: $1,700 (+%9.8)
- hedef 2: $1,850 (+%19.4)
- R:R: 2.0
- pozisyon: **$15,480 YARIM POZ** → ~10 hisse

### agresif — AMAT

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $354.31 | |
| P/E TTM | 35.8 | yüksek ama kalite kabul |
| ROIC | %22.6 | ✅ +2 (>15) |
| 1M | +%9.1 | ✅ +1 |
| 3M | +%27 | ✅ +2 |
| 6M | +%62.9 | ✅ +3 (>50) |
| RSI | 52.4 | ✅ +2 (fresh momentum) |
| SMA50/200 | ✅/✅ | +2 + golden cross +2 |
| **SKOR** | **14** | **EKLE** (eşik 14) |

**tez**: ekipman katman 2. pozisyonu, KLAC ile birlikte — K-17 korelasyon limit max 3 ekipman altında. ROIC %22.6 sağlam, stable trend (en az volatil), RSI 52 fresh momentum açısı = giriş için ideal. AI tedarik zinciri ekipman katmanı iki güçlü oyuncuyla kapsanmış

**karşıt argüman**: KLAC ile aynı katman (K-17 yüksek korelasyon). Capex cycle iptal riski her ikisinde de çalışır. Ekipman cyclical

**giriş planı**:
- hedef giriş: $345-360
- stop: $332 (-%6.3)
- hedef 1: $395 (+%11.5)
- hedef 2: $430 (+%21.4)
- R:R: 2.0
- pozisyon: **$14,880 YARIM POZ** → ~42 hisse

**⚠️ K-17 uyarısı**: KLAC + AMAT aynı ekipman katmanı. Her ikisi de gap-down olursa birlikte zarar = korelasyon kayıp. Bu bilinçli kabul — fundamental ikisi de güçlü, tez aynı, her ikisi veya hiçbiri kararı vermek daha doğru. Limit 3 altında (2 pozisyon)

### temettü — MRK (en sağlıklı temettü adayı)

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $119.36 | |
| yield | %2.78 | sınır (hedef %3 altı), 0 puan |
| payout | %44.8 | ✅ +3 (<50%) |
| P/E TTM | 16.3 | ✅ +1 (<18) |
| ROIC | %20.8 | ✅ +2 (>15) |
| FCF yield | %4.19 | ✅ +1 (>0) |
| SMA50 | ✅ | +1 |
| SMA200 | ✅ | +1 |
| **SKOR** | **9** | **EKLE** (eşik 9 sınır) |

**tez**: P/E 16.3 ucuz, ROIC %20.8 mükemmel, payout %44.8 çok sürdürülebilir. Keytruda dünyanın en çok satan onkoloji ilacı ($25B/yıl). 6 ay +%38 güçlü trend. SMA50/SMA200 üstünde. **Skor düşük görünüyor çünkü yield eşik altı (%2.78 vs %3), ama fundamental kalite en yüksek temettü adayı**

**karşıt argüman**: Keytruda 2028 patent cliff — sonrası satış düşüş riski (2 yıl uzak ama fiyatlanmaya başladı). Yield %2.78 temettü portföy hedefi %3+ altı. Sağlık sektörü politika riski (ilaç fiyat düzenleme)

**giriş planı**:
- hedef giriş: $118-122
- stop: $112 (-%6.2)
- hedef 1: $135 (+%13.1)
- hedef 2: $150 (+%25.6)
- R:R: 2.2
- pozisyon: 50 hisse × $120 = $6,000 (PM sermayesinden)

### temettü — UPS (yüksek yield, payout sınırda)

| metrik | değer | değerlendirme |
|--------|-------|---------------|
| fiyat | $97.58 | |
| yield | %6.72 | ✅ +3 (5-7% aralığı) |
| payout | %96.9 | sınır (<100 trap değil, ama >%75 eşik) 0 puan |
| P/E TTM | 14.9 | ✅ +2 (<15) |
| ROIC | %10.6 | ✅ +1 (>10) |
| FCF yield | %5.75 | ✅ +2 (>5%) |
| SMA50 | ❌ | 0 |
| SMA200 | ✅ | +1 |
| RSI | 40.4 | oversold yakını |
| **SKOR** | **9** | **EKLE** (eşik 9 sınır) |

**tez**: Yield %6.72 çok yüksek, P/E 14.9 sektör ortalaması altı. **FCF yield %5.75 kritik**: temettü FCF'den ödenebilir (payout %96.9 kağıt üstü yüksek ama nakit akışı yeterli). Ateşkes sonrası petrol -%19 = kargo maliyeti düşüş = marj iyileşme beklentisi

**karşıt argüman ⚠️ KRİTİK**: 
- Payout %96.9 ÇOK yüksek (eşik %75 üstü, ama <%100 yield trap değil)
- **SMA50 altında (K-04 ihlal)** — trend bozuk
- Amazon rekabet baskısı sürüyor (2 yıldır)
- Son 1 ay -%4.7 negatif momentum

**GİRİŞ ÖN KOŞULU**: UPS K-04 (SMA50 altı) ihlalinde. Normal kural = GEÇ. Ama skor 9 sınırda, yield çok cazip, FCF sağlıklı. **Şartlı giriş**: seans ilk 30 dk RALLI + SMA50 kırılım teyidi gelirse EKLE, aksi halde **İZLE** olarak watchlist'te kal.

**giriş planı**:
- koşullu giriş: $97-100 ancak $106.7 (SMA50) kırılım sonrası
- stop: $92 (-%5.7)
- hedef 1: $108 (+%10.7)
- hedef 2: $115 (+%17.8)
- R:R: 1.8
- pozisyon: 60 hisse × $97 = $5,820 (PM sermayesinden, koşullu)

---

## 3. bugün için final aksiyon planı

### 🔴 hemen (seans açılışında, ilk 30 dk sonra)

**DÖNDÜR**:
1. **PM SAT** — temettü, 77 hisse @ piyasa — koşul: $160 altı ilk 30 dk kapanışı. $160 üstü → trailing $156 aktive, tutuş

**EKLE** (PM çıkışı + mevcut nakit):
2. **MRK AL** — temettü, 50 hisse @ $120 = $6,000
3. **UPS AL** — temettü, **KOŞULLU**: SMA50 ($106.7) kırılım teyidi olursa 60 hisse @ $97 = $5,820. Yoksa İZLE

**BÜYÜT**:
4. **MO (temettü) BÜYÜT** — +75 hisse @ $66 = $5,000 (koşul: SMA50 üstü teyit)

**YENİ GİRİŞLER** (K-14 yarım pozisyon, agresif):
5. **WDC AL** — 48 hisse @ $312 = $15,000
6. **KLAC AL** — 10 hisse @ $1,548 = $15,480
7. **AMAT AL** — 42 hisse @ $355 = $14,910

**YENİ GİRİŞLER** (dengeli):
8. **CAT AL** — 23 hisse @ $725 = $16,675

### Toplam işlem özeti

| portföy | işlem | nominal | sonrası nakit | sonrası poz |
|---------|-------|--------:|--------------:|:-----------:|
| dengeli | CAT ekle | $16,675 | $65,938 | 3/6 |
| agresif | WDC + KLAC + AMAT | $45,390 | $312,433 | 3/10 |
| temettü (MRK+MO) | PM sat → MRK + MO büyüt | net -$11,127 (sat) +$11,000 (alım) = -$127 | $90,928 | 5/15 |
| temettü (UPS koşullu) | UPS AL | +$5,820 | $85,108 | 6/15 |

**toplam yeni pozisyon sayısı**: 6 (CAT, WDC, KLAC, AMAT, MRK, UPS)
**UPS koşullu** — ilk 30 dk kırılım olmazsa 5 pozisyon açılır.

### kümülatif risk değerlendirmesi

- **Yeni alım toplamı**: ~$73,881 + MO büyütme $5,000 = **$78,881 hareket**
- **K-14 yarım poz disiplini**: agresif pozisyonlar $45K (normal $90K) — %50 risk azaltma
- **K-17 korelasyon**: 
  - Agresif ekipman (KLAC + AMAT) = 2 — limit 3 altında ✅
  - Agresif farklı katman: memory (WDC) + ekipman (KLAC/AMAT) — 2 katman ✅
- **K-12 sektör limit**: 
  - Dengeli sanayi: CAT $16.7K = %14.9 — limit %25 altı ✅
  - Agresif semiconductor: 3 pozisyon $45K = %12.6 — limit %20 altı ✅
  - Temettü sağlık: MO + MRK = varsa çift pozisyon hesabı — %15 altı ✅
- **Maksimum zarar** (tüm stoplar tetiklenirse): ~$5,000-5,800 (%0.8 portföy toplamı)

**ateşkes çökme senaryosu (%15 ihtimal)**: tüm 6 pozisyon birlikte zarar eder ama stop'lar ile kontrol altında. Toplam max zarar ~$5K aralığı — kabul edilebilir.

### 🟡 izle (seans içinde)

9. **UPS SMA50 kırılım** — $106.7 üstü kapanış → koşullu giriş aktif
10. **DAL earnings tepkisi** — havayolu sektörü rallisi havayolu pozisyonumuz yok ama sektör lider teyidi
11. **FOMC tutanakları 21:00 TR** — dovish finansal pozitif, hawkish negatif

### 🟢 pasif (seviye bekle)

12. **LLY** $900 altı → dengeli İZLE (skor 8)
13. **MU** SMA50 kırılım → agresif İZLE (skor 12)
14. **GEV** pullback → agresif İZLE
15. **HUM/ELV** — dengeli sağlık alternatifi olarak 1-2 hafta görev takibi

---

## 4. önceki sürümlerin durumu

- `DAILY_PORTFOY_2026-04-08.md` (v1): **geçersiz** — FMP alan hatası ile yanlış fundamentals
- `DAILY_PORTFOY_2026-04-08_REVIZE.md` (v2): **geçersiz** — fundamental düzeldi ama niteliksel bonuslar sübjektifti
- **`DAILY_PORTFOY_2026-04-08_FINAL.md` (v3)**: **GEÇERLİ** — mekanik skor sistemi kalibre edilmiş

**`data/watchlist.json`** ile senkronize: v3 şema, 6 aktif EKLE aday, 5 haric tutulan.

---

*finzora ai | portfolio opportunity system v1.0 + portfolio_scan_common.py v3 kalibre | 8 nisan 2026 FİNAL*
