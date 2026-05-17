# Polymarket Slug Araştırması — 17 Mayıs 2026

> Bu doküman `data/polymarket_themes.json` v2 güncellemesi sırasında yapılan keşfin notlarıdır. Gelecek bakım/genişletme için referans.

## Polymarket API Yapısı (Keşif Bulguları)

### URL Pattern
- **Event**: `polymarket.com/event/{event-slug}` — bir tema grubu, içinde birden fazla market
- **Market**: Event içindeki tek bir binary (Yes/No) piyasa, kendi slug'ı var

### Gamma API
- Base: `https://gamma-api.polymarket.com`
- `/markets?slug={market-slug}` — tek market detayı
- `/events?slug={event-slug}` — event + içindeki markets array
- `/markets?active=true&closed=false&limit=100&offset=N` — pagination ile aktif listesi
- Default sıralama: volume desc (en likit önce)
- `tag_id` parametresi var ama tag taksonomisi sığ (`/tags?limit=500` → 100 tag dönüyor)

## Doğrulanan Gerçek Slug'lar

### Fed Faiz İndirimi (`fed_rate_cut`)
**Event slug**: `fed-rate-cut-by-629` — total $1.72M vol, 8 binary market

En likit 4 market (whitelist'te):
| Slug | Volume | Yes prob |
|---|---|---|
| `fed-rate-cut-by-january-2026-meeting-412` | $588k | 1.65% |
| `fed-rate-cut-by-april-2026-meeting` | $543k | — |
| `fed-rate-cut-by-june-2026-meeting` | $277k | — |
| `fed-rate-cut-by-december-2026-meeting` | $109k | — |

Daha düşük volume (whitelist dışı): March, July, September, October 2026 meetings.

### China-Taiwan Gerilimi (`china_taiwan_tension`)
| Slug | Volume | End | Yes prob |
|---|---|---|---|
| `will-china-invade-taiwan-before-2027` | $23.4M | 2026-12-31 | düşük |

Skip: `will-china-invades-taiwan-before-gta-vi-716` ($1.8M, viral şaka marketi).

### ABD Resesyon (`us_recession_2026`)
| Slug | Volume | End |
|---|---|---|
| `us-recession-by-end-of-2026` | $1.46M | 2027-01-31 |

Aynı tema için `canada-recession-before-2027` ($67k) — düşük volume, atlandı.

## Pending Araştırma (boş slug listesi)

### Iran / Orta Doğu (`iran_escalation`)
Polymarket Iran kategorisinde:
- 20 aktif market, $279.1M total volume
- Çoğu "by [tarih]" formatlı, prob 100% Yes → olay olmuş, deadline'a kadar açık duruyor
- Aktif "geleceğe yönelik" tek-olay marketleri:
  - `israel-strikes-iran-by-june-30-2026` — Yes 100%, end Jun 30 (zaten gerçekleşmiş)
  - `israel-military-action-against-iran-by-167` — 3 hafta önce, muhtemelen resolved
  - "How many different countries will Israel strike in 2026?" — multi-outcome, $7M vol

Gelecek araştırma:
- "U.S. invade Iran before 2027?" benzeri uzun vadeli marketler için ara
- Multi-outcome marketler şu an kalibratör tarafından desteklenmiyor (binary only) — gelecek extension

### Trump Tariff Action (`trump_tariff_action`)
- Tariff kategorisi 114 market, $23.3M total vol — çoğu RESOLVED
- Aktif olanlar Trump-Xi summit'e bağlı (May 22, 2026 deadline) — kısa vadeli
- Web search'te bulunan event URL'leri:
  - `trump-xi-summit-what-will-trump-announce-by-may-22` ✓ aktif (deadline yakın)
  - `trump-xi-summit-what-will-china-announce-by-may-22` ✓ aktif ($324k vol)
  - `100-tariff-on-china-in-effect-by-november-1` ❌ resolved
  - `will-trump-visit-china-by` ❌ resolved
- Daha uzun vadeli "tariff in effect" marketi bulunamadı

Trump-Xi summit marketleri eklenebilir ama dikkat: deadline 5 gün sonra (May 22), kısa ömürlü.

## Önemli Notlar

### Min Volume Eşiği Stratejisi
Eski v1'de tüm temalar için $500k veya $1M sabit eşik. v2'de tema bazlı:
- **Yüksek-etki + tek market** (china_taiwan): $1M — manipulation guard güçlü
- **Çok marketli event** (fed): $250k — her market düşük vol, toplu sinyal alınır
- **Orta-etki** (recession): $500k — denge

### Çoklu Market Aynı Tema
Fed temasında 4 farklı slug var (Jan/Apr/Jun/Dec 2026). Kalibratör çalıştığında:
1. Her market için ayrı eşleşme/skor üretir
2. `Candidate.apply_calibration` (Adım 2'de implement) "en aşırı kazanır + downside protection" mantığıyla en güçlü sinyali seçer
3. Birden fazla bayrak listede (kalibrasyon transparency)

Test ile doğrulandı: `test_multiple_theme_matches_extreme_wins`.

### Multi-Outcome Marketler
Polymarket bazı eventlerde 3+ outcome destekliyor (örn. "How many Fed rate cuts in 2026?", "How many countries will Israel strike?"). Mevcut kalibratör SADECE binary Yes/No marketleri destekliyor (`outcomes` listesi ["Yes","No"] olmalı). `refresh_cache_for_themes` non-binary marketleri atlıyor (test ile doğrulandı).

Gelecek extension: Multi-outcome marketler için "biggest outcome probability change" mantığı eklenebilir.

### Resolved Markets
Gamma API `active=true&closed=false` filtresi kullanılıyor — resolved marketler zaten dahil edilmiyor. Whitelist'te yanlışlıkla resolved bir slug kalırsa kalibratör `markets[slug]` lookup başarısız olur, no-op yapar. Hata değil.

## Bakım Akışı

Yeni tema ekleme veya mevcut tema güncelleme:
1. Polymarket.com'da temayla ilgili kategoriyi gez (örn. `/economy`, `/predictions/tariff`)
2. En likit + aktif + uzun vadeli marketleri seç (deadline yakın olanları skip)
3. Gamma API'de doğrula: `curl gamma-api.polymarket.com/markets?slug=X`
4. Volume + end date + outcomes alanları konfirme et
5. `data/polymarket_themes.json` güncelle, `_slug_status: verified_YYYY-MM-DD` işaretle
6. min_volume_usd eşiğini volume'a uygun seç (likitin %20-50'si gibi)
