# SEANS İÇİ FAZ 2 — ORTA SEANS PROMPT v1.0

> **çalışma zamanı**: NYSE orta seans (TR 18:00-21:00)
> **öncelik**: ANALİZ + KARAR — tam teknik, yeni giriş taraması, GO/NO-GO, karar matrisi
> **ön koşul**: FAZ 1 tamamlanmış, `data/session_state.json` FAZ 1 bloğu yazılmış
> **çıktı**: karar matrisi sonuçları + al/sat emirleri + JSON + git + telegram
> **dil**: küçük harf türkçe, teknik terimler ingilizce
> **kaynak atfı**: sadece "finzora ai"
> **format**: em dash kullanma

> ⛔ **KRİTİK: SEANS İÇİNDE RAPOR (.md) YAZILMAZ**
> ⛔ **SEN KARAR VER**: tüm aksiyonlar onay beklemeden uygulanır. K-rule kontrolü yaptıktan sonra karar claude'da.

---

## çalıştırma tetikleyicileri

- "faz 2"
- "orta seans güncelleme"
- "piyasa nasıl, ne yapıyoruz?"
- "yeni giriş tara"

---

## aşama listesi

- [ ] 1. FAZ 1 state'ini oku, delta hesapla
- [ ] 2. tam teknik göstergeler (RSI + SMA50 + SMA200 tüm pozisyonlar)
- [ ] 3. sektör RS analizi canlı
- [ ] 4. piyasa istihbaratı + prediction markets delta
- [ ] 5. karar matrisi (portföyler) — 3a
- [ ] 6. karar matrisi (swing) — 3b
- [ ] 7. portföyler arası korelasyon (K-12 + K-17)
- [ ] 8. yeni giriş fırsatları (tematik tedarik zinciri taraması)
- [ ] 9. GO/NO-GO her yeni giriş için
- [ ] 10. satış/çıkış değerlendirmesi
- [ ] 11. trade uygulama (JSON + CSV + git)
- [ ] 12. watchlist güncellemesi
- [ ] 13. telegram bildirimleri
- [ ] 14. `session_state.json` FAZ 2 bloğu
- [ ] 15. chat özet raporu

---

# 1. FAZ 1 state okuma

```python
state = json.load(open("data/session_state.json"))
faz1 = state["faz1"]
# faz1 verilerini context olarak al
# tekrar çekmeye gerek yok: SPY/QQQ/VIX, gap raporu, BMO earnings, twitter ilk çekim
```

delta kontrolü:
- faz 1'den bu yana SPY/QQQ/VIX ne yöne gitti?
- risk ortamı değişti mi?
- faz 1'de açık kalan sorular var mı?

---

# 2. tam teknik göstergeler

