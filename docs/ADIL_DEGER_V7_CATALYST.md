# Adil Değer v7 — Katalist Katmanı

> **Versiyon:** v7.0-catalyst (7 Mayıs 2026)
> **Önceki sürüm:** v6.0 (cycle phase + AI consultation)
> **Önceki dokümantasyon:** `ADIL_DEGER_KULLANIM.md`

---

## 1. v7'nin Çözdüğü Problem

v6'ya kadar adil değer hesabı tamamen **finansal verilere** dayanıyordu (P/E, P/B, DCF, EV/EBITDA, NAV vb.). Bu, 95% durumda doğru çalışıyor ama iki durumda yetersiz kalıyor:

**Durum 1: Pre-revenue şirketler.** AIRJ gibi yıllardır $0 ciro üreten cleantech/hardware şirketleri için geleneksel metotların hiçbiri çalışmaz. v6'da bu şirketler `generic_equity` fallback'ına düşüp güven 10/100 ile yetersiz veri kararı alıyordu.

**Durum 2: Açıklanamayan fiyat hareketleri.** AIRJ'nin 6 Mayıs 2026'da +%13.6 sıçraması finansal verilerle açıklanamaz. Sebep haber, 8-K dosyası veya makro olabilir. v6 bunu sessizce görmezden geliyordu — kullanıcıya "iyi giriş noktası" sinyali verirken aslında haber-tetikli geçici bir hareket olabilirdi.

v7 bu iki problemi çözer:
1. **`pre_revenue_hardtech` archetype** — AIRJ tipi şirketler için NAV-tabanlı 5 metot
2. **Catalyst Layer** — Haber + SEC dosyalarıyla bağlam ekler

---

## 2. Mimari Değişiklikler

### 2.1. Yeni Archetype: `pre_revenue_hardtech`

`agent/valuation/archetypes.py` içinde tanımlı. Tetiklenme kriteri (`classifier.py`):

```
ttm_revenue < $1M
AND
sektör/sanayi içinde (industrial, electrical equipment,
                      electronic equipment, machinery,
                      renewable, solar, clean, battery,
                      fuel cell, hydrogen, water)
AND
mcap < $5B
```

Aktif metotlar:

| Tier | Metot | Ağırlık | Açıklama |
|------|-------|---------|----------|
| primary | `nav_per_share_adjusted` | 35% | (Nakit + LT yatırım - düzeltilmiş borç) / hisse |
| primary | `tangible_book_capped` | 20% | TBV × P/B çarpanı, dilüsyon penaltısı dahil |
| primary | `cash_plus_runway` | 20% | Nakit/hisse × runway çarpanı (1-1.3) |
| secondary | `price_to_tangible_book` | 10% | Klasik P/TBV |
| secondary | `price_to_book` | 5% | Klasik P/B |
| sanity | `analyst_target_method` | 10% | Analist konsensüsü (düşük güven) |

Yasaklanan metotlar (toplam 18): tüm P/E varyantları, EV/EBITDA, EV/Revenue, DCF varyantları, FCF yield, dividend discount, biotech-specific metotlar, REIT-specific metotlar.

### 2.2. Catalyst Layer

`agent/valuation/catalyst_layer.py` (yeni dosya, 410 satır).

**İki veri kaynağı:**
- FMP `/news/stock?symbols=X` — son 90 gün haberleri (limit 50)
- FMP `/sec-filings-search/symbol?symbol=X&from=...&to=...` — son 90 gün SEC dosyaları (limit 30)

**Üç işlem:**

**1. Relevance filter (gürültü temizleme).**
FMP haber endpoint'i bazen alakasız haberleri ticker'a etiketler (örn AIRJ Montana merkezli olduğu için tüm Montana haberleri etiketleniyordu). Çözüm: şirket profilinden distinctive isim çıkar (`AirJoule` gibi), title+text içinde ya bu isim ya ticker geçmiyorsa ele.

AIRJ örneğinde 22 haberden 8'e indi (14 gürültü).

**2. Sınıflandırma (keyword-tabanlı).**

Pozitif keyword'ler (40 adet): partnership, agreement, contract awarded, fda approval, beats estimates, raises guidance, milestone, insider buying, buyback authorized, vb.

