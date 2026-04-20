# Tematik Katalist Takvimi — Prompt Entegrasyon Rehberi

**Amaç:** `agent/thematic_calendar.py` modülünü sabah/kapanış prompt'larına bağlamak.
**Bağlı doküman:** `docs/THEMATIC_CATALYST_CALENDAR.md` (v1.0, 20 Nisan 2026)

---

## 1. Ne değişti (kod tarafı)

### Yeni modül: `agent/thematic_calendar.py`

13 yıllık tekrarlayan tematik etkinlik takvimlendi: CES, GTC Spring/Fall, Computex, WWDC, Build, I/O, Dreamforce, re:Invent, OpenAI Dev Day, World Quantum Day, Intel Innovation, Snowflake/Databricks Summit.

İki ana fonksiyon:

```python
from thematic_calendar import check_thematic_event, build_thematic_context

# Ham durum kontrolü
status, event = check_thematic_event()
# status: None | "pre" | "event" | "post"
# event: {"name", "theme", "primary", "ecosystem", "speculative", "days_delta", ...}

# Orkestratör için hazır markdown bağlam
thematic_md = build_thematic_context()  # boş string veya dolu bağlam
```

### Orkestratör entegrasyonu

`agent/orchestrator.py` içinde `collect_context(mode)` fonksiyonu dönüş sözlüğüne `"thematic"` anahtarını ekler. Bu alan:

