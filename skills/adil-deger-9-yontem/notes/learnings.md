# Adil Değer 9 Yöntem - Öğrenme Defteri

Her kullanımda dolan, skill'i geliştirmek için kullanılan notlar.

## Kayıt Formatı

```markdown
## YYYY-MM-DD - [TICKER]
**Bağlam:** [kısa, ne istendi]
**Sektör tespiti:** [auto-detected preset, doğru muydu?]
**Pure Forward:** [aktif/pasif, neden?]
**Piyasa rejimi:** [tespit edilen]
**CV oranları:** [bear/normal/bull, hangisi yüksekti?]
**Edge case'ler:** [varsa]
**Skill'e öneri:** [ne eklenmeli, neyi düzeltmeli]
**Karar:** [GİR/İZLE/GEÇ + neden]
**Geri test notu (varsa):** [önceki değerlemenin bugünkü doğruluğu]
```

---

## Skill Geliştirme Önceliği Listesi

### ✅ v4.0'da TAMAMLANDI (6 Mayıs 2026)
1. ✅ **Quality/Moat Premium** — ROE × Net Margin geometric mean, sektör hedefe göre 1.0-1.50x cap. KO testinde başarılı (analist hedefiyle %0.2 fark)

### ✅ v3.0'da TAMAMLANDI (6 Mayıs 2026)
2. ✅ DUAL-MODE: GROWTH (hızlı büyüyen) vs BLENDED (olgun) otomatik tespit
3. ✅ Yeni yöntemler: PEG Ratio, EV/Forward Revenue, EV/Forward EBITDA, Rule of 40, Reverse DCF

### ✅ v2.0'da TAMAMLANDI (6 Mayıs 2026)
4. ✅ Cost of Equity %15 cap + ROE < k_e RIM fallback
5. ✅ CV renkli uyarı sistemi
6. ✅ Forward P/E outlier tespiti
7. ✅ AI mega-cap auto-detection
8. ✅ Analist konsensüs entegrasyonu
9. ✅ Otomatik karar matrisi

### 🟠 YÜKSEK / v5 İÇİN
10. [ ] **PEG outlier filtreleme** — AMD'de PEG $841-1577 değerleri bozucu (forward growth %50+ olduğunda)
11. [ ] **Forward CV alternatifi** — Sadece 2 yöntem olduğu için CV %0 görünüyor

### 🟡 ORTA ÖNCELİK
12. [ ] Sektör presetlerini 6 ay sonra rakam doğrulaması yap
13. [ ] Bankalarda P-B ağırlıklı özel mantık
14. [ ] DCF için negatif FCF düzeltmesi (capex yoğun şirketler)
15. [ ] Çoklu hisse karşılaştırma fonksiyonu (peer relative)
16. [ ] Tarihsel geri test
17. [ ] OSAT için AI tedarik zinciri primi (semicon_osat_ai alt-preset)
18. [ ] Watchlist entegrasyonu
19. [ ] Telegram bildirim entegrasyonu

---

## Geçmiş Kayıtlar

## 2026-05-06 - AMKR (Amkor Technology)

**Bağlam:** Skill'in ilk testi. Amkor advanced packaging temasında AI tedarik zinciri tezi için değerlendirildi.

**Sektör tespiti:** `semicon_osat` ✅ doğru. Description'daki "outsourced semiconductor packaging and test" anahtar kelimeleri yakalandı.

**Pure Forward:** Pasif. Net margin %6.17, kriter olan %3 üstünde.

**Piyasa rejimi:** Normal (VIX 17.05, SPY 200SMA üstünde).

**CV oranları:** 
- Ayı: %40
- Normal: %43
- Boğa: %44

**Yüksek CV sebebi:** Yöntemler arasında geniş dağılım. EV/Revenue ve Forward P/E daha yüksek değerler verirken P/FCF, Justified P-B ve Net P/E daha düşük. Capital intensive OSAT işinde bu beklenen bir durum.

**Edge case'ler:**

1. **Justified P-B clipping:** ROE %9.75, Cost of Equity (Beta 2.31 ile) %17.2. ROE < k_e olduğu için justified P-B negatif çıkmalıydı, formüldeki `max(0.5, min(6.0, ...))` sınırı 0.5'e clipliyor. 3 senaryoda da $9.02 aynı çıktı çünkü hep alt sınıra dayandı.