Negatif keyword'ler (35 adet): going concern, bankruptcy, sec investigation, misses estimates, lowers guidance, ceo resigns, dilutive offering, shelf registration, product recall, dividend suspended, vb.

Karışık durumda negatif baskın — "raises guidance but warns of..." cümleleri negatif sayılır.

SEC dosya tipi sınıflandırması:
- **Negatif:** S-1, S-3, S-3ASR, 424B5, 424B3 (sulandırma); NT 10-K/10-Q (geç dosyalama)
- **Pozitif:** 8-K item 1.01 (maddi anlaşma), item 8.01 (diğer pozitif duyuru)
- **İçeriden:** Form 3, 4, 5
- **Rutin:** 10-K, 10-Q, DEF 14A

**3. Zaman ağırlığı.**

| Yaş | Ağırlık | Mantık |
|-----|---------|--------|
| 0-7 gün | 1.0 | Taze, fiyatlanmamış olabilir |
| 7-30 gün | 0.5 | Hâlâ etkili ama çoğunlukla fiyatlanmış |
| 30-90 gün | 0.25 | Eski, sadece bağlam |
| 90+ gün | 0 | İlgisiz |

**Skor formülü:**
```
score = sum(pozitif_haberler) × 10 × ağırlık
      - sum(negatif_haberler) × 15 × ağırlık
      + sum(pozitif_filings) × 8 × ağırlık
      - sum(negatif_filings) × 12 × ağırlık

Sınır: -100 ile +100
```

### 2.3. Bayraklar (Flags)

Catalyst layer aşağıdaki bayrakları üretir:

| Bayrak | Tetik | Etki |
|--------|-------|------|
| `fresh_positive` | Son 7 günde pozitif maddi haber | Güven +8 |
| `fresh_negative` | Son 7 günde negatif maddi haber | Güven -12 |
| `dilution_risk` | Son 30 günde S-3/S-1/şelf | Güven -10 |
| `going_concern` | Haberde "going concern" / "bankruptcy" | Güven -20 |
| `insider_buying_cluster` | Son 30 günde 3+ Form 4 | Güven +5 |
| `no_recent_news` | Son 90 günde hiç haber yok | (sadece bilgi) |
| `pre_revenue_no_positive_90d` | Pre-revenue + 90 günde pozitif yok | Karar max NÖTR |
| `unexplained_move` | %7+ hareket + son 7 gün haber/8-K yok | Güven -8 + red flag |

Toplam confidence düzeltmesi -20 ile +15 arası klemplenir.

### 2.4. Pre-Revenue Override Mantığı

Pre-revenue archetype'ında ekstra kural: son 90 günde **hiç pozitif maddi haber yoksa**, karar etiketi en iyi ihtimalle "ADİL" olabilir, "UCUZ" olamaz. Sebep: pre-revenue şirketlerin değeri **gelecekteki katalist gerçekleşmesine** bağlıdır. Katalist gelmiyorsa (90+ gün sessizlik), şirket muhtemelen unutulmuş veya proje yavaşlamış demektir, defter değeri tabanı yeterli güvence değil.

Pratikte: AIRJ son 90 günde Q4 2025 sonuçlarını yayınladı (pozitif sınıflandı, "partnership" kelimesi geçtiği için), bu nedenle override **devreye girmedi**. Eğer hiç haber olmasaydı, $4.99 adil değer + +%42.5 upside olduğu halde karar "UCUZ" değil "ADİL" olurdu.

---

## 3. Cache Mekanizması

Konum: `data/rag/catalyst_cache/<TICKER>.json`
TTL: 6 saat

Aynı ticker için 6 saat içinde tekrar `compute_catalyst_layer` çağrıldığında FMP'ye gitmek yerine cache okur. Bu önemlidir çünkü her morning_scan / closing rapor için 12+ portföy ticker'ı sorgulanır, FMP rate limit'i (2,500/dakika) için verimlilik gerek.

`.gitignore`'da: `data/rag/catalyst_cache/`

Manuel temizleme: `rm -rf data/rag/catalyst_cache`

---

## 4. fetch_all_data Güncellemeleri

`agent/valuation/methods/__init__.py` içinde yeni alanlar:

