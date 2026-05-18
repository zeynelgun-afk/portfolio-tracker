---
title: Daily Sabah Prompt (Konsolide)
description: Eski 3-prompt sistemi (PART 1 SABAH + 1B SWING + 1C PORTFÖY) tek prompt'ta birleşik
tags:
  - prompt
  - daily
  - morning
  - consolidated
related:
  - "[[SESSION_REFERENCE]]"
  - "[[PORTFOLIO_OPPORTUNITY_SYSTEM]]"
  - "[[TRADING_PLAYBOOK]]"
  - "[[MARKET_INTELLIGENCE]]"
version: 1.0 (17 May 2026, konsolidasyon — eski PART 1 + 1B + 1C yerine geçer)
---

# DAILY SABAH PROMPT — KONSOLİDE

> **Kullanım**: NYSE açılışından önce (TR 14:00-16:00 arası), günde 1 kez yapıştırılır.
> Çıktı: `reports/daily/DAILY_SABAH_YYYY-MM-DD.md` + JSON güncellemeleri + git push.
> **Hafta sonu çalıştırma**: TR 14:30 öncesi hafta içi mesai günleri.

---

## Prompt başlangıcı (chat'e yapıştırılacak metin)

```
SABAH MODU. Hafta içi NYSE öncesi (~TR 14:00-16:00). Konsolide sabah raporu üret.
Bugün: {DATE_ISO}.

Çıktı tek dosya: reports/daily/DAILY_SABAH_{DATE}.md
Final aksiyon: git add + commit + push (mesaj Türkçe). Sonra Telegram özet (group).

ADIMLAR:
1. user_time_v0 ile TARIH+SAAT kontrol et. Cumartesi/Pazar ise → "Piyasa kapalı, sabah raporu yok" → DUR.
2. user_time_v0 sonucu hafta içi ise → aşağıdaki 4 bölümü sırayla üret.
3. Hiçbir bölümü atlamayacaksın. Bölüm başlıklarını rapor MD'sine aynen kullan.
4. Veri yoksa "veri yok" yaz ama bölüm başlığını sil. Sessiz atlama yok.

KISITLAMALAR (kritik):
- Veriler FMP fmp_client (50ms throttle, 3000/min) üzerinden — başka kaynak yok.
- Polymarket kalibratör flag CALIBRATOR_ENABLED'a göre çalışır (aktif ise score_components'ta görürsün).
- "şu an" fiyatları PRE-MARKET ise: aftermarket-quote 0 dönerse → web search ile pre-market özeti çek.
- Calibration flag varsa rapor bölümüne yaz, sessiz geçme.
- K-rules çapraz kontrolü → docs/K_RULES_QUICK_REF.md. Aktif alert: K-13 (VIX>30 DM), K-23 (drawdown).
- Watchlist'e EKLEME ve portföye TRADE sabah yapılmaz. Sabah PLAN'lar. Aksiyon FAZ 1-3'te.

═══ BÖLÜM 1: MAKRO + REJİM ═══

a) Risk panel snapshot — scripts/risk_panel_generator.py çalıştır → outputs/risk_panel/{DATE}.png üret.
   Aynı dosya yolu raporda referans olarak verilsin (img link).
b) Rejim göstergeleri (FMP fmp_get):
   - SPY/QQQ quote: spot fiyat, dünden % değişim
   - VIX (^VIX): seviye + 1g delta
   - 10Y treasury (TNX veya treasury-rates endpoint): seviye
   - USD index (DXY): seviye + 1g delta
   - WTI (CL=F): seviye + 1g delta
c) Pre-market lider/laggard (web search): "premarket movers today"
   Sadece >$2B mcap + >%2 hareket olanlar.
d) ÖNEMLİ HABER (web search): "stock market news today"
   Yalnızca aşağıdakilerden biri: fed/cpi/jobs/geopolitical/earnings_megacap. 3 başlık max.
e) Sektör rotasyonu — XLF/XLK/XLV/XLE/XLY/XLP/XLI/XLU/XLB/XLRE/XLC için stock-price-change
   1g/5g/1ay % değişim. En iyi/en kötü 3 sektör.

REJİM ÖZETİ (1 paragraf):
   "Risk on/off + sektör momentumu + ana tema." Subjektif değil, veri-bazlı.

═══ BÖLÜM 2: PORTFÖY SAĞLIK KONTROLÜ ═══

a) data/portfolio.json oku — açık pozisyonlar.
b) Her pozisyon için (FMP quote ile):
   - Mevcut fiyat (dünün kapanışı)
   - Stop'a mesafe: (price - stop_loss) / price * 100
   - Target'a mesafe: (target - price) / price * 100
   - P&L %: (price - entry_price) / entry_price * 100
   - Hold gün sayısı
c) UYARILAR (otomatik tetik):
   - Stop'a %5'ten yakın → 🔴 acil dikkat
   - Stop'a %5-10 → 🟡 yakın takip
   - Target'a %5'ten yakın → 🟢 satış planı
   - %15+ kayıp (entry'den) → 🔴 tez gözden geçirme
   - 30+ gün açık + sideways (±5% entry'den) → 🟡 fırsat maliyeti
d) data/watchlist.json oku — high-urgency olanlar (urgency=high):
   Her birini bugün izlenmesi gereken hisse olarak listele (sebep + tetik fiyatı).
e) Polymarket kalibrasyon (CALIBRATOR_ENABLED açıksa):
   - watchlist score_components'tan polymarket_calibration alanları
   - pm_conflict olan hisseleri listele (manuel review için)

PORTFÖY ÖZETİ:
   - Toplam P&L $ ve %
   - Sektör konsantrasyonu (% pozisyon değeri / portföy değeri)
   - Bugün izlenecek pozisyon sayısı (uyarı tetikleyenler)

═══ BÖLÜM 3: SWING FIRSATLAR ═══

a) data/watchlist.json'dan SWING uygun aday filtrele:
   - score_components.swing_setup mevcut, VEYA
   - Tag'lerde "swing" var, VEYA
   - urgency >= medium ve fair_value_discount yok (uzun vadeli değil, kısa setup)
b) Aktif swing pozisyonları (eğer varsa data/swing_active.json):
   - Her biri için P&L + stop/target mesafesi
   - Bugün hangi seviyeye yakın
c) Yeni swing setup adayları (max 3):
   - Ticker, sektör, tema (varsa)
   - Setup tipi (breakout / pullback / bounce)
   - Tetik fiyatı (giriş için)
   - Stop önerisi
   - Risk:Reward
   - K-rule uyumluluğu (K-04 daily 200SMA üstü, K-05 RS rank ≥80)
d) İzleme listesi (max 5):
   - Bugün izlenmesi gereken hisseler — alım sinyali henüz oluşmadı ama yakın

═══ BÖLÜM 4: PORTFÖY FIRSATLARI ═══

PORTFOLIO_OPPORTUNITY_SYSTEM.md mantığını uygula. 3 portföy için:

a) Dengeli Portföy:
   - Açık pozisyon + boş slot sayısı (max 6)
   - Yeni aday(lar) — multi-sector value+momentum
b) Agresif Büyüme Portföyü:
   - Açık pozisyon + boş slot sayısı (max 8)
   - Yeni aday(lar) — momentum + earnings surprise
c) Değer + Temettü Portföyü:
   - Açık pozisyon + boş slot sayısı
   - Yeni aday(lar) — yield ≥3%, payout <60%, dividend growth

Her aday için (max 2 portföy başına = max 6 toplam):
   - Skor (PORTFOLIO_OPPORTUNITY_SYSTEM.md skor sistemi)
   - Sektör konsantrasyon kontrolü (yeni eklemeyle sektör payı %)
   - Mevcut watchlist'te mi
   - K-04/K-05/K-17 ortak filtre check
   - Karar: EKLE / İZLE / GEÇ (sabah TRADE yok, sadece plan)

═══ KAPANIŞ ═══

ÖZET (rapor başı):
   - Bugünün ana mesajı (1 cümle, "risk-on/off + öncelik")
   - Bugün izlenecek sayısı (toplam pozisyon + swing + portföy adayları)
   - Anomali / dikkat çekici tek şey

FORMAT:
   - Markdown, Türkçe
   - Her sayı 2 decimal max
   - Tablolar: bayrak emoji + ticker kalın
   - Risk panel PNG path raporda link olarak

GIT + TELEGRAM:
   1. reports/daily/DAILY_SABAH_{DATE}.md yaz
   2. data/ değişen JSON'ları stage'le (watchlist tag güncellemeleri yapıldıysa)
   3. git add -A && git commit -m "[sabah] {DATE} özet" && git push
   4. Telegram GROUP'a kısa özet (max 800 char): ana mesaj + uyarı sayısı + en önemli swing/portföy fırsatı
```

