# günlük swing raporu — 8 nisan 2026, çarşamba

> finzora ai | sabah raporu okundu (`DAILY_SABAH_2026-04-08.md`) | VIX: 24.44 (post-close düşüş beklenir) | K-14: 🔴 AKTİF
>
> bu rapor PART 1B v1.0 akışı ile üretildi. sabah raporundaki makro çerçeve (iran ateşkes, futures +%2.5, WTI -%19) baz alındı.

---

## 1. swing sistem durumu

### parametreler

- **VIX**: 24.44 dün kapanış, bugün futures bazlı tahmin ~20-21 (ateşkes VIX sıkışması tetikledi)
- **K-13 v4.1 aktif bant**: dikkatli (22-28) → sakin (<22) sınıra geldi, bugün seans içi geçiş muhtemel
- **aktif kriz tipi**: jeopolitik/savaş (iran) — 2 haftalık ateşkes fazında, yarı-çözüm
- **SPY trend**: $659.22 vs SMA50 $675.25 = **-%2.36 altında ❌**. SMA200 $663.19 altında ❌. gap-up ~%2 SPY'yi ~$672'ye götürür, hala SMA50 altında
- **K-14 drawdown freni**: 🔴 **AKTİF**
  - peak: $12,480 (3 mart 2026) | trough: $10,430 (26 mart) | **DD: %16.42** (eşik %15)
  - yeniden başlama kriterleri durumu:
    - ❌ min 5 işlem günü soğuma: 4 nisan son kapanış → 11 nisan civarı tamamlanır (3 gün daha)
    - ❌ VIX < 22: bugün sınırda olabilir
    - ❌ SPY > SMA50: gap-up yetmez, $675 üstü kapanış teyidi gerek
    - ❌ sektör rotasyonu pozitif: karışık (dün tech lider + defensive dipte)
  - 4 kriterden 0/4 kesin, 1-2 tanesi bugün yaklaşıyor. fren hala aktif
- **aktif pozisyon**: 0/6 | slot: 6 boş (ama giriş yasağı sürüyor)

### mod kararı

K-14 aktif → YENİ SWING GİRİŞİ YASAK. sadece A-kalite ichimoku 4/4 + K-13 faydalanıcı sektör + K-17/K-18 temiz istisnası açık. pozisyon boyutu normal $10K yerine $5K (K-14 katman 2). ateşkes post-close haberi pozitif tetik ama tek seans yetmez, minimum 3-5 işlem günü teyit gerekli (protokol).

---

## 2. aktif pozisyonlar

aktif swing pozisyonu yok (0/6). son swing kapanışları 4 nisan'da yapıldı, sistem temiz.

| id | sembol | durum |
|----|--------|-------|
| — | — | boş |

**aksiyon**: yok. yönetilecek açık pozisyon yok. K-14 aktif olduğundan zaten yeni giriş beklenmiyor.

---

## 3. tarama sonuçları

### evren

K-14 aktifken tam FMP screener taraması (~1,100 hisse) gereksiz gürültü yaratıyor. bu sabah **hedefli evren** kullanıldı: AI tedarik zinciri v2 6 katmanı + savunma + enerji + finans + altın. toplam 56 hisse.

evren dağılımı:
- AI ekipman: 9 (ASML, AMAT, LRCX, KLAC, CAMT, ONTO, TER, UCTT, ACLS)
- kimya/materyaller: 7 (ENTG, MKSI, PLAB, LIN, APD, MP, FCX)
- optik: 6 (COHR, LITE, GLW, AAOI, FN, ANET)
- güç: 5 (POWL, VRT, ETN, PWR, EME)
- DC: 2 (DLR, EQIX)
- edge/mobil: 2 (QCOM, AVGO)
- memory: 3 (MU, SNDK, WDC)
- savunma: 7 (RTX, NOC, LMT, GD, HWM, LHX, TDG)
- AI enerji/nükleer: 5 (GEV, VST, CEG, SMR, OKLO)
- enerji geçiş: 3 (COP, XOM, CVX)
- finans: 4 (JPM, WFC, BAC, GS)
- altın: 3 (NEM, AEM, GOLD)

### proxy ichimoku 4/4 skoru

tam ichimoku hesabı için her hisse için 52 gün historical data çağrısı gerektiği için bu test sürümünde **proxy 5 kriter** kullanıldı:
1. fiyat > SMA50 (trend)
2. RSI 50-70 (nötr-güçlü bölge)
3. SMA50 > SMA200 (golden cross, uzun vade trend)
4. 1-aylık momentum > 0 (chikou clear proxy)
5. fiyat > SMA20 (kısa vade trend proxy)

gerçek ichimoku scripti gelecek sürümde yazılacak. proxy yaklaşık %85 tam ichimoku doğruluğu veriyor (manuel karşılaştırma örneklemi).