- Hiçbir etkinliğe yakın değilse **boş string** (prompt'u kirletmez)
- Pre/event/post durumunda dolu markdown bağlam

Her modda (morning, closing, monitor, weekly) çalışır çünkü maliyeti ihmal edilebilir.

---

## 2. Prompt'a ADIM 0.5 ekleme

Aşağıdaki bölümü **PART 1 SABAH, KAPANIŞ ve HAFTALIK** prompt'larının makro kontrol bölümünden hemen sonra, scanner/analiz bölümünden ÖNCE ekle.

### Şablon (prompt'a kopyala-yapıştır)

```markdown
## ADIM 0.5: TEMATİK KATALİST KONTROLÜ

`{thematic}` bağlamını kontrol et:

**Boşsa:** Bu adımı atla, raporda bahsetme.

**`PRE-EVENT` (1-2 iş günü sonra):**
- Etkinliğin "birincil" + "ekosistem" ticker'larını izleme listesine geçici olarak ekle
  (`scan_method: "thematic_event_preposition"`, `urgency: "medium"`)
- Filtre: RSI < 65, 50SMA üstü, son 10 gün değişim < %20
- Aksiyon: GİRİŞ YAPMA. İzle. Etkinlik günü stratejisi hazırla.
- Raporda "Yaklaşan Tematik Katalist" bölümü aç.

**`EVENT DAY` (bugün):**
- Tüm ticker'lar için gün içi ek izleme (volume, fiyat tepkisi, haber akışı)
- KOVALAMA YASAK. İlk gün girişi, dersimiz (KTOS/CEG/HAL/LASR 2 Mart: 5/5 kayıp) gereği yasak.
- Canlı keynote TR saatine göre takip et; her önemli duyuru sonrası `data/session_state.json`'a not düş.
- Raporda `DAILY_TEMATIK_YYYY-MM-DD.md` başlığı altında ayrı bölüm oluştur.

**`POST-EVENT` (1-5 iş günü önce):**
- 2. gün: Açılış aralığı (ilk 30dk) sonrası RSI < 75 ise yarım pozisyon denenebilir.
  Stop = maks(2×ATR, %5); hedef = %10 veya 2R.
- 3-5. gün: Volume düşüyorsa VE RSI 75+ ise giriş YASAK. Momentum güçlü devam ediyor VE volume
  artıyorsa yarım pozisyon devam edilebilir.
- 5. gün sonrası: Geç giriş. Distribution riski yüksek. Yalnız mean-reversion setup varsa ve 
  K-13 VIX-bazlı rejim kuralına uyuyorsa.

**Saf oyuncular (screener dışı, yalnız thematic override ile izlenir):**
- Örnek: Quantum Day → IONQ, RGTI, QBTS, QUBT
- Bunlar normal alım taramasında elenir (EPS negatif). Thematic override AKTİF olduğunda
  pozisyon boyutu normal agresif sizing'in **yarısı** (sermayenin max %3'ü) olmalı.
- Stop daha sıkı: %5 sabit, 2×ATR değil. Volatilite çok yüksek.

**Çıktı formatı (rapor içinde):**

```
### Tematik Durum: {status}
- Etkinlik: {name}
- Tema: {theme}
- Birincil izleme: {primary}
- Ekosistem: {ecosystem}
- Saf oyuncular: {speculative} (override aktif)
- Bugünkü aksiyon: {action}
```
```

---

## 3. DAILY_TEMATIK raporu (event day özel)

Event day'de normal `DAILY_SABAH` raporuna ek olarak `reports/daily/DAILY_TEMATIK_{YYYY-MM-DD}.md` oluştur.

### Şablon

```markdown
# Tematik Katalist Raporu — {etkinlik adı}
**Tarih:** {YYYY-MM-DD}
**Tema:** {theme}

## Etkinlik Özeti
(Keynote öncesi beklentiler — analist tahminleri, piyasa fiyatlaması)

## İzleme Listesi
| Ticker | Kategori | Fiyat | RSI | Volume (5g ort.) | SMA50 Konumu | Not |
|--------|----------|-------|-----|------------------|--------------|-----|
| ...    | Primary  | ...   | ... | ...              | ...          | ... |

## Geçmiş Benzer Etkinlikler
(Varsa: önceki yılların tepkileri, ortalama sektör hareketleri)

## Giriş/Çıkış Seviyeleri
(İlk 30dk sonrası, her ticker için hedef giriş ve stop)

## Canlı Takip (keynote sırası güncellenecek)
- HH:MM TR — (önemli duyuru)
- HH:MM TR — ...

## Kapanış Analizi
(Keynote sonrası 2 saat içinde — fiyat tepkisi, volume, anlamlı kırılımlar)

## Yarın için Plan
(Ertesi gün açılış stratejisi, giriş öncelikleri)
```

---

## 4. Rapor ekleme noktası

Sabah raporu üst satırına eklenecek metaalan:

```markdown
**Tematik durum:** {Yok} | {Pre-event: {name} ({delta} gün sonra)} | {Event day: {name}} | {Post-event: {name} ({delta} gün önce)}
```

Bu satır, raporun en üstünde (tarih ve VIX/SPY satırının altında) dursun — bir bakışta görülebilsin.

---

## 5. Dersler bölümüne otomatik ekleme

Her etkinlik sonrası 2 hafta içinde `docs/THEMATIC_CATALYST_CALENDAR.md` dosyasının **Dersler (Event Log)** bölümüne şu şablonla kayıt düş:

```markdown
### {YYYY-MM-DD} — {Etkinlik adı}

**Durum:** Yakalandı / Kısmen yakalandı / Kaçırıldı

**Piyasa tepkisi:**
- {Ticker}: %{değişim} ({duyuru öncesi son kapanış → zirve kapanışı})
- ...

**Finzora aksiyonu:**
- Açılan pozisyonlar: ({ticker}, {giriş fiyatı}, {pozisyon boyutu})
- Kaçırılan fırsatlar: (ticker ve sebep)
- Yapılan hatalar: (varsa)

**Dersler:**
- ({sonraki yıl için iyileştirme})
```

Bu kayıt `logs/events.jsonl`'a da `{"event_type": "thematic_review", ...}` olarak düşer.

---

## 6. Sıradaki kontrol tarihleri

Bugün 20 Nisan 2026 itibarıyla yakında tetiklenecek etkinlikler:

| Etkinlik | Tarih (yaklaşık) | Pre-event tetiği | Event day | Post-event penceresi |
|----------|------------------|------------------|-----------|---------------------|
| Microsoft Build | 19 Mayıs | 17-18 Mayıs | 19 Mayıs | 20-24 Mayıs |
| Google I/O | 20 Mayıs | 18-19 Mayıs | 20 Mayıs | 21-25 Mayıs |
| Computex | 3 Haziran | 1-2 Haziran | 3 Haziran | 4-8 Haziran |
| Apple WWDC | 9 Haziran | 5-6 Haziran | 9 Haziran | 10-14 Haziran |
| Snowflake/Databricks Summit | 10 Haziran | 8-9 Haziran | 10 Haziran | 11-15 Haziran |

Gerçek tarihler her yıl Ocak ayında resmi kaynaklardan doğrulanıp `agent/thematic_calendar.py` içindeki `THEMATIC_EVENTS` sözlüğünde güncellenecek.

---

## 7. Test komutu

Entegrasyonu elle test etmek için:

```bash
# Bugün için
python3 agent/thematic_calendar.py

# Belirli tarih için
python3 agent/thematic_calendar.py --date 2026-05-19

# JSON formatında (script entegrasyonu için)
python3 agent/thematic_calendar.py --date 2026-04-14 --json
```

---

## 8. Bakım

- **Yıllık:** Her Ocak 1'de `THEMATIC_EVENTS` sözlüğündeki `approximate` tarihleri resmi duyurularla güncelle.
- **Aylık:** Yeni etkinlik / IPO saf oyuncusu eklenmesi review'ı.
- **Etkinlik sonrası:** 2 hafta içinde `dersler` kaydı zorunlu.
