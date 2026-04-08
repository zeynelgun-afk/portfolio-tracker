# GÜNLÜK RAPOR PART 1B — SWING TARAMA v1.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt sadece swing trade için çalıştırılır. sabah raporunu (PART 1) okur ve üstüne inşa eder. tarama, filtreleme, giriş kararı ve aktif pozisyon yönetimi burada yapılır.
>
> **ön koşul**: aynı gün içinde PART 1 çalıştırılmış ve `DAILY_SABAH_YYYY-MM-DD.md` üretilmiş olmalıdır. yoksa DUR ve kullanıcıya uyar.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 0 — sabah raporunu oku (makro, VIX, trend, senaryolar)
> - [ ] ADIM 1 — swing sistem durumu (K-14 drawdown status, K-13 VIX bandı, SPY trend)
> - [ ] ADIM 2 — aktif pozisyonlar (chandelier stop güncelle, çıkış sinyali kontrol)
> - [ ] ADIM 3 — tam evren tarama (swing_full_universe.py, iki aşamalı)
> - [ ] ADIM 4 — ichimoku 4/4 doğrulama (Aşama 2 otomatik)
> - [ ] ADIM 5 — K filtreleri sırayla (K-17, K-18, K-19, K-20, K-05, K-15)
> - [ ] ADIM 6 — finviz teyit (web search)
> - [ ] ADIM 7 — giriş planı (varsa) + rapor yaz + git push
>
> **geçmiş hatalar**: tarama atlandığında setup kaçırıldı. filtre atlandığında yanlış giriş yapıldı (örn: POWL insider satışı K-18 atlanması). her adımı tamamla.

> **versiyon**: 1.0 | **son güncelleme**: 8 nisan 2026
> **çıktı dosyası**: `reports/daily/DAILY_SWING_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00-14:00 (sabah raporundan SONRA)
> **amaç**: swing tarama + aktif pozisyon yönetimi + giriş kararı
> **referans**: `docs/SWING_SYSTEM_V2.md` (sistem detayı), `docs/TRADING_PLAYBOOK.md` (K kuralları)
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[SWING RAPORU] DD Ay YYYY - kısa özet`

---

## ZAMAN BİLİNCİ

- rapor TR ~09:00-14:00 arası yazılır, sabah raporundan sonra
- FMP fiyatları = dünün kapanışı
- swing tarama seans içinde fiyat güncellenmiş verilerle çalışır

---

## ÇALIŞMA AKIŞI

