# Sektör Deep Dive Raporu — Veri Şeması

> Template: `template.html`
> Örnek: `ornek_veri_merkezi_zinciri_2026-04-19.html`
> Skill dokümantasyonu: `docs/SEKTOR_DEEP_DIVE_SKILL.md`

Bu dosya, `template.html` içindeki tüm `{{PLACEHOLDER}}` alanlarının ne anlama geldiğini ve hangi formatta doldurulacağını açıklar.

---

## 1. ÜST METİN PLACEHOLDER'LARI (string)

| Placeholder | Açıklama | Örnek (Veri Merkezi raporu) |
|---|---|---|
| `{{TEMA_BASLIGI}}` | `<title>` etiketi için. Tam tema adı. | `Veri Merkezi Tedarik Zinciri` |
| `{{TEMA_KISA}}` | Nav subtitle, kısa tema. | `Veri Merkezi Zinciri` |
| `{{RAPOR_TARIHI}}` | Nav'da gösterilecek tam tarih. | `19 Nis 2026 · 15:20 TR` |
| `{{RAPOR_TARIH_KISA}}` | Sonuç meta'sındaki kısa tarih. | `19 Nis 2026` |
| `{{HERO_BASLIK_PRE}}` | Hero h1 başlığında <em> öncesi metin. | `Veri merkezi zincirinin` |
| `{{HERO_BASLIK_VURGU}}` | Hero h1 vurgu kelimesi (italik altın). | `fiyatlanmamış` |
| `{{HERO_BASLIK_POST}}` | Hero h1 vurgudan sonraki metin. | `halkaları` |
| `{{HERO_OZET}}` | Hero altındaki 1-2 cümlelik özet. | `Dev bulut şirketleri 2026'da altyapıya $600–700 milyar harcayacak...` |
| `{{KATMAN_SAYISI}}` | Üst metada gösterilen toplam katman sayısı. | `12` |
| `{{HISSE_SAYISI}}` | Toplam analiz edilen hisse sayısı. | `54` |
| `{{ONERI_SAYISI}}` | 3 portföye toplam öneri sayısı. | `22` |
| `{{UYARI_SAYISI}}` | Avoid kategorisindeki hisse sayısı. | `13` |
| `{{ANA_BULGU_BASLIK}}` | Key finding kutu başlığı. HTML `<strong>` kullanılabilir. | `Piyasa, yapay zekâ hikâyesini en çok <strong>üç katmanda yetersiz fiyatlıyor</strong>...` |
| `{{ANA_BULGU_GOVDE}}` | Key finding kutu gövdesi. HTML span sınıfları kullanılabilir: `<span class="bull">`, `<span class="warn">`. | `<span class="bull">GE Vernova, Cummins, Onto Innovation...</span> aynı AI rüzgârını saf lider değerlemesinin yarısında sunuyor...` |
| `{{TEMA_POTANSIYEL_ETIKETI}}` | Harita y-eksen etiketinde kullanılan tema kısa adı. | `AI` |
| `{{INSIDER_UYARI_GOVDE}}` | İçeriden satış uyarısı gövde metni. Eğer bu bölüm tema için anlamlı değilse boş bırak veya tüm `<section>` bloğunu sil. | `Nisan 2026 itibariyle aynı anda görülen içeriden satış yoğunlukları...` |

---

## 2. PORTFÖY METİN PLACEHOLDER'LARI

| Placeholder | Açıklama | Örnek |
|---|---|---|
| `{{DENGELI_POZ_SAYISI}}` | Dengeli portföy pozisyon sayısı (sekmede). | `7` |
| `{{AGRESIF_POZ_SAYISI}}` | Agresif pozisyon sayısı. | `9` |
| `{{TEMETTU_POZ_SAYISI}}` | Temettü pozisyon sayısı. | `6` |
| `{{DENGELI_HEDEF}}` | Dengeli portföy panel hedef cümlesi. `<em>` vurgu kullanılabilir. | `Tek hisse riskini yaymak; <em>kâr eden, temettü ödeyen, sipariş defteri görünürlüğü yüksek</em> isimleri öne çıkarmak.` |
| `{{AGRESIF_HEDEF}}` | Agresif hedef cümlesi. | `En yüksek <em>AI kaldıracı</em>, en hızlı kazanç büyümesi...` |
| `{{TEMETTU_HEDEF}}` | Temettü hedef cümlesi. | `Çift haneli <em>nakit akış getirisi</em>...` |

---

## 3. KAÇINILACAKLAR & SONUÇ

| Placeholder | Açıklama | Örnek |
|---|---|---|
| `{{KACINILACAK_BASLIK}}` | Avoid bölümü başlığı. | `Kusursuz fiyatlı + yönetişim uyarısı` |
| `{{KACINILACAK_OZET}}` | Avoid kutusu altındaki açıklama. | `Bu 13 isim ya fiyatı hikâyenin çok önüne geçmiş...` |
| `{{SONUC_PARAGRAFLARI}}` | 3-4 paragraflık sonuç. Her paragraf `<p>...</p>` içinde, `<strong>`, `<span class="bull">`, `<span class="bear">` kullanılabilir. | `<p>Nisan 2026'da veri merkezi zincirinin <strong>her halkası AI hikâyesini duymuş durumda</strong>...</p>` |