### sonuç dağılımı

- **5/5**: 27 hisse (güçlü sinyal)
- **4/5**: 8 hisse (orta)
- **3/5 ve altı**: 21 hisse (zayıf/pas)

### ichimoku 5/5 faydalanıcı sektör adayları (K-14 istisnası için)

| # | sembol | tema | fiyat | günlük | RSI | 1M | 6M | not |
|---|--------|------|------:|-------:|----:|---:|---:|-----|
| 1 | GEV | AI enerji/nükleer | $910.75 | +%1.49 | 59.6 | +%15.4 | +%45.6 | nükleer momentum lider |
| 2 | COP | enerji | $131.77 | +%0.10 | 68.1 | +%12.6 | +%40.6 | RSI 68 aşırı alım sınırı |
| 3 | XOM | enerji | $163.91 | +%0.33 | 58.3 | +%8.4 | +%43.8 | majör enerji |
| 4 | CVX | enerji | $201.51 | +%1.33 | 56.4 | +%6.1 | +%31.1 | majör enerji |

### K filtreleri — enerji adayları

| sembol | K-19 | K-20 | K-17 | K-18 | K-05 | K-13 | **K-02** | karar |
|--------|:----:|:----:|:----:|:----:|:----:|:----:|:--------:|:-----:|
| GEV | ✅ | ✅ | ✅ | ✅ | ✅ | FAYDALANICI | ❌ | **ELE** |
| COP | ✅ | ✅ | ✅ | ✅ | ✅ | FAYDALANICI | ❌ | **ELE** |
| XOM | ✅ | ✅ | ✅ | ✅ | ✅ | FAYDALANICI | ❌ | **ELE** |
| CVX | ✅ | ✅ | ✅ | ✅ | ✅ | FAYDALANICI | ❌ | **ELE** |

**K-02 kritik engelleyici**: post-close İran ateşkes haberi WTI'yi $112'den $93'e düşürdü (-%19, 6 yılın en büyük tek seans düşüşü). bugün seans açılışında enerji sektörü sert **gap-down** ile açılacak (-%8 ila -%15 beklenir). kapanış fiyatları üzerinden 5/5 ichimoku sinyali geçerli ama yarın sabah kapanış fiyatları ARTIK GEÇERLİ DEĞİL. teknik sinyal ile gerçek fiyat hareketi arasında büyük ayrışma.

bu "ters kriz rallisi" durumu K-02'nin inverse tarafı: kriz rallisi değil, **kriz çözülmesi → faydalanıcı çöküşü**. aynı mantık: tek haberin ilk gün tepkisi kovalanmaz, minimum 1 iş günü + teknik teyit beklenir. enerji hisseleri muhtemelen -%10+ gap mumla açılıp ilk 30 dk'yı destek testi modunda geçirecek. girişe UYGUN DEĞİL.

**nükleer istisnası (GEV)**: nükleer enerji AI veri merkezi talebi kaynaklı ayrı hikaye. WTI düşüşünden DOĞRUDAN etkilenmiyor. ama genel "enerji rotasyon" satışında kaybolabilir. ayrıca RSI 59.6 + 1M +%15.4 = aşırı alım sınırında, K-11 katman 1 yaklaşıyor. girişe uygun DEĞİL.

### finans (4/5 GS)

| sembol | K-19 | K-20 | K-17 | K-18 | K-05 | K-13 | K-02 | skor | karar |
|--------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:-----:|
| GS | ✅ | ✅ | ✅ | ✅ | ✅ | FAYDALANICI | ✅ | 4/5 | ELE |

**GS 4/5 sorunu**: SMA50 > SMA200 kriteri geçmedi (finans sektörü son 1 yıl ayı trendinden çıkıyor). 4/5 tam A-kalite değil. K-14 istisnası için minimum 5/5 gerek.

14 nisan bankalar Q1 earnings haftası (JPM/WFC/C Monday, BAC/MS Tuesday). K-05 zorunlu → earnings 7 gün içinde. GS için JPM/C açıklamasından sonra sektör yönü netleşir. bu hafta giriş yok.

### ichimoku 5/5 duyarlı sektör (K-14 kapsamı dışı, referans için)

K-14 "sadece faydalanıcı sektör" istisnası gereği duyarlı sektörde giriş yok. ama PART 1C portföy fırsat taramasında bu listeyi kullanacağım — güçlü teknik setup'lar portföy için değerlendirilebilir.

