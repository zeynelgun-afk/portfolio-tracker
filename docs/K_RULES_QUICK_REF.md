# K-RULES HIZLI REFERANS — tek kaynak özet

> bu dosya tüm seans ve sabah promptlarında K-kural referansı olarak kullanılır.
> detaylar için → `docs/TRADING_PLAYBOOK.md` ilgili bölüm.
> amaç: prompt'larda K-kural tekrarını önlemek ve tek kaynak tutmak.

## kaldırılanlar
- **K-01**: kaldırıldı (7 nisan 2026) — K-05 ile çakışma
- **K-03**: kaldırıldı — içerik K-13 v4.1'e taşındı
- **K-08**: kaldırıldı — K-07 chandelier zaten kapsıyor
- **K-14**: kaldırıldı (11 nisan 2026) — psikoloji testi ile değiştirildi. Her giriş öncesi: "Bu girişi yarın tekrar inceleseydim, tüm kuralları tam uyguladım mı?" Drawdown geçmişi `data/swing/status.json`'da kayıtlı.
- **K-18**: kaldırıldı (11 nisan 2026) — geriye dönük test sonucu: $5M+ insider satışı sonrası hisseler ortalama +2.1% kazandı, kazanma oranı %60. Kural ters çalışıyor. İnsiderlar çoğunlukla rutin sebeplerle satar (10b5-1 planı, vergi, çeşitlendirme) ve piyasa bunu fiyatlıyor. `scripts/k18_insider_check.py` devre dışı bırakıldı.

---

## aktif kurallar (18 kural)

### giriş filtreleri

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-02** | kriz/şok başlangıcı | momentum sektörlerine 3 iş günü yeni giriş yok |
| **K-04** | SMA50+SMA200 altı | giriş yok (RSI<30 istisnası hariç), SMA50+SMA200 altı + insider yoğun → mutlak yasak |
| **K-05** | swing pozisyonu için earnings ≤2 iş günü | tam çıkış, exception yok, binary risk alma |
| **K-13** v4.1 | VIX bantları × sektör kategorisi | 4 bant × 2 kategori matrisi (faydalanıcı/duyarlı) — altta tam tablo |
| **K-13b** | VIX 28+ duyarlı sektör | ichimoku 4/4 şartıyla çeyrek pozisyon istisnası, stop chandelier 3×ATR (%5 taban yok — VIX yüksek olduğu için geniş stop gerekli) |
| **K-15a** | RSI<35 oversold | 1 gün teyit bekle (mevcut pozisyon için değil, sadece yeni giriş) |
| **K-15b** | momentum hisse (3ay >%30 + P/E neg/>50) | `scripts/k15b_dilution_check.py SYMBOL` zorunlu |
| **K-17** | korelasyon + tema çakışması | `scripts/k17_correlation_check.py SYMBOL` — 3 soru testi, tema %40 limit |
| **K-19** | XLP swing girişi | yasak — düşük volatilite (std 3.6% vs momentum 6.3%) swing hedef fiyatına ulaşmayı engeller; sadece portföy pozisyonu olarak alınabilir |
| **K-20** | sektör RS dead cat bounce | `scripts/k20_rs_filter.py` — son 3g RS negatif + bounce yanıltıcı |
| **K-ZST** | swing pozisyon 10. gün | RSI yönü + hacim + RS → 2/3 negatifse çık (bekleme yok) |
| **K-EVR** | swing aday tarama | beta(1Y) < 0.7 olan hisseyi evrenden ele; swing %10 hedefe ulaşamaz |
| **K-ATR** | giriş stop kurulumu | stop mesafesi < 2×ATR(14) ise pozisyon yarıya indir veya girme |

### çıkış disiplini

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-06** | stop tetiklendi | %100 çık, override YASAK, duygusal karar yok, K-09 ile sıralı |
| **K-06 giriş stop** | ilk giriş | `max(2×ATR(14), %5)` — sabit %5 tek başına yetersiz, K-13b modunda chandelier 3×ATR (sabit %5 taban yok) |
| **K-07** | chandelier trailing tetiklendi | %100 çık, sadece yukarı çekilir — matematik tek yön |
| **K-07 kâr kilidi** | pozisyon kârda | kâr <%7 → 3×ATR / %7-15 → 2×ATR / %15+ → 1.5×ATR |
| **K-09** | fiyat stop'a <%2 | `scripts/k09_proximity_check.py` — 4 kontrol (RSI/hacim/SPY+VIX/sektör) → 3+ negatif=EXIT_NOW, 2=WAIT, 0-1=TUT |