---

## 4. VERİ DİZİLERİ (JavaScript object/array — placeholder yorum satırları)

### `{{LAYERS_VERILERI}}`

```javascript
const LAYERS = {
  1: {
    num: '01',                    // İki haneli (string)
    title: 'Elektrik & Şebeke',   // Katman ana adı
    sub: 'Dev bulut şirketlerinin enerji açlığı',  // Alt başlık
    summary: 'Eaton sektör lideri ama çarpanı doluya yakın. Gerçek fırsat GE Vernova ve Cummins\'te...'  // 1-2 cümle özet
  },
  2: { num: '02', title: '...', sub: '...', summary: '...' },
  // ... her katman için bir kayıt
};
```

**Kurallar:**
- Anahtar `1, 2, 3, ...` integer
- `num` string olmalı, baştaki sıfır korunmalı (`'01'`, `'02'`)
- `summary` 1-2 cümle, hangi isim ucuz, hangi pahalı, neden — özet kararı içerir
- Türkçe metin, finans dili, "AI" gibi yerleşik kısaltmalar bırakılır

### `{{STOCKS_VERILERI}}`

```javascript
const STOCKS = [
  {
    t: 'GEV',                     // Ticker (string, 1-5 harf)
    n: 'GE Vernova',              // Tam şirket adı
    l: 1,                         // Katman numarası (LAYERS anahtarı)
    cat: 'cheap',                 // Kategori (5 değerden biri - aşağıda)
    val: 3,                       // Değerleme skoru 1-10 (1=çok ucuz, 10=çok pahalı)
    pot: 9,                       // Potansiyel skoru 1-10 (1=düşük, 10=yüksek)
    fwdPE: '50x / 16x (2028)',    // İleri F/K metni — serbest format
    peerDisc: 'Büyük (2027-28 FAVÖK bazında)',  // Rakibe göre iskonto
    why: '150 milyar $ sipariş defteri, 83 GW gaz türbini <strong>2028\'e kadar satılmış</strong>...',
    risk: 'Rüzgar segmenti yakın dönem kazancı baskılıyor...',
    portfolios: ['balanced']      // Hangi portföylerde önerilir: 'balanced', 'aggressive', 'dividend' veya boş []
  },
  // ... her hisse için bir kayıt
];
```

**Kategori değerleri (`cat`):**

