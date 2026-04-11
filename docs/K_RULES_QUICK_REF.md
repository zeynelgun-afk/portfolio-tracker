# K-RULES HIZLI REFERANS — tek kaynak özet

> bu dosya tüm seans ve sabah promptlarında K-kural referansı olarak kullanılır.
> detaylar için → `docs/TRADING_PLAYBOOK.md` ilgili bölüm.
> amaç: prompt'larda K-kural tekrarını önlemek ve tek kaynak tutmak.

## kaldırılanlar
- **K-01**: kaldırıldı (7 nisan 2026) — K-05 ile çakışma
- **K-03**: kaldırıldı — içerik K-13 v4.1'e taşındı
- **K-08**: kaldırıldı — K-07 chandelier zaten kapsıyor
- **K-18**: kaldırıldı (11 nisan 2026) — geriye dönük test sonucu: $5M+ insider satışı sonrası hisseler ortalama +2.1% kazandı, kazanma oranı %60. Kural ters çalışıyor. İnsiderlar çoğunlukla rutin sebeplerle satar (10b5-1 planı, vergi, çeşitlendirme) ve piyasa bunu fiyatlıyor. `scripts/k18_insider_check.py` devre dışı bırakıldı.

---

## aktif kurallar (16 kural)

### giriş filtreleri

| kural | kısa tetik | ana aksiyon |
|---|---|---|
| **K-02** | kriz/şok başlangıcı | momentum sektörlerine 3 iş günü yeni giriş yok |
| **K-04** | SMA50+SMA200 altı | giriş yok (RSI<30 istisnası hariç), SMA50+SMA200 altı + insider yoğun → mutlak yasak |
| **K-05** | swing pozisyonu için earnings ≤2 iş günü | tam çıkış, exception yok, binary risk alma |
| **K-13** v4.1 | VIX bantları × sektör kategorisi | 4 bant × 2 kategori matrisi (faydalanıcı/duyarlı) — altta tam tablo |
| **K-13b** | VIX 28+ duyarlı sektör | ichimoku 4/4 şartıyla çeyrek pozisyon istisnası, stop chandelier 3×ATR (%5 taban yok — VIX yüksek olduğu için geniş stop gerekli) |
| **K-14** | drawdown fren aktif | yeni swing girişi yok (A-kalite istisna), ortam testi: VIX<22 + SPY>SMA50 |
| **K-15a** | RSI<35 oversold | 1 gün teyit bekle (mevcut pozisyon için değil, sadece yeni giriş) |
| **K-15b** | momentum hisse (3ay >%30 + P/E neg/>50) | `scripts/k15b_dilution_check.py SYMBOL` zorunlu |
| **K-17** | korelasyon + tema çakışması | `scripts/k17_correlation_check.py SYMBOL` — 3 soru testi, tema %40 limit |
| **K-19** | XLP swing girişi | yasak — düşük volatilite (std 3.6% vs momentum 6.3%) swing hedef fiyatına ulaşmayı engeller; sadece portföy pozisyonu olarak alınabilir |
| **K-20** | sektör RS dead cat bounce | `scripts/k20_rs_filter.py` — son 3g RS negatif + bounce yanıltıcı |

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
| **K-12 Agresif** | tek hisse > %20 | küçült |
| **K-12 Temettü** | tek hisse > %15 | küçült |
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
| `scripts/k14_drawdown_track.py` | drawdown serisi + ortam testi | her sabah + stop tetik sonrası |
| `scripts/k15b_dilution_check.py SYMBOL` | momentum hisse dilüsyon skoru | yeni momentum giriş öncesi |
| `scripts/k16_sell_the_news_score.py SYMBOL` | earnings 7g öncesi skor | portföy pozisyonu earnings öncesi |
| `scripts/k17_correlation_check.py SYMBOL` | sektör + tema çakışması | her yeni giriş öncesi |
| `scripts/k19_xlp_filter.py SCAN_FILE` | XLP swing elemesi | swing tarama çıktısı üzerinde |
| `scripts/k20_rs_filter.py SCAN_FILE` | dead cat bounce elemesi | swing tarama çıktısı üzerinde |

not: script'ler `_QUIET_MODE=True` varsayılanı ile çalışır. info severity telegram'a gitmez, warning/critical kritik gider. `send_k_alert(force=True)` override eder.

---

## kural hiyerarşisi (çakışma durumunda)

1. **K-06 stop tetiği** → her şeyin üstünde, override yasak
2. **K-07 kâr kilidi** > K-11 katman 2 (kazançlı pozisyonda K-11 sıkı, kazançsız K-07 gevşek)
3. **K-14 drawdown fren** > tüm yeni giriş kuralları (A-kalite istisna hariç)
4. **K-13 v4.1** > K-02 (kriz şok kuralı artık K-13 v4.1 matrisinde)
5. **K-10 portföy seviyesi alt sınır** paralel çalışır, K-13 sektör seçer
6. **K-17 tema** > K-12 sektör (anlatı tema daha dar tanım)

---

> son güncelleme: 11 nisan 2026 | finzora ai | K-18 kaldırıldı (backtest), K-19 argümanı güncellendi
> değişiklik gerektiren güncellemeler doğrudan `docs/TRADING_PLAYBOOK.md`'de yapılır, bu dosya senkron tutulur.
