# GÜNLÜK RAPOR PART 1 — SABAH RAPORU v3.0

> ⛔ **KRİTİK: ADIM ATLAMA YASAĞI**
>
> bu prompt'taki her adım sırayla ve eksiksiz uygulanmalıdır. hiçbir adım atlanamaz, kısaltılamaz veya "sonra yaparım" diye ertelenmez. bir adımı tamamlamadan diğerine geçme.
>
> **zorunlu adımlar (teker teker kontrol et):**
> - [ ] ADIM 0 — playbook + piyasa istihbaratı (`TRADING_PLAYBOOK.md` + `MARKET_INTELLIGENCE.md` + web arama)
> - [ ] ADIM 0.5 — dün FAZ 3 state handoff (`data/session_state.json` → `yarin_flag_listesi[]` oku)
> - [ ] ADIM 1 — piyasa verisi (FMP batch-quote, teknik göstergeler, emtia, treasury, ön piyasa)
> - [ ] ADIM 2 — haber toplama (FMP news/stock keyword filtresi, web search, twitter takip listesi)
> - [ ] ADIM 3 — earnings takvimi (FMP earnings-calendar, market cap filtresi)
> - [ ] ADIM 4 — portföy sağlık kontrolü (3 portföy mevcut pozisyonlar, stop mesafeleri, K-04 trend, K-09 stop yakınlık)
> - [ ] ADIM 5 — analiz, plan ve kayıt (playbook kurallarını planla çapraz kontrol et)
> - [ ] RAPOR — tüm bölümler (0, 0.5, 1, 2, 3, 4) eksiksiz yazıldı mı?
> - [ ] GIT — commit + push yapıldı mı?
>
> **geçmiş hatalar**: adım atlama maliyetli oldu (örn: kazanç açıklaması taramasını atlama → Oracle bilançosu rapordan eksik kaldı). her adımı tamamla, sonra raporu yaz.
>
> **v3.1 değişikliği (9 nisan 2026)**: ADIM 0.5 eklendi (dün FAZ 3'ten gelen `yarin_flag_listesi[]` okunur ve raporda bölüm 0.5'e yansıtılır). K-kural detayları `docs/K_RULES_QUICK_REF.md` tek kaynağa referanslı.
>
> **v3.0 değişikliği (8 nisan 2026)**: swing tarama PART 1B'ye, portföy fırsat taraması PART 1C'ye taşındı. bu prompt artık sadece makro çerçeve + mevcut portföy sağlığı + günün planı üretir. tarama yok.