**1b — batch-quote sadece delta için** (FAZ 1'den beri değişim):
```python
quotes = fmp_get("batch-quote", {"symbols": ",".join(unique_symbols)})
```

**teknik göstergeler — tüm portföy + swing sembolleri**:
```python
for symbol in unique_symbols:  # ~15-20 sembol
    rsi = fmp_get("technical-indicators/rsi", 
                  {"symbol": symbol, "periodLength": 14, "timeframe": "1day"})
    sma50 = fmp_get("technical-indicators/sma", 
                    {"symbol": symbol, "periodLength": 50, "timeframe": "1day"})
    sma200 = fmp_get("technical-indicators/sma", 
                     {"symbol": symbol, "periodLength": 200, "timeframe": "1day"})
```

her sembol için durum tablosu:
```
SEMBOL | fiyat | günlük% | RSI | SMA50 | SMA200 | durum
```

durum kodları:
- ✅ GÜÇLÜ: trend yukarı, RSI 50-70, SMA'lar üzerinde
- ⚠️ DİKKAT: SMA kırılımı yakın, RSI aşırı bölgede, stop yakın
- 🔴 ACİL: K-06/K-09 tetik yaklaşıyor
- 💰 KAR AL: RSI 80+ ve kâr %15+ (K-11 katman 2 tetik)
- 🔄 NÖTR: bekle

**toplam**: ~1 batch + 3×N (teknik) = ~45-60 FMP

---

# 3. sektör RS analizi

```python
sectors = fmp_get("sector-performance-snapshot", {"date": TODAY})
```

```
sektor_rs = sektor_degisim - SPY_degisim

sinyaller:
- SPY düşerken sektör RS > +1.0% → 🔥 güç sektör
- SPY düşerken sektör RS > +0.5% → 💪 dirençli
- SPY yükselirken sektör RS < -1.0% → ⚠️ zayıf sektör
```

FAZ 1 snapshot'ıyla karşılaştır, rotasyon değişikliği var mı?

---

# 4. piyasa istihbaratı + prediction markets delta

### piyasa istihbaratı

sabah raporundaki piyasa istihbaratını ve FAZ 1 twitter özetini baz al. yeni haber varsa:

```
1. web araması: "stock market news {TIME_RANGE}"
2. portföy sembolleri için: "{SECTOR/THEME} news today"
3. her haber için neden-sonuç zinciri:
   - 1. derece: kim etkilenir
   - 2. derece: tedarik zinciri
   - 3. derece: yan etki (enerji, hammadde, lojistik)
4. portföy etkisi + fırsat değerlendirmesi
```

**toplam**: 2-4 websearch

### prediction markets delta

```
websearch → "kalshi fed rate probability today"
websearch → "polymarket" + gündem olay
```

sabahtan değişim:
- > %10 değişim → önemli sinyal
- <%5 değişim → "PM stabil"
- whale manipulation uyarısı (<$10K hacim güvenilmez)

aksiyon tetikleyicileri (`docs/PREDICTION_MARKETS_GUIDE.md`):
- fed rate cut odds > %30 → defansif azalt, cyclical ekle
- iran escalation > %50 → enerji pozisyonları koru/artır

**toplam**: 2 websearch

### haber endpoint (isteğe bağlı)
```python
news = fmp_get("news/stock", {"symbols": ALL_SYMBOLS, "limit": 30})
# filtre: negatif (lawsuit, downgrade, SEC, investigation, cut, miss, warning, recall)
# pozitif (beat, upgrade, raise, target, deal, contract, approval)
# dolgu haberler (zacks "is X undervalued") → atla
# ⚠️ press-releases endpoint bozuk — kullanma
```

---

# 5. karar matrisi — portföyler (3a)

> K-rule detayları: `docs/K_RULES_QUICK_REF.md`

her pozisyon için karar ağacı:

```
1. K-06 stop tetiklendi mi?
   evet → 🔴 HEMEN SAT, override yasak
   hayır → devam

2. K-11 kademeli kâr alma?
   - katman 1: RSI 70+ VE kâr %15+ → kâr kilidi aktif (max(2×ATR, 20SMA altı))
   - katman 2: RSI 80+ VEYA (RSI 75+ + negatif div/20SMA altı) → %25-30 kısmi sat
   - katman 3: 50SMA altı kapanış VEYA chandelier trailing → tam çık
   hayır → devam

3. K-16 sell-the-news skor (earnings 7g öncesi, portföy pozisyonu)
   scripts/k16_sell_the_news_score.py SYMBOL
   - skor 2-3: %25 kısmi + K-11 trailing sıkılaştır
   - skor 4-5: %50 kısmi çık, post-earnings bekle
   hayır → devam

4. tez bozuldu mu?
   - temel kötüleşme (earnings miss, temettü kesintisi, guidance düşürme)
   - sektör yapısal zayıflık (K-20 dead cat paterni)
   - korelasyon riski (K-17 + K-12 sektör/tema %40 limit)
   evet → ⚠️ küçült veya kapat

5. K-12 konsantrasyon (portföy bazlı)?
   - Dengeli hisse > %25 → küçült
   - Agresif hisse > %20 → küçült
   - Temettü hisse > %15 → küçült
   - $600K bazlı sektör > %40 → en zayıfı kes
   - $600K bazlı anlatı tema > %40 (K-17) → tema yoğunluğu azalt

6. K-10 VIX allokasyon kontrolü
   VIX bandına göre min savunmacı + nakit eşiği sağlanıyor mu?
   eksik → yeni agresif giriş yasak, savunmacı/nakit artır

7. teknik izleme (K-11 zaten yönetiyor):
   - RSI > 80 + kâr %15+ → K-11 katman 2 baskın tetik aktif
   - RSI < 35 + mevcut pozisyon: tez gözden geçir (K-15a MEVCUT pozisyona uygulanmaz, sadece yeni giriş filtresi)
   - SMA200 altı kırılım → trend dönüşü uyarısı

8. hiçbir tetik yok → ✅ TUT
```

---

# 6. karar matrisi — swing (3b)

> swing sistemi v2.3, detay: `docs/SWING_SYSTEM_V2.md`

```
0. K-14 drawdown status (günlük tek sefer)
   data/swing/status.json oku
   K14_DRAWDOWN_FREN aktif → yeni giriş yok (A-kalite istisna hariç)

1. chandelier stop tetik? (K-06 + K-07)
   fiyat <= chandelier → 🔴 %100 SAT, override yasak
   closed.json'a tüm zorunlu alanlarla kaydet

2. K-09 stop yakınlık
   mesafe <%2 mi?
   scripts/k09_proximity_check.py çalıştır
   3+ negatif = EXIT_NOW, 2 = WAIT, 0-1 = TUT

3. K-07 kâr kilidi güncelle (chandelier multiplier)
   kâr <%7: 3×ATR (normal)
   kâr %7-15: 2×ATR (kilit aktif)
   kâr %15+: 1.5×ATR (agresif kilit)
   highest_high arttıysa stop yukarı çek

4. K-05 earnings koruması (earnings ≤2 iş günü kala ZORUNLU)
   earnings ≤2 iş günü → ✂️ TAM ÇIK, exception yok

5. hacim + momentum (K-07 zaten yönetiyor, sadece rapor)
   OBV yükseliş + fiyat yükseliş → sağlıklı
   OBV düşüş + fiyat yükseliş → ayrışma, belirt

6. hiçbir tetik yok → ✅ TUT (chandelier aktif)
```

**not v2.1'den v2.3'e kaldırılanlar**:
- "kijun altı kapanış" otomatik çıkış → kaldırıldı (chandelier aldı)
- "TK cross aşağı" otomatik çıkış → kaldırıldı (sadece rapor)
- stop hesaplama: kijun → chandelier

---

# 7. portföyler arası korelasyon

> detaylı sektör exposure tablosu: `docs/DECISION_FRAMEWORK.md` bölüm 5

```
kontrol 1: K-12 cross-portfoy
- aynı hisse birden fazla portföyde mi?
- swing + portföy çakışması kabul (farklı zaman ufku)
- iki portföyde aynı hisse → $600K bazlı %10 üstünde mi, bilinçli mi?

kontrol 2: K-12 GICS sektör limiti
- 3 portföy toplamı bir GICS sektör > %40 → en zayıfı kes

kontrol 3: K-17 anlatı tema limiti
- anlatı tema (AI tedarik zinciri, savunma, enerji vb.) > %40 → yeni tema girişi yok
- scripts/k17_correlation_check.py YENI_SYMBOL
- 3 soru testi: makro hikaye / katalist / senaryo

kontrol 4: yön korelasyonu
- hepsi aynı yönde mi? (çeşitlendirme çalışıyor mu?)
- temettü piyasa düşerken yükseliyorsa → hedge OK
- hepsi aynı anda düşüyor → korelasyon riski
```

---

# 8. yeni giriş fırsatları — proaktif tematik tarama

> **felsefe**: claude kendi başına düşünür, haberleri okur, sektörel trendleri analiz eder, tedarik zinciri katmanlarını araştırır. watchlist'e ekleyip beklemez, uygun setup'a giriş yapar.

### kaynak 0: tematik tedarik zinciri taraması

```
AI TEDARİK ZİNCİRİ KATMANLARI:
  çip tasarımı:     NVDA, AMD, MRVL, AVGO, CRDO
  çip ekipmanı:     ASML, AMAT, LRCX, KLAC, CAMT, ONTO
  kimyasal/malzeme: ENTG, MKSI, PLAB, CCMP, LIN, APD
  optik bağlantı:   COHR, LITE, GLW, AAOI
  güç altyapısı:    POWL, VRT, ETN, PWR, GNRC
  soğutma/termal:   VRT, TT, JCI
  veri merkezi:     DLR, EQIX
  enerji:           COP, XOM, CVX
  nadir toprak:     MP, FCX, BHP

SAVUNMA/UZAY:       LMT, RTX, GE, RKLB, KTOS
ENERJİ GEÇİŞİ:      FSLR, ENPH, NEE, VST
```

her seansta:
1. web aramasıyla güncel tema/haber
2. hangi katman öne çıkıyor
3. katmandaki hisseleri ichimoku ile tara
4. güçlü setup → giriş (watchlist'e ekleme yerine)

### kaynak 1-5: geniş ağ

```python
# kaynak 1: biggest-gainers momentum
gainers = fmp_get("biggest-gainers", {"limit": 30})
# filtre: price > $15, volume > 500K, mcap > $3B

# kaynak 2: screener — güçlü sektörlerden
for sektor in en_guclu_3_sektor:
    fmp_get("company-screener", {
        "sector": sektor,
        "marketCapMoreThan": 3000000000,
        "volumeMoreThan": 500000,
        "priceMoreThan": 15,
        "exchange": "NYSE,NASDAQ",
        "isActivelyTrading": "true",
        "limit": 15
    })

# kaynak 3: mevcut watchlist
# urgency=high, tetiklenen seviyeler

# kaynak 4: portföy temaları

# kaynak 5: finviz websearch
# "finviz screener 52 week high unusual volume mid cap"
```

hedef: 20-30 benzersiz aday. portföyde olanları çıkar.

### adım 2: SMA50 + SMA200 ön filtre
```python
for sym in adaylar:
    sma50, sma200 = fmp("technical-indicators/sma", ...)
    # fiyat > SMA50 ve > SMA200 → ichimoku taramasına gönder
    # fiyat < SMA50 → eleme (kumo altı ihtimali yüksek)
```

hedef: 10-15 aday.

### adım 3: ichimoku tam tarama
FMP historical data ile ichimoku 4/4 tarama (bkz. `docs/SWING_SYSTEM_V2.md` bölüm 9).

### adım 4: claude temel değerlendirme
"GİRİŞ ✅" / "GİRİŞ ⚠️" veren hisseler için:
- sektör bağlamı (utilities borç normal, enerji döngüsel)
- katalizör ve hikaye
- mevcut portföyle korelasyon
- risk/ödül
- VIX ortamı (K-13 v4.1)

**sabit rasyo filtresi yok.** metrikler sektör ve şirkete göre yorumlanır.

---

# 9. GO/NO-GO — her yeni giriş için ZORUNLU

> tek "hayır" = giriş iptal

```
□ 1. sinyal var mı? (ichimoku 4/4, kumo kırılımı, portföy tezi)
□ 2. stop tanımlı mı? (K-06 giriş: max(2×ATR(14), %5), K-13b kriz: sadece 2×ATR)
□ 3. R:R ≥ 2:1 mi?
□ 4. K-13 v4.1 VIX uygun mu? (sektör kategorisi × VIX bandı matrisi — K_RULES_QUICK_REF.md)
□ 5. K-18 insider temiz? (scripts/k18_insider_check.py SYMBOL)
□ 6. K-17 korelasyon temiz? (scripts/k17_correlation_check.py SYMBOL)
□ 7. K-15a teyit: RSI <35 ise 1 gün bekle? (portföy girişlerine — swing için UYGULANMAZ, swing RSI 40-65 bandında zaten filtreli)
□ 8. K-15b dilüsyon: momentum hisse ise (scripts/k15b_dilution_check.py)
□ 9. K-05 earnings: swing ve portföy için ≤2 iş günü içinde earnings → GİRMEZ
□ 10. K-19 + K-20: XLP değil mi, sektör RS dead cat yok mu?
□ 11. K-14 drawdown status: K14_DRAWDOWN_FREN değil mi?
□ 12. K-12 konsantrasyon: giriş sonrası portföy limiti aşılmıyor mu?
□ 13. K-10 VIX allokasyon: min savunmacı + nakit eşiği sağlanıyor mu?
□ 14. nakit yeterli mi? (giriş sonrası nakit <%5 olacak mı?)
□ 15. sabah planında var mı? (plan dışı → ekstra gerekçe zorunlu)
□ 16. karşıt argüman düşündüm mü? (`docs/DECISION_FRAMEWORK.md` bölüm 3)
```

### düşünce zinciri (her al/sat kararında, stop hariç)

```
KARAR: [AL/SAT/TUT] — [SEMBOL]
1. VERİ: somut — fiyat, RSI, hacim, haber, teknik
2. KURAL: hangi playbook/sistem sinyali destekliyor
3. KARŞIT: bu kararın neden yanlış olabileceği
→ SONUÇ: uygula / ertele / vazgeç
```

### önyargı hızlı kontrol (şüphe anında)

```
□ çıpa etkisi: "eskiden X dolardı, şimdi ucuz" → geçmiş fiyat referans değil
□ batık maliyet: "bu kadar zarar ettim, satamam" → bugün sıfırdan alır mıydım?
□ sürü/FOMO: "herkes alıyor" → 2 gün önce görsem alır mıydım?
□ aşırı güven: "kesin yükselir" → son 3 trade kârlıysa risk yüksek
□ sonuç yanlılığı: "kârlı çıktım, strateji doğru" → süreç mi şans mı?
```
detay: `docs/DECISION_FRAMEWORK.md` bölüm 4

---

# 10. satış/çıkış değerlendirmesi

portföy hissesi satış nedenleri:
```
1. K-06 stop tetik (max(2×ATR(14), %5), ATR tabanlı)
   • temettü ek: tema/kalite/skor bazlı çıkış (docs/DIVIDEND_SYSTEM.md)
2. tez bozuldu
3. sektör RS sürekli zayıf (3+ gün negatif)
4. daha iyi fırsat (aynı sektör/tema güçlü alternatif)
5. portföy ağırlık dengesizliği
6. K-11 katman 2: kısmi kâr
7. K-16 skor 4-5: earnings öncesi kısmi
```

### satış uygulama (SEN KARAR VER)

- tüm satışlar (acil, stratejik, kar alma) doğrudan uygulanır
- K-rule çapraz kontrol yap, gerekçeyi chat'te açıkla
- JSON güncelle, CSV kaydet, git push, telegram bildir
- onay istemek = kural ihlali

---

# 11. trade uygulama

### her SATIŞ için
1. portföy JSON'undan pozisyonu kaldır
2. `nakit.miktar += adet × satis_fiyati`
3. portföy `transactions[]` ekle (SATIŞ)
4. `data/transactions.csv` satır ekle
5. swing ise → `data/swing/closed.json`'a tam kayıt:
   - zorunlu: cikis_tarihi, cikis_fiyati, kar_zarar_yuzde, cikis_nedeni, sonuc, ders
   - yeni zorunlu (docs/POST_TRADE_REVIEW.md): process_score (1-5), root_cause, corrective_action, bias_detected
   - K-rule etiketleri: k_rules_applied, k_rules_violated, giris_filtre_sonuc
6. `data/summary.json` güncelle

### her ALIŞ için
1. portföy JSON `pozisyonlar[]` ekle — ZORUNLU alanlar:
   - **temel**: sembol, sektor, adet, maliyet_baz, giris_tarihi, guncel_fiyat
   - **tez + risk**: giris_nedeni (detaylı tez), katalizor (tetikleyen olay), tez (bull case), risk (bear case)
   - **seviyeler**: hedef_fiyat, stop_loss (K-06 max(2×ATR(14), %5)), hedef_agirlik
   - **K-rule etiketleri**: k_rules_applied (hangi filtreler geçti: K-04, K-05, K-13, K-17, K-18)
   - **giriş filtre sonucu**: giris_filtre_sonuc (GO/NO-GO 16 madde özet)
2. `nakit.miktar -= adet × fiyat`
3. portföy `transactions[]` ekle (ALIŞ) — tarih, sembol, adet, fiyat, tutar, sebep
4. `data/transactions.csv` satır ekle (ZORUNLU: date, type=BUY, symbol, shares, price, amount, reason)
5. swing ise → `data/swing/active.json`'a ekle (zorunlu: id, giris_tarihi, giris_fiyati, giris_sinyali, stop_loss, stop_tipi, kijun_sen, kumo_ust, kumo_alt, tenkan_sen, atr_14, giris_nedeni, katalizor, tez, risk, tarama_yontemi)
6. `data/summary.json` güncelle

### fiyat güncellemesi (trade yoksa da)
```python
for portfolio JSON:
    for position:
        # guncel_fiyat, gunluk_degisim_yuzde, guncel_deger, kar_zarar, agirlik_yuzde
    # toplam_deger, toplam_getiri_yuzde
```

---

# 12. watchlist güncellemesi

`data/watchlist.json` tek merkezi watchlist (portföy + swing + temel adaylar):
```
- mevcut adayların fiyatları
- tetiklenen giriş seviyesi → urgency=high + ⚠️ alarm
- her adayın hedef_portfoy alanı (swing/agresif/dengeli/temettü)
- artık geçersiz adaylar → haric_tutulanlar (neden ile)
- yeni aday (zorunlu: sembol, guncel_fiyat, sektor, hedef_portfoy, hedef_giris, hedef_fiyat, stop_loss, urgency, ekleme_tarihi)
```

⛔ `data/swing/watchlist.json` KALDIRILDI
⛔ portföy JSON'larında `watchlist[]` KULLANILMAZ

---

# 13. git commit + telegram

```bash
# trade varsa
git commit -m "[ALIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SATIŞ] Portföy - SEMBOL @FİYAT - neden"
git commit -m "[SWING-GİRİŞ] SEMBOL @FİYAT - neden"
git commit -m "[SWING-ÇIKIŞ] SEMBOL @FİYAT - sonuç +/-%X"

# trade yoksa
git commit -m "[GÜNCELLEME] FAZ 2 fiyat + watchlist - {tarih}"

# watchlist sadece
git commit -m "[WATCHLIST] yeni aday X / tetiklenen Y"
```

telegram (git push'tan SONRA):
```bash
python scripts/telegram_notify.py --type action --symbol SEMBOL --price FIYAT --action ALIŞ/SATIŞ --details "..."
python scripts/telegram_notify.py --type session --theme "faz 2 özet: [tema]"
```

---

# 14. session state handoff

```python
# data/session_state.json FAZ 2 bloğu ekle
state["faz2"] = {
    "zaman": "HH:MM",
    "spy_delta": ...,  # faz 1'den değişim
    "risk_ortami_delta": "...",
    "teknik_durum": {...},  # sembol bazlı RSI/SMA özet
    "sektor_rs": {...},
    "pm_delta": {...},
    "kararlar": {
        "alis": [...],
        "satis": [...],
        "tut": [...],
        "izle": [...]
    },
    "yeni_adaylar": [...],
    "go_no_go_sonuclari": {...},
    "faz3_icin_notlar": ["AMC earnings: ...", "trailing güncelle: ...", ...]
}
```

✅ `session_state.json` git'e commit EDİLİR (9 nisan 2026 mimari kararı): `[SESSION STATE] FAZ 2 - {tarih}`.

---

# 15. chat özet raporu

```markdown
## 🔔 FAZ 2 orta seans — {tarih} {saat} TR

### piyasa delta (faz 1'den beri)
SPY ±%X | QQQ ±%X | VIXY ±%X
risk ortamı: [aynı/değişti → neden]

### sektör RS
güçlü: ...
zayıf: ...

### portföy durumu
| portföy | değer | günlük% | durum |
|---|---|---|---|
| dengeli | $ | ±% | ✅/⚠️/🔴 |
| agresif | $ | ±% | ... |
| temettü | $ | ±% | ... |
| **toplam** | **$** | **±%** | |

dikkat: {RSI/SMA/stop yakın olanlar}

### swing
| ID | sembol | k/z% | stop mesafe | durum |
|---|---|---|---|---|

### aksiyonlar
{yapılan alış/satış/kısmi}
{trailing stop güncellemeleri}
{watchlist değişiklikleri}

### yeni adaylar (girilen/değerlendirilen)
{GO/NO-GO geçen adaylar + karar}

### prediction markets delta
{sabahtan ve faz 1'den değişim}

### faz 3'e notlar
{power hour'da bakılacak şeyler}
```

---

# SELF-VALIDATION

- [ ] FAZ 1 state okundu mu, tekrar veri çekmekten kaçınıldı mı?
- [ ] tüm teknik göstergeler (RSI + SMA50 + SMA200) çekildi mi?
- [ ] her yeni giriş için GO/NO-GO 16 madde tek tek geçti mi?
- [ ] her karar için düşünce zinciri (VERİ + KURAL + KARŞIT) yazıldı mı?
- [ ] K-rule çapraz kontrol yapıldı mı?
- [ ] korelasyon kontrolü (K-12 + K-17) yapıldı mı?
- [ ] JSON tutarlılığı OK (yatirim, guncel_deger, nakit, agirlik toplamı ~%100)?
- [ ] trailing stop sadece yukarı gitti mi?
- [ ] git push başarılı mı?
- [ ] `session_state.json` FAZ 2 bloğu yazıldı mı?
- [ ] rapor dosyası (.md) YAZILMADI mı?

---

> referans: `docs/K_RULES_QUICK_REF.md` (K-kural özetleri) | `docs/SESSION_REFERENCE.md` (versiyon, API opt) | `docs/DECISION_FRAMEWORK.md` (karşıt argüman, önyargı) | `docs/SWING_SYSTEM_V2.md` (swing v2.3)
> son güncelleme: 9 nisan 2026 v1.0 | finzora ai
