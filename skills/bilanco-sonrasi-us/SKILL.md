---
name: bilanco-sonrasi-us
description: ABD bilanço sezonu sonrasında yüksek potansiyelli hisseleri 4 katmanlı veri ile otomatik tarayan sistem. FMP earnings calendar → mid-cap+ filtre → YoY/QoQ iyileşme → 4 yöntem adil değer → bilanço sonrası analist revize sayımı (raised vs lowered) → telekonferans transcript guidance extract → 13F kurumsal birikim trendi → smart money portföy kontrolü → yıldız skorlu final shortlist. Adil Değer 9 Yöntem (v3.7.2) ve FMP_SKILL ile entegre. Kullanıcının bilanço sonrası fırsat aradığı her durumda tetikle - "bugün bilanço açıklayanları tara", "yeni bilançolardan yüksek potansiyelli hisseler bul", "earnings sonrası fırsat tarama", "post-earnings opportunity scan", "guidance teyitli tarama", "ABD bilanço tarayıcı", "şirket guidance raise eden hisseleri bul", "raised guidance momentum scan", "Q1/Q2/Q3/Q4 sonrası value momentum", "kurumsal birikim doğrulamalı tarama" gibi her ifadede. Sadece açık talep değil, "bu hafta bilanço açıklayan şirketlerden hangileri yatırımlık" gibi dolaylı sorularda da kullan.
---

# Bilanço Sonrası ABD Fırsat Tarayıcısı

