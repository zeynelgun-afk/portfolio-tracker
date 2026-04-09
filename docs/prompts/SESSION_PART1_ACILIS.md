# SEANS İÇİ FAZ 1 — AÇILIŞ PROMPT v1.0

> **çalışma zamanı**: NYSE açılışından sonra ilk 60 dakika (TR 16:30-17:30, yaz saati)
> **öncelik**: ACİL KONTROL — gap, stop tetiği, BMO earnings, twitter
> **ön koşul**: o günün sabah raporu yazılmış olmalı (`DAILY_SABAH_{TODAY}.md`)
> **çıktı**: acil aksiyonlar + `data/session_state.json` FAZ 1 bloğu + JSON fiyat güncelleme + git push
> **dil**: küçük harf türkçe, teknik terimler ingilizce kalabilir
> **kaynak atfı**: sadece "finzora ai"
> **format**: em dash kullanma, narrative akış

> ⛔ **KRİTİK: SEANS İÇİNDE RAPOR (.md) YAZILMAZ**
> json/csv güncellemeleri repoya gider, rapor dosyası asla.
> seans içi gözlemler sadece chat'te kalır.

> ⛔ **SEN KARAR VER**: tüm aksiyonlar onay beklemeden uygulanır. K-rule kontrolü yaptıktan sonra son karar claude'da. onay istemek = kural ihlali.

---

## çalıştırma tetikleyicileri

kullanıcı şunlardan birini söylediğinde bu prompt devreye girer:
- "piyasa açıldı, kontrol et"
- "faz 1"
- "açılış kontrolü"
- "seans başladı"

---

## aşama listesi (sırayla, atlama yasak)

- [ ] 1. açılış verisi (endeks + VIX + emtia + treasury)
- [ ] 2. portföy batch-quote + gap tespiti
- [ ] 3. stop-loss tetik taraması (K-06 + K-09)
- [ ] 4. BMO earnings sonuçları kontrolü
- [ ] 5. twitter takip listesi ilk çekim
- [ ] 6. sabah planı acil aksiyon uygulaması
- [ ] 7. JSON fiyat güncellemesi (tüm portföyler + swing)
- [ ] 8. git commit + push
- [ ] 9. telegram action bildirimleri (varsa)
- [ ] 10. `data/session_state.json` FAZ 1 bloğu yaz
- [ ] 11. chat özet raporu

---

# 1. açılış verisi

```python
# endeksler + VIX proxy
spy = fmp_get("quote", {"symbol": "SPY"})
qqq = fmp_get("quote", {"symbol": "QQQ"})
dia = fmp_get("quote", {"symbol": "DIA"})
iwm = fmp_get("quote", {"symbol": "IWM"})
vixy = fmp_get("quote", {"symbol": "VIXY"})  # VIX proxy

# emtia
uso = fmp_get("quote", {"symbol": "USO"})   # petrol
gld = fmp_get("quote", {"symbol": "GLD"})   # altın
usdtry = fmp_get("quote", {"symbol": "USDTRY"})
```

**changesPercentage güvenilmezse** manuel: `((price - previousClose) / previousClose) × 100`

**websearch** (sadece 1 arama, sabah raporunda beklenen özel olay varsa):
- "stock market open {DATE}" veya sabah raporundaki özel konu

**toplam**: ~7 FMP + 0-1 websearch

---

# 2. portföy batch-quote + gap tespiti

```python
# 3 portföy + swing active sembollerini birleştir
symbols = kullan_json_listelerini(balanced, aggressive, dividend, swing_active)
unique = list(set(symbols))
quotes = fmp_get("batch-quote", {"symbols": ",".join(unique)})
```

her sembol için gap hesapla:
```
gap% = ((acilis_fiyati - dun_kapanis) / dun_kapanis) × 100
```

**gap sınıflandırma**:
- gap > +%5 → 🚀 GAP-UP, ilk 15dk bekle, volatilite düşsün
- gap > +%3 → ⚠️ pozitif gap, izle
- gap < -%3 → ⚠️ negatif gap, stop yakınlığı kontrol et
- gap < -%5 → 🔴 GAP-DOWN, acil stop/K-09 değerlendir

**toplam**: 1 FMP

---

# 3. stop-loss tetik taraması (K-06 + K-09)

> K-rule detayları: `docs/K_RULES_QUICK_REF.md`

### K-06 kontrolü (tüm pozisyonlar)

```
her pozisyon için:
  if guncel_fiyat <= stop_loss:
    → 🔴 K-06 TETİK, %100 SAT
    → override YASAK
    → duygusal karar yok
```

### K-09 yakınlık kontrolü (fiyat stop'a <%2 olanlar)