### portföy yönetimi

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-10** | VIX bandına göre | min savunmacı + nakit eşiği (statik alt sınır), K-13 paralel çalışır |
| **K-11 katman 1** | RSI 70+ VE kâr %15+ | kâr kilidi aktif: max(2×ATR, 20SMA altı) — K-07'ye göre öncelikli (sıkı 20SMA) |
| **K-11 katman 2** | RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) | %25-30 kısmi sat |
| **K-11 katman 3** | 50SMA altı kapanış VEYA chandelier trailing | tam çık |
| **K-12 Dengeli** | tek hisse > %25 | küçült |
| **K-12 Agresif** | tek hisse > %20 (max 6 poz) | küçült |
| **K-12 Temettü** | tek hisse > %15 (max 6 poz) | küçült |
| **K-12 sektör/tema** | toplam $600K bazlı > %40 | en zayıfı kes |
| **K-16** | portföy pozisyonu earnings 7g öncesi | `scripts/k16_sell_the_news_score.py` — skor 2-3 → %25, skor 4-5 → %50 |

---

## K-13 v4.1 sektör bazlı VIX matrisi

### sektör kategorileri (aktif kriz: jeopolitik/savaş — iran)

**faydalanıcı sektörler** (VIX'e karşı dayanıklı):
- enerji: XOM, CVX, COP, OXY, EOG, SLB
- savunma: LMT, RTX, GD, NOC, LHX, KTOS, RKLB
- altın/gümüş: GLD, SLV, NEM, GOLD, RGLD, AEM
- defansif REIT: O, WELL, VICI
- tütün/staples: MO, PM, PG, KO, PEP, CL (K-19 nedeniyle sadece portföy)

**duyarlı sektörler** (VIX'e karşı zayıf):
- tech momentum: NVDA, AMD, MRVL, AVGO, CRDO
- consumer discretionary: AMZN, TSLA, NKE, HD, LOW
- küçük/orta cap growth: IWM, MDY
- high-beta: biotech, fintech, clean energy

### VIX bant × sektör matrisi

| VIX bandı | faydalanıcı | duyarlı |
|---|---|---|
| **<22** | tam pozisyon | tam pozisyon |
| **22-28** | tam pozisyon | yarım pozisyon |
| **28-35** | yarım pozisyon | giriş yok (K-13b istisna: ichimoku 4/4 → çeyrek) |
| **35+** | çeyrek pozisyon | giriş yok |

### kriz tipi değişirse
kriz tipi değiştiğinde (pandemi/finansal/ticaret/enflasyon) faydalanıcı ve duyarlı listeleri güncellenir. `docs/TRADING_PLAYBOOK.md` K-13 bölümünde geçiş protokolü var.

---

## otomatik script'ler (K-rule)

| script | ne yapar | ne zaman çalıştır |
|---|---|---|
| `scripts/k09_proximity_check.py SYMBOL` | stop yakınlık 4 kontrol | fiyat stop'a <%2 kala |
| `scripts/k15b_dilution_check.py SYMBOL` | momentum hisse dilüsyon skoru | yeni momentum giriş öncesi |
| `scripts/k16_sell_the_news_score.py SYMBOL` | earnings 7g öncesi skor | portföy pozisyonu earnings öncesi |
| `scripts/k17_correlation_check.py SYMBOL` | sektör + tema çakışması | her yeni giriş öncesi |
| `scripts/k19_xlp_filter.py SCAN_FILE` | XLP swing elemesi | swing tarama çıktısı üzerinde |
| `scripts/k20_rs_filter.py SCAN_FILE` | dead cat bounce elemesi | swing tarama çıktısı üzerinde |

not: script'ler `_QUIET_MODE=True` varsayılanı ile çalışır. info severity telegram'a gitmez, warning/critical kritik gider. `send_k_alert(force=True)` override eder.

---


---

## K-ZST 10. gün momentum protokolü

10. günde 3 kontrol yap, 2/3 negatifse çık:

| kontrol | negatif sinyal |
|---|---|
| RSI yönü | 10. gün RSI < giriş günü RSI |
| Hacim trendi | son 3g ort. hacim < ilk 3g ort. hacim |
| Relative Strength | hisse son 5g SPY'dan zayıf (RS negatif) |

→ 2/3 negatif = **ÇIK** | 1/3 negatif = izle | 0/3 = tut

**Kanıt:** GOOGL(23g→+7.8%), XOM(15g→+5.5%), LMT(18g→+1.4%), GE(13g→+1.7%) — 4 trade'de erken çıkış optimal olurdu.

## K-EVR swing evreni beta filtresi

Beta(1Y) < 0.7 olan hisseler swing evrenine giremez.

**Evrenden çıkarılanlar (örnekler):**
- Telekom: VZ, T, TMUS
- Kamu hizmetleri: DUK, NEE, SO, EXC
- Defensif sağlık: DVA, HUM, UHS
- Büyük defensif perakende: WMT, TGT, COST
- Defensif REIT (swing): AMT, O, VICI

Bu hisseler dengeli/temettü portföyüne gönderilir.

**Kanıt:** WMT(-3.5%), T(-5.5%), DUK(+1.5%), DVA(+1.1%) — 4 trade, ortalama puan 2.25/10.

## K-ATR giriş stop mesafesi zorunlu kontrolü

```
stop_mesafe  = giris_fiyati − stop_fiyati
min_mesafe   = 2 × ATR(14)

eğer stop_mesafe < min_mesafe:
    → pozisyonu yarıya indir
    → veya girme
```

**Kanıt:** AMT(-3.4%, %1.7 mesafe), ZS(+2.5%, dar trailing), NEM(+2.1%, ATR önerisi) — 3 trade.

## kural hiyerarşisi (çakışma durumunda)

1. **K-06 stop tetiği** → her şeyin üstünde, override yasak
2. **K-07 kâr kilidi** > K-11 katman 2 (kazançlı pozisyonda K-11 sıkı, kazançsız K-07 gevşek)
3. **K-13 v4.1** > K-02 (kriz şok kuralı artık K-13 v4.1 matrisinde)
5. **K-10 portföy seviyesi alt sınır** paralel çalışır, K-13 sektör seçer
6. **K-17 tema** > K-12 sektör (anlatı tema daha dar tanım)

---

> son güncelleme: 12 nisan 2026 | finzora ai | K-14 kaldırıldı (psikoloji testi); K-18 kaldırıldı (backtest); K-ZST/K-EVR/K-ATR eklendi (3+ trade kanıtı)

---

## YENİ DÖKÜMANLAR (11 Nisan 2026)

| Döküman | İçerik |
|---------|--------|
| `docs/THEMATIC_SYSTEM.md` | Tema bazlı portföy rotasyonu, TEMA_PUANI sistemi, 7 ana tema |
| `docs/SECTOR_AGENTS.md` | Araştırma ajanları, supply chain haritası, conviction scorer |
| `docs/STOP_MANAGEMENT_V2.md` | Stepped ATR trailing, VIX bazlı çarpan, confluence stop |
| `docs/DECISION_ARCHITECTURE_V2.md` | 3 katmanlı karar sistemi, rejim adaptasyonu, bias korumaları |

## HEDEFLER (11 Nisan 2026 itibaren)

| Portföy | Sermaye | Max Poz | Hedef |
|---------|---------|---------|-------|
| Dengeli | 00K | **6** | **%50+/yıl** |
| Agresif | 00K | **6** | **%80+/yıl** |
| Temettü | 00K | **6** | **%25+/yıl + temettü** |
| Swing | Ayrı | 5 | Aylık pozitif beklenti |

## FMP API LİMİTİ DÜZELTMESİ

~~Günlük 2,500 call~~ **YANLIŞ** — Gerçek limit: **Dakikada 2,500 call, günlük limitsiz.**
Bu kritik bir düzeltmedir — API kullanımını gereksiz kısıtlamak zorunda değiliz.

> değişiklik gerektiren güncellemeler doğrudan `docs/TRADING_PLAYBOOK.md`'de yapılır, bu dosya senkron tutulur.

---

## 📊 K-kural performans analizi (11 nisan 2026)

**22 trade üzerinde otomatik analiz — `scripts/k_rule_performance.py`**

### kural uyumunun sayısal etkisi

| metrik | kural ihlali olan (8 trade) | kural uyumlu (14 trade) |
|---|---|---|
| ortalama PnL | -1.1% | +1.0% |
| win rate | %50 | %64 |
| **avantaj** | — | **+2.1% PnL farkı** |

### en sık ihlal edilen kurallar

| kural | ihlal sayısı | ana hata |
|---|---|---|
| K-zaman (15 gün) | 6 trade | GOOGL(23g), T(22g), DVA(27g), DUK(28g) |
| K-evren (swing evreni) | 7 trade | VZ, WMT, AMT, T, DUK, DVA — düşük beta |
| K-13 (VIX matrisi) | 1 trade | AROC — VIX>27'de duyarlı sektör girişi |
| K-stop (ATR mesafesi) | 1 trade | AMT — %1.7 mesafe, ATR kullanılmamış |

### onaylı sistem değişiklikleri

> aşağıdakiler veri destekli — tek kaynak bu bölüm.

**SWING EVRENİ'NDEN ÇIKARILAN:** VZ, T, TMUS, DUK, NEE, SO, DVA, WMT, TGT, COST, AMT  
(düşük beta, swing %10 hedefe ulaşamaz, temettü/değer portföyüne gönder)

**K-06 GİRİŞ STOP güçlendirildi:** min. stop mesafesi = `max(2×ATR(14), %5)` — %1.7 gibi dar mesafelerde pozisyon yarıya indir veya girme.

### zeynel onayı bekleyen kural adayları

| kod | açıklama | kanıt |
|---|---|---|
| **K-ZST** | 10. günde momentum kontrol protokolü | 4 trade (GOOGL, XOM, LMT, GE) |
| **K-EVR** | Beta>0.7 swing evren zorunlu filtresi | 4 trade (WMT, T, DUK, DVA) |
| **K-ATR** | Giriş stop mesafesi ≥ 2×ATR(14) zorunlu | 3 trade (ZS, AMT, NEM) |
| **K-KRZ** | Kriz gün-1 giriş yasağı (1 gün cooling) | 1 trade (RTX, LMT, HAL genel) |
| **K-JEO** | Jeopolitik trade'de çıkış tetikleyicisi zorunlu | 1 trade (HAL) |

> `scripts/k_rule_performance.py --all` → tam rapor + backtest sonuçları güncelleme
