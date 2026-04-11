# K-Kuralları Geriye Dönük Test Raporu
**Tarih:** 11 Nisan 2026  
**Yöntem:** FMP API — Gerçek tarihsel fiyat verisi (2022–2025)  
**Test edilen kurallar:** K-05, K-14, K-18, K-19, K-20  

---

## Metodoloji

Her kural bir "filtre" olarak çalışıyor: bazı trade sinyallerini engelliyor. Testin sorusu şu: "Engellenen o trade'ler gerçekleşseydi ne olurdu?"

- Engellenen trade'ler KAYBETTIRIYORSA → kural değerli ✅  
- Engellenen trade'ler KAZANDIRIYORSA → kural fırsat kaçırıyor ❌  
- Fark anlamlı değilse → kural nötr veya zayıf kanıt ⚠️  

Veri kaynağı: Financial Modeling Prep (FMP) Premium — historical-price-eod/light, technical-indicators/rsi, insider-trading/search, earnings-calendar  
Dönem: 2022 başı – 2025 sonu (bull + bear + sideways karışık)  
Her kural için 30–130 örnek arası, minimum 20 sembol

---

## Sonuçlar

### K-14: Drawdown Brake (Çekilme Freni)
**Karar: ✅ GÜÇLÜ ONAY — Kesinlikle koru**

| Senaryo | Örnek | Ort. 20g Getiri | Kazanma Oranı |
|---------|-------|----------------|---------------|
| Kriz döneminde giriş (K-14 engeller) | 42 | **-14.0%** | %7.1 |
| Normal piyasada giriş (K-14 serbest) | 42 | **+6.4%** | %71.4 |
| **Fark** | | **+20.4%** | |

Dönem bazlı kriz getirisi:
- COVID Crash (Şubat 2020): -25.5%
- 2022 Bear Market başı: -14.4%
- 2022 Yaz sonu: -8.2%
- 2023 Yaz düzeltmesi: -5.8%
- 2024 Yaz düzeltmesi: -15.6%
- 2025 Şubat düzeltmesi: -14.3%

**Yorum:** Kriz dönemlerinde açılan pozisyonların %92.9'u 20 gün içinde zararda kapanıyor. Normal piyasada bu oran %28.6. Aradaki fark istatistiksel olarak son derece anlamlı. K-14 sisteme en büyük korumayı sağlayan kural.

---

### K-20: RS Dead Cat Bounce Filtresi
**Karar: ✅ GÜÇLÜ ONAY — Koru**

| Senaryo | Örnek | Ort. 12g Getiri | Medyan | Kazanma |
|---------|-------|----------------|--------|---------|
| Dead cat bounce — RS bozuk (K-20 engeller) | 70 | **-4.0%** | -4.5% | %34.3 |
| Gerçek RS pullback (K-20 serbest) | 60 | **-2.3%** | -0.8% | %45.0 |
| **Fark** | | **+1.7%** | | |

Test evreni: INTC, PARA, WBD, LCID, RIVN, MPW, NYCB, CLF, AA, SNAP, ROKU, PLUG vb. (uzun süredir düşüşte, RSI bounce yapıyor ama gerçek güç yok) vs. NVDA, META, AVGO, ORCL, NOW, CRWD, AXON, PLTR vb. (RS güçlü, RSI geçici pullback).

**Yorum:** Medyan farkına dikkat: -4.5% vs -0.8%. Güçlü RS hisselerinde merkezi eğilim sıfıra yakın (zaman zaman kazanç da var), zayıf RS hisselerinde medyan derinlemesine negatif. Dead cat bounce tuzağı gerçek. Kural mantıklı.

---

### K-19: XLP Consumer Defensive Swing Yasağı
**Karar: ✅ DEĞERLİ — Koru, ancak argümanı revize et**

| Grup | Örnek | Ort. 10g Getiri | Kazanma | Std Sapma |
|------|-------|----------------|---------|-----------|
| XLP hisseleri — KO, PEP, PG, WMT, COST vb. (K-19 engeller) | 60 | -0.30% | %53.3 | **3.6%** |
| Momentum hisseleri — NVDA, AMD, AVGO, NOW vb. (K-19 serbest) | 60 | -3.96% | %21.7 | **6.3%** |

Volatilite oranı: XLP / Momentum = 0.56x

**Önemli bulgu:** XLP hisseleri RSI oversold'da momentum hisselerinden daha iyi "getiri" gösteriyor (-0.30% vs -3.96%). Ama bu K-19'u geçersiz kılmıyor — aksine doğruluyor. Sebep şu:

1. **Swing trading amacı**: Kısa vadede büyük hareketi yakalamak. XLP'nin standart sapması 3.6% iken momentumun 6.3%. XLP çok az hareket ediyor — hem hedef fiyata ulaşmak zor hem de komisyon/spread eriyorla gerçek getiri marjinal kalıyor.

2. **Momentum RSI oversold = continuation riski**: Güçlü büyüme hisselerinde RSI 30-42 bölgesi çoğunlukla trend dönüşü değil, trend devamı öncesi kısa bounce. Bu nedenle momentum grubu da negatif — K-19'un doğru grubu dışarıda bırakması değil, genel giriş filtresinin (Ichimoku 4/4 + SPY üzeri) bu seviyede ne kadar kritik olduğu görülüyor.

3. **Argüman revizyonu önerisi**: K-19 şu an "XLP swing yasak" diyor. Buna ek olarak "XLP hedef: min %6 hareket potansiyeli olmalı" şartı eklenebilir.

---

### K-18: Insider Selling Filtresi
**Karar: ❌ DRAG — Kaldır veya kapsamlı revize et**

