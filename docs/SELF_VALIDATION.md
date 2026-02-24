# SELF-VALIDATION SİSTEMİ

> **versiyon**: 1.0 | **oluşturma**: 24 şubat 2026
> **amaç**: her veri toplama, analiz ve karar adımından sonra çıktıyı doğrulama
> **ilham**: dexter (virattt/dexter) multi-agent validation mimarisi
> **entegrasyon**: DAILY_REPORT_PROMPT + SESSION_ACTION_PROMPT

---

## NEDEN GEREKLİ?

mevcut sistem sadece "hesaplama tutarlılığı" kontrol ediyor (yatirim = adet × maliyet_baz).
ama şu soruları sormuyoruz:

- FMP'den gelen fiyat mantıklı mı? (sıfır, negatif, %50 gap olabilir)
- analiz çıktısı soruyla tutarlı mı?
- karar önermesi verilerle destekleniyor mu?
- rapordaki bilgiler birbirleriyle çelişiyor mu?

---

## 3 KATMANLI VALIDATION

```
KATMAN 1: VERİ DOĞRULAMA (data validation)
  → FMP'den gelen ham veri mantıklı mı?
  → her API çağrısından hemen sonra

KATMAN 2: ANALİZ DOĞRULAMA (analysis validation) 
  → hesaplamalar ve yorumlar tutarlı mı?
  → bölüm yazıldıktan sonra

KATMAN 3: KARAR DOĞRULAMA (decision validation)
  → öneriler verilerle destekleniyor mu?
  → aksiyon planı yazıldıktan sonra
```

---

## KATMAN 1 — VERİ DOĞRULAMA

her FMP API çağrısından sonra otomatik kontrol:

### 1a. boş/hatalı yanıt kontrolü

```python
def validate_fmp_response(endpoint, data, symbol=None):
    # boş yanıt
    if data is None or data == []:
        log(f"⚠️ {endpoint} boş döndü ({symbol})")
        return False
    
    # hata mesajı
    if isinstance(data, dict) and 'Error Message' in data:
        log(f"🔴 {endpoint} hata: {data['Error Message']}")
        return False
    
    return True
```

### 1b. fiyat mantık kontrolü

```
quote/batch-quote yanıtı için:

✓ price > 0 (negatif/sıfır fiyat → hatalı veri)
✓ price < 100,000 (mantıksız yüksek → muhtemelen crypto karışmış)
✓ changesPercentage > -50% VE < +50% (bir günde ±%50 → kontrol et)
✓ volume > 0 (sıfır hacim → piyasa kapalı mı, delisted mi?)
✓ marketCap > 0 (profil verisi için)

tetiklenirse:
- |changesPercentage| > %20 → "⚠️ SEMBOL dün %XX hareket etmiş, haber kontrol et"
- |changesPercentage| > %50 → "🔴 SEMBOL %XX — veri hatası olabilir, teyit et"
- price = 0 veya null → "🔴 SEMBOL fiyat verisi yok — skip, önceki fiyatı koru"
```

### 1c. tarih kontrolü

```
✓ FMP'den gelen fiyat tarihi dünün tarihi mi?
  - hafta sonu/tatil: cuma kapanışı gelir, beklenen
  - iş günü ama tarih eski → "⚠️ FMP verisi güncel değil"

✓ sektör performans tarihi istenen tarih mi?
  - date param gönderdik ama başka tarih döndü → uyar

✓ earnings calendar tarihleri gelecekte mi?
  - geçmiş tarihli earnings → skip
```

### 1d. teknik gösterge mantık kontrolü

```
✓ RSI: 0-100 arası (dışındaysa hatalı veri)
✓ SMA: > 0 ve hisse fiyatının %80-%120 bandında makul (SMA200 = $500, fiyat = $50 → kontrol et)
✓ MACD: signal ve histogram mevcut mu?
```

### 1e. çapraz doğrulama

```
✓ batch-quote fiyatı ≈ historical-price-eod son gün fiyatı (varsa)
✓ profile'daki sektör = bizim JSON'daki sektör (değiştiyse not düş)
✓ market cap = price × shares outstanding (büyük sapma → uyar)
```

---

## KATMAN 2 — ANALİZ DOĞRULAMA

her rapor bölümü yazıldıktan sonra kendi kendine kontrol:

### 2a. sayısal tutarlılık

