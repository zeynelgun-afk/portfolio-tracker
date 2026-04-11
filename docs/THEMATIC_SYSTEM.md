# TEMATİK PORTFÖY SİSTEMİ v1.0
> **oluşturulma**: 11 nisan 2026
> **amaç**: 3 portföyü de aktif temaya/sektöre yönlendiren, Claude'un günlük karar verdiği dinamik rotasyon sistemi

---

## FELSEFESİ

Sabit sektör allokasyonu tarihini doldurdu. VettaFi thematic rotation index 2025'te %24 kazandı (Nasdaq 100: %20, S&P 500: %16). BlackRock ve iShares, "thematic momentum rotation" stratejisini 2026'nın en güçlü alpha kaynağı olarak konumlandırıyor.

**Ana prensip:** Her dönemde bir veya birkaç tema piyasayı domine eder. Bütün portföyler o temaya yönelir. Tema değişince portföyler döner.

**Kanıt:** FactSet araştırması (2025) — top-quintile thematic funds long-only: yıllık %21+. Momentum-based thematic rotation: CAGR %25.

---

## PORTFÖY YENİ YAPILANMASI

### Ortak Çerçeve (3 portföy için)
- **Max pozisyon:** 6 (tümü için)
- **Tema uyumu:** Her portföy aktif temadan hisse seçer, ama kendi filtresiyle
- **Günlük tema kararı:** Claude her sabah TEMA_PUANI hesaplar ve yön belirler

### 1. Dengeli Portföy — $100K
- **Hedef:** Yıllık **%50+**
- **Strateji:** Aktif temadan orta-yüksek kaliteli hisseler (ROE>15, P/E<40, RS güçlü)
- **Risk:** 2×ATR stop, max %20/pozisyon
- **Tema filtresi:** Temadan lider hisse + defensive karıştırma (tema bozulursa buffer)

### 2. Agresif Portföy — $400K  
- **Hedef:** Yıllık **%80+**
- **Strateji:** Aktif temadan en yüksek momentum hisseler (RS rank üst %20, earnings beat, vol 2x+)
- **Risk:** 2×ATR stop, max %20/pozisyon
- **Tema filtresi:** Temadan sadece tier-1 hisseler — supply chain leader ya da direct beneficiary

### 3. Temettü Portföy — $100K
- **Hedef:** Yıllık **%25+** + **temettü geliri**
- **Strateji:** Aktif temadan yüksek FCF + temettü büyümesi olan hisseler (yield >%2, FCF yield >%4, D/E<1.5)
- **Risk:** Temel bozulma veya 50SMA altı kapanış
- **Tema filtresi:** Temadan defensive/cash-generative katman (enerji majörleri, savunma prime contractors, royalty şirketleri)

---

## GÜNLÜK TEMA KARARI (Claude'un sorumluluğu)

### TEMA_PUANI Hesaplama (her sabah, 5 dakika)

**7 Veri Noktası — Her biri 0-10 puan:**

```
1. MOMENTUM  (0-10): Tema ETF'i son 20 günlük RS vs SPY
   → RS20 > +5%: 10p | +2-5%: 7p | 0-2%: 5p | negatif: 2p | RS20 < -3%: 0p

2. KATALIZÖR  (0-10): Aktif haber/olay gücü
   → Çok güçlü (earnings season, politika kararı): 10p
   → Güçlü (düzenleyici onay, sözleşme): 7p
   → Zayıf (genel haber): 3p | Haber yok: 1p

3. VIX UYUMU  (0-10): VIX rejimi × sektör tipi
   → K-13 v4.1 matrisine göre: tam izin=10, yarım=6, çeyrek=3, yasak=0

4. HAREKETLİLİK (0-10): Tema ETF hacim artışı
   → 20g ortalamasının 1.5x+: 10p | 1.2x: 7p | 0.8-1.2x: 5p | <0.8x: 2p

5. GENİŞLİK (0-10): Tema içinde kaç hisse yukarı?
   → Tema hisselerinin %70+: 10p | %50-70: 7p | %30-50: 4p | <%30: 1p

6. SEKTÖR ROTASYONU (0-10): Para akışı yönü
   → Güçlü giriş (institutional flow pozitif): 9-10p
   → Nötr: 5p | Çıkış: 1-2p

7. MAKRO UYUM (0-10): Faiz/dolar/emtia konjonktürü
   → Temayı doğrudan destekliyor: 9-10p | Nötr: 5p | Zıt: 1-2p
```

**Toplam max: 70 puan**