```
ADIM 0 — SABAH RAPORUNU OKU
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md dosyasını ara
  → yoksa DUR: "sabah raporu (PART 1) çalıştırılmadan swing taramasına geçilemez"
  → varsa oku ve şu bilgileri al:
    - VIX seviyesi ve K-13 aktif bandı (sakin/dikkatli/gergin/panik)
    - SPY/QQQ trend (SMA50 üstü/altı, RSI)
    - aktif tema listesi (agresif v2 hangi katmanlar öne çıkmış?)
    - günün makro riski (FOMC, earnings, binary olay)
    - sabah raporunda K-14 drawdown status
  → bu çerçeveyi akılda tutarak tarama kararını ayarla

ADIM 1 — SWING SİSTEM DURUMU
  → data/swing/status.json oku
    - K14_DRAWDOWN_FREN aktif mi?
    - peak/trough/drawdown yüzdeleri
    - yeniden başlama kriterleri durumu
  → data/swing/active.json oku (aktif pozisyon sayısı, slot kapasite)
  → karar:
    - K-14 AKTİF: sadece A-kalite ichimoku 4/4 + K-13 faydalanıcı + K-17/K-18 temiz istisnası
    - K-14 PASİF: normal tarama
  → slot kontrolü: aktif pozisyon sayısı < 6 mı? dolu ise yeni giriş yapılmaz
  → mod seçimi:
    - VIX <22 (sakin): tam pozisyon, normal eşikler
    - VIX 22-28 (dikkatli): faydalanıcı tam, duyarlı yarım
    - VIX 28-35 (gergin): faydalanıcı yarım, duyarlı sadece K-13b ichimoku 4/4 çeyrek poz
    - VIX 35+ (panik): faydalanıcı çeyrek, duyarlı giriş yok

ADIM 2 — AKTİF POZİSYON YÖNETİMİ
  → her aktif swing pozisyonu için:
    1. FMP batch-quote ile güncel fiyat çek
    2. FMP historical-price-eod/full ile son 14 gün OHLC çek
    3. ATR(14) yeniden hesapla
    4. highest_high güncelle (giriş tarihinden bu yana en yüksek)
    5. chandelier stop yeniden hesapla: highest_high - 3×ATR
       ⚠️ stop ASLA aşağı çekilmez (sadece yukarı)
    6. kâr kilidi kontrolü (K-07):
       - kâr %7-15: chandelier sıkılaş → 2×ATR
       - kâr %15+: chandelier agresif → 1.5×ATR
    7. çıkış sinyali kontrolü:
       a. chandelier stop tetiklendi → 🔴 ÇIK (K-06 override YASAK)
       b. TK cross aşağı → ⚠️ savunmacı çıkış değerlendir
       c. kumo içine giriş → ⚠️ trend zayıf, sıkı izle
       d. hacim ayrışması (düşen hacim + yükselen fiyat) → ⚠️ izle
    8. stop yakınlık (K-09):
       - güncel fiyat stop arası %2 altı ise K-09 4 kontrol çalıştır
       - script: scripts/k09_stop_proximity_check.py SYMBOL
       - 3+ negatif kontrol → EXIT_NOW
  → aktif pozisyonların tablo halinde raporu yazılır

ADIM 3 — TAM EVREN TARAMA (İKİ AŞAMALI)
  → önce K-14 drawdown durumu oku: data/swing/status.json
  → K-14 aktifse: "yeni swing girişi YASAK" notunu rapora ekle, hedefli evrene geç
  → K-14 kalktıysa: scripts/swing_full_universe.py ile tam evren taraması çalıştır

  ÇALIŞTIRMA:
    python scripts/swing_full_universe.py --max-candidates 200

  AKIŞ:
    Aşama 1 (momentum pre-filter):
      - FMP company-screener: mcap>$2B, price>$10, vol>500K, NYSE+NASDAQ
      - K-19 XLP otomatik ön eleme (Consumer Defensive sektörü hariç)
      - Günlük momentum pozitif filtresi (batch-quote)
      - 1M >=0 + 3M >=%5 teyidi (stock-price-change)
      - Sonuç: tipik 30-80 survivor
    
    Aşama 2 (RSI + Ichimoku derin analiz):
      - swing_ichimoku.full_analysis her survivor için
      - RSI 40-65 filtresi
      - Ichimoku 4/4 bullish zorunlu
      - SMA200 üstü zorunlu
      - Sonuç: tipik 5-15 A-kalite aday

  ÇIKTI: data/daily_full_scan.json dosyasına kaydedilir
  NOT: Tam çalışma ~2-5 dakika, 300-400 FMP çağrısı yapar. Günde 1 defa yeterli.

  K-14 AKTİFKEN (DRAWDOWN FREN):
    - Tam evren yerine hedefli evren kullan (mevcut watchlist + son 3 haftanın kazananları)
    - Script: python scripts/swing_full_universe.py --max-candidates 50 --skip-stage2
    - Amaç: hazır olduğunda hızlı geri dönüş için izlemeye devam

ADIM 4 — ICHIMOKU 4/4 DOĞRULAMA (Aşama 2 zaten yapıyor)
  → swing_full_universe.py Aşama 2'de ichimoku 4/4 zaten uygulanıyor:
    a. fiyat > kumo (senkou A ve senkou B üstünde)
    b. tenkan > kijun (TK cross bull)
    c. chikou clear (26 periyot önceki fiyatın üstünde)
    d. kumo yeşil (senkou A > senkou B)
  → hacim teyidi: swing_ichimoku.py "analyze_volume" fonksiyonu otomatik çalışır
  → bu adımda yalnızca data/daily_full_scan.json'ı oku, stage2_adaylar listesini
    sonraki K filtrelerine gönder

ADIM 5 — K FİLTRELERİ (SIRAYLA)
  her geçen filtre aday listesini daraltır. bir sonraki filtreye sadece geçenler geçer.

  1. K-19 — XLP dışlama:
     scripts/k19_xlp_filter.py SCAN_FILE --write
     aday sektörü "Consumer Defensive" ise eleme

  2. K-20 — RS dead cat bounce:
     scripts/k20_rs_filter.py SCAN_FILE --write
     son 1 ay SPY'den %10+ geride + son 5 gün +%5 yukarı = dead cat, eleme

  3. K-15a — RSI <35 teyit:
     RSI <35 ise 1 gün teyit bekle (giriş sonrası gün)
     script: scripts/k15a_rsi_confirm.py SYMBOL

  4. K-15b — momentum hisse dilüsyon:
     scripts/k15b_dilution_check.py SYMBOL
     yüksek short interest + recent dilution = eleme

  5. K-17 — korelasyon + tema çakışması:
     scripts/k17_correlation_check.py SYMBOL
     mevcut portföy + swing sektörüyle korelasyon >0.8 = eleme
     aynı anlatı temasından 2+ pozisyon varsa eleme

  6. K-18 — insider kontrolü:
     scripts/k18_insider_check.py SYMBOL
     senior sell (CEO/CFO/direktör) >$5M son 30 gün = eleme

  7. K-05 — earnings 2+ gün içinde:
     FMP earnings-calendar kontrol
     2+ gün içinde earnings varsa GİR-ME (binary gap riski)
     script: scripts/k05_earnings_check.py SYMBOL

  8. K-13 v4.1 — sektör bazlı VIX kontrolü:
     aktif kriz tipi (jeopolitik/savaş) + sektör tipi (faydalanıcı/duyarlı)
     VIX bandına göre pozisyon boyutu belirlenir (tam/yarım/çeyrek/yok)

  → sonuç: K filtrelerinden geçen nihai aday listesi (tipik 3-10 hisse)

ADIM 6 — FİNVİZ TEYİT
  → websearch: finviz screener ile ADIM 5 sonucundaki adayları teyit et
  → finviz.com/quote.ashx?t=SYMBOL kontrolü:
    - pattern (head and shoulders, breakout, vs.)
    - short float % (çok yüksekse squeeze riski)
    - analyst target (upside %)
    - insider transactions son 30 gün
  → finviz'de ADIM 5 listesinde olmayan ama güçlü setup gösteren hisse varsa → "FINVIZ_EXTRA" etiketiyle ekle

ADIM 7 — GİRİŞ PLANI + RAPOR
  → her nihai aday için giriş planı oluştur:
    - giriş koşulu: "ilk 30 dk bekle, $XX.XX üzerinde konfirmasyon mumu"
    - pozisyon büyüklüğü: VIX bandı + K-13 v4.1'e göre (tam/yarım/çeyrek)
    - stop: chandelier 3×ATR veya %5 max (K-06 kuralı: max(2×ATR, %5))
    - K-13b modu: VIX 28+ ise chandelier 3×ATR ama %5 cap YOK
    - hedef 1: +%10 (K-07 kâr kilidi tetik noktası)
    - hedef 2: chandelier trailing takip
    - R:R: (hedef - giriş) / (giriş - stop) ≥ 2:1 olmalı
  → karşıt argüman zorunlu: her aday için "neden yanlış olabilirim" 1-2 cümle
  → raporu yaz
  → reports/daily/DAILY_SWING_YYYY-MM-DD.md olarak kaydet
  → git commit + push: "[SWING RAPORU] DD Ay YYYY - kısa özet"
  → TELEGRAM: yeni giriş planı varsa
    python scripts/telegram_notify.py --type alert --theme "swing giriş adayları: ..."
```

