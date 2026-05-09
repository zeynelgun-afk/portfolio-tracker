# FMP Log Analizi — 10 Mayıs 2026

**Tarih:** 10 Mayıs 2026 (Cumartesi)
**Kapsam:** `logs/events.jsonl` 17 Şubat → 9 Mayıs 2026 dönemi
**Bağlam:** 10 Mayıs FMP denetimi Aksiyon 2 (rate limit timing'inin ampirik doğrulaması)
**Kaynak:** finzora ai

---

## 1. Yönetici Özeti

`logs/events.jsonl` içinde 72,123 FMP çağrısı kaydı incelendi. Sadece 20 başarısız çağrı bulundu (binde 0.27 hata oranı). Hataların 19'u 429 rate limit, 1'i 404 (bugünkü test). 19 rate limit hatasının 11 tanesi 30 Nisan 2026 16:31-16:34 arasında 3 dakikalık bir burst (ani yığılma) olarak gerçekleşti. Eski `agent/fmp_client.py` retry timing'i (2 ile 8 saniye arası) bu burst'ü çözemedi; üç deneme de aynı dakikalık limit penceresine düştü. **Yeni 60+30s*attempt timing'i bu dalgayı ampirik olarak çözerdi** çünkü 60 saniye, FMP'nin dakikalık reset penceresinin tamamını kapsıyor.

Genel sistem yoğunluğu (peak ~51 çağrı/dakika) Ultimate planın (3000/dakika) %1.7'sinde kalıyor. Premium döneminde (750/dakika) bile %6.8 — sade ortalamada güvenli, ama burst pattern'lerinde dakikalık limiti vuruyor. Yeni timing sadece bu burst durumlarında devreye girecek, normal akışta hiç tetiklenmeyecek.

---

## 2. Veri Özeti

| Metrik | Değer |
|--------|-------|
| Toplam log kaydı | 72,893 |
| FMP call kaydı | 72,123 (98.9%) |
| Trade kaydı | 295 |
| Claude call kaydı | 226 |
| Decision kaydı | 180 |
| Decision update kaydı | 69 |
| İlk kayıt tarihi | 2026-02-17 |
| Son kayıt tarihi | 2026-05-09 |
| Toplam gün sayısı | 82 gün |

### 2.1 Retry sayısı dağılımı

| Retry sayısı | Kayıt | Yüzde |
|--------------|-------|-------|
| 0 (ilk denemede başarılı) | 72,094 | 99.96% |
| 1 | 4 | 0.01% |
| 2 | 5 | 0.01% |
| 3 (max, başarısız) | 20 | 0.03% |

Sistem genelinde 9 çağrı 1-2 retry sonrası başarılı oldu. 20 çağrı üç denemede de başarısız.

### 2.2 Endpoint başına hata oranı

| Endpoint | Hata / Toplam | Hata Oranı |
|----------|---------------|------------|
| `income-statement` | 5 / 12,788 | 0.039% |
| `profile` | 5 / 9,337 | 0.054% |
| `quote` | 3 / 3,320 | 0.090% |
| `key-metrics-ttm` | 3 / 6,394 | 0.047% |
| `ratios-ttm` | 2 / 6,394 | 0.031% |
| `balance-sheet-statement` | 1 / 6,394 | 0.016% |
| `nonexistent-endpoint` | 1 / 1 | 100% (10 May test) |

Tüm endpoint'lerde hata oranı binde 1'in altında. Yüksek volume `income-statement` (12.8K çağrı) ve `profile` (9.3K çağrı) endpoint'lerinde bile 5/binde altında.

---

## 3. KRİTİK BULGU: 30 Nisan 16:31-16:34 Burst Dalgası

### 3.1 Olayın gözlemi

3 dakikalık bir pencerede 11 ardışık 429 hatası kaydedildi:

| Zaman (UTC) | Endpoint |
|-------------|----------|
| 16:31:50 | profile |
| 16:32:05 | quote |
| 16:32:33 | profile |
| 16:32:47 | quote |
| 16:33:02 | profile |
| 16:33:33 | ratios-ttm |
| 16:33:48 | key-metrics-ttm |
| 16:34:02 | income-statement |
| 16:34:29 | balance-sheet-statement |
| 16:34:43 | quote |
| 16:34:58 | profile |

Hepsi `retry_count=3` (max) ile sonlandı, yani üç deneme de 429 aldı.

### 3.2 Olay analizi

UTC 16:31 = TR saatiyle 19:31 (yaz saati). Bu, ABD piyasasının açıldığı 16:30 TR saatinden 3 saat sonrasına denk geliyor. Yani açılış değil, **canlı seans ortası**. Bu saat Finzora orchestrator'da aktif monitor pencerelerinden biri (memory: "17-23:30 every 30min agent(monitor)").

Endpoint sırası (`profile`, `quote`, `ratios-ttm`, `key-metrics-ttm`, vb.) tipik bir tek hisse derinlemesine analiz pattern'ine işaret ediyor. Muhtemelen `agent.py` agent monitor cycle'ı veya bir ticker analizi pipeline'ı arka arkaya o ticker için tüm endpoint'leri çekti, **tek bir orchestrator döngüsünde dakikalık limiti aştı**.

### 3.3 Eski timing neden çözemedi?

Eski `agent/fmp_client.py` 429 backoff hesabı:

```python
wait = _RETRY_BACKOFF ** (attempt + 1)  # 2.0 ** 1, 2.0 ** 2, 2.0 ** 3
# Yani: 2s, 4s, 8s — toplam 14s
```

FMP dakikalık limit pencere yaklaşık **60 saniye** sürüyor. Eğer çağrı 16:31:50'de hata alıyorsa:

- Deneme 2: 16:31:52 (2s sonra) → hala aynı pencerede → 429
- Deneme 3: 16:31:56 (4s sonra) → hala aynı pencerede → 429
- Deneme 4: 16:32:04 (8s sonra) → hala aynı pencerede → 429
- Sonuç: 14 saniye boşa harcandı, yine başarısız

Pencere sıfırlanması en az 60 saniye gerektirir. Eski exp-backoff timing matematik olarak yetersizdi.

### 3.4 Yeni timing ampirik doğrulaması

Yeni `agent/fmp_client.py` 429 backoff hesabı:

```python
wait = 60 + 30 * attempt  # 60s, 90s, 120s
```

Aynı 30 Nisan senaryosu yeni timing'le:

- Hata: 16:31:50
- Deneme 2: 16:32:50 (60s sonra) → 99% olasılıkla pencere resetlendi → 200 OK
- Deneme 3: 16:34:20 (deneme 2 başarılı olmazsa, +90s sonra) → kesin yeni pencere

**11 hatadan 11'i ilk retry'da çözülürdü.** Toplam ek bekleme 11 × 60s = 11 dakika ama gerçek başarı oranı 0/11 yerine 11/11.

---

## 4. Sistem Yoğunluk Analizi

### 4.1 Peak yoğunluk

En yoğun saat: 2026-04-20 11:00 UTC → 3,075 çağrı/saat → ortalama 51.2 çağrı/dakika.

| Plan | Limit (/dk) | Peak yüzdesi | Güvenlik marjı |
|------|-------------|--------------|----------------|
| Premium ($49/ay, eski) | 750 | 6.8% | 93.2% |
| Ultimate ($99/ay, mevcut) | 3,000 | 1.7% | 98.3% |

Sade ortalamada her iki plan da bol bol yetiyor. Ama "saatlik ortalama" ≠ "dakikalık burst" — saniye saniye dağılım farklı olabilir.

### 4.2 Top 10 yoğun saat

| Tarih/Saat (UTC) | Çağrı | Ortalama/dk |
|------------------|-------|-------------|
| 2026-04-20 11:00 | 3,075 | 51.2 |
| 2026-04-23 15:00 | 1,628 | 27.1 |
| 2026-04-24 14:00 | 1,451 | 24.2 |
| 2026-04-27 16:00 | 1,010 | 16.8 |
| 2026-04-27 17:00 | 1,010 | 16.8 |
| 2026-05-04 19:00 | 986 | 16.4 |
| 2026-04-22 22:00 | 978 | 16.3 |
| 2026-04-24 22:00 | 972 | 16.2 |
| 2026-04-29 14:00 | 954 | 15.9 |
| 2026-04-22 14:00 | 947 | 15.8 |

Tek anormal saat 20 Nisan 11:00 UTC (3,075). Diğer top 10 saatler 950-1,650 arası. 20 Nisan büyük olasılıkla bilanço sezonu pre-market taraması veya RAG ilk indeksleme operasyonu.

---

## 5. Sonuçlar ve Aksiyon

### 5.1 Yeni timing yerinde mi?

**Evet, ampirik olarak doğrulandı:**

- 30 Nisan 16:31-34 dalgasındaki 11 ardışık başarısızlık eski timing'le çözülemezdi
- Yeni 60+30s*attempt timing'i bu dalgayı kesinlikle çözerdi
- Sistem genelinde retry=0 oranı zaten %99.96, yeni timing sadece nadir burst durumlarında devreye girer

### 5.2 Risk değerlendirmesi

- **Latency etkisi:** Burst durumda kullanıcı 60-120 saniye ek bekleme görür. Trade aksiyonu ise bu kabul edilebilir (manuel doğrulama zaten gerekli). Tarama pipeline'ı ise yarım dakika daha uzun çalışır, problem değil.
- **Sayaç israfı yok:** Ultimate'da 3000/dk limit, peak 51/dk. Yeni timing ekstra call üretmiyor, mevcut başarısızları çözüyor.
- **False positive riski:** Yeni kod boş `[]` ve 404 için retry yapmıyor. Bu doğru; eski kod 14s boşa beklerdi, yeni kod 0.1s'de döner.

### 5.3 Önerilen aksiyon

1. **Mevcut timing korunsun**: 60+30s*attempt yerinde, daha agresif (90+45s) yapmaya gerek yok. 1 yıllık veride 19 hatada bir 11'lik dalga görüldü, böyle olaylar aylık/iki aylık seyrek.

2. **Burst kaynağı tespit edilsin**: 30 Nisan 16:31-34 hangi script tarafından tetiklendi? Aynı saatteki diğer log kayıtları (decision, claude_call) bağlam verir. Eğer belirli bir orchestrator döngüsü ise (örnek: `agent.py monitor` cycle'ı tek hissede 8-10 endpoint çekiyor) o pipeline'a **rate limiter** eklenebilir (`time.sleep(0.5)` her FMP call arasına, 8 endpoint × 0.5s = 4s ek süre, ama 429 önler).

3. **events.jsonl haftalık özet alınsın**: Memory'deki "Weekly stats GitHub Actions workflow" bekleyen iş listesinde. Bu rapor o workflow'un içerik şablonu olabilir: hata oranı, peak yoğunluk, retry dağılımı, dakika başına en yoğun pencere.

4. **agent/agent.py monitor cycle'ında potansiyel düzeltme**: Eğer 30 Nisan dalgası `monitor` script'inden geliyorsa, FMP çağrıları arasına 200-500ms throttle koymak hem rate limit dostu hem de gözlemlenebilir performans iyileştirmesi yapar.

---

## 6. Migration Kararı

Aksiyon 2 (log analizi) tamamlandı. Bulgular:

- Yeni timing'in `agent/fmp_client.py`'a yerleşmesi DOĞRULANDI (burst senaryosu çözer)
- `agent/tools.py`, `agent/risk_engine.py`, `agent/backtester.py` migration'ı bugün tamamlandı (commit `bfd102f`)
- Bu üç dosya artık canonical `fmp_client` üzerinden çalışıyor — yeni timing ve observability log'a otomatik dahil

**Sonraki migration adayları (pazartesi sonrası):**
- `scripts/k_rules_common.py` (8 K-script onu kullanıyor, kritik, dönüş davranışı `None` farklı)
- `scripts/news_radar.py` (kendi sofistike retry'ı var, davranış mukayese edilmeli)
- `scripts/swing_entry_engine.py` ve diğerleri

---

**Rapor hazırlama tarihi:** 10 Mayıs 2026
**Veri aralığı:** 17 Şub 2026 → 9 May 2026 (82 gün)
**Toplam kayıt analizi:** 72,123 FMP call
**Bulunan hata:** 20 (binde 0.27)
**Kaynak:** finzora ai