| Puan | Karar | Portföy Aksiyonu |
|------|-------|-----------------|
| 56-70 | 🟢 GÜÇLÜ — Temayı genişlet | Nakit varsa yeni pozisyon aç, mevcutları büyüt |
| 42-55 | 🟡 DEVAM — Mevcut pozisyonları koru | Yeni giriş temkinli, stop'ları sık |
| 28-41 | 🟠 ZAYIFLAMA — Küçül | Kısmi kar al, stop'ları sıkılaştır |
| <28  | 🔴 DÖNDÜR — Tema bitti | Pozisyonları kapat, yeni temayı ara |

---

## AKTİF TEMA LISTESI (Claude günlük değerlendirir)

Sistem şu an **7 ana temayı** takip eder. Her biri için TEMA_PUANI hesaplanır. En yüksek puanlı tema "aktif tema" olur.

```
TEMA-1: AI ALTYAPI          → NVDA, AVGO, ANET, MRVL, CRDO, CIEN
TEMA-2: SAVUNMA/JEOPOLİTİK → LMT, RTX, NOC, GD, HII, KTOS, PLTR
TEMA-3: ENERJİ/HAM MADDE   → XOM, CVX, COP, EOG, SLB, FCX, NEM
TEMA-4: SAĞLIK/BİYOTEK     → LLY, ABBV, VRTX, REGN, MRNA, UNH
TEMA-5: FİNANS/BANKALAR    → JPM, GS, MS, V, MA, SOFI (faiz+kredi döngüsü)
TEMA-6: İNŞAAT/ALTYAPI     → CAT, DE, VMC, MLM, PRIM, POWL
TEMA-7: TÜKETİCİ/TİCARET   → AMZN, COST, HD, MCD, SBUX, NKE
```

**Tema ekle/çıkar:** VettaFi, BlackRock ve iShares thematic ETF akışları izlenerek. Claude haftalık değerlendirme yapar.

---

## TEMA ROTASYON KURALLARI

**Rotasyon tetikleyicileri (OTOMATIK):**
- TEMA_PUANI 3 ardışık gün <28 → zorunlu tema değerlendirmesi
- Aktif tema RS20 < -5% → kırmızı alarm, rotasyon değerlendirmesi
- Alternatif temada TEMA_PUANI >60 iken aktif tema <35 → derhal rotasyon

**Rotasyon prosedürü:**
1. Aktif tema pozisyonları → K-06/K-07 kurallarına göre kademeli çıkış (stop üstü varsa tut, yoksa sat)
2. Yeni tema → önce araştırma ajanı çalıştır (bkz. SECTOR_AGENTS.md)
3. Yeni temadan hisse taraması → portföy başına max 2 yeni giriş/gün (K-17)
4. Geçiş süresi max 3 iş günü

**Geçiş döneminde koruma:**
- Eski tema: stop'lar sıkılaştırılır (chandelier 2×ATR'ye geç)
- Yeni tema: ilk giriş yarım pozisyon, teyit gelince tam

---

## PORTFÖY × TEMA MATRİSİ

Her portföy temadan farklı katmanı seçer:

| Tema Katmanı | Dengeli | Agresif | Temettü |
|---|---|---|---|
| Tier 1 — Doğrudan faydalanıcı | ✅ Ağırlıklı | ✅ Ağırlıklı | ⚡ Seçici |
| Tier 2 — Tedarik zinciri | ✅ Seçici | ✅ Ağırlıklı | ❌ Genellikle hayır |
| Tier 3 — Dolaylı faydalanıcı | ❌ Hayır | ✅ Seçici | ❌ Hayır |
| Temaya özgü defansifler | ✅ Buffer | ❌ Hayır | ✅ Ağırlıklı |

**Örnek:** Aktif tema = ENERJİ
- Dengeli: XOM (tier 1) + CVX (tier 1) + FCX (hammadde buffer)
- Agresif: COP (tier 1) + EOG (tier 2) + SLB (tier 2) yüksek momentum
- Temettü: XOM temettü ($0.99/Q) + CVX (temettü büyümesi) + NEM (altın/FCF)

---

## SABAH RUTINI — TEMA KARARI

Her sabah Part 1A'da (piyasa öncesi) Claude şunları yapar:

```
ADIM 1: VIX oku (web search), SPY EMA21 durumu
ADIM 2: Tüm 7 tema için TEMA_PUANI hesapla (FMP sector-performance + ETF fiyatları)
ADIM 3: Aktif tema puanı kontrol — düşüşte mi?
ADIM 4: Alternatif temalar yükselişte mi?
ADIM 5: KARAR → DEVAM / ZAYIFLAMA / DÖNDÜR
ADIM 6: Üst portföy için bu tema kararı ne anlama geliyor? (açık pozisyon etkisi)
ADIM 7: Seans için fırsat listesi — hangi hisseler taranacak
```

Bu karar chat'te gösterilir, Telegram'a gönderilmez (operasyonel bilgi).

---

*finzora ai | thematic system v1.0 | 11 nisan 2026*