```
her pozisyon için:
  mesafe = (guncel_fiyat - stop_loss) / stop_loss
  if 0 < mesafe < 0.02:
    → scripts/k09_proximity_check.py SYMBOL çalıştır
    → 4 kontrol: RSI / hacim / SPY+VIX / sektör ETF
    → 3+ negatif = EXIT_NOW
    → 2 negatif = WAIT_STOP
    → 0-1 negatif = TUT
```

k09_proximity_check.py zaten telegram'a kritik alert gönderir.

---

# 4. BMO earnings sonuçları

açılıştan önce açıklanan BMO (before market open) kazançlar fiyatı etkilemiş olabilir:

```python
# sabah raporundaki BMO earnings listesini oku
# fiyat etkisini kontrol et
# büyük gap varsa → haber doğrulaması yap
```

**websearch** (BMO earnings sayısına göre 0-3 arama):
- "{SYMBOL} earnings {DATE} results"

**etki değerlendirmesi**:
- portföy pozisyonu mu? → `scripts/k16_sell_the_news_score.py SYMBOL` çalıştır
- swing pozisyonu mu? → K-05 zaten 2+ gün öncesi çıkış yapmış olmalı, çıkmadıysa hatadır
- watchlist'teki mi? → izle, giriş sinyali oluştu mu kontrol et

---

# 5. twitter takip listesi (ilk çekim)

**API**: RapidAPI → twitter241.p.rapidapi.com
**key**: `fe410e5222msh20c82b1bc9f4905p10ad02jsnb1c2402c92b7`
**endpoint**: `GET /user-tweets?user={numeric_id}&count=20`

**takip listesi** (10 hesap):
```
@CheddarFlow       → kurumsal para akışı / opsiyon
@berkdemirkiran_   → türk finans yorumcusu
@yatirim           → türk finans yorumcusu
@onestoploss       → teknik analiz / trade fikirleri
@StockSavvyShay    → ivme hisse önerileri
@BerkUcmz          → türk finans yorumcusu
@TrendSpider       → teknik analiz
@Jake__Wujastyk    → ivme trader
@RyanDetrick       → mevsimsellik / istatistik
@VolSignals        → volatilite / opsiyon
```

### filtreleme kuralı
- portföy sembolleri geçiyor mu? → öne çıkar
- genel piyasa yorumu mu? → özet
- spam/reklam → atla

### ⛔ VERİ KURALI
twitter verisi **claude context'ine girer, rapora yazılmaz**. insight organik olarak analize işlenir.

**toplam**: ~20 RapidAPI çağrısı

---

# 6. sabah planı acil aksiyon uygulaması

sabah raporunu oku: `reports/daily/DAILY_SABAH_{TODAY}.md`

acil aksiyon listesini tara:
- "açılışta SEMBOL sat" → uygula
- "gap-down olursa SEMBOL K-09 çalıştır" → koşul sağlandıysa uygula
- "açılışta SEMBOL giriş" → FAZ 2'ye ertele (ilk 15dk volatilitesi sonrası)

**kural**: FAZ 1'de yeni giriş yapılmaz. ilk 60 dakika sadece çıkış ve stop yönetimi içindir.

**istisna**: sabah planında açıkça "açılışta giriş" yazılıysa + gap durumu uygunsa + K-13 ve K-17/K-18 temizse → uygulanır.

---

# 7. JSON fiyat güncellemesi

```python
for portfolio in [balanced, aggressive, dividend]:
    for position in portfolio.pozisyonlar:
        position.guncel_fiyat = quotes[sym].price
        position.gunluk_degisim_yuzde = hesap_veya_fmp
        position.guncel_deger = adet × guncel_fiyat
        position.kar_zarar = guncel_deger - yatirim
        position.kar_zarar_yuzde = (kar_zarar / yatirim) × 100
        position.agirlik_yuzde = (guncel_deger / toplam_deger) × 100
        position.son_guncelleme = datetime.now().isoformat()
    
    portfolio.toplam_deger = sum(p.guncel_deger) + nakit.miktar
    portfolio.toplam_getiri_yuzde = ((toplam_deger - baslangic) / baslangic) × 100

for swing_position in data/swing/active.json:
    swing_position.guncel_fiyat = quotes[sym].price
    swing_position.guncel_kar_zarar_yuzde = ...
    swing_position.tutulan_gun = (today - giris_tarihi).days
    swing_position.son_guncelleme = datetime.now().isoformat()

data/summary.json güncelle
```

