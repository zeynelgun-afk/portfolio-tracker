# GÜNLÜK RAPOR PROMPT v3.0 — SADELEŞTİRİLMİŞ

> **çalışma zamanı**: TR ~14:00 (NYSE dün kapandı, bugün 17:30'da açılacak)
> **çıktı**: `reports/daily/DAILY_REPORT_YYYY-MM-DD.md`
> **dil**: küçük harf türkçe
> **kaynak**: sadece "finzora ai"

---

## ⚠️ 3 FAZLI ÇALIŞMA - HER FAZ AYRI COMMIT

```
FAZ 0: repo oku, dünkü raporu değerlendir (commit yok)
FAZ 1: FMP veri çek → JSON güncelle → git push
FAZ 2: rapor yaz → git push
```

**Her fazı bitir, commit et, sonrakine geç. Tek seferde yapma - sistem durur.**

---

## FAZ 0 — OKUMA (commit yok)

```bash
git pull
cat reports/daily/DAILY_REPORT_[DÜN].md
```

**oku ve değerlendir**:
- dünkü plan tuttu mu?
- hangi kararlar doğru/yanlış çıktı?
- kaçırılan fırsatlar?

→ sohbette özet ver, "faz 1'e geç" de

---

## FAZ 1 — VERİ ÇEKME + JSON GÜNCELLEME

### adım 1a: sembolleri topla

```python
import json, glob

symbols = set()
for f in glob.glob("data/portfolios/*.json") + glob.glob("data/swing/*.json"):
    with open(f) as fp:
        d = json.load(fp)
        for p in d.get('pozisyonlar', []) + d.get('aktif_pozisyonlar', []):
            symbols.add(p['sembol'])
```

### adım 1b: FMP toplu çek

```python
import requests
from datetime import datetime

API_KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
BASE = "https://financialmodelingprep.com/stable"

symbols_str = ",".join(symbols)

# tek call - tüm fiyatlar
quotes = requests.get(f"{BASE}/batch-quote", 
    params={"symbols": symbols_str, "apikey": API_KEY}).json()

# tek call - tüm RSI
rsi_data = {}
for sym in symbols:
    r = requests.get(f"{BASE}/technical-indicators/rsi",
        params={"symbol": sym, "periodLength": 14, "timeframe": "1day", "apikey": API_KEY}).json()
    rsi_data[sym] = r[0]['rsi'] if r else None

# tek call - tüm SMA
sma_data = {}
for sym in symbols:
    for period in [20, 50, 200]:
        s = requests.get(f"{BASE}/technical-indicators/sma",
            params={"symbol": sym, "periodLength": period, "timeframe": "1day", "apikey": API_KEY}).json()
        sma_data[f"{sym}_{period}"] = s[0]['sma'] if s else None
```

### adım 1c: JSON güncelle

**portföy dosyaları** (`data/portfolios/*.json`):

```python
for poz in data['pozisyonlar']:
    q = next(x for x in quotes if x['symbol'] == poz['sembol'])
    poz['guncel_fiyat'] = q['price']
    poz['gunluk_degisim_yuzde'] = q['changesPercentage']
    poz['guncel_deger'] = poz['adet'] * q['price']
    poz['kar_zarar'] = poz['guncel_deger'] - poz['yatirim']
    poz['kar_zarar_yuzde'] = (poz['kar_zarar'] / poz['yatirim']) * 100
    poz['son_guncelleme'] = datetime.now().isoformat()

toplam = sum(p['guncel_deger'] for p in data['pozisyonlar']) + data['nakit']['miktar']
data['toplam_deger'] = toplam
data['toplam_getiri_yuzde'] = ((toplam - data['baslangic_sermaye']) / data['baslangic_sermaye']) * 100

for poz in data['pozisyonlar']:
    poz['agirlik_yuzde'] = (poz['guncel_deger'] / toplam) * 100
```

**swing dosyası** (`data/swing/active.json`):

```python
from datetime import datetime, date

for poz in data['aktif_pozisyonlar']:
    q = next(x for x in quotes if x['symbol'] == poz['sembol'])
    poz['guncel_fiyat'] = q['price']
    poz['guncel_kar_zarar_yuzde'] = ((q['price'] - poz['giris_fiyati']) / poz['giris_fiyati']) * 100
    
    giris = datetime.strptime(poz['giris_tarihi'], "%Y-%m-%d").date()
    poz['tutulan_gun'] = (date.today() - giris).days
    
    poz['son_guncelleme'] = datetime.now().isoformat()
```

**summary.json**:

```python
summary['toplam_deger'] = sum(port['toplam_deger'] for port in portfolios.values())
summary['toplam_kar_zarar'] = summary['toplam_deger'] - 400000
summary['toplam_kar_zarar_yuzde'] = (summary['toplam_kar_zarar'] / 400000) * 100
```

### adım 1d: git push

```bash
git add data/
git commit -m "[GÜNCELLEME] $(date +%d) $(date +%B | tr 'A-Z' 'a-z') - kapanış fiyatları"
git push
```

→ "faz 1 tamam, faz 2'ye geç" de

---

## FAZ 2 — RAPOR YAZMA

### web search (5-7 call)

```
1. "S&P 500 futures pre-market [BUGÜN]"
2. "NASDAQ futures today [BUGÜN]"
3. "sector performance yesterday [DÜN]"
4. "earnings results after hours [DÜN gecesi]"
5. "[kritik sembol] news today" (varsa)
```

### rapor formatı

```markdown
# günlük rapor — DD ay YYYY

*new york kapalı | bir sonraki seans: bugün 17:30 tr | hazırlayan: finzora ai*

---

## 0. dünkü plan gerçekleşme

| aksiyon | plan | gerçekleşen | sonuç |
|---------|------|-------------|-------|
| [örnek] | NEM %50 sat @$130 | tutmadı, $124.5'ta | hedefe ulaşmadı |

**performans özeti**:
- toplam: $XXX,XXX (+%X.XX)
- en iyi: [portföy] +%X.XX
- en zayıf: [portföy] -%X.XX
- swing: X/10 aktif, ort %X.XX

**dersler**:
- ✅ [doğru karar]
- ❌ [yanlış karar]
- 💡 [içgörü]

**JSON durumu**: ✅ tüm dosyalar güncellendi (faz 1)

---

## 1. piyasa — dünkü kapanış + bugünkü görünüm

### dünkü kapanış (new york 00:00 tr)

| ticker | kapanış | değişim |
|--------|---------|---------|
| SPY | $XXX.XX | +X.XX% |
| QQQ | $XXX.XX | +X.XX% |
| IWM | $XXX.XX | +X.XX% |

**sektör hareketi**: [en güçlü 3] vs [en zayıf 3]

### bugünkü futures (pre-market önü)

[web search sonucu]

### gece haberleri (AMC earnings, FED konuşması, vb)

[web search sonucu - max 3-4 madde]

**bugünkü risk**: [en büyük katalizör/risk]

---

## 2. portföy takibi

### dengeli portföy

| sembol | adet | maliyet | güncel | k/z % | RSI | SMA20 | SMA50 | durum |
|--------|------|---------|--------|-------|-----|-------|-------|-------|
| SM | X | $XX.XX | $XX.XX | +X.X% | XX | ✅/❌ | ✅/❌ | [not] |

**toplam**: $XXX,XXX (+%X.XX) | **ağırlık**: en büyük [XX%] | **nakit**: $X,XXX

**portföy notu**: [1-2 cümle]

**sektör dağılımı**: enerji XX%, tütün XX%, ...

**uyarılar**:
- 🔴 [kritik uyarı]
- 🟡 [dikkat gereken]
- ✅ [sorunsuz]

---

*[agresif, temettü, rotasyon için tekrar]*

---

## 3. swing trade

| id | sembol | giriş | güncel | k/z % | stop | hedef | gün | durum |
|----|--------|-------|--------|-------|------|-------|-----|-------|
| SWING-XXX | XXX | $XX | $XX | +X% | $XX | $XX | X | [not] |

**aktif**: X/10 | **ortalama**: +%X.XX

**bugünün swing aksiyonları**:
- 🔴 [hemen yapılacak]
- 🟡 [izlenecek]
- ✅ [sorunsuz]

**watchlist** (X aday): [sembol, sembol, ...]

**istatistik**: kazanç X/X (XX%), kayıp X/X, toplam P&L %XX

---

## 4. earnings takvimi

### dün gece (AMC sonuçları)

| sembol | actual EPS | expected | fark | AH fiyat | etki |
|--------|------------|----------|------|----------|------|
| XXX | $X.XX | $X.XX | +XX% | +X% | [portföy/watchlist etkisi] |

### bugün

**BMO (09:00 tr önce)**: [semboller]
**AMC (00:00-02:00 tr gece)**: [semboller]

**portföy etkisi**: [hangi pozisyonlar etkilenecek]

### bu hafta özet

[Mon-Fri critical earnings]

---

## 5. sonuç

### özet

[3-4 cümle - genel durum, fırsatlar, riskler]

### bugünün aksiyonları (17:30 tr açılış → 00:00 tr kapanış)

**hemen yapılacak (seans açılışında)**:
1. [aksiyon - tetikleyici - hedef]

**izlenecek**:
2. [koşul] → [aksiyon]

**pasif (alarm kur)**:
3. [fiyat seviyesi] → [değerlendir]

### sonraki güncelleme

[cuma ise] → hafta sonu özet raporu
[değilse] → yarın kapanış raporu

---

*finzora ai ile hazırlanmıştır | veri kaynağı: fmp api*
```

### git push

```bash
git add reports/daily/
git commit -m "[GÜNLÜK RAPOR] $(date +%d) $(date +%B | tr 'A-Z' 'a-z') YYYY - [kısa özet]"
git push
```

→ BİTTİ ✅

---

## ÖNEMLİ NOTLAR

### fiyat kaynaklarını karıştırma

- **portföy JSON'ları**: FMP'den çekilmiş kapanış fiyatları (faz 1'de)
- **rapor yazdığında**: JSON'dan oku, FMP'yi TEKRAR ÇEKME
- tek istisna: futures, haberler (websearch)

### stop/hedef kontrolü

```python
# swing için
if guncel_fiyat <= stop_loss:
    durum = "🔴 STOP TETİKLENDİ"
elif guncel_fiyat >= hedef_fiyat:
    durum = "🟢 HEDEF TUTTURULDU"
elif guncel_fiyat >= hedef_fiyat * 0.95:
    durum = "🟡 HEDEFE YAKIN"
```

### RSI/SMA göstergeleri

```python
if rsi < 30: rsi_durum = "oversold ⚠️"
elif rsi > 70: rsi_durum = "overbought ⚠️"
else: rsi_durum = "normal"

sma_check = {
    20: "✅" if guncel > sma20 else "❌",
    50: "✅" if guncel > sma50 else "❌",
    200: "✅" if guncel > sma200 else "❌"
}
```

### dosya doğrulama (faz 1 sonrası)

```python
# her portföy için
assert data['toplam_deger'] > 0
assert abs(sum(p['agirlik_yuzde'] for p in data['pozisyonlar']) + (data['nakit']['miktar']/data['toplam_deger']*100) - 100) < 0.1

# swing için
assert len(data['aktif_pozisyonlar']) <= 10
assert all(p['stop_loss'] < p['giris_fiyati'] < p['hedef_fiyat'] for p in data['aktif_pozisyonlar'])
```

---

## API BÜTÇE

| faz | endpoint | call sayısı |
|-----|----------|-------------|
| 1 | batch-quote | 1 |
| 1 | RSI | ~15 |
| 1 | SMA (20,50,200) | ~45 |
| **toplam faz 1** | | **~61** |
| 2 | websearch | 5-7 |
| **günlük toplam** | | **~20-30 FMP + 5-7 web** |

**oran**: 30/2500 = %1.2 günlük limit

---

## HATA AYIKLAMA

**"sistem durdu"** → fazları ayrı çalıştır, tek seferde yapma
**"fiyat güncel değil"** → faz 1'i tekrar çalıştır
**"JSON tutarsız"** → doğrulama hatası, manuel kontrol et
**"rapor yarım kaldı"** → faz 2'yi tek başına çalıştır (faz 1 verileri kullanır)