| Alan | Kaynak | Kullanım |
|------|--------|----------|
| `change_pct_today` | quote (manuel hesap) | unexplained_move tespiti |
| `long_term_investments` | balance-sheet | NAV hesabı (JV iştiraki vb.) |
| `deferred_tax_liab` | balance-sheet | NAV düzeltmesi |
| `total_liabilities` | balance-sheet | NAV hesabı |
| `current_assets` | balance-sheet | likidite kontrolü |
| `current_liabilities` | balance-sheet | likidite kontrolü |

`change_pct_today` özellikle kritik: FMP `changesPercentage` seans esnasında 0 dönebildiği için manuel hesap (`(price - prev_close) / prev_close × 100`) yapıldı.

---

## 5. AIRJ Test Sonucu (7 Mayıs 2026)

```
Archetype:  pre_revenue_hardtech (%85 güven)
Trigger:    Pre-revenue hardtech (rev=$0.0M, mcap=$240M, ind=Electrical Equipment & Parts)
Cycle:      mid (50%)

Adil değer:  $4.99
Aralık:      $4.86 - $5.41
Mevcut:      $3.50
Upside:      +%42.5
Karar:       UCUZ
Güven:       62/100

Metotlar:
  - nav_per_share_adjusted    $4.34  (w=0.35)
  - tangible_book_capped      $4.46  (w=0.20)
  - price_to_tangible_book    $4.83  (w=0.10)
  (cash_plus_runway, price_to_book, analyst_target_method outlier filtresine takıldı)

Catalyst Layer:
  Skor:    +2.5 (90 gün)
  Haberler: 1 pozitif, 0 negatif, 7 nötr (toplam 8 ilişkili)
  Dosyalar: 15 (8-K: 2, şelf: 0)
  Bayraklar: [unexplained_move (+13.6%)]

Red Flags:
  - 2_outliers_removed
  - konsensüs_orta_sapma_bearish (-36% vs $7, conf -10)
  - catalyst: unexplained_move (+13.6%)
```

**Yorum:** Adil değer $4.99 hesaplandı. Upside +42.5% görünmesine rağmen "unexplained_move" bayrağı dünkü +%13.6 sıçramayı haber/8-K ile açıklayamadı, güven -8 düşürüldü ve red flag eklendi. Bu yatırım kararı için kritik uyarıdır: **fiyat hareketinin sebebi belirsiz, önce neden yükseldiğini anlamadan giriş yapılmamalı**.

---

## 6. Regresyon Testi (5 Ticker)

| Ticker | Archetype | Adil | Mevcut | Upside | Güven | Catalyst |
|--------|-----------|------|--------|--------|-------|----------|
| AAPL | mature_megacap_tech | $285.15 | $287.51 | -0.8% | 88/100 | +5.0 |
| MSFT | mature_megacap_tech | $336.75 | $413.96 | -18.7% | 78/100 | +50.0 |
| JNJ | pharma_big | $187.71 | $224.62 | -16.4% | 88/100 | +15.0 |
| KO | consumer_staples_aristocrat | $84.23 | $79.23 | +6.3% | 92/100 | 0 |
| NVDA | hyper_growth_semi | $354.42 | $207.83 | +70.5% | 86/100 | +60.0 |

Hepsinde framework çalıştı, hiçbir kırılma yok. Catalyst layer farklı ticker'larda farklı flag profilleri üretti (AAPL hem fresh_positive hem fresh_negative, JNJ insider_buying_cluster, NVDA fresh_positive).

---

## 7. Geri Uyumluluk

- v6 API'sini kullanan tüm script'ler değişiklik gerektirmeden çalışır
- `valuate()` fonksiyonu çıktı dict'ine `"catalyst_layer"` ve `"framework_version": "v7.0-catalyst"` alanlarını eklediği için downstream consumers (raporlar, telegram bildirimleri) eski şemayı okumaya devam eder
- Catalyst layer modülü import edilemezse framework sessizce eski v6 davranışına döner (`_CATALYST_AVAILABLE = False`)

---

## 8. Bilinen Limitasyonlar

1. **Keyword-tabanlı sınıflandırma sınırlı.** İngilizce keyword listesi 75 kelime. Daha doğru sınıflandırma için Claude API çağrısı yapılabilir ama maliyet/latency tradeoff'u var. Şu an her ticker için ~2 FMP çağrısı yapılıyor; AI sınıflandırma eklenirse her haber için ek ~1 saniye + token maliyeti.