**trade yapıldıysa ek işlemler** (al/sat varsa):
1. pozisyon ekle/çıkar
2. nakit güncelle
3. portföy `transactions[]` ekle
4. `data/transactions.csv` satır ekle
5. swing çıkışıysa → `data/swing/closed.json` (tüm zorunlu alanlar: cikis_tarihi, cikis_fiyati, kar_zarar_yuzde, cikis_nedeni, sonuc, ders, process_score, root_cause, corrective_action, bias_detected, k_rules_applied, k_rules_violated, giris_filtre_sonuc)

---

# 8. git commit + push

```bash
# trade varsa
git commit -m "[SATIŞ] Portföy - SEMBOL @FİYAT - K-06 stop tetik / gap-down"
git commit -m "[SWING-ÇIKIŞ] SEMBOL @FİYAT - K-09 3 negatif / erken çıkış -%X"

# trade yoksa
git commit -m "[GÜNCELLEME] FAZ 1 fiyat güncelleme - {tarih}"
```

conflict pattern (auto-updater çakışması):
```
git rebase --abort → git reset --hard origin/main → git pull → python script ile değişikleri yeniden uygula → git add -A && commit && push
```

---

# 9. telegram bildirimleri (git push'tan SONRA)

```bash
# aksiyon varsa
python scripts/telegram_notify.py --type action --symbol SEMBOL --price FIYAT --action ALIŞ/SATIŞ/STOP/KAR_AL --details "detay"

# yoksa session özeti opsiyonel
python scripts/telegram_notify.py --type session --theme "faz 1 özet: [tema]"
```

**telegram'a gönderilmez**: sistem/kural güncellemeleri, stop yakın info uyarıları (warning/critical hariç), K-script info severity

---

# 10. session state handoff

```python
# data/session_state.json FAZ 1 bloğunu yaz
{
  "tarih": "YYYY-MM-DD",
  "son_guncelleme": "ISO",
  "faz1": {
    "zaman": "HH:MM",
    "spy": {"fiyat": ..., "degisim": ...},
    "qqq": {...},
    "vixy": {...},
    "risk_ortami": "RISK-ON/OFF",
    "gap_raporu": [{"sembol": "...", "gap_pct": ..., "sinif": "..."}],
    "acil_aksiyonlar": ["SEMBOL satıldı K-06", ...],
    "bmo_earnings": [{"sembol": "...", "sonuc": "beat/miss", "etki": "..."}],
    "twitter_ozet": [{"hesap": "...", "sembol": "...", "not": "..."}],
    "k06_tetikler": [],
    "k09_tetikler": [],
    "sabah_plani_uygulandi": true/false,
    "faz2_icin_notlar": ["..."]
  }
}
```

bu dosya FAZ 2 başlangıcında okunur, ham veriyi tekrar çekmek gerekmez.

⛔ `session_state.json` git'e commit EDİLMEZ. `.gitignore`'a ekli (veya eklenmeli). local çalışma dosyası.

---

# 11. chat özet raporu

```markdown
## 🔔 FAZ 1 açılış — {tarih} {saat} TR

### piyasa
SPY $XXX (±%X) | QQQ $XXX (±%X) | VIXY $XXX (±%X)
risk ortamı: RISK-ON/OFF | sabahtan değişim: [aynı/değişti → neden]

### acil aksiyonlar
{varsa 🔴 SATIŞ listesi}
{varsa 💰 KAR AL listesi}
{yoksa: "acil aksiyon yok, pozisyonlar güvende"}

### gap durumu
{portföy hisselerinde gap > %3 olanlar}

### BMO earnings
{sabah açıklanan earnings sonuçları ve etki}

### twitter öne çıkanlar (faz 1)
{10 hesap özetinden seçilmiş 3-5 önemli gelişme}

### K-06 / K-09 tetikler
{varsa listele, alınan aksiyon}

### faz 2'ye notlar
{faz 2 başlarken dikkat edilecek şeyler}
```

---

# SELF-VALIDATION

- [ ] tüm aşamalar sırayla tamamlandı mı?
- [ ] stop tetiklenen pozisyon kaldı mı? (kaldıysa kural ihlali)
- [ ] JSON güncellemesi tutarlı mı? (yatirim, guncel_deger, nakit, agirlik)
- [ ] git push başarılı mı?
- [ ] telegram aksiyon bildirimleri gitti mi?
- [ ] `session_state.json` FAZ 1 bloğu yazıldı mı?
- [ ] rapor dosyası (.md) YAZILMADI mı? (yazıldıysa kural ihlali)

---

> referans: `docs/K_RULES_QUICK_REF.md` (K-kural özetleri) | `docs/SESSION_REFERENCE.md` (versiyon, karşılaştırma tabloları, API optimizasyon)
> son güncelleme: 9 nisan 2026 v1.0 | finzora ai