---

## RAPOR FORMATI

```markdown
# günlük swing raporu — {tarih}, {gün}

> finzora ai | sabah raporu okundu | VIX: XX.X (K-13 [bant]) | K-14: [aktif/pasif]

---

## 1. swing sistem durumu

### parametreler
- VIX: XX.X → K-13 v4.1 bandı: [sakin/dikkatli/gergin/panik]
- SPY trend: [SMA50 üstü/altı], eğim [↗/↘/→]
- K-14 drawdown freni: [aktif/pasif]
  - peak: $XX,XXX (TARİH) | trough: $XX,XXX (TARİH) | DD: %XX.X
  - yeniden başlama kriterleri: [liste, hangisi karşılandı/karşılanmadı]
- aktif pozisyon: X/6 | slot: X boş

### mod kararı
[1-2 cümle — bu sabah hangi modla tarama yapılacak, giriş açık mı]

---

## 2. aktif pozisyonlar

| id | sembol | giriş | güncel | k/z | ATR | chandelier | highest high | mesafe | gün | sinyal | durum |
|----|--------|-------|--------|-----|-----|-----------|--------------|--------|-----|--------|-------|

### önceki seansa göre değişiklikler
- [SEMBOL]: chandelier $XX → $XX (güncellendi/korundu)
- [SEMBOL]: ATR $X.XX → $X.XX
- [SEMBOL]: çıkış sinyali var/yok

### aksiyonlar
🔴 **hemen**: [SEMBOL] → [stop tetiklendi → çık]
🟡 **izle**: [SEMBOL] → [koşul]
✅ **sorunsuz**: [liste]

---

## 3. tarama sonuçları

### evren
- FMP screener: ~X,XXX hisse (mcap >$2B, vol >500K, price >$10)

### ichimoku 4/4 + hacim teyitli adaylar (ADIM 4 sonrası)

| # | sembol | sektör | fiyat | RSI | TK | kumo | chikou | hacim | not |
|---|--------|--------|-------|-----|----|----|--------|-------|-----|
| 1 | | | | | ✅ | ✅ | ✅ | 1.Xx | |

**toplam**: X aday

### K filtreleri sonrası (ADIM 5 sonrası)

| # | sembol | sektör | K-19 | K-20 | K-17 | K-18 | K-05 | K-13 | karar |
|---|--------|--------|:----:|:----:|:----:|:----:|:----:|:----:|-------|
| 1 | | | ✅ | ✅ | ✅ | ✅ | ✅ | TAM | ADAY |

**elenen**: X (hangi filtreyle)
**nihai aday**: X

### finviz ek adaylar (ADIM 6)
- [FINVIZ_EXTRA SEMBOL]: [neden ek]

---

## 4. nihai aday detayları

**[SEMBOL]** — [kısa başlık]
- sektör: [sektör] | tema: [ilgili tema varsa]
- fiyat: $XX.XX | RSI: XX | ATR: $X.XX
- ichimoku: 4/4 (fiyat $XX vs kumo $XX-$XX)
- katalizör: [tez]
- giriş koşulu: [ilk 30 dk bekle, $XX.XX üzerinde konfirmasyon]
- pozisyon büyüklüğü: [tam/yarım/çeyrek $XX,XXX] — K-13 bandı gereği
- stop: $XX.XX ([-%X.X], chandelier 3×ATR / max(2×ATR, %5))
- hedef 1: $XX.XX (+%10)
- hedef 2: chandelier trailing
- R:R: X.X:1
- karşıt argüman: [neden yanlış olabilir, 1-2 cümle]
- filtreler: K-19 ✅, K-20 ✅, K-17 ✅, K-18 ✅, K-05 ✅, K-13 [mod]

---

## 5. giriş planı özet

**bugün için hazır adaylar** (öncelik sırasıyla):
1. [SEMBOL] — [1 cümle neden öncelikli]
2. [SEMBOL] — [1 cümle neden öncelikli]

**koşullu adaylar** (seviye bekle):
3. [SEMBOL] $XX.XX kırarsa → giriş

**bugün GİRİŞ YOK gerekçesi** (varsa):
- [neden — K-14 aktif, VIX panik, binary olay yakın, vs.]

---

## 6. istatistik (güncel swing)

- toplam kapanan trade (hayat boyu): X
- kazanan: X (%XX)
- kaybeden: X (%XX)
- ortalama kazanan: +%X.X
- ortalama kaybeden: -%X.X
- profit factor: X.X
- son 10 trade sonucu: [W W L W L L W W L W] +%X.X

---

*finzora ai | fmp api + web search | sabah raporu bağlantılı*
```

---

## KURALLAR

- rapor github'a push edilir (`reports/daily/DAILY_SWING_YYYY-MM-DD.md`)
- JSON dosyalarına sadece swing için dokunulur (`data/swing/active.json` chandelier stop güncellemesi)
- ön koşul: aynı gün sabah raporu (PART 1) üretilmiş olmalı
- yeni giriş planları sadece bu prompttan gelir (sabah promptu artık swing giriş planı yazmaz)
- K-14 aktifse çok sıkı filtre, sadece A-kalite istisna
- K-13 v4.1 sektör bazlı VIX zorunlu
- ichimoku 4/4 zorunlu, eksik sinyal ile giriş yapılmaz
- K-05 zorunlu: earnings 2+ gün içinde → giriş yok (swing için istisna yok)

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