```
✓ portföy toplam = tüm pozisyonların toplamı + nakit
✓ ağırlık yüzdeleri toplamı ≈ %100 (±%0.5 tolerans)
✓ kar_zarar = guncel_deger - yatirim (her pozisyon için)
✓ kar_zarar_yuzde = (kar_zarar / yatirim) × 100
✓ yatirim = adet × maliyet_baz (sabit, asla değişmez)
✓ nakit: trade olmadıysa değişmemiş olmalı
✓ summary toplam = 4 portföy toplamı (kesin eşitlik)
```

### 2b. metin-veri uyumu

```
raporda yazdığın yorum, verilere dayanıyor mu?

✓ "SPY düştü" diyorsan → SPY changesPercentage < 0 olmalı
✓ "enerji sektörü güçlü" diyorsan → enerji RS > 0 olmalı
✓ "RSI aşırı alımda" diyorsan → RSI > 70 olmalı
✓ "SMA200 üzerinde" diyorsan → fiyat > SMA200 olmalı
✓ "temettü portföyü lider" diyorsan → en yüksek k/z% temettüde olmalı

tetiklenirse: ifadeyi düzelt veya veriyi yeniden kontrol et
```

### 2c. trend tutarlılığı (önceki raporla)

```
✓ dünkü raporda "risk-off" dedik, bugün "risk-on" diyorsak → neden değişti, açıkla
✓ dünkü raporda "NEM stop yakın" dedik → bugün NEM durumu ne? takip edildi mi?
✓ dünkü raporda "AVGO $315-320 giriş" dedik → fiyat o aralığa geldi mi? atlanmadı mı?
✓ bir pozisyon hakkında 3 gün üst üste "izle" dediysen → artık somut karar ver
```

### 2d. swing trade özel doğrulamalar

```
✓ trailing stop ASLA düşmemiş (bugünkü ≥ dünkü)
✓ trailing stop hesaplaması: zirve × 0.95 = trailing
✓ tutulan_gun = bugün - giris_tarihi (gün sayısı doğru mu?)
✓ hedef_fiyat > giris_fiyati × 1.10 (min %10 hedef)
✓ stop_loss < giris_fiyati × 0.95 (max %5 zarar)
✓ R:R ≥ 2:1 (hedef/stop oranı yeterli mi?)
✓ aktif pozisyon sayısı ≤ 10
✓ SWING-ID sıralı ve unique
```

---

## KATMAN 3 — KARAR DOĞRULAMA

aksiyon önerisi yazıldıktan sonra her öneriyi test et:

### 3a. öneri-veri tutarlılığı

```
her aksiyon önerisi için şu soruyu sor:
"bu öneriyi destekleyen veri var mı?"

✓ "SAT" önerisi → stop tetiklendi mi? tez bozuldu mu? somut neden var mı?
✓ "AL" önerisi → RSI, SMA, momentum, temel veriler giriş destekliyor mu?
✓ "TUT" önerisi → kritik bir tetikleyici atlanmadı mı?

kırmızı bayrak:
- veri olmadan "hissediyorum" tarzı öneri → düzelt
- çelişkili veri varken tek yönlü öneri → her iki tarafı göster
- "izle" demek ama somut tetikleyici belirtmemek → tetikleyici ekle
```

### 3b. portföy uyum kontrolü

```
yeni pozisyon önerisi için:
✓ hangi portföye öneriliyor → o portföyün kurallarıyla uyumlu mu?
  - agresif portföye temettü hissesi önerme
  - temettü portföyüne growth/momentum hissesi önerme
  - rotasyon portföyüne bireysel hisse önerme (ETF olmalı)
  - dengeli portföye tek sektörde %30+ yoğunlaşma yaratacak hisse önerme

✓ nakit yeterli mi? (önerilen alım tutarı > mevcut nakit → uyar)
✓ max pozisyon sayısı aşılıyor mu?
```

### 3c. risk tutarlılığı

```
✓ "risk-off" ortamında agresif alım önerme
✓ "risk-on" ortamında tüm defensive pozisyonları satma önerme
✓ aynı sektörde 3+ pozisyon açma (portföy + swing toplamı)
✓ bir günde portföyün %20'sinden fazlasını hareket ettirme
✓ stop-loss'suz pozisyon önerme (her öneride stop seviyesi zorunlu)
```

### 3d. bias kontrolü (en kritik)