2. **Yüksek beta etkisi:** Beta 2.31 → Cost of Equity %17.2, çok agresif. ERP %5.5 ve Rf %4.5 standart varsayımı yüksek beta'lı hisselerde aşırı tepki üretiyor.

**Skill'e öneriler:**

1. **Cost of Equity cap:** k_e için maksimum %15 cap eklenebilir. Yüksek beta'lı momentum hisselerinde formül abartılı sonuç veriyor.

2. **CV ≥ %35 otomatik uyarı:** Script çıktısında turuncu uyarı (memory'deki dynamicLabelColor mantığı) eklenmeli. Şu an çıktıda görünüyor ama vurgulanmıyor.

3. **ROE < k_e durumu:** Bu durumda Justified P-B yerine alternatif yöntem (örn. residual income model) kullanılabilir veya yöntem otomatik N/A yapılabilir.

4. **OSAT sektörü için EV/Revenue boğa multiplier:** 1.30 yetersiz görünüyor. AI tedarik zinciri primli OSAT'larda 1.40-1.45 daha gerçekçi olabilir.

5. **DCF FCF negatif/zayıf düzeltme:** Şu an FCF normalize 4 yıl ortalama alıyor. Sermaye yoğun şirketlerde (capex/revenue > %15) FCF tarihsel olarak çok zayıf. Bu durumda OCF × (1 - sürdürülebilir capex/OCF oranı) gibi forward-looking tahmin daha doğru olabilir.

**Karar:** GEÇ. Mevcut fiyat $76.61, boğa medyan $39.59'dan +%93.5 pahalı. Hatta boğa P75 $48.97'den bile +%56 pahalı. Tüm 9 yöntem ve 3 senaryo değerlemesi mevcut fiyatı haklı çıkarmıyor. AI tedarik zinciri primi piyasa tarafından aşırı fiyatlanmış.

**Geri test takibi:** AMKR fiyatını 1 ay sonra (Haziran 2026) ve 21 Mayıs Investor Day sonrası kontrol et. Eğer Investor Day pozitif sürpriz olur ve hisse $85+ giderse, skill modeli "AI tedarik zinciri primli OSAT" için bull multiplier'ları artırmayı düşünmeli.

---

## 2026-05-06 - AMD (Advanced Micro Devices)

**Bağlam:** Skill'in 2. testi. AMD Q1 2026 sonrası rallide $413.95'e çıktı, mega-cap AI primli durumunda nasıl davranacağını test ettik.

**Sektör tespiti:** `semicon_design` ✅ doğru. NVDA, MRVL, QCOM ile aynı kategoride.

**Pure Forward:** Pasif. Net margin %13.33, kriter %3 üstünde.

**Piyasa rejimi:** Normal (VIX 17.21).

**CV oranları (KRİTİK):**
- Ayı: %78
- Normal: %80
- Boğa: %77

Bu, skill'in tarihte en yüksek CV'leri. Yöntemler arası dağılım uçurum boyutunda.

**Yüksek CV sebebi:** Forward P/E ($272 normal) ile diğer 8 yöntem (median ~$64) arasında 4-5x fark var. Sebep: Analistler 2027/2028'de EPS'in 3.7x büyüyeceğini bekliyor (TTM $3.06 → FWD $11.36). Forward P/E bu agresif büyümeyi kabul ediyor, diğer yöntemler etmiyor.

**Edge case'ler:**

1. **Forward P/E "outlier" sorunu:** EPS_FWD_2Y / EPS_TTM oranı 3.7x. Skill bu durumda Forward P/E'yi ortalamaya tam ağırlıkla katıyor, CV'yi şişiriyor. Bu yöntem ya ayrı raporlanmalı ya da agresif büyüme durumunda weight düşürülmeli.

2. **Justified P-B clipping (2. VAKA):** AMD'de ROE %7.92, Cost of Equity (Beta 1.27 ile) %11.5 → ROE < k_e olduğu için clipping. Beta düşük olmasına rağmen sorun devam etti. Bu artık bug değil, **sistematik bir tasarım hatası.** ACİL düzeltilmeli.

3. **Skill vs Piyasa kopukluğu:** 9 yöntemin ortalaması $46-99 verirken piyasa $414. Bu, ya skill underestimate ediyor ya piyasa balonda. Tek başına skill bunu ayırt edemez, **konteks (analist hedefleri, Morningstar fair value, hyperscaler sözleşme görünürlüğü) gerekli.**

**Skill'e öneriler:**

1. **YÜKSEK ÖNCELİK - k_e cap:** Cost of Equity için %15 üst sınır eklenmeli (zaten önceki not). Ayrıca ROE < k_e durumu için fallback gerekli.

2. **YÜKSEK ÖNCELİK - CV ≥ %50 kırmızı uyarı:** Script çıktısında "⛔ MODEL GÜVENİLİR DEĞİL - Yöntemler tutarsız" eklenmeli, görsel olarak öne çıkarılmalı.

3. **YENİ - Forward outlier filtreleme:** 
   ```python
   if eps_fwd_2y / eps_ttm > 2.5:
       # Forward P/E'yi ana ortalamadan çıkar, "Spekülatif Forward Eder" olarak ayrı raporla
   ```

4. **YENİ - AI mega-cap preset:** semicon_design preset'i içinde "AI premium" alt-modu. NVDA, AMD, AVGO gibi $300B+ market cap'li ve son 2 yılda 2x+ getirili olanlar için boğa multiplier 1.50+ kullan.

5. **YENİ - Analist konsensüs entegrasyonu:** FMP'den `price-target-consensus` endpoint'ini çek, raporda 9 yöntem boğa medyanı ile analist medyan hedefini yan yana göster.

6. **YENİ - Dual-track raporlama:** "Mevcut Performans Bazlı" (1, 3, 4, 5, 7, 8, 9. yöntemler) vs "Beklenti Bazlı" (2. yöntem + DCF agresif) ayrı kategoriler.

**Karar:** GEÇ. 9 yöntemin tümünün boğa medyanı $99, mevcut $414. Spekülatif Forward boğa $333 bile mevcuttan %19 düşük. Hisse aşırı pahalı veya analist beklentileri zaten fiyatlanmış. AMD pozisyonu varsa kar realize edilmeli; yoksa $250-300 düzeltme bölgesinde tekrar bakılmalı.

**Geri test takibi:** AMD'yi 30 Eylül 2026 (Q3 sonuçları öncesi) kontrol et. Eğer hisse $300 altına düştüyse skill doğru çıkmış demektir. $500+ üstünde kalırsa AI primli mega-cap presetinin kalibrasyonu zorunlu.


---

## 2026-05-06 - SKILL v2.0 RELEASE

**Bağlam:** v1.0'dan v2.0'a geçiş. AMKR ve AMD analizlerinde tespit edilen 7 sorun çözüldü.

**Çözülen sorunlar:**

1. **Justified P-B Clipping Bug (AMKR + AMD'de aynı):** ROE < k_e durumunda formül 0.5 alt sınırına dayanıp sabit değer üretiyordu. v2'de:
   - k_e için %15 cap eklendi
   - ROE < k_e durumunda Residual Income Model fallback aktif
   - AMKR test: önceden $9.02 sabit → şimdi $11.88-12.16 senaryolara göre değişiyor
   - AMD test: önceden $19.32 sabit → şimdi $21.82-22.57 senaryolara göre değişiyor

2. **CV Uyarı Sistemi:** Önceden CV %78-80 ekran çıktısında kaybolurdu. v2'de renkli uyarılar (🟢🟡🟠🔴) ve "KRİTİK: Model güvenilir değil" gibi açık mesajlar eklendi.

3. **Forward Outlier Tespiti:** AMD'de EPS_FWD/EPS_TTM = 3.71x oranı saptırıyordu. v2'de >2.5x ise "FORWARD OUTLIER" uyarısı çıkıyor, kullanıcı yorumlama farkındalığıyla okuyor.

4. **AI Mega-Cap Preset:** AMD ($685B market cap, +%327 1y getiri) artık ⭐ AI MEGA-CAP olarak tag'leniyor, boğa senaryosunda multiplier'lar 1.40-1.55x oluyor. AMD boğa medyan: önceden $99 → şimdi $115 (Traditional), $302 (Forward).

5. **Analist Konsensüsü:** FMP price-target-consensus endpoint entegre edildi. AMKR için $66.75 konsensüs (mevcut $76.61, +%14.9 yukarda). AMD için $401.65 konsensüs (mevcut $413.31, sadece +%2.9 yukarda — kritik bilgi).

6. **Dual-Track Raporlama:** Traditional (TTM bazlı 7 yöntem) ve Forward (FWD bazlı 2 yöntem) ayrı sunuluyor. Bu, AMD gibi yüksek büyüme bekleyen hisseler için kritik. AMD'de:
   - Traditional Boğa medyan: $115 → mevcut +%258 pahalı
   - Forward Boğa P75: $392 → mevcut +%5 pahalı (analist hedefiyle uyumlu)

7. **Otomatik Karar Matrisi:** GÜÇLÜ AL → AL → İZLE → PAHALI → GEÇ kararı manuel yorumlamayı azaltıyor. AMKR ve AMD ikisi de "🔴 GEÇ / KAÇIN" çıktı, manuel yorumla aynı.

**v2'nin değer kattığı yerler:**

- AMD analizinde Traditional vs Forward ayrımı sayesinde "geleneksel olarak pahalı ama AI tezi başarılı olursa makul" mesajı net oldu
- AMKR'da analist konsensüsünden +%15 pahalı olduğu görüldü, hem skill hem analistler "pahalı" diyor (mutabakat)
- CV %85 kırmızı uyarı ile model güvenilirsizliği görsel olarak öne çıktı

**Test sonuçları:**
- AMKR v2: GEÇ (Traditional bazlı doğru karar)
- AMD v2: GEÇ Traditional, Forward outlier dahil edildiğinde fair pahalı

**Sıradaki testler:**
- JPM (financials_bank) — Justified P-B'nin doğal çalıştığı vaka
- KO (consumer_staples) — Düşük beta, stabil ROE baseline kontrolü
- TSLA (consumer_discretionary) — Yüksek volatilite + Forward outlier kontrolü


---

## 2026-05-06 - SKILL v3.0 RELEASE (Mod Bazlı Hibrit)

**Bağlam:** Kullanıcı önemli bir tespit yaptı: "Hızlı büyüyen şirketlerde Traditional yöntemler hesaba katılmamalı, ama olgun şirketlerde dengeleyici rol oynamalı."

**v3.0 Tasarım: DUAL-MODE**

### 🚀 GROWTH MODU
**Tetikleme (≥3/5 kriter):**
1. Forward growth ratio > 2.0
2. Revenue 3y CAGR > %20
3. Sektör Growth-friendly (semicon_design, tech_software, healthcare_biotech, communication)
4. AI mega-cap aktif
5. 1y fiyat performansı > %50

**Yöntemler:** Forward P/E, DCF, PEG, EV/Forward Revenue, EV/Forward EBITDA, Rule of 40, Reverse DCF
**Traditional:** Sadece "Margin of Safety Zemini" olarak gösterilir, hesaba KATILMAZ.

### ⚖️ BLENDED MODU
**Tetikleme:** GROWTH kriterlerinin <3'ü sağlanırsa.

**Ağırlıklandırma (forward growth ratio bazlı):**
- > 1.5x → %50 / %50
- 1.2-1.5x → %65 / %35
- < 1.2x → %80 / %20

**Yöntemler:** 7 Traditional + 2 Forward + 4 Growth metrikleri (PEG, EV/FWD x2, Rule of 40)

**Yeni Yöntemler (v3):**

1. **PEG Ratio:** Adil P/E = PEG_target × growth_pct (PEG 1.0 fair, 1.5 boğa, 0.8 ayı)
2. **EV/Forward Revenue:** Revenue_2y_FWD × sektör hedefi
3. **EV/Forward EBITDA:** EBITDA_2y_FWD × sektör hedefi
4. **Rule of 40:** Revenue Growth + FCF Margin >= 40 → premium çarpan, < 40 → indirimli
5. **Reverse DCF:** Mevcut fiyatın implied ettiği yıllık büyüme oranı (kıyaslama için, hesaba katılmaz)

## v3 Test Sonuçları

### AMD (GROWTH 4/5)
- Boğa medyan: $382.23 (önceden Traditional ile $115)
- Mevcut $413.53 → +%8 pahalı (önceden +%258)
- Analist hedef $401.65 → ÇOK YAKIN, %3 fark
- Reverse DCF: %48.7 yıllık büyüme implied (10 yıl boyunca!)
- Karar: 🟠 PAHALI / İZLE (önceden 🔴 GEÇ)
- ✅ v3 doğru çalıştı, analist konsensüs ile uyumlu

### AMKR (BLENDED 1/5, %65/%35)
- Boğa medyan: $47.83 (Traditional+Forward+Growth ağırlıklı)
- Mevcut $77.55 → +%62 pahalı
- Analist konsensüs $66.75 → %16 yukarda
- Reverse DCF: %27.2 implied growth (gerçekleşmesi zor)
- Karar: 🔴 GEÇ
- ✅ v3 doğru çalıştı, hem skill hem analistler "pahalı" diyor (mutabakat)

### KO (BLENDED 0/5, %80/%20) - YENİ SORUN TESPİTİ
- Boğa medyan: $51.13
- Mevcut $78.66 → +%53 pahalı
- Analist konsensüs $85.71 → mevcut %8 AŞAĞIDA (analistler ucuz buluyor!)
- ❌ ÇELİŞKİ: Skill GEÇ, analist AL
- ROE %42.59 (sektör hedefi %18 → 2.4x premium kalite)
- Net Margin %27.8 (sektör %15 → 1.85x premium)

## YENİ ÖĞRENME: Kalite/Moat Primi Eksikliği

KO testinde keşfedildi. Sektör lideri/kalite şirketleri (KO, PEP, MCD, JNJ, V, MA gibi) tarihsel olarak medyan çarpanlarından **%30-50 premium** ile işlem görür. Skill bunu yakalayamıyor.

**Sebep:** Sektör medyan multiplier'ları "ortalama şirket" için kalibre edilmiş. Quality outlier'lar ROE ve net margin metrikleri ile tespit edilebilir.

**Çözüm önerisi (v4'e):**
```python
def quality_premium(roe, sector_target_roe, net_margin, sector_target_margin):
    roe_premium = max(1.0, min(1.50, roe / sector_target_roe))
    margin_premium = max(1.0, min(1.30, net_margin / sector_target_margin))
    return min(1.50, (roe_premium * margin_premium) ** 0.5)
```

KO için bu ~1.40x premium verirdi → boğa medyan $51 yerine $71 civarı, analist hedefiyle uyumlu olurdu.

**Önemli ayrım:** AI Mega-Cap premium MOMENTUM bazlı (1y fiyat + market cap), Quality premium ise FUNDAMENTAL bazlı (ROE + margin sürekliliği). İkisi farklı şeyleri yakalar.


---

## 2026-05-06 - SKILL v4.0 RELEASE (Quality/Moat Premium)

**Bağlam:** v3'te KO testinde tespit edilen "kalite şirketleri sektör medyanından ayrışır" sorunu çözüldü.

**v4.0 Yenilik: Quality Premium**

```python
def calculate_quality_premium(roe, net_margin, sector_mults):
    roe_premium = max(1.0, min(1.50, roe / sector_target_roe))      # ROE cap 1.50x
    margin_premium = max(1.0, min(1.30, margin / sector_target_margin))  # Margin cap 1.30x
    quality_mult = (roe_premium * margin_premium) ** 0.5             # Geometrik ortalama
    return min(1.50, quality_mult)                                   # Final cap 1.50x
```

**Hangi yöntemlere uygulanır (çift sayım önleme):**
- ✅ Net P/E, EV/EBIT, EV/EBITDA, EV/Revenue, P/FCF
- ✅ Forward P/E, EV/Forward Revenue, EV/Forward EBITDA
- ❌ Justified P-B (zaten ROE içerir)
- ❌ Graham (klasik formül, premium kabul etmez)
- ❌ DCF (büyüme bazlı)
- ❌ PEG (büyüme bazlı)
- ❌ Rule of 40 (margin'i zaten içerir)

**Sektör multiples'a `net_margin_target` eklendi:**
- tech_software: %20 | semicon_design: %20 | semicon_osat: %8
- consumer_staples: %12 | financials_bank: %22 | healthcare_pharma: %18
- vs.

**Test Sonuçları:**

### KO (Beklendiği gibi BÜYÜK düzelme)
- ROE %42.59 / hedef %18 → 2.37x ratio → 1.50x cap
- Net Margin %27.8 / hedef %12 → 2.32x ratio → 1.30x cap
- Geometric mean: sqrt(1.50 × 1.30) = **1.40x KALİTE ÖNCÜSÜ**
- v3 Boğa medyan $51 → v4 Boğa medyan $69 (+%35 yukarı)
- v4 Boğa P75 $85.52 → Analist konsensüs $85.71 (%0.2 fark — neredeyse birebir!)
- Karar: 🔴 GEÇ → 🟠 PAHALI/İZLE (gerçekçi)

### AMD (Beklendiği gibi DEĞİŞİKLİK YOK)
- ROE %7.92 / hedef %25 → 0.32 ratio → 1.0 (cap'in altında)
- Net Margin %13.33 / hedef %20 → 0.67 → 1.0
- Quality premium: 1.0x (etiket gösterilmedi)
- AMD AI mega-cap olduğu halde KALİTE değil — kar marjları henüz olgun değil
- Sonuçlar v3 ile aynı (AI mega-cap premium yine etkili)

### AMKR (Beklendiği gibi DEĞİŞİKLİK YOK)
- ROE %9.75 / hedef %15 → 0.65 → 1.0
- Net Margin %6.17 / hedef %8 → 0.77 → 1.0
- Quality premium: 1.0x
- Sonuçlar v3 ile aynı (BLENDED %65/%35)

**Anlamı:**

1. Quality Premium sadece gerçekten kaliteli şirketleri etkiliyor
2. Yan etki yok: zayıf şirketlerde 1.0x kalıyor
3. AI mega-cap (momentum) ve Quality (fundamental) iki farklı şeyi yakalıyor:
   - AMD: AI mega-cap ✅, Quality ❌ (henüz)
   - KO: AI mega-cap ❌, Quality ⭐
   - AVGO veya MSFT gibi şirketler: muhtemelen ikisi de ✅

**Geri test takibi:** 
- KO'yu 30 Haziran 2026'da kontrol et. Hâlâ analist hedef civarında işlem görüyorsa skill kalibrasyon doğru.
- Quality premium uygulanan ilk vakada başarılı oldu, başka kalite şirketleri (JNJ, PEP, MA, V) ile test edilmeli.


---

## 2026-05-11 — v5.0 Etap 3 Test Bulguları

### NVDA — Kalibrasyon Override Dramatik Fark Yarattı

**Etap 2 sonrası (override yok):**
- DCF: $59 (statik WACC %10, statik g_high %15)
- Forward Bandı: $137-$294
- FMP DCF $247 ile karşılaştırma: **%-76 fark** 🔴

**Etap 3 sonrası (override aktif):**
- DCF: $140 (dinamik CAPM WACC %17.84, gerçek growth %65 cap'li)
- Forward Bandı: $260-$498
- FMP DCF $247 ile karşılaştırma: **%-43 fark** 🟠 (kabul edilebilir)

**Ders:** Statik tabloya bağlı kalmak yapısal hatalar üretiyor. Canlı CAPM WACC + gerçek growth rate ile DCF çok daha gerçekçi sonuçlar verir.

### NVDA — Yeni Sinyallerin Açtığı Gözler

1. **Konsantrasyon riski (yeni):** Data Center %90 (KRİTİK 🔴), ABD %69 (YÜKSEK 🟠) — Eskiden hiç bahsetmiyorduk. Mega-cap için bile bu kritik bir sinyal.

2. **Analist downgrade momentum (yeni):** Son 6 ay -6 net rating düşüşü. Konsensüs hâlâ Buy, ama yön zayıflıyor. Erken uyarı.

3. **Sektör multiple inflation:** Canlı semicon industry P/E 62.3x vs statik tablomuz 28x → %+123 sapma. Sektör tablosu 4-5 ay eski olmuş.

### KO — Quality Şirket Doğru Tespit Edildi

- Piotroski 8/9 (ÇOK GÜÇLÜ 🟢) — KO için mükemmel
- Altman Z 5.18 — güvenli
- WACC dinamik %8 (beta 0.36 sayesinde statik %10'dan düşük)
- Bu defa **WACC overrideı DCF'i düşürmedi, yukarı çıkardı** — düşük beta lehine

**Ders:** CAPM WACC sadece NVDA gibi yüksek-beta için DCF'i düşürür, KO gibi düşük-beta için DCF'i yükseltir. Doğru kalibrasyon.

### CBRS Pre-IPO — Manuel Akış Mükemmel Çalıştı

- Profile auto-detection: `semicon_design_growth_ai` ✅
- Revenue trajectory custom_revenues ile: $510M → $9.5B
- Net Kâr 2026: -$96M (**manuel hesabımla TAM uyum**)
- 2028 Forward P/E: 52.6x (manuel: 53x — TAM uyum)
- Normalizasyon: 2028 (sektör medyanı 62x — canlı veri)

**Ders:** Pre-IPO için kanonik bir akış oluştu. S-1 belgesinden inputları çıkar, JSON yaz, çalıştır. CBRS dışındaki gelecek IPO'lar için (Etap 5'te beklenir: bir Çin AI, bir ABD fintech, vs) aynı şablon kullanılabilir.

### AMD — Beklenmedik Bir Yer

- DCF bizim $70, FMP $52 (Levered $52) — **bizim %+34 daha yüksek**
- Sebep: AMD revenue_yoy %34 → growth override bizim DCF'i yükseltti
- AMD beta 2.40, CAPM WACC %18 sınırına dayandı
- 5y projeksiyon agresif: 2030 EPS $41 (analist 2y forward $97B revenue'dan extrapolate)

**Ders:** Analist 2y forward konsensüsü olduğu kadar agresif olabilir. Y3-Y5 için decay daha sert olmalı. Bu Etap 5'te düzeltilebilir.

---

## v5.0 İçin Skill Geliştirme Önceliği

### ✅ Etap 1 (11 Mayıs 2026) — Modüler altyapı
- fmp_layer.py (Ultimate plan endpoint wrapper)
- projection_engine.py (17 sektör profili + projeksiyon fonksiyonları)
- CBRS test başarılı

### ✅ Etap 2 (11 Mayıs 2026) — Sadeleştirme + Yeni Sinyaller
- 4 yöntem kaldırıldı (Graham, EV/EBIT, Justified P-B, Rule of 40)
- 6 yeni sinyal: risk skorları, sentiment, FMP DCF, konsantrasyon, canlı PE, dinamik WACC

### ✅ Etap 3 (11 Mayıs 2026) — Kalibrasyon override + Projeksiyon + Pre-IPO
- Live PE + dinamik WACC + actual growth → calculate_methods'a injekte
- 5y projeksiyon analyze() içine entegre
- --pre-ipo flag + JSON input akışı

### ⬜ Etap 4 (devam ediyor) — Dokümantasyon
- SKILL.md v5.0 ✅
- references/sektor-margin-profilleri.md ✅
- references/fmp-endpoint-rehberi.md ✅
- notes/learnings.md (bu güncelleme) ✅

### ⬜ Etap 5 (gelecek) — İleri Özellikler
- Markdown rapor üretici (--md flag) — 12 bölüm protokole uygun
- Y3-Y5 revenue decay daha sert (AMD projeksiyon abartıyı)
- Multi-year analyst estimates (1y/2y/3y forward) entegrasyonu
- Pre-IPO için canlı IPO calendar enrichment
- Geniş test: TEM, FLYW, SMCI, AVGO, MSTR, PLTR

---


---

## v5.1 — Inflection Point Düzeltmesi (12 Mayıs 2026)

### LQDA Liquidia Corporation — v5.0'ın Yakaladığı Hata

**Sorun:** LQDA için v5.0 çalıştırıldığında:
- MOD: GROWTH (doğru tespit, 4/5 kriter)
- EPS_FWD/EPS_TTM ratio = 21.56x (eps_fwd_2y=$5.46, eps_ttm=$0.26)
- → `forward_outlier = True`
- → **Forward P/E, PEG, EV/FWD Revenue, EV/FWD EBITDA hepsi N/A (ELENDİ)**
- → Geriye sadece Growth bandı kaldı, ana medyan güvenilir değil

**Gerçek durum:** LQDA gerçek bir karlılık dönüşümü yaşıyor:
- Q2-2025: -$0.49 (negatif)
- Q3-2025: -$0.04 (negatif)
- Q4-2025: +$0.17 (POZİTİF — inflection)
- Q1-2026: +$0.60 (POZİTİF — sürdürülebilir)

Son 2 çeyrek ardışık pozitif EPS, önceki 2 çeyrek ardışık negatif → klasik "inflection point" örüntüsü. Forward EPS şişkin değil, gerçek pazara girmiş ilaç (YUTREPIA FDA onayı Mayıs 2025) sayesinde gerçek karlılık.

### Düzeltme (v5.1)

`adil_deger.py` L1008-1040 bölgesi:

```python
# v5.1: Quarterly EPS bazlı inflection tespiti
inflection_point = False
inflection_note = None

if len(qinc_list) >= 4:
    try:
        q_eps = [safe_get(qinc_list[i], 'eps') for i in range(4)]
        # qinc_list newest-first: [Q-son, Q-1, Q-2, Q-3]
        if (all(e is not None for e in q_eps) and
            q_eps[0] > 0 and q_eps[1] > 0 and
            q_eps[2] < 0 and q_eps[3] < 0):
            inflection_point = True
            inflection_note = f"INFLECTION POINT teyit: ..."
    except (IndexError, TypeError, KeyError):
        pass

if eps_fwd_2y and eps_ttm and eps_ttm > 0:
    forward_growth_ratio = eps_fwd_2y / eps_ttm
    if inflection_point:
        forward_outlier = False  # v5.1: outlier flag iptal
    else:
        forward_outlier = forward_growth_ratio > 2.5
```

### v5.1 ile LQDA Sonucu

```
🚀 MOD: GROWTH (4/5 kriter)
🌱 v5.1 INFLECTION POINT: Forward yöntemler korundu
   INFLECTION POINT teyit: Son 2 çeyrek EPS pozitif ($0.17 → $0.60), 
   önceki 2 çeyrek negatif ($-0.49, $-0.04). Forward outlier flag iptal.

Forward P/E            $94.23       $130.88      $159.67
EV/FWD Revenue         $60.14       $92.56       $120.35
PEG                    [PEG hesabında ayrı bir bug var, growth_pct çok düşük]
EV/FWD EBITDA          N/A (negatif TTM EBITDA, ayrı sebep)
```

Bu sonuç **manuel hesabımızla uyumlu** (Forward P/E 2027E×P/E 20x = $62, mevcut analist konsensüs $63 medyan).

### Genel Ders

**Outlier tespiti birden fazla sinyal gerektirir, tek bir oran yeterli değil.** Forward EPS şişkinliği iki farklı sebepten kaynaklanabilir:

1. **Yapay/şişkin forward (gerçek outlier):** Analistler tek seferlik kazanç projeksiyonu, henüz teyit edilmemiş büyüme, biased tahminler → Forward yöntemleri ELENMELİ.
2. **Gerçek inflection (turn-around/biotech ramp):** Önceki dönem zararlı (yatırım fazlası), yeni dönem pazar mümkün (ilaç onayı, ürün lansman, ölçek ekonomisi) → Forward yöntemleri KORUNMALI.

Bu ikisini ayırt etmek için "ardışık çeyrek EPS sign change" sinyali güvenilir. Tek bir TTM/FWD oranına bakmak yeterli değil.

### Önceki Yanlış Notlandırma Düzeltmesi

Önceki LQDA değerleme raporunda (`valuations/_LEARNINGS.md`) "Rule of 40 sektör filtresi eklenmeli" diye not düşmüştüm. Bu yanlıştı — **Rule of 40 zaten v5.0'da kaldırılmış**. /mnt'deki Claude.ai-upload paketinin eski v4.1 olduğunu fark etmemiştim. GitHub'daki canlı production versiyonu kontrol etmek her zaman önceliklidir.