> **versiyon**: 3.1 | **son güncelleme**: 9 nisan 2026 (session_state handoff + K-kural referans)
> **çıktı dosyası**: `reports/daily/DAILY_SABAH_YYYY-MM-DD.md`
> **çalışma zamanı**: TR ~09:00-14:00 (NYSE dün 23:00'da kapandı, bugün 16:30 açılacak — yaz saati)
> **amaç**: makro çerçeve + mevcut portföy sağlığı + günün planı
> **sonraki adım**: bu rapor tamamlandıktan sonra PART 1B (swing) ve PART 1C (portföy fırsat) promptları çalıştırılabilir. bu iki prompt sabah raporunu okur ve üstüne inşa eder
> **dil**: küçük harf türkçe, dilbilgisi kurallarına uygun
> **kaynak**: sadece "finzora ai"
> **git commit**: `[SABAH RAPORU] DD Ay YYYY - kısa özet`
> **K-kural referansı**: `docs/K_RULES_QUICK_REF.md` — tüm K-kural detayları bu dosyada, prompt içinde tekrar etme
> **session state okuma**: `data/session_state.json` — dün FAZ 3'ten gelen `yarin_flag_listesi[]` bu raporda bölüm 0.5'e yansıtılır

---

## ZAMAN BİLİNCİ

- rapor TR ~09:00-14:00 arası yazılır — NYSE dün gece 23:00'da kapandı
- **yaz saati (mart-kasım)**: NYSE açılış 16:30 TR, kapanış 23:00 TR
- **kış saati (kasım-mart)**: NYSE açılış 17:30 TR, kapanış 00:00 TR
- FMP fiyatları = dünün kapanışı (kesinleşmiş)
- tarama bu promptta yok — swing için PART 1B, portföy için PART 1C

---

## ÇALIŞMA AKIŞI

```
ADIM 0 — PLAYBOOK + PİYASA İSTİHBARATI
  → docs/TRADING_PLAYBOOK.md dosyasını oku
  → docs/K_RULES_QUICK_REF.md tek sayfa K-kural özetini referans olarak hatırla
  → aktif kuralları gözden geçir (özellikle K-02, K-13 v4.1 sektör bazlı VIX, K-14 drawdown freni)
  → docs/MARKET_INTELLIGENCE.md okuyarak istihbarat çerçevesini hatırla
  → web aramasıyla güncel piyasa istihbaratı topla:
    - dünden bu yana kritik haberler (makro, jeopolitik, sektörel)
    - her haberin neden-sonuç zinciri (1./2./3. derece etki)
    - bu haftanın kritik olayları ve senaryolar (FOMC, earnings, veri)
    - aktif tema güç skorları (AI altyapı, enerji, savunma vb.)
    - prediction markets değişimleri (kalshi, polymarket)
    - AI tedarik zinciri katmanlarının durumu (ekipman, kimya, güç, optik)
  → PORTFÖY ÖNCEDEN POZİSYONLAMA kararı:
    - hangi temaya ağırlık artır/azalt?
    - hangi katmanda fırsat var?
    - mod değişikliği gerekiyor mu? (agresif/normal/dikkatli/defansif)

ADIM 0.5 — DÜN FAZ 3 STATE HANDOFF
  → data/session_state.json dosyasını oku (yoksa atla, uyarı ver)
  → tarih kontrolü: state.tarih == dün olmalı (değilse eski/bozuk state, uyarı ver)
  → state.faz3.yarin_flag_listesi[] oku, her flag için aksiyon belirle:
    - tip "amc_earnings": dün AMC açıklanan earnings sonucu — bugün gap/tepki kontrolü
    - tip "gap_riski": bugün açılışta gap olasılığı — seans öncesi ön piyasa takibi
    - tip "stop_yakin_gece": gece stop'a yakın geceleyen — açılışta K-09 erken kontrol gerekebilir
    - tip "acilista_izlenecek": belirli seviye bekleyen — bölüm 4 plana dahil et
    - tip "makro_veri": beklenen makro veri saati — bölüm 2 veri takvimine ekle
  → state.faz3.after_hours_izleme[] oku:
    - FMP aftermarket-quote seans dışında 0 döner, web search ile AH fiyat teyidi al
  → state.seans_ozet[] oku (dünün trade özeti) — istatistik için
  → bu verileri raporda BÖLÜM 0.5 olarak yansıt (aşağıdaki format)
  → kapanış raporu (PART 2) bu veriyi zaten işledi — burada tekrar işleme değil, sadece yarına taşınan flag'ler için kullan

ADIM 1 — PİYASA VERİSİ (FMP + WEB)
  → batch-quote: SPY, QQQ, DIA, IWM, VIXY, GCUSD, USO (petrol proxy)
    ⚠️ VIX SEVİYESİ: get_vix_level() [k_rules_common] → Yahoo Finance ^VIX
       VIXY fiyatı ($29-30) ≠ VIX seviyesi (tipik 10-40). K-13 eşikleri için VIXY fiyatını KULLANMA.
       VIXY sadece yön için: get_vix_direction(). CLUSD/WTIUSD güvenilmez → USO kullan.
  → stock-price-change: tüm portföy sembolleri (1D, 5D, 1M güvenilir)
  → teknik göstergeler: portföy hisseleri için RSI(14), SMA50, SMA200
  → sector-performance-snapshot (date = dünün tarihi)
  → biggest-gainers, biggest-losers (limit 15)
  → treasury-rates (son 5 gün)

  ⚠️ ÖN PİYASA VERİSİ — WEB ARAMASI ZORUNLU:
  FMP aftermarket-quote endpoint'i NYSE seans dışında sıfır dönüyor.
  → websearch: "S&P 500 futures today" / "stock market premarket today"
  → kaynak önceliği: investing.com, cnbc.com, tradingeconomics.com, robinhood.com
  → endeks vadeli (ES, NQ, YM), petrol (Brent, WTI), altın, AH hareketleri
  → raporda tablo formatında sun: ticker | dün kapanış | ön piyasa | fark% | not

ADIM 2 — HABER TOPLAMA
  → FMP news/stock: tüm portföy + swing + watchlist sembollerini virgülle birleştir, TEK çağrıda çek (limit 50)
    - negatif sinyal: lawsuit, downgrade, SEC, investigation, cut dividend, miss, warning, recall, resign
    - pozitif sinyal: beat, upgrade, raise, target, deal, contract, approval, partnership
    - eşleşen haberler → web search ile doğrula ve derinleştir
    - dolgu haberler (zacks "is X undervalued" vb.) → atla
    ⚠️ press-releases endpoint'i symbol filtresini düzgün uygulamıyor — KULLANMA
  → FMP: upgrades-downgrades (portföy hisseleri, limit 20)
  → websearch: dün gece / bugün sabah önemli piyasa haberleri
  → websearch: portföy hisselerini etkileyen gelişmeler
  → websearch: Fed faiz olasılıkları (Kalshi/Polymarket)

  TWİTTER TAKİP LİSTESİ (RapidAPI / twitter241):
  → 10 hesabın son tweetlerini çek (her biri için 15-20 tweet)
  → portföy sembolleriyle örtüşenleri öne çıkar
  → endpoint: GET /user-tweets?user={numeric_user_id}&count=20

  TAKİP LİSTESİ:
    @CheddarFlow, @berkdemirkiran_, @yatirim, @onestoploss, @StockSavvyShay,
    @BerkUcmz, @TrendSpider, @Jake__Wujastyk, @RyanDetrick, @VolSignals,
    @theaiportfolios (LLM portföy yarışması — Grok/ChatGPT/Claude $150M, rakip analiz + içerik ilhamı)

  ÖNEMLİ: tweet verileri SADECE claude'un bağlamına girer, rapora yazılmaz.
  tweet bilgileri yorumlanarak piyasa değerlendirmelerine yedirilir.

ADIM 3 — EARNINGS
  → FMP: earnings-calendar (bugün + 7 gün)
  → websearch: dün gece açıklanan earnings sonuçları (portföy/swing/majör)
  → websearch: bugünkü ekonomik veri takvimi

ADIM 4 — PORTFÖY SAĞLIK KONTROLÜ
  → data/portfolios/{balanced,aggressive,dividend}.json oku
  → data/swing/active.json oku
  → her pozisyon için hesapla:
    - güncel fiyat vs maliyet → k/z %
    - güncel fiyat vs stop → mesafe % (K-09 yakınlık)
    - RSI (K-11 tetik: 70+/80+)
    - SMA50 + SMA200 durumu (K-04 trend filtresi + uzun vade)
    - günlük değişim
    - konsantrasyon (K-12 limitleri — detay: `docs/K_RULES_QUICK_REF.md`)
  → uyarı kategorileri:
    🔴 ACİL: stop mesafesi <%2 VEYA günlük <-%5 VEYA fiyat < SMA200
      ⚠️ k09_proximity_check.py BURDA ÇALIŞTIRILMAZ — mesafe yüzdesi tabloya yazılır, script SESSION FAZ1'de çalışır
    ⚠️ İZLE: RSI 70+ VEYA RSI <40 VEYA SMA50 altı VEYA K-12 limit yakını
    🟢 NORMAL: trend içinde, uyarı yok
  → SEKTÖR EXPOSURE: 3 portföy toplam sektör dağılımı hesapla (K-12 %40 kontrol)
  → NAKİT DURUMU: her portföy için nakit % + kullanılabilir alım gücü
  → K-rule detayları için `docs/K_RULES_QUICK_REF.md` referansını kullan, prompt içinde tekrarlama

ADIM 5 — ANALİZ, PLAN VE KAYIT
  → tüm verileri sentezle (ADIM 0.5 dün FAZ 3 flag listesi dahil)
  → PLAYBOOK ÇAPRAZ KONTROL: günün planındaki her aksiyonu `docs/K_RULES_QUICK_REF.md` ile kontrol et
    mevcut portföy yönetimi için kritik olanlar: K-04 (trend), K-06 (stop, override yasak), K-07 (trailing), K-09 (stop yakınlık), K-11 (kademeli kâr), K-12 (konsantrasyon), K-13 v4.1 (VIX bandı), K-14 (drawdown fren)
  → NOT: giriş kuralları (K-02, K-05, K-15, K-17, K-18, K-19, K-20) burada kullanılmaz
    — bunlar PART 1B (swing) ve PART 1C (portföy) promptlarında uygulanır
  → SENTIMENT: CBOE put/call ratio (web search) + FMP grades-consensus
    put/call <0.7 = aşırı iyimser uyarı, >1.0 = aşırı kötümser, >1.2 = panik
  → raporu yaz (aşağıdaki format)
  → reports/daily/DAILY_SABAH_YYYY-MM-DD.md olarak kaydet
  → GIT COMMIT + PUSH: "[SABAH RAPORU] DD Ay YYYY - kısa özet"
  → TELEGRAM GÖNDERİMİ (git push'tan SONRA):
    1. python scripts/telegram_notify.py --type premarket --theme "[günün özeti]"
    2. python scripts/telegram_notify.py --type report --file reports/daily/DAILY_SABAH_YYYY-MM-DD.md
  → RİSK PANELİ GÖRSELİ (telegram report'tan SONRA):
    python scripts/risk_panel_generator.py
    python scripts/telegram_notify.py --type photo --image outputs/risk_panel/{TARIH}.png --caption "risk paneli - sabah"
```

---

## RAPOR FORMATI (GITHUB'A GÖNDERİLİR)

rapor 6 bölümden oluşur (0, 0.5, 1, 2, 3, 4).

---

### BÖLÜM 0: PİYASA İSTİHBARATI

```markdown
## 0. piyasa istihbaratı

### aktif temalar

| tema | güç skoru | değişim | neden |
|------|-----------|---------|-------|
| AI altyapı harcaması | X/10 | ↑/↓/→ | [kısa açıklama] |
| enerji güvenliği | X/10 | ↑/↓/→ | |
| savunma harcaması | X/10 | ↑/↓/→ | |
| faiz indirimi beklentisi | X/10 | ↑/↓/→ | |

### kritik haber → etki zinciri

1. **[haber başlığı]**
   - 1. derece: [direkt etki]
   - 2. derece: [tedarik zinciri etkisi]
   - 3. derece: [yan etkiler]
   - portföy aksiyonu: [ne yapılmalı]

### bu haftanın senaryoları

**[olay]** — olasılıklar:
- senaryo A (%XX): [sonuç → aksiyon]
- senaryo B (%XX): [sonuç → aksiyon]
- önceden pozisyonlama: [ne yapılmalı]

### tedarik zinciri katman durumu

ekipman: [güçlü/zayıf/nötr] | kimya: [...] | güç: [...] | optik: [...] | soğutma: [...]
```

---

### BÖLÜM 0.5: DÜN FAZ 3 NOTLARI (SESSION STATE HANDOFF)

```markdown
## 0.5. dün seans sonu notları

> kaynak: `data/session_state.json` → `faz3.yarin_flag_listesi[]`
> dün seans içi power hour'da bugüne bırakılan takip listesi
> kapanış raporu bu veriyi zaten değerlendirdi, burada sadece yarına taşınan açık flag'ler var

### dün seans özeti
- toplam trade: X (alış Y, satış Z)
- net k/z: ±$X,XXX
- aktif pozisyon: X
- nakit oranı: %X

### bugün açılışta takip edilecek

**AMC earnings sonuçları (dün kapanıştan sonra açıklananlar)**:
| sembol | eps sonuç | tepki (AH) | portföy etkisi | aksiyon |
|---|---|---|---|---|

**gap riski** (ön piyasa takibi öneriliyor):
- [SEMBOL]: neden (earnings, haber, AH hareketi)

**stop yakınında geceleyenler**:
- [SEMBOL]: gece kapanış mesafe %X → açılışta K-09 erken kontrol

**açılışta izlenecek seviyeler**:
- [SEMBOL]: $X seviyesinde [giriş / çıkış] planı

**makro veri beklenen**:
- [saat TR]: [veri adı] — bölüm 2 veri takvimine dahil

### state yoksa / eski ise
> bugün PART 1 ilk çalıştırma, state dosyası bulunamadı → bu bölüm boş
> veya state tarihi eski (dün seans çalışmamış, hafta sonu, tatil) → bu bölüm boş
```

---

### BÖLÜM 1: PİYASA GÖRÜNÜMÜ

```markdown
## 1. piyasa — dün + bugün

### dünün kapanışı ({tarih}, {gün})

| ticker | kapanış | değişim | RSI | SMA50 | SMA200 | not |
|--------|---------|---------|-----|-------|--------|-----|
| SPY | $XXX.XX | +X.XX% | XX.X | ✅/❌ | ✅/❌ | |
| QQQ | $XXX.XX | +X.XX% | | | | |

**emtia + döviz**: altın $X,XXX (±%), WTI $XX (±%), DXY XX.X, 10Y %X.XX

### bugünün öncü göstergeleri

**vadeli işlemler / ön piyasa** ({bugün sabah}, web aramasından):

| ticker | dün kapanış | ön piyasa | fark | not |
|--------|------------|-----------|------|-----|
| S&P 500 vadeli | X,XXX | X,XXX | ±%X.XX | |

> kaynak: investing.com / cnbc / robinhood (FMP aftermarket seans dışında sıfır dönüyor)

### sektör performansı (dün)

en güçlü 3: [sektör +%], [sektör +%], [sektör +%]
en zayıf 3: [sektör -%], [sektör -%], [sektör -%]
rotasyon sinyali: [risk-on / risk-off / karışık]

### risk değerlendirmesi

- VIX: XX.X (Yahoo Finance ^VIX — get_vix_level()) → [risk-on/off/nötr]
- K-13 v4.1 aktif bant: [sakin/dikkatli/gergin/panik]
- K-14 drawdown status: [aktif/pasif]
- breadth: gainers/losers oranı
- prediction markets: Kalshi Fed faiz %XX
```

---

### BÖLÜM 2: HABER VE ANALİZ

```markdown
## 2. haber ve analiz

### portföyü doğrudan etkileyen

**[SEMBOL] — [başlık]**
etki: [✅/❌/➡️] | portföy: [hangisi]
[2-3 cümle analiz]
aksiyon: [ne yapılacak]

### sektör ve makro gelişmeler

| gelişme | etki | ilgili hisse | yorum |
|---------|------|--------------|-------|

### analist notları

| tarih | sembol | kurum | önceki → yeni | hedef fiyat |
|-------|--------|-------|---------------|-------------|

### makro yorum

[2-4 cümle]

### bugünün veri takvimi

| saat (TR) | veri | beklenti | önceki |
|-----------|------|----------|--------|

**genel sentiment**: [pozitif / negatif / nötr / karışık]
```

---

### BÖLÜM 3: PORTFÖY SAĞLIK DURUMU + EARNINGS

```markdown
## 3. portföy sağlık durumu

### 3a. dengeli portföy (X/6 pozisyon, $XXK nakit, %XX nakit oranı)

| sembol | fiyat | günlük | k/z | RSI | 50 | 200 | stop | mesafe | durum |
|--------|-------|--------|-----|-----|:--:|:---:|------|--------|-------|
| XXX | $XX.XX | ±%X.X | ±%X.X | XX | ✅ | ✅ | $XX | X.X% | [not] |

**toplam**: $XXX,XXX (±%X.XX) | **nakit**: $XX,XXX (%XX)

### 3b. agresif portföy (X/10 pozisyon, $XXXK nakit, %XX nakit oranı)

[aynı tablo]

### 3c. temettü portföyü (X/15 pozisyon, $XXK nakit, %XX nakit oranı)

[aynı tablo]

### 3d. sektör exposure (3 portföy toplam)

| sektör | $ tutar | % | K-12 limit | durum |
|--------|--------:|---|-----------:|-------|
| Teknoloji | $XX,XXX | XX% | %40 | [içinde/sınır/aşım] |

### 3e. uyarı özeti

🔴 **acil**: [SEMBOL] — [neden]
⚠️ **izle**: [SEMBOL] — [neden]
🟢 **normal**: [kaç pozisyon]

### 3f. earnings takvimi

**dün gece (AMC) — sonuçlar**:

SEMBOL — [şirket]
  EPS: $X.XX vs beklenti $X.XX → beat/miss %X
  gelir: $X.XXB vs beklenti $X.XXB → beat/miss %X
  guidance: [yükseltildi / korundu / düşürüldü]
  AH/PM tepki: $XXX (±%X)
  portföy etkisi: [doğrudan/dolaylı — aksiyon]

**bugün ve haftalık kritik**:

| tarih | sembol | timing | beklenti | portföy etkisi |
|-------|--------|--------|----------|----------------|
```

---

### BÖLÜM 4: GÜNÜN PLANI

```markdown
## 4. günün planı

### strateji notu

[2-3 cümle — bugünün seansı için yön ve yaklaşım, makro çerçeve]

### mevcut pozisyon aksiyonları

> ⛔ bu plan SADECE mevcut pozisyonların yönetimini içerir (sat, kısmi kâr al, trailing güncelle, stop yakın izle). YENİ giriş planları bu prompttan çıkmaz, PART 1B (swing) ve PART 1C (portföy) raporlarından gelir.
> bu plan BÖLÜM 0.5'teki dün FAZ 3 flag listesini ve BÖLÜM 3'teki uyarıları (🔴 acil / ⚠️ izle) baz alır.

**hemen** (seans açılışında):
1. [aksiyon] — [sebep] — [hangi portföy, hangi hisse]

**izle** (seans içinde):
2. [koşul] → [aksiyon]

**pasif** (seviye bekle):
3. [sembol] $XXX'e gelirse → [değerlendir]

### bugün için tarama durumu

- swing tarama: PART 1B promptunda → `DAILY_SWING_YYYY-MM-DD.md`
- portföy fırsat: PART 1C promptunda → `DAILY_PORTFOY_YYYY-MM-DD.md`

### dikkat edilecekler

- [risk 1]
- [fırsat 1]

---

*finzora ai | fmp api | new york kapalı*
```

---

## KURALLAR

- rapor github'a push edilir (`reports/daily/DAILY_SABAH_YYYY-MM-DD.md`)
- JSON dosyalarına dokunma (veri güncellemesi PART 2'de yapılacak)
- amaç: sabah bilgilendirme + makro çerçeve + mevcut portföy sağlığı
- **tarama bu promptta YOK** — swing için PART 1B, portföy için PART 1C çalıştır
- VIX kuralı: K-13 v4.1 sektör bazlı — detay: docs/TRADING_PLAYBOOK.md
- ADIM 4 sadece MEVCUT pozisyonları yönetir, YENI giriş planı üretmez
- yeni giriş planları sadece PART 1B ve PART 1C promptlarından gelir

---

**API KEY**: g1GFJZtV5rCP49UCir4WuP56VjhmA6F8
**BASE URL**: https://financialmodelingprep.com/stable
**REPO**: https://github.com/zeynelgun-afk/portfolio-tracker
**TOKEN**: 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
**RAPIDAPI KEY**: fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7
**RAPIDAPI HOST**: twitter241.p.rapidapi.com