```
insan gibi düşün: hangi cognitive bias'lar sızabilir?

✓ TEYIT YANILGISI (confirmation bias):
  - sadece "al" destekleyen verileri mi topladın?
  - karşıt argümanları göz ardı ettin mi?
  → çözüm: her "al" önerisinde 1 karşıt risk yaz

✓ KAYIP KORKUSU (loss aversion):
  - zarar eden pozisyonu "kesinlikle düzelir" diye mi tutuyorsun?
  - tez bozulmuş ama satmaktan kaçınıyor musun?
  → çözüm: tezi tekrar oku, hala geçerli mi dürüstçe değerlendir

✓ AŞIRI GÜVEN (overconfidence):
  - "%100 yükselecek" tarzı kesin ifadeler mi kullanıyorsun?
  → çözüm: her tahminde olasılık aralığı ver, "olabilir" dil kullan

✓ YAKINLIK YANILGISI (recency bias):
  - dünkü büyük hareket yüzünden uzun vadeli stratejiyi mi değiştiriyorsun?
  → çözüm: 1 günlük hareket ≠ trend dönüşü, 3-5 günlük veri iste

✓ FOMO:
  - "herkes alıyor, biz de alalım" mantığı mı?
  - biggest-gainers'ta gördüğün hisseyi hemen önerme
  → çözüm: zaten %10+ yükselmiş hisseyi "fırsat" olarak sunma
```

---

## UYGULAMA — PROMPTLARA ENTEGRASYON

### günlük rapor (DAILY_REPORT_PROMPT)

```
BÖLÜM 0 (kapanış değerlendirmesi):
  → KATMAN 2 (sayısal tutarlılık) — JSON güncelleme sonrası
  → KATMAN 2c (trend tutarlılığı) — dünkü raporla karşılaştırma

BÖLÜM 1 (piyasa):
  → KATMAN 1 (veri doğrulama) — FMP verileri geldikten sonra
  → KATMAN 2b (metin-veri uyumu) — bölüm yazıldıktan sonra

BÖLÜM 2 (portföy):
  → KATMAN 1 (fiyat mantık kontrolü) — batch-quote sonrası
  → KATMAN 2a (sayısal tutarlılık) — hesaplamalar sonrası
  → KATMAN 2d (swing özel) — swing bölümü sonrası

BÖLÜM 6 (aksiyon planı):
  → KATMAN 3 (karar doğrulama) — her aksiyon önerisi için
  → KATMAN 3d (bias kontrolü) — bölüm sonu self-check
```

### seans içi (SESSION_ACTION_PROMPT)

```
AŞAMA 1 (veri toplama):
  → KATMAN 1 tümü — her FMP çağrısından sonra

AŞAMA 2 (durum tespiti):
  → KATMAN 2b (metin-veri uyumu) — yorumlar verilere dayanıyor mu

AŞAMA 3 (aksiyon kararları):
  → KATMAN 3 tümü — her al/sat/tut kararı için
  → KATMAN 3d (bias kontrolü) — karar öncesi

AŞAMA 4 (uygulama):
  → KATMAN 2a (sayısal tutarlılık) — JSON güncelleme sonrası
```

---

## VALIDATION ÇIKTI FORMATI

doğrulama sonuçlarını rapor sonuna ekle:

```markdown
### validation özeti

| katman | kontrol | sonuç | not |
|--------|---------|-------|-----|
| veri | FMP yanıtları | ✅ 45/45 geçerli | — |
| veri | fiyat mantık | ⚠️ 44/45 | NEM %22 hareket — haber teyidi yapıldı |
| analiz | sayısal tutarlılık | ✅ geçti | — |
| analiz | metin-veri uyumu | ✅ geçti | — |
| analiz | trend tutarlılığı | ⚠️ | risk ortamı değişti, nedeni açıklandı |
| karar | öneri-veri tutarlılığı | ✅ geçti | — |
| karar | portföy uyumu | ✅ geçti | — |
| karar | bias kontrolü | ✅ geçti | — |
```

kısa versiyon (normal günler): `validation: ✅ tüm kontroller geçti`
detaylı versiyon (sorun varsa): yukarıdaki tablo

---

## ÖNEMLİ KURALLAR

1. validation başarısız olursa → veriyi/analizi düzelt, sonra devam et
2. validation sonucunu gizleme — sorun varsa raporda göster
3. validation için ekstra API çağrısı yapma — mevcut veriyle doğrula
4. her rapor ve seans güncellmesinde en az KATMAN 1 + 2a zorunlu
5. KATMAN 3 (karar doğrulama) sadece aksiyon önerisi varken
6. bias kontrolü haftada en az 1 kez detaylı yap (cuma raporu)
