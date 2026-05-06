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

1. [ ] Sektör presetlerini 6 ay sonra rakam doğrulaması yap
2. [ ] Bankalarda P-B ağırlıklı, diğer yöntemler düşük ağırlık - özel mantık eklenebilir
3. [ ] DCF için negatif FCF düzeltmesi geliştirilmeli
4. [ ] Çoklu hisse karşılaştırma fonksiyonu (peer relative) eklenebilir
5. [ ] Tarihsel geri test: 1 yıl önce değerlenen hisselerin bugünkü uyumu
6. [ ] AI primli sektörlerde boğa multiplier yetersiz olabilir (NVDA gibi)
7. [ ] **YENİ:** Cost of Equity %15 cap eklenmeli (yüksek beta hisseler için) — AMKR analizinden çıkan gözlem
8. [ ] **YENİ:** ROE < k_e durumunda Justified P-B yerine alternatif yöntem
9. [ ] **YENİ:** CV ≥ %35 turuncu uyarı script çıktısında belirginleştirilmeli
10. [ ] **YENİ:** OSAT sektörü için boğa multiplier 1.40-1.45'e güncellenebilir (AI tedarik zinciri primi varsa)
11. [ ] **YENİ:** Karar matrisi otomatikleştirilebilir (mevcut fiyat vs senaryo aralık → GİR/İZLE/GEÇ otomatik öneri)

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