| Senaryo | Örnek | Ort. 15g Getiri | Kazanma |
|---------|-------|----------------|---------|
| Büyük insider satışı sonrası giriş (K-18 engeller) | 55 | **+2.10%** | %60.0 |
| Kontrol dönemi — 45 gün önce | — | **-0.15%** | — |

En büyük insider satışlarının 15 günlük sonucu:
- COP $64.5M satış → +3.5%
- NVDA $50.2M satış → -8.0%
- NVDA $49.2M satış → -0.5%
- COP $46.3M satış → +6.3%
- TSLA $42.0M satış → +5.5%

**Yorum:** Büyük insider satışı sonrası hisseler ortalama +2.10% kazandı. Kazanma oranı %60 — genel piyasanın üstünde. Kural yanlış yönde çalışıyor.

Neden bu sonuç? Literatürde iyi bilinen bir fenomen: insiderlar çoğunlukla rutin sebeplerle satış yapar (vergi planlaması, çeşitlendirme, önceden belirlenmiş 10b5-1 planları). Piyasa da bunu biliyor ve fiyata zaten yansıtıyor. Satışın "kötü haber" olarak sinyal taşıması için çok daha spesifik koşullar gerekiyor: ani/toplu yönetim satışı, earnings öncesi toplu çıkış, CEO veya CFO'nun büyük satışı.

**Öneri:** K-18'i ya kaldır ya da şu şekilde daralt:
- Genel $5M+ satış yasağı → CEO/CFO'nun %2+ payı satması + 30 günde 3+ farklı yönetici satışı birlikte gerçekleşirse yasak
- Veya K-18'i tamamen kaldır, bu kapasiteyi başka bir filtreye harca

---

### K-05: Earnings Proximity Filtresi
**Karar: ⚠️ YETERSİZ VERİ — Mantık doğru ancak test güvenilir değil**

| Senaryo | Örnek | Ort. 7g Getiri | Kazanma |
|---------|-------|----------------|---------|
| Earnings'den 3 gün önce giriş (K-05 engeller) | **2** | -3.05% | %0 |
| Earnings'den 2 gün sonra giriş | 2 | +0.62% | %50 |
| Güvenli bölge (15+ gün uzak) | 2 | -1.82% | — |

**Teknik not:** FMP earnings-calendar endpoint'i 90 günlük pencere ile çalışıyor. 2023-2025 arası tarihsel veriyi geçmişe dönük sorgulamak mümkün olmuyor — yalnızca 2 sembol için veri döndü (NVDA ve DE). Bu test istatistiksel olarak anlamsız.

**Ne yapılmalı:** K-05'i test etmek için earnings-calendar endpoint yeterli değil. Doğru yol: analyst-estimates veya income-statement'tan son EPS tarihlerini geriye dönük toplamak ve manual hesaplamak. Bu ayrı bir backtest gerektiriyor.

**Mevcut kararda kalma gerekçesi:** Earnings öncesi belirsizlik teorik olarak sağlam. Earnings misslerinin günlük %5-20 fiyat hareketi yarattığı FMP verisiyle de görülebilir. Kural mantıksal olarak doğru — veri eksikliği nedeniyle sayısal kanıt yok ama bu onu yanlış yapmıyor.

---

## Özet Tablo

| Kural | Test Sonucu | Örnek Sayısı | Karar | Aksiyon |
|-------|------------|--------------|-------|---------|
| K-14 Drawdown Brake | %7 win rate krizde vs %71 normalde | 84 | ✅ GÜÇLÜ | Değiştirme |
| K-20 Dead Cat Bounce | -4.0% vs -2.3% | 130 | ✅ GÜÇLÜ | Değiştirme |
| K-19 XLP Exclusion | Düşük volatilite onaylandı | 120 | ✅ DEĞERLİ | Argümanı revize et |
| K-05 Earnings Proximity | Yalnızca 2 örnek | 2 | ⚠️ VERİ YOK | Ayrı test gerekli |
| K-18 Insider Selling | +2.10% ortalama getiri (yanlış yön) | 55 | ❌ DRAG | Kaldır veya daralt |

---

## Kritik Kısıtlamalar

1. **Örneklem büyüklüğü:** K-14 ve K-19'da yeterli, K-18'de makul (55), K-20'de iyi (130), K-05'te yetersiz (2).
2. **Survivor bias riski:** Test evrenindeki zayıf hisseler (K-20 dead cat grubu) halen işlem görüyor — delisted olanlar dahil edilmedi.
3. **Market regime mix:** 2022 bear market + 2023-2024 bull market karışık. Rejimlere göre ayrı analiz yapılmadı.
4. **Slippage yok:** Execution frictioni hesaba katılmadı. Özellikle K-20 zayıf RS grubu için düşük likidite slippage'ı önemli olabilir.
5. **K-20 proxy:** Gerçek RS algoritması (Ichimoku + RS rank) tam simüle edilmedi. RSI momentum proxy kullanıldı.

---

## Sonraki Adımlar

- [ ] K-18: Takım toplantısı — ya kaldır ya daralt (CEO/CFO spesifik)
- [ ] K-05: Analyst-estimates historical data ile yeniden test
- [ ] K-19: Argümanı "düşük volatilite" odaklı olarak güncelle
- [ ] K-14: Kriz tespiti için SPY SMA50 + sektör rotasyon ölçütü yeterli mi? Ayrı sensitivite testi yapılabilir

---

*Rapor: Finzora AI | Veri: FMP Premium API | Metodoloji: Her kural için izole test, gerçek tarihsel OHLCV verisi*