2. **8-K item-level detay yok.** FMP'nin filings endpoint'i 8-K'nın hangi item olduğunu (1.01 maddi anlaşma vs 5.02 yönetici ayrılışı) döndürmüyor — sadece "8-K" diyor. Bu nedenle 8-K içerik analizi için ek scraping gerekecek (`finalLink` URL'sini fetch et + parse). Şu an "8k_event" olarak nötr sayılıyor.

3. **Insider buying/selling karıştırılıyor.** Form 4 için alış mı satış mı ayrımı FMP'de yok. Şu an heuristic: Form 4 = alış kabul edilmiş. Bu hatalı olabilir, gerçek alış/satış için Form 4 XML parse gerekir.

4. **Relevance filter yanlış pozitif üretebilir.** Şirket adının distinctive parçası başka bir bağlamda da geçebilir (örn. "AirJoule" başka bir teknolojide kullanılırsa). Pratikte AIRJ için sorun çıkmadı ama kenar durumlar mümkün.

5. **Pre-revenue eşiği katı (`rev < $1M`).** Yıllık $5M ciro üreten ama hâlâ erken aşama bir cleantech şirketi `pre_revenue_hardtech` yerine başka bir archetype'a (örn. industrial_cyclical) düşebilir. İleride `early_stage_hardtech` (rev $1M-$50M) gibi ara bir archetype gerekebilir.

6. **Catalyst skor henüz fair value'yu doğrudan değiştirmiyor.** Sadece confidence ve red flags etkiliyor. İleride çok güçlü pozitif katalist (skor > +50) durumunda fair value'ya küçük bir momentum çarpanı (1.05-1.10) eklenebilir, ama bu kovalama riskini artırır — şu an muhafazakâr yaklaşım tercih edildi.

---

## 9. Kullanım Örnekleri

**Tek ticker:**
```bash
export FMP_API_KEY="..."
python3 scripts/adil_deger_calculator.py AIRJ
```

**Portföy:**
```bash
python3 scripts/adil_deger_calculator.py --portfolio aggressive --report
```

**Sadece catalyst layer testi:**
```bash
python3 agent/valuation/catalyst_layer.py AIRJ pre_revenue_hardtech
```

**Python'dan:**
```python
import sys; sys.path.insert(0, 'agent')
from valuation.framework import valuate
result = valuate('AIRJ', verbose=True)
print(result['catalyst_layer'])
```

---

## 10. Neden Yanlış Olabilirim

- Catalyst skor hesabı backtest edilmedi. Tarihsel veriyle hangi skor eşiklerinin gerçekten yatırım kararını iyileştirdiğini bilmiyoruz. İlk 30 gün canlı kullanım sonrası tuning gerek.
- Keyword listesi tek başına yetersiz olabilir. "Wins major contract from Lockheed Martin" → pozitif yakalanır, ama "Court rules in favor of company" → yakalanmaz çünkü "rules" pozitif keyword listemizde yok.
- Pre-revenue override (90 gün sessizlik → max NÖTR) belki çok katı. Bazı pre-revenue şirketler 6 ay sessiz kalıp sonra major katalist üretebilir; bu süreçte değeri olabilir.
- Confidence düzeltmesi `-20 ile +15` aralığı asimetrik (negatif daha ağır). Bu bilinçli bir tercih (sermaye koruma) ama yanlış pozitif kaçırma riskini artırır.

---

## 11. İleri Adımlar

1. **8-K item parser** — `finalLink` URL'sinden 8-K içeriğini çek ve item numarasını çıkar
2. **AI keyword classification fallback** — keyword sözlüğü 0 hit verirse Claude API ile sınıflandır
3. **Insider Form 4 detay** — XML parse ile alış/satış ayrımı
4. **Catalyst-fair-value coupling** — çok güçlü pozitif katalistte fair value'ya momentum çarpanı ekle (ihtiyatlı)
5. **Backtest** — son 6 ay AIRJ + 5 pre-revenue ticker için historical catalyst replay; hangi flag'lerin gerçekten alpha ürettiğini ölç

---

Kaynak: finzora ai