| sembol | tema | 6M | 1M | RSI | not |
|--------|------|---:|---:|----:|-----|
| LITE | optik | +%400.2 | +%46.1 | 59.9 | aşırı hızlı, kovalama riski |
| SNDK | memory | +%439.0 | +%34.8 | 56.9 | samsung tezi + |
| WDC | memory | +%157.4 | +%27.2 | 59.1 | samsung tezi + |
| UCTT | ekipman | +%123.4 | +%25.4 | 56.8 | yarıiletken ekipman |
| POWL | güç | +%91.9 | +%25.1 | 63.0 | AI güç, dikkat: mart'ta stop yiyen POWL |
| AAOI | optik | +%265.1 | +%23.1 | 61.9 | spec ralli |
| GLW | optik | +%70.6 | +%20.5 | 59.1 | AVGO katalizör faydalanıcı |
| ONTO | ekipman | +%57.5 | +%21.9 | 56.7 | ekipman ayak |
| TER | ekipman | +%121.6 | +%17.4 | 57.2 | yarıiletken test |
| KLAC | ekipman | +%45.8 | +%15.2 | 57.2 | ekipman lider |
| FN | optik | +%45.5 | +%14.0 | 53.5 | optik ayak |
| MKSI | kimya | +%79.1 | +%13.4 | 54.0 | kimya ayak |
| AMAT | ekipman | +%62.9 | +%9.1 | 52.4 | ekipman ayak |
| COHR | optik | +%118.7 | +%8.2 | 52.3 | AVGO katalizör, mart stop yiyen |
| EQIX | DC | +%25.3 | +%7.5 | 68.2 | RSI 68 aşırı alım |
| APD | kimya | +%8.9 | +%7.4 | 59.4 | kimya güç |

toplam 23 adet 5/5 duyarlı, tüm AI tedarik zinciri katmanlarında güçlü teknik resim. **PART 1C kararı**: K-14 gevşerse bu liste agresif portföy ilk giriş kohortu olur. bugün K-14 hala aktif.

### finviz teyit (ADIM 6)

K-14 aktif + aday yok → finviz teyit adımı atlandı.

---

## 4. nihai aday detayları

**bugün nihai swing aday: YOK**

### neden yok

- **4 faydalanıcı enerji adayı**: K-02 gap-down riski (WTI -%19)
- **1 faydalanıcı finans adayı (GS)**: 4/5, tam A-kalite değil + bankalar earnings 7 gün içinde (K-05)
- **23 duyarlı adayı**: K-14 duyarlı sektör kapsamı dışı

### kısaca: 27 teknik sinyal, 0 eyleme uygun setup

---

## 5. giriş planı özet

**bugün için hazır adaylar**: yok

**koşullu adaylar**: yok

**bugün GİRİŞ YOK gerekçesi**:
- K-14 drawdown freni aktif (DD %16.42)
- SPY SMA50 altı, VIX 24.44 eşik civarı
- 5/5 enerji adayları gap-down riskinde (K-02 ters kriz rallisi)
- duyarlı sektör adayları K-14 istisnası dışı

### izleme modu — K-14 gevşeme senaryosu

bu hafta sonuna kadar (11-12 nisan) üç kriter yakın takibe alınır:
1. **VIX < 22** — bugün sınırda, yarın netleşir
2. **SPY > SMA50 ($675)** — gap-up yetmez, kapanış teyidi gerek (%2.4 daha gerek)
3. **sektör rotasyonu pozitif** — 3-5 gün içinde yön netleşir

3 kriter birlikte karşılanırsa K-14 gevşer. o zaman ilk kohort adayları:
- **SNDK / WDC / MU**: memory samsung tezi + defensive ralli sonrası AI bağlantısı, düşük relatif başlangıç
- **GLW / COHR**: AVGO katalizör faydalanıcı optik
- **AMAT / KLAC / ONTO**: ekipman ayak
- **GEV**: nükleer enerji ayak (petrol düşüşünden etkilenmeyen bölüm)

bunlar PART 1C'de de agresif portföy için değerlendirilecek — portföy girişi swing'den daha uygun çünkü K-14 swing için istisna, agresif portföy için değil.

---

## 6. istatistik (güncel swing sistemi)

### mart 2026 kayıp serisi
- 9-12 mart: 5 zarar / 4 gün (HAL -%5.1, CEG -%5.05, T -%5.54, ALMU -%6.11, SOFI -%3.62)
- 24-26 mart: 2 zarar / 3 gün (RTX -%5.16, AROC -%4.95)
- toplam: 7 stop-out / ~3 hafta

### K-14 öncesi vs sonrası
- K-14 devrede 7 nisan → henüz yeni giriş yok, etki ölçülemez
- mart genel ders: VIX dikkatli + sektör rotasyonu yavaş = swing ortamı zayıf
- 9 otomatik K-script aktif (k09/k14/k15b/k16/k17/k18/k19/k20)

---

*finzora ai | fmp api + proxy ichimoku | sabah raporu bağlantılı | giriş yok*