| Kategori | Anlamı | Renk | Ne zaman kullanılır |
|---|---|---|---|
| `cheap` | En Ucuz + Yüksek Potansiyel | Yeşil (#7dd3a0) | val ≤ 4 ve pot ≥ 7. "Altın madeni" kadran. |
| `hidden` | Gizli Kazanan | Cyan (#4ecdc4) | val 3-6, pot 6-8. Piyasanın gözden kaçırdığı. |
| `quality` | Kaliteli / Makul Fiyat | Altın (#f4c430) | Lider ama prim ödüyorsun, fiyat dolu sayılır. |
| `hold` | Portföyde / Koru | Violet (#a78bfa) | Zeynel'in mevcut portföyünde olan, korunması önerilen. |
| `avoid` | Kaçın | Kırmızı (#ff6b6b) | val ≥ 7 + pot ≤ 5, ya da yönetişim/insider/hukuki risk. |

**Kurallar:**
- `val` ve `pot` raporun haritasını oluşturur. Aynı val-pot çiftine düşen hisseler haritada otomatik ofset alır.
- `why` hisse kartında yeşil noktalı satır (pozitif tez) olarak çıkar. `<strong>` ile vurgu yapılabilir.
- `risk` kartta kırmızı noktalı satır (risk) olarak çıkar.
- `portfolios` boşsa "Öneri yok" tag'i çıkar.
- `cat: 'avoid'` olan hisseler ayrıca "Kaçınılacaklar" bölümünde otomatik listelenir.
- `fwdPE` içinde `<strong>` kullanılırsa kart üstündeki metric'te görünür.
- Türkçe yazılmalı; `dev bulut şirketleri` (hyperscaler), `nearline HDD`, `HBM` gibi yerleşik teknik terimler korunur.

### `{{PORTFOLIOS_VERILERI}}`

```javascript
const PORTFOLIOS = {
  balanced: [
    {
      t: 'GEV',                         // STOCKS dizisinden bir ticker (mutlaka var olmalı)
      metric: '50x/16x 2028',           // Kart sağda altın renk metric
      reason: '<strong>Uzun vadeli altyapı franchise\'ı</strong>. 150 milyar $ sipariş defteri, 2028\'e kadar satılmış gaz türbini, değerleme 2027-28 FAVÖK\'e göre makul.'
    },
    // ...
  ],
  aggressive: [
    // 6-9 öneri
  ],
  dividend: [
    // 5-6 öneri, hepsi temettü ödeyen
  ]
};
```

**Kurallar:**
- Her portföy için 5-9 pozisyon öneril
- `t` mutlaka `STOCKS` içinde tanımlı bir ticker olmalı (yoksa kart adı gösterilmez)
- `metric` 2-4 kelimelik kısa rakam etiketi (P/E, temettü, büyüme yüzdesi vs.)
- `reason` 1-2 cümlelik gerekçe; <strong> ile en kritik veriyi vurgula
- Aynı hisse birden fazla portföyde olabilir (örn. CMI hem balanced hem dividend)
- Portföy max ağırlık kuralları:
  - **Dengeli ($100K):** her hisse en fazla %20
  - **Agresif ($400K):** her hisse en fazla %15
  - **Temettü ($100K):** minimum %3 temettü, max %15 her hisse

### `{{TICKER_VERILERI}}`

```javascript
const tickerStocks = [
  { t: 'GEV', p: 658.40, c: +2.34 },  // Ticker, fiyat (USD), günlük değişim %
  { t: 'CMI', p: 438.15, c: +1.12 },
  // 15-20 önemli hisse — raporun ana karakterleri (cheap+hidden+avoid karışımı)
];
```

**Kurallar:**
- 15-20 ticker yeterli (sayfanın üstündeki kayan band için)
- `p` rapor tarihindeki son fiyat
- `c` günlük yüzde değişim (negatif için `-`, pozitif için `+`)
- Hem yeşil (cheap'ler) hem kırmızı (avoid'lar) görünmeli — denge için

### `{{INSIDER_VERILERI}}` (opsiyonel)

```javascript
const INSIDER_SIGNALS = [
  { t: 'VRT', text: '123M$ 1. çeyrek yönetici satışı · açığa satış aylık +%47' },
  { t: 'APH', text: '112M$ satış vs 1.3M$ alış · UBS fiyat hedefini düşürdü' },
  // ...
];
```

**Kurallar:**
- Tema için anlamsızsa boş dizi `[]` olarak bırak — section otomatik gizlenir.
- Sadece `cat: 'avoid'` olan ve gerçekten içeriden satış uyarısı olan hisseler için kullan.
- 4-8 sinyal ideal.

---

## 5. RENGİ DEĞİŞTİRİLEN HTML SPAN SINIFLARI (gövde metinlerinde)

`{{HERO_OZET}}`, `{{ANA_BULGU_GOVDE}}`, `{{SONUC_PARAGRAFLARI}}` içinde kullanılabilir:

| Sınıf | Renk | Kullanım |
|---|---|---|
| `<span class="bull">...</span>` | Yeşil | Olumlu/ucuz isimler vurgu |
| `<span class="bear">...</span>` veya `<span class="warn">...</span>` | Kırmızı | Negatif/pahalı isimler vurgu |
| `<strong>...</strong>` | Beyaz, kalın | Genel vurgu |
| `<em>...</em>` | İtalik altın (sadece h1/h2 içinde) | Başlık vurgu |

---

## 6. DOSYA İSİMLENDİRME (Çıktı)

```
reports/research/
├── DC_CHAIN_2026-04-19.html        # Veri merkezi tedarik zinciri
├── AUTO_EV_CHAIN_2026-05-15.html   # EV/otomotiv elektrifikasyon
├── DEFENSE_CHAIN_2026-06-01.html   # Savunma sanayisi
└── ROBOTICS_CHAIN_2026-07-10.html  # Robotik
```

Format: `{TEMA_KOD}_CHAIN_{YYYY-MM-DD}.html` veya `{TEMA_KOD}_RADAR_{YYYY-MM-DD}.html` (mevcut radar raporlarıyla tutarlı).

---

## 7. KALİTE KONTROL CHECKLIST

Rapor üretildikten sonra şunlar sağlanmalı:

- [ ] `{{` ile başlayan hiçbir kalan placeholder yok (`grep "{{" rapor.html` boş dönmeli)
- [ ] Her `STOCKS[i].l` değeri `LAYERS` içinde mevcut
- [ ] Her `PORTFOLIOS[*].t` değeri `STOCKS` içinde mevcut
- [ ] Toplam `STOCKS.length` = `{{HISSE_SAYISI}}` ile eşleşiyor
- [ ] `STOCKS.filter(s => s.cat === 'avoid').length` = `{{UYARI_SAYISI}}` ile eşleşiyor
- [ ] Her katman (LAYERS) içinde en az 2-3 hisse var
- [ ] Hero, key finding, conclusion'da sayısal iddia varsa kaynağı kontrol edilmiş (FMP veya araştırma)
- [ ] Türkçe yazım: ş, ğ, ü, ö, ç, ı, İ doğru; "şirket'in" değil "şirketin" (apostrofsuz) — özel isimde de
- [ ] Em dash (—) kullanımı serbest, ama AI tonuna kayma yok
- [ ] Browser'da açıldığında: harita yükleniyor, tooltip çalışıyor, filtreler çalışıyor, karşılaştırma çekmecesi açılıyor