---

## Açıklamalar (Zeynel için referans)

### Bu prompt neyi değiştiriyor?

| Eski (3 prompt) | Yeni (1 prompt) |
|---|---|
| PART 1 SABAH (makro) | Bölüm 1 |
| PART 1B SWING (kısa vade) | Bölüm 3 |
| PART 1C PORTFÖY (3 portföy) | Bölüm 4 |
| Her birinin tekrarlı bağlam yazısı | Tek bağlam, başta |
| 3 ayrı yapıştırma | 1 yapıştırma |
| Bölüm geçişlerinde durma riski | Sıralı, atlama yok |

### Önemli farklar

1. **Portfolio Health (Bölüm 2)** eskiden 1B'nin başında küçük bir satırdı — şimdi tam bir bölüm. Uyarı eşikleri belirgin (%5/15, 30 gün).

2. **Kalibrasyon entegrasyonu** — Faz 2 sonrası eklendi. CALIBRATOR_ENABLED açıksa polymarket_calibration alanları raporda yer alır.

3. **K-rules referansları** azaltıldı — sadece active alert'ler (K-13, K-23). Discipline rules (K-19, K-20, K-21) Zeynel'in kafasında. Bunlar dosyada `docs/K_RULES_QUICK_REF.md` v2'de tutulur.

