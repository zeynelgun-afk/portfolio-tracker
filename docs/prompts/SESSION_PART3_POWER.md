# SEANS İÇİ FAZ 3 — POWER HOUR PROMPT v1.0

> **çalışma zamanı**: NYSE son saat (TR 22:00-23:00)
> **öncelik**: FİNAL AKSİYONLAR — kapanışa yakın kâr alma, trailing final, AMC earnings, yarın hazırlık
> **ön koşul**: FAZ 1 ve FAZ 2 tamamlanmış, `data/session_state.json` güncel
> **çıktı**: final trade'ler + trailing final + AMC earnings listesi + yarın notları + git + telegram
> **dil**: küçük harf türkçe
> **kaynak atfı**: "finzora ai"
> **format**: em dash kullanma

> ⛔ **KRİTİK: SEANS İÇİNDE RAPOR (.md) YAZILMAZ**
> ⛔ **SEN KARAR VER**: power hour'da acele etme, ama kararlar onay beklemez.

---

## çalıştırma tetikleyicileri

- "faz 3"
- "power hour"
- "kapanışa yakın"
- "son saat"

---

## aşama listesi

- [ ] 1. FAZ 2 state okuma + delta
- [ ] 2. minimal batch-quote (sadece fiyat delta)
- [ ] 3. FAZ 2 kararlarının takibi (bekleyen aksiyonlar)
- [ ] 4. trailing stop final güncelleme
- [ ] 5. kapanış öncesi kâr alma değerlendirmesi (K-11)
- [ ] 6. AMC earnings listesi (bugün kapanıştan sonra)
- [ ] 7. twitter delta (faz 1'den bu yana yeni tweet)
- [ ] 8. yarın sabah raporu için flag'ler
- [ ] 9. after-hours izleme listesi
- [ ] 10. final JSON güncelleme + git push
- [ ] 11. telegram final özet
- [ ] 12. `session_state.json` FAZ 3 bloğu
- [ ] 13. chat final özet

---

# 1. FAZ 2 state okuma

```python
state = json.load(open("data/session_state.json"))
faz1 = state["faz1"]
faz2 = state["faz2"]
# faz2.faz3_icin_notlar → öncelikli yapılacaklar
```

**delta kontrol**:
- FAZ 2'den beri SPY/QQQ/VIX ne oldu?
- bekleyen aksiyonlar var mı (FAZ 2'de "ilk 15dk bekle" denenler)?
- karar matrisi sonuçları hala geçerli mi?

---

# 2. minimal batch-quote

sadece fiyat delta için:
```python
quotes = fmp_get("batch-quote", {"symbols": ",".join(unique_symbols)})
```

**teknik gösterge TEKRAR ÇEKİLMEZ** — FAZ 2'dekiler hala geçerli. sadece kapanışa yakın çok oynayan sembol varsa 1-2 spesifik RSI çek.

**toplam**: 1 FMP + 0-3 spesifik

---

# 3. FAZ 2 kararlarının takibi

FAZ 2'de alınan ama power hour'a ertelenen kararlar:
- "kapanışa yakın kâr al" → fiyat hala geçerli mi?
- "son saat rebalance" → uygula
- "trailing sıkılaştır" → uygula
- "FAZ 3'te kontrol" → kontrol et

her bekleyen aksiyon için düşünce zinciri (VERİ + KURAL + KARŞIT) yaz.

---

# 4. trailing stop final güncelleme

> K-07 kâr kilidi: `docs/K_RULES_QUICK_REF.md`

tüm aktif swing pozisyonları için FMP historical data ile:
```python
for swing in active.json:
    atr14 = hesapla_atr(symbol, 14)
    highest_high = hesapla_highest_high(symbol, giris_tarihi)
    
    kar_pct = ((guncel - giris) / giris) × 100
    if kar_pct < 7:
        multiplier = 3  # normal
    elif kar_pct < 15:
        multiplier = 2  # kâr kilidi
    else:
        multiplier = 1.5  # agresif kilit
    
    yeni_stop = highest_high - (multiplier × atr14)
    
    # ASLA aşağı çekme — matematik tek yön
    if yeni_stop > swing.stop_loss:
        swing.stop_loss = yeni_stop
        swing.stop_tipi = f"chandelier {multiplier}×ATR"
```

portföy pozisyonları için K-11 katman 1 kâr kilidi kontrolü:
```python
for position in portfolios:
    if position.RSI >= 70 and position.kar_pct >= 15:
        # K-11 katman 1: kâr kilidi aktif (max(2×ATR, 20SMA altı))
        # K-07'ye göre öncelikli (sıkı 20SMA)
        hesapla_ve_guncelle_kar_kilidi()
```

### ⛔ stop asla aşağı çekilmez

override yapılmaz. kural: K-06 ve K-07 hiyerarşinin tepesinde.

---

# 5. kapanış öncesi kâr alma (K-11)

power hour'da RSI kontrolü özellikle önemli — kapanış fiyatı teknik göstergeleri kilitler.

```
K-11 katman 2 baskın tetik:
- RSI 80+ → %25-30 kısmi sat (acil)
- RSI 75+ VE negatif divergence → %25 kısmi
- RSI 75+ VE 20SMA altı → %25 kısmi

K-11 katman 3:
- 50SMA altı kapanış yaklaşıyor → tam çık
- chandelier trailing tetik → tam çık
```

**seans içi satış uygulaması (SEN KARAR VER)**:
- onay beklemez
- gerekçeyi chat'te açıkla
- JSON + CSV + git + telegram

---

# 6. AMC earnings listesi (bugün kapanıştan sonra)

**FMP earnings-calendar** ile filtreleme:
```python
earnings = fmp_get("earnings-calendar", {"from": TODAY, "to": TODAY})
# filtre: time == "amc" veya "after market close"
# market cap filter güvenilmez → bilinen sembol listesiyle eşleştir
# veya epsEstimated > 0.5 filtresi
```

**portföy/swing/watchlist etkisi**:
- portföy pozisyonunda olan → K-16 skor hesapla, gerekirse kısmi çık
- swing pozisyonunda olan → K-05 kontrol (≤2 iş günü öncesi çıkış olmalıydı, olmadıysa **kural ihlali**)
- watchlist'te olan → post-earnings drift (PEAD) değerlendir

**çıktı**: AMC earnings listesi + etki notu (yarın sabah raporu için)

---

# 7. twitter delta (faz 1'den beri yeni tweet)

**API**: RapidAPI twitter241
**farklı parametre**: FAZ 1'deki son_tweet_id'den sonrasını çek

```python
for hesap in takip_listesi:
    last_id = state["faz1"]["twitter_ozet"][hesap]["last_id"]
    yeni = get_user_tweets(hesap, since_id=last_id)
    if yeni:
        portfoy_iliskili_filtrele(yeni)
```

**öncelik**:
- portföy sembolü geçiyor mu → acil bildir
- genel piyasa yorumu → özet
- RyanDetrick mevsimsellik / StockSavvyShay ivme → watchlist güncelle

### ⛔ VERİ KURALI
twitter verisi rapor dosyasına yazılmaz. chat context + analize organik entegre.

**toplam**: ~10-20 RapidAPI (delta)

---

# 8. yarın sabah raporu için flag'ler

seans kapanmadan not düş (yarın FAZ1 SABAH raporunda kullanılacak):

```
yarın için flag'ler:
- [ ] AMC earnings takip: {SEMBOL1, SEMBOL2, ...}
- [ ] açılışta izlenecek: {SEMBOL} — neden
- [ ] stop yakınında geceleyen: {SEMBOL} — mesafe %X
- [ ] yeni watchlist adayı: {SEMBOL} — katalist
- [ ] makro veri beklentisi: {CPI/PPI/FOMC/NFP}
- [ ] jeopolitik olay takibi: {konu}
- [ ] gap riski: {SEMBOL} — earnings/haber
```

bu flag'ler `session_state.json` içinde `yarin_flag_listesi[]` alanına yazılır. yarın sabah FAZ1 SABAH promptu bunu okur.

---

# 9. after-hours izleme listesi

kapanıştan sonra after-hours'ta izlenecek hisseler:
- AMC earnings açıklayacaklar (volatilite bekleniyor)
- gün içinde gap yapan ve teyit için AH izlenecekler
- haber beklenen (FDA, contract, M&A söylentileri)

**not**: after-hours fiyatları FMP `aftermarket-quote` endpoint'i seans dışında 0 döndürür. web search kullan.

---

# 10. final JSON güncelleme + git push

### fiyat güncelleme (son güncel değerler)

```python
for portfolio in [balanced, aggressive, dividend]:
    for position:
        # son batch quote değerleriyle güncelle
# swing active.json aynı
# data/summary.json güncelle
```

**not**: bu "final" fiyat değil — resmi kapanış fiyatı yarın 14:00 sabah raporunda işlenecek. bu sadece power hour snapshot'ı.

### trade uygulaması

power hour'da yapılan tüm alış/satış:
1. JSON pozisyon ekle/çıkar
2. nakit güncelle
3. transactions[] + CSV
4. swing closed.json (tam kayıt: ders, process_score, root_cause, corrective_action, bias_detected, k_rules_applied, k_rules_violated, giris_filtre_sonuc)
5. summary.json

### git commit

```bash
# trade varsa
git commit -m "[SATIŞ] Portföy - SEMBOL @FİYAT - K-11 katman 2 / RSI 82"
git commit -m "[SWING-ÇIKIŞ] SEMBOL @FİYAT - chandelier kilit / +%X"

# trailing güncelleme varsa
git commit -m "[TRAILING] Swing chandelier stop final güncelleme - {tarih}"

# sadece fiyat
git commit -m "[GÜNCELLEME] FAZ 3 power hour snapshot - {tarih}"
```

### conflict pattern
```
git rebase --abort → git reset --hard origin/main → git pull → python ile değişiklikleri yeniden uygula → add -A && commit && push
```

---

# 11. telegram final özet

```bash
# aksiyon varsa
python scripts/telegram_notify.py --type action --symbol SEMBOL --price FIYAT --action SATIŞ/KAR_AL --details "K-11 katman 2 tetik"

# seans sonu özet
python scripts/telegram_notify.py --type session --theme "faz 3 özet: [tema], yarın takip: {AMC earnings}"
```

**gönderilmez**: sistem güncellemeleri, info severity K-script alert'leri

---

# 12. session state handoff

```python
# data/session_state.json FAZ 3 bloğu
state["faz3"] = {
    "zaman": "HH:MM",
    "spy_kapanisa_yakin": ...,
    "aksiyonlar": {
        "kar_alma": [...],
        "trailing_guncelleme": [...],
        "final_satis": [...]
    },
    "amc_earnings": [{"sembol": ..., "time": "amc", "eps_est": ...}],
    "twitter_delta": [...],
    "after_hours_izleme": [...],
    "yarin_flag_listesi": [
        {"tip": "amc_earnings", "sembol": ..., "not": ...},
        {"tip": "gap_riski", "sembol": ..., "neden": ...},
        {"tip": "stop_yakin_gece", "sembol": ..., "mesafe": ...}
    ]
}

state["seans_ozet"] = {
    "tarih": TODAY,
    "toplam_trade_sayisi": ...,
    "net_kar_zarar": ...,
    "aktif_pozisyon_sayisi": ...,
    "nakit_oran": ...
}
```

✅ `session_state.json` git'e commit EDİLİR (9 nisan 2026 mimari kararı): `[SESSION STATE] FAZ 3 - {tarih}`. Yarın sabah PART 1 bu dosyayı git pull sonrası okur, `yarin_flag_listesi[]` bölüm 0.5'e yansır.

---

# 13. chat final özet

```markdown
## 🔔 FAZ 3 power hour — {tarih} {saat} TR

### gün özeti
SPY $ (±%) | QQQ $ (±%) | VIXY $ (±%)
gün teması: [tek cümle]

### bugün yapılan trade'ler (3 faz toplam)
| zaman | tip | sembol | fiyat | neden | K-rule |
|---|---|---|---|---|---|

### portföy final
| portföy | açılış | kapanış | günlük % | durum |
|---|---|---|---|---|

### power hour aksiyonları
{kâr alma, trailing güncelleme, final satış}

### AMC earnings (bugün kapanıştan sonra)
- {SEMBOL}: eps est $X, portföy etkisi [var/yok]

### twitter delta öne çıkanlar
{faz 1'den beri önemli yeni tweet'ler}

### after-hours izleme
{izlenecek hisseler ve neden}

### yarın flag listesi
- [ ] {AMC earnings takip}
- [ ] {stop yakın geceleyen}
- [ ] {açılışta izlenecek}
- [ ] {makro veri beklenen}

### sonraki kontrol
yarın TR 14:00 → sabah raporu (FAZ1 SABAH)
```

---

# SELF-VALIDATION

- [ ] FAZ 2 state okundu mu?
- [ ] trailing stop sadece yukarı gitti mi? (asla aşağı)
- [ ] K-11 kapanış öncesi kâr alma kontrolü yapıldı mı?
- [ ] AMC earnings listesi çıkarıldı mı?
- [ ] K-05 ihlali var mı? (swing pozisyonu earnings ≤2 iş günü içinde mi?)
- [ ] twitter delta çekildi mi?
- [ ] yarın flag listesi `session_state.json`'a yazıldı mı?
- [ ] JSON tutarlılığı OK?
- [ ] git push başarılı mı?
- [ ] telegram özet gönderildi mi?
- [ ] rapor dosyası (.md) YAZILMADI mı?

---

> referans: `docs/K_RULES_QUICK_REF.md` (K-kural özetleri) | `docs/SESSION_REFERENCE.md` (versiyon, API opt) | `docs/SWING_SYSTEM_V2.md` (swing v2.3)
> kapanış raporu yarın sabah `DAILY_PART2_CLOSING.md` ile yazılır (bugün için), `DAILY_PART1_SABAH.md` ile planlanır (yarın için)
> son güncelleme: 9 nisan 2026 v1.0 | finzora ai