**Versiyon**: v1.0 (9 Mayıs 2026)
**Bağımlılıklar**: FMP API (Ultimate plan zorunlu — transcript + 13F endpoint'leri için), `docs/FMP_SKILL.md`, `skills/adil-deger-9-yontem/`
**Kaynak**: finzora ai

## Amaç

Bilanço açıklamış ABD hisseleri arasından yapısal olarak iyileşme gösteren ve birden fazla bağımsız sinyalle teyit edilmiş yüksek potansiyelli hisseleri sistematik olarak tarar. Tek bir gecikmeli sinyal (örn. analist target consensus) yerine 4 farklı veri katmanını kombinleyerek false-positive'leri eler.

## Ne Zaman Tetiklenir

- "Bugün bilanço açıklayanları tara"
- "Son iki günün bilançolarından yüksek potansiyelli hisseler"
- "Earnings sonrası fırsat tarama"
- "Bu hafta bilanço veren şirketlerden yatırımlık olan var mı"
- "Guidance raise eden şirketleri bul"
- "Şirket forward outlook teyitli tarama"
- "Kurumsal birikim doğrulamalı bilanço sonrası tarama"

## Veri Katmanları (4 Katman)

| # | Katman | FMP Endpoint | Sinyal Türü |
|---|--------|--------------|-------------|
| 1 | Bilanço Temel Verileri | `income-statement?period=quarter`, `profile`, `ratios-ttm`, `key-metrics-ttm` | YoY/QoQ ciro+kâr büyüme, mid-cap+ filtre |
| 2 | Adil Değer ve Analist Hedefi | `price-target-consensus`, `analyst-estimates`, `key-metrics-ttm` | 4 yöntem ağırlıklı fair value, analist konsensüs hedefi |
| 3 | **Bilanço Sonrası Sinyaller (CORE)** | `price-target-news` (analist revize haberleri), `earning-call-transcript` (Ultimate gerekiyor) | Analist raised vs lowered yön sayımı, CFO/CEO doğrudan guidance sözleri |
| 4 | **Smart Money Birikim (CORE)** | `institutional-ownership/symbol-positions-summary`, `institutional-ownership/extract` | 13F shares net değişim, Druckenmiller/Buffett/Burry portföy kontrolü |

3. ve 4. katmanlar bu skill'in özgün değer önermesidir — diğer tarayıcılarda yoktur. Bu iki katman olmadan **HUBS örneği** (analyst downgrade dalgası) veya **CON örneği** (yatırımcı sayısı +10 yeni isim) tespit edilemez.

## Workflow (4 Aşama)

### Aşama 1 — Earnings Tarama ve Mid-Cap+ Filtre

`scripts/01_earnings_calendar.py` çalıştır:
- FMP `earnings-calendar?from={tarih_baslangic}&to={tarih_bitis}` ile bilanço açıklayan tüm ABD hisseleri çekilir
- Sadece `epsActual` veya `revenueActual` dolu olanlar (gerçekten raporlamış)
- `profile?symbol=...` ile her biri için `marketCap`, `price`, `exchange` (NYSE/NASDAQ/AMEX) çekilir

**KRİTİK ALAN ADI TUZAĞI** (bkz. `docs/FMP_SKILL.md`):
- `profile` endpoint'inde **`exchange`** alanı kullanılır, `exchangeShortName` DEĞİL
- `epsActual`/`revenueActual` (NOT: `actualEPS`, `actualRevenue` v3 legacy)

Filtre: `mcap >= $2B`, `price >= $10`, `exchange in (NYSE, NASDAQ, AMEX)`, `not isEtf`, `not isFund`, `isActivelyTrading`

Çıktı: `01_filtered_midcap.json` (~150-300 hisse)

### Aşama 2 — İyileşme Filtresi (YoY/QoQ)

`scripts/02_growth_filter.py`:
- Her hisse için `income-statement?period=quarter&limit=5` çekilir (son 5 çeyrek)
- `q[0]` = en son çeyrek, `q[1]` = QoQ karşılaştırma, `q[4]` = YoY karşılaştırma

Kriterler (en az 3/4 + YoY rev zorunlu):
- YoY ciro artışı ≥ 8%
- YoY net kâr artışı ≥ 15% **VEYA** zarardan kâra geçiş (L2P)
- QoQ ciro artışı ≥ 3%
- QoQ net kâr iyileşmesi

**Outlier filtre**: `yoy_rev > 500%` IPO/M&A artefaktı, ele.

Çıktı: `02_growth_passed.json` (~30-60 hisse)

### Aşama 3 — Adil Değer + Analist Target Teyidi

`scripts/03_valuation.py` — 4 yöntem ağırlıklı:

1. **Analist hedef konsensüs** (`price-target-consensus`) — ağırlık 30%
2. **Forward P/E × NTM EPS** (sektör çarpanı, `analyst-estimates`) — ağırlık 30%
3. **PEG = 1 fair value** (TTM EPS × growth, capped 5-30%) — ağırlık 20%
4. **EV/EBITDA peer median × EBITDA − Net debt** — ağırlık 20%

**Sağlamlık filtresi**:
- Analist hedef ZATEN minimum +25% upside vermeli (en güvenilir tek metrik)
- En az 1 fundamental yöntem (Forward P/E veya EV/EBITDA) +20% pozitif teyit

**L2P (zarardan kâra) hisselerde**: PEG yöntemini ağırlıktan çıkar (TTM EPS düşük baz distortion'a neden olur).

Detay metodoloji: `references/workflow_detail.md` ve `skills/adil-deger-9-yontem/SKILL.md`.

Çıktı: `03_solid_shortlist.json` (~10-20 hisse)

### Aşama 4 — Bilanço Sonrası Sinyaller (BU SKILL'İN ÖZGÜN KISMI)

`scripts/04_post_earnings_signals.py` — 3 alt katman:

#### 4a) Analist Revize Yön Sayımı

Her hisse için `price-target-news?symbol=X&limit=15` ile bilanço sonrası analist hedef revize haberleri.

Yön tespiti: `newsTitle` içinde "raise" veya "lower"/"cut" anahtar kelimesi.

| Sinyal | Yorum |
|--------|-------|
| Tüm raised, hiç lowered yok | 🟢 Çok Güçlü (BILL örneği: MS+Oppenheimer raised) |
| 2/3+ raised, 1/3 lowered | 🟢 Güçlü (CELH örneği: DB raised, MS lowered) |
| Karışık (eşit) | 🟡 Nötr |
| 2/3+ lowered | 🔴 Zayıf (TOST: 3/3 lowered) |
| Hepsi lowered, 8+ broker | 🔴🔴 Kapitulasyon (HUBS: 13/13 lowered) |

#### 4b) Telekonferans Transcript Guidance Extract

`earning-call-transcript?symbol=X&year=YYYY&quarter=Q` (FMP Ultimate gerekli, **`earning` TEKİL** — `earnings-call-transcript` 404 verir)

**Fiscal year tuzağı**: BILL Haziran biten fiscal year, 7 May 2026 raporu Q3 FY26 (`quarter=3`). VST/CON/CELH calendar year, `quarter=1`. Belirsizse önce `earnings-transcript-list` ile mevcut dönemleri kontrol et.

**Yayın gecikmesi**: Bilanço açıklamasından 12-48 saat sonra transcript yayınlanır. Aynı gün/ertesi gün boş dönebilir (FIS 8 May raporu için 9 May sabahı transcript yoktu).

Anahtar kelime tabanlı skor (cümle bazında):
- `guidance`, `outlook`, `reaffirm`, `raise`: ağırlık 3
- `expect`, `forecast`, `project`: ağırlık 2
- `fiscal year`, `full year`, `second quarter`: ağırlık 2
- `2027`, `partnership`: ağırlık 2-3

Top 10-12 cümleyi extract et, manuel okuma için raporta sun.

**Ne aranıyor**:
- "Reaffirming our guidance" → REAFFIRMED
- "Raising the midpoint of our guidance" → RAISED ✓
- "Lowering our outlook" → LOWERED ✗
- "We expect to update our guidance ranges following X" → upcoming UPWARD revize sinyali (VST Cogentrix örneği)
- "Side-step", "plateau" → kısa vade momentum uyarısı (CELH Q2 örneği)

#### 4c) 13F Kurumsal Birikim ve Smart Money Kontrolü

`institutional-ownership/symbol-positions-summary?symbol=X&year=Y&quarter=Q`

Sinyal yorumu:
- `numberOf13FsharesChange > 0` → kurumsal birikim
- `investorsHoldingChange > 0` → yeni yatırımcı girişi (CON örneği: +10)
- `numberOf13FsharesChange < 0` ama `investorsHoldingChange > 0` → konsolidasyon (yeni isim girip eski büyük çıktı)
- Yatırımcı sayısı ↓ ama shares ↑ → kalan büyük yatırımcılar pozisyon büyütüyor (CELH örneği)

**Smart money kontrolü** (`institutional-ownership/extract` ile):
- Druckenmiller (Duquesne, CIK `0001536411`)
- Buffett (Berkshire, CIK `0001067983`)
- Burry (Scion, CIK `0001649339`)
- Tepper (Appaloosa, CIK `0001656456`)
- Ackman (Pershing Square, CIK `0001336528`)

Bu yatırımcıların tüm holdings'ini çekip shortlist'in onlarda olup olmadığına bak. Tam CIK tablosu: `references/smart_money_ciks.md`.

**13F gecikmesi**: SEC kuralı 45 gün. Q1 2026 verisi ~15 May 2026 sonrası gelir. Şu an (9 May) en güncel Q4 2025.

Çıktı: `04_signals_enriched.json`

### Aşama 5 — Final Sıralama ve Yıldız Skor

`scripts/05_finalize.py`:

Her shortlist hissesi için 5 yıldız skoru:

```
+1 yıldız: Adil değer +30%+ analist hedefli
+1 yıldız: Şirket guidance RAISED (transcript veya 8-K)
+1 yıldız: Net analist target raised > lowered (post-earnings)
+1 yıldız: 13F shares net birikim Q4 (>+1M)
+1 yıldız: Smart money portföyünde (Druckenmiller/Buffett/Burry/Tepper)
```

Maks 5 yıldız. 4+ yıldız → öncelikli aday. 3 yıldız → ikinci tier. 2 yıldız → izleme. 1 yıldız → ele.

Final sıralama: yıldız skoru → adjusted upside %.

## Çıktı Formatı

`templates/rapor_template.md` şablonunu kullan:
- Yenilenmiş final tablo (yıldız + sektör + fiyat + hedef + üst pot. + sinyal özeti)
- Top 5 için detaylı hisse öneri formatı (4 alan: tetikleyici, veri, risk/stop, portföy)
- Shortlist'ten ÇIKARILANLAR (analist downgrade dalgası alanlar — fallen angel adayı olarak takipte)
- Bekleme listesi (ARGX/foreign issuer 6-K, transcript yok, vb.)
- Veri kaynakları tablosu
- KESİN/MUHTEMEL/SPEKÜLATİF etiketleri
- "Neden yanlış olabilirim" bölümü (zorunlu, en az 5 madde)

Rapor `reports/research/IYILESEN_BILANCOLAR_{YYYY-MM-DD}.md` olarak kaydedilir, GitHub'a push edilir.

## Hisse Öneri Formatı (Zorunlu — Memory Notu)

Her shortlist hissesi için 4 alan dolu olmalı:

1. **Tetikleyici (sinyal)**: Bilanço özelinde ne gerçekleşti?
2. **Veri dayanağı**: FMP metrik + somut rakam (mcap, fiyat, hedef, EPS, EBITDA, vs.)
3. **Risk / bear case / stop**: Tezi geçersizleştirebilecek senaryo, stop seviyesi (%)
4. **Hangi portföye uygun**: Dengeli / Aggressive / Dividend / Swing

## Bilinen Tuzaklar (Önemli)

`references/known_traps.md` — tüm tuzakların listesi. Özet:

1. **Day-1 chasing yasak** (KTOS/CEG/HAL/LASR): Bilanço sonrası ilk gün almak forbidden, min 1 gün cooldown + RSI confirmation
2. **L2P PEG distortion**: Zarardan kâra geçişlerde TTM EPS düşük baz, PEG yöntemini eleme
3. **Outlier YoY %500+**: IPO/M&A artefaktı, AHR örneği (%120279 YoY rev gerçek değil)
4. **Fiscal year vs calendar**: BILL/HUBS/CRM/ADBE/ORCL/NKE Haziran-Mayıs biten fiscal year, `quarter` parametresi dikkat
5. **Pre-market yanıltıcı olabilir**: %5+ pre-market hareketi açılışta tersine dönebilir
6. **Sayısal guidance vermeyen sektörler**: Energy drink, beverages, restaurant chains nadiren forward guidance verir; "ton" + "stair step" sinyalleri kullan (CELH örneği)
7. **Smart money tek başına yetmez**: Druckenmiller'da yok diye "kötü" denemez, broad institutional birikim daha geniş onay
8. **Strong earnings ≠ rally**: "Sell the news" riski (MU/RKLB örnekleri)
9. **13F gecikme**: 45 gün geçmeden önceki çeyrek verisi gelmez
10. **Same-sector aynı gün multiple entries**: Korelasyon riski

## Pipeline Komutu

Tek komutla baştan sona:

```bash
cd skills/bilanco-sonrasi-us/scripts
python3 run_pipeline.py --from 2026-05-07 --to 2026-05-08 --top 5
```

Argümanlar:
- `--from` / `--to`: Bilanço tarama dönemi (varsayılan: dünden bugüne)
- `--top`: Final shortlist boyutu (varsayılan: 10)
- `--push`: GitHub'a push (varsayılan: True)
- `--telegram`: Özet Telegram'a gönder (varsayılan: True, DM)

## References

- `references/workflow_detail.md` — Her aşamanın detaylı metodoloji açıklaması
- `references/smart_money_ciks.md` — Yatırımcı CIK referans tablosu (genişletilmiş)
- `references/known_traps.md` — Bilinen tuzaklar ve örnekler

## Bağlantılı Skill'ler

- `skills/adil-deger-9-yontem/SKILL.md` — Tek hisse için 11-bölüm tam adil değer raporu (final shortlist'in Top 3'ü için ayrıca çalıştırılır)
- `skills/finzora-stock-analysis/SKILL.md` — Tek hisse derinlemesine analiz
- `docs/FMP_SKILL.md` — FMP endpoint referansı (özellikle Ultimate-only endpoint'ler ve alan adı tuzakları)
- `docs/PORTFOLIO_OPPORTUNITY_SYSTEM.md` — Sabah taraması ile entegrasyon (PART 1C portföy fırsat taraması)

## CHANGELOG

### v1.0 — 9 Mayıs 2026
- İlk sürüm. 7-8 Mayıs 2026 bilanço taraması (1.296 hisse → Top 5: VST, BILL, CON, CELH, FIS) bu skill'in ilk uygulamasından doğdu
- 4 katmanlı veri pipeline (bilanço temel, adil değer, post-earnings sinyaller, smart money)
- Yıldız skor sistemi (5 maddeli)
- Bilinen tuzaklar listesi (10 madde)
- Adil Değer 9 Yöntem skill ile entegre