4. **Hafta sonu kontrolü** prompt başında — user_time_v0 ile. Sat/Sun → ilk satırda DUR.

### Tam çıktı şeması (örnek başlık ağacı)

```markdown
# DAILY SABAH — 2026-05-18

## ÖZET
- Bugünün ana mesajı: ...
- Bugün izlenecek: X pozisyon + Y swing + Z aday
- Anomali: ...

![Risk Panel](../../outputs/risk_panel/2026-05-18.png)

## 1. Makro + Rejim
### 1a. Rejim göstergeleri
| Metrik | Seviye | 1G Δ |
| SPY | 478.30 | -0.42% |
...

### 1b. Pre-market hareketler
...

### 1c. Önemli haberler
...

### 1d. Sektör rotasyonu
...

**Rejim Özeti**: ...

## 2. Portföy Sağlık
### Açık pozisyonlar
| Ticker | Mevcut | P&L | Stop | Target | Uyarı |
| **NVDA** | 145.20 | +12.5% | -6.5% | +8.2% | 🟢 target yakın |
...

### Watchlist uyarıları
...

### Polymarket kalibrasyon (varsa)
...

## 3. Swing Fırsatlar
### Aktif pozisyonlar
...

### Yeni setup adayları
...

### İzleme listesi
...

## 4. Portföy Fırsatları
### Dengeli — boş slot: 2
### Agresif — boş slot: 3
### Temettü — boş slot: 1

(her birinde aday listesi)
```

### Test/dry-run

Prompt'un ilk test çalıştırmasında:
- Hiçbir aksiyon almasın (commit/push hariç)
- Tüm bölümler dolmasa olur — "veri yok" yazıp atlasın
- Rapor MD'si oluşsun
- Zeynel dosyayı okuyup iteratif geliştirsin

İlk hafta sonra varyasyon belirlenir → bu doküman 1.1, 1.2 olarak güncellenir.

---

## Bağlam — neden konsolide?

Eski 3-prompt sistemi:
- Zeynel 3 ayrı kez yapıştırıyor → zaman kaybı, dikkat dağılımı
- Bağlam tekrarı → token israfı
- Bölüm geçişi karışıklığı → Claude bazen başka oturuma geçtiğini sanıyor
- Sıra ihlali → 1B atlanırsa 1C'nin context'i kayboluyor

Konsolide:
- Tek yapıştırma → 3 kat hızlı başlatma
- Tek bağlam → daha tutarlı çıktı
- Belirgin sıra → atlama yok
- Test edilebilir tek çıktı (DAILY_SABAH_*.md)

---

## Geliştirme ipuçları

- **Bir prompt değiştiğinde**: version bump (1.0 → 1.1) + bu dokümana not düş
- **Hafta sonu erken çalıştırma yapılırsa**: prompt'un başında "DUR" çıkışı bu konsolide versiyonda zaten var
- **Yeni bölüm eklenmek istenirse**: Bölüm 5 olarak ekle, mevcut 4 bölüm dokunulmasın (regression riski)
- **Bölüm sırası değişmesin**: 1 (makro) → 2 (sağlık) → 3 (swing) → 4 (portföy fırsatları) doğal information hierarchy

---

## Bağlantılar

- [[SESSION_REFERENCE]] — seans öncesi vs içi protokol
- [[PORTFOLIO_OPPORTUNITY_SYSTEM]] — 3 portföy tarama mantığı detayı
- [[TRADING_PLAYBOOK]] — K-rules tam referans
- [[K_RULES_QUICK_REF]] — aktif K-rules (sade)
- [[MARKET_INTELLIGENCE]] — proactive tema tracking, Section 0 mandatory
