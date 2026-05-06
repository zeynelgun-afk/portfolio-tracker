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

Kullanım arttıkça bu listeyi güncelle:

### 🔴 KRİTİK / ACİL (2+ vakada görüldü)
1. [ ] **Cost of Equity %15 cap + ROE < k_e fallback** — AMKR ve AMD'de yaşandı, sistematik bug
2. [ ] **CV ≥ %50 kırmızı uyarı** çıktıda belirginleştirilmeli — AMD %80 verdi

### 🟠 YÜKSEK ÖNCELİK (1 vakada görüldü)
3. [ ] **Forward P/E outlier filtreleme:** EPS_FWD_2Y / EPS_TTM > 2.5x ise ayrı raporla
4. [ ] **AI mega-cap preset:** Boğa multiplier 1.50+ (AMD analizinde piyasa fiyatı modeli %319 aştı)
5. [ ] **Analist konsensüs entegrasyonu:** FMP price-target-consensus endpoint
6. [ ] **Dual-track raporlama:** Mevcut performans vs Beklenti bazlı ayrı kategoriler
7. [ ] **Karar matrisi otomatikleştirilebilir** (GİR/İZLE/GEÇ)

### 🟡 ORTA ÖNCELİK
8. [ ] Sektör presetlerini 6 ay sonra rakam doğrulaması yap
9. [ ] Bankalarda P-B ağırlıklı, diğer yöntemler düşük ağırlık - özel mantık eklenebilir
10. [ ] DCF için negatif FCF düzeltmesi geliştirilmeli
11. [ ] Çoklu hisse karşılaştırma fonksiyonu (peer relative) eklenebilir
12. [ ] Tarihsel geri test: 1 yıl önce değerlenen hisselerin bugünkü uyumu
13. [ ] OSAT sektörü için boğa multiplier 1.40-1.45 (AI tedarik zinciri primli)

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

