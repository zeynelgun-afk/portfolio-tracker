# SEKTÖR DEEP DIVE RAPORU SKILL v1.0
> **oluşturulma**: 27 nisan 2026
> **amaç**: Bir sektör/tema için tedarik zincirini katman katman ayırıp; her katmandaki hisseleri değerleme + potansiyel matrisine yerleştiren, 3 portföy önerisine bağlayan editörel finansal araştırma raporu
> **çıktı formatı**: tek-dosya interaktif HTML
> **yer**: `reports/research/{TEMA_KOD}_CHAIN_{YYYY-MM-DD}.html`

---

## NE ZAMAN KULLANILIR

Bu skill **Zeynel'in açık talebi** veya aşağıdaki tetikleyicilerle çalışır:

### Açık tetikleyiciler (kelime/ifade)
- "X sektörü incelemesi yap"
- "X temasının tedarik zincirini çıkar"
- "X için derinlemesine rapor hazırla"
- "X araştırması" (kapsamlı talep)
- "X zinciri raporu"
- "Bu temada hangi katmanlar var?"
- "Bu hikâyeyi katman katman aç"

### Otomatik tetikleyiciler (haftalık raporda)
- Pazar haftalık değerlendirmesinde sektör rotasyon analizine ek olarak, **dominant_temalar.güç_skoru ≥ 8** olan tema için ay başında bir kez tam zincir raporu üretilebilir
- `data/macro_intelligence.json` içinde **aktif kriz** veya **yeni katalist** çıkmışsa o tema için zincir raporu

### NE ZAMAN KULLANILMAZ
- Tek hisse derin analizi → `reports/research/TICKER_RADAR_*.md` (mevcut format)
- Kısa günlük gözlem → SABAH/SWING/PORTFÖY raporları
- Tek tablo halinde tarama → CSV/JSON
- Bilanço sonrası ucuzlama taraması → `bilanco-sonrasi-ucuzlama-tarayicisi` skill

---

## RAPORUN YAPISI (8 BÖLÜM)

```
┌─────────────────────────────────────────────────────────┐
│ 1. TICKER STRIP (üst kayan band - 15-20 ana hisse)     │
├─────────────────────────────────────────────────────────┤
│ 2. NAV (logo + bölüm linkleri + tarih)                 │
├─────────────────────────────────────────────────────────┤
│ 3. HERO                                                 │
│   • Etiket + büyük başlık + özet paragraf              │
│   • 4 metrik kutu (katman/hisse/öneri/uyarı)           │
│   • ANA BULGU kutusu (key finding - altın çerçeveli)   │
├─────────────────────────────────────────────────────────┤
│ 4. SECTION 01 — DEĞERLEME HARİTASI                     │
│   • SVG scatter (val 1-10 X, pot 1-10 Y, 4 kadran)     │
│   • Tüm hisseler kategori rengiyle                     │
│   • Hover tooltip                                       │
│   • Terim sözlüğü (jargon → Türkçe)                    │
├─────────────────────────────────────────────────────────┤
│ 5. INSIDER WARNING (opsiyonel)                          │
│   • Yönetici satışları varsa toplu uyarı                │
├─────────────────────────────────────────────────────────┤
│ 6. SECTION 02 — KATMAN HARİTASI                         │
│   • 12 (veya N) katman özet kartı                       │
│   • Her kart: katman no, isim, en cazip pick, F/K      │
├─────────────────────────────────────────────────────────┤
│ 7. SECTION 03 — HİSSE KARTLARI                          │
│   • Filtre bar (kategori + arama)                      │
│   • Her katman için bölüm + hisse kart grid             │
│   • Karta tıkla → karşılaştırmaya ekle (max 3)          │
├─────────────────────────────────────────────────────────┤
│ 8. SECTION 04 — PORTFÖY ÖNERİLERİ                       │
│   • 3 sekme: Dengeli ($100K) / Agresif ($400K) / Temettü ($100K)│
│   • Her portföyde 5-9 numaralı pozisyon liste           │
├─────────────────────────────────────────────────────────┤
│ 9. SECTION 05 — KAÇINILACAKLAR                          │
│   • Avoid kategorisindeki tüm hisseler grid              │
├─────────────────────────────────────────────────────────┤
│ 10. SECTION 06 — SONUÇ                                  │
│    • 3-4 paragraf kapanış                                │
│    • Meta: Araştırma · Tarih · Güven düzeyi              │
└─────────────────────────────────────────────────────────┘
```

---

## ÜRETİM AKIŞI (8 ADIM)

### Adım 1: Tema kapsamı belirle
Zeynel'in talebini netleştir. Eğer belirsizse netleştirici sor:
- Tema sınırı ne? (örn: "savunma" → uçak/deniz/uzay/siber dahil mi?)
- Hangi piyasalar? (varsayılan: ABD borsa)
- Zeynel'in portföyünden tutulacak isim var mı? (`hold` kategorisine alınır)

### Adım 2: Tedarik zincirini katmanlara ayır
Tema için **8-12 katman** çıkar. Her katman:
- Fiziksel/teknik bir halka (bileşen, malzeme, hizmet, müşteri)
- Borsada en az 2-3 yatırım yapılabilir hisse içermeli
- Tek katmanda hep aynı sektör değil — alt segmentlere bölünebilir

**Veri merkezi örnek katmanları:** Elektrik & Şebeke / Nükleer / Soğutma / Optik / Ağ / Depolama / GYO+İnşaat / Kimyasal+Nadir Toprak / Üretim Cihazı / Sunucu+Montaj / Konnektör / Enerji Depolama

### Adım 3: Hisse evreni topla
Her katman için:
- FMP `screener` ile aday hisseler (mcap > $1B, hacim > 200K, ABD listed)
- Her katmanda 3-7 hisse hedefle (toplam 40-60 ideal)
- Sembolleri `STOCKS` dizisi formatına çevir
- Eksik veri için FMP `quote`, `ratios-ttm`, `key-metrics-ttm`, `analyst-estimates` çağır
- ⚠️ FMP field traps: `changePercentage` (singular), `priceToEarningsRatioTTM`, `dividendYieldTTM` — `docs/FMP_SKILL.md` referans

### Adım 4: Değerleme + Potansiyel skoru
Her hisseye `val` (1-10) ve `pot` (1-10) ata. Mantık:

**val (değerleme, 1=ucuz, 10=pahalı):**
- 1-3: İleri F/K < sektör medyanı, PEG < 1, EV/EBITDA < 12
- 4-5: Sektör medyanına yakın
- 6-7: Hafif prim
- 8-10: 2 katı veya üzeri prim, "kusursuz fiyatlı"

**pot (potansiyel, 1=düşük, 10=yüksek):**
- Tema saflığı (gelirin % kaçı doğrudan tema)
- Katalist görünürlüğü (sipariş defteri, sözleşme, ürün lansmanı)
- Yapısal moat (tek üretici, tekel, altyapı)
- Yönetim kalitesi
- Düşürücü: yönetişim/insider/dava/likidite riskleri

**Kategori atama kuralları (`cat`):**
| Koşul | Kategori |
|---|---|
| `val ≤ 4 && pot ≥ 7` | `cheap` |
| `val ≤ 6 && pot ≥ 6 && val > 4` | `hidden` |
| `val 5-7 && pot 4-6` | `quality` |
| Zeynel portföyünde mevcut | `hold` (override) |
| `val ≥ 7 && pot ≤ 5` | `avoid` |
| Yönetişim/insider/hukuki risk yoğun | `avoid` (override) |
| Gelir üretmeyen spekülatif | `avoid` |

### Adım 5: Tez ve risk yaz
Her hisse için 1-2 cümlelik `why` (pozitif tez) ve `risk`:
- `<strong>` ile en kritik sayıyı vurgula
- Kuru veri değil, **karar argümanı** olmalı
- Türkçe finans dili, AI tonuna kaçma
- Örnek why: `"Gelir +%200, <strong>2026 mali yılı üçe katlanıyor</strong>, aktif elektrik kabloda lider. PEG<1 olan tek büyük-büyüme bağlantı ismi."`
- Örnek risk: `"<strong>1 yılda %1100. İleri F/K 85+. Analist hedefleri spotun çok altında.</strong>"`

### Adım 6: 3 portföye dağıt
Skill mimarisinde 3 portföy var:

| Portföy | Anapara | Pozisyon | Filtre |
|---|---|---|---|
| **Dengeli** | $100K | 6-7 | Kalite + temettü + uzun vadeli görünürlük; her hisse max %20 |
| **Agresif** | $400K | 7-9 | En yüksek kazanç büyümesi + en yüksek tema kaldıracı; max %15 |
| **Temettü** | $100K | 5-6 | Min %3 temettü + güçlü FCF + AI/tema bonus; max %15 |

**Çakışma izinli:** Aynı hisse 2 portföyde olabilir (örn. CMI hem Dengeli hem Temettü).
**Mevcut portföy korunur:** Eğer Zeynel'in mevcut bir pozisyonu (`hold` kategorisi) varsa **satılması önerilmez** — sadece "koru, şu seviye üstü ekleme yapma" gibi öneri ile sonuç paragrafına işle.

### Adım 7: Anlatı bölümlerini yaz
- **Hero özeti:** 1-2 cümle. Tema neden önemli, neden şimdi rapor?
- **Ana Bulgu:** 1 başlık + 1 paragraf gövde. En çarpıcı çıkarım. Hangi 3 katman fiyatlanmamış, hangi isimler aşırı pahalı.
- **Insider uyarısı (opsiyonel):** Tema için anlamlıysa 4-8 sinyal listele.
- **Sonuç:** 3-4 paragraf. Hangi katman geride, hangi öne çıkmış. Üç portföyde en yüksek asimetri nerede. Zeynel'in mevcut pozisyonu varsa açık tavsiye.

### Adım 8: Template'i doldur ve commit
1. `templates/sektor_deep_dive/template.html`'i kopyala
2. Hedef: `reports/research/{TEMA_KOD}_CHAIN_{YYYY-MM-DD}.html`
3. `SCHEMA.md` listesindeki tüm `{{...}}` placeholder'ları doldur
4. Browser'da test et (mümkünse) — harita yükleniyor mu, tooltip çıkıyor mu
5. KQ checklist'i kontrol et (SCHEMA.md son bölümü)
6. Git commit + push:
   ```bash
   git add reports/research/{TEMA_KOD}_CHAIN_{YYYY-MM-DD}.html
   git commit -m "research: {tema} tedarik zinciri raporu {YYYY-MM-DD}"
   git push
   ```
7. Telegram bildirim:
   - **GROUP** (`-1003827034395`): Sadece kısa duyuru + GitHub link.
   - Format: `📊 finzora ai · {tema} zinciri raporu yayınlandı\nKatman: N · Hisse: M · Öneri: K\n{github_url}`

---

## ÖNEMLİ KURALLAR

### Veri kalite eşikleri
- **Her sayısal iddia FMP'den veya doğrulanabilir kaynaktan gelmeli** — uydurma sayı yasak
- **Belirsizlik etiketi:** İddia kesin değilse "yaklaşık" / "tahmini" / "muhtemel" — `KESİN/MUHTEMEL/SPEKÜLATİF` ayrımı yap
- **Eski veri yasak:** Quote'lar rapor tarihine ait olmalı (FMP `quote` çağrısı her seferinde)

### Yazım kuralları
- **Türkçe**, ciddi finans dili, cümle başında büyük harf
- **Em dash kullanılabilir** (`—`) — AI tonuna kaçma riski yok burada, çünkü editörel rapor
- **Apostrof** özel isimde **kullanılmaz**: "Cisco'nun" değil "Cisconun" / "Cisco-nun" değil "Cisconun" — *ama* mali ayraçlarda zorunluysa kullanabilirsin (bk. örnek raporda "Apple's" gibi). **Türkçe ek için apostrof yok.**
- **Kaynak ataması:** "finzora ai" lowercase, fakat brand kullanımında "Finzora AI" büyük olabilir

### Yapı kuralları
- **Min katman:** 8 / **Max katman:** 12
- **Min hisse/katman:** 2 / **İdeal:** 3-7
- **Min toplam hisse:** 30 / **İdeal:** 40-60 / **Max:** 80
- **Avoid kategorisi:** toplam hissenin %15-30'u olmalı (her sektörde her şey ucuz değil)
- **Cheap kategorisi:** %15-25 (asimetri için 5-10 isim)

### Görsel kurallar
- **Renk paleti SABİT:** `cheap=yeşil`, `hidden=cyan`, `quality=altın`, `hold=violet`, `avoid=kırmızı`
- **Font sabit:** Fraunces (display), DM Sans (body), JetBrains Mono (mono)
- **Arkaplan:** koyu (#0a0e14)
- **Mobil responsive:** 700px altında tüm grid'ler tek sütun

---

## ÖRNEK RAPORLAR

| Tema | Dosya | Tarih | Katman | Hisse |
|---|---|---|---|---|
| Veri Merkezi Tedarik Zinciri | `templates/sektor_deep_dive/ornek_veri_merkezi_zinciri_2026-04-19.html` | 19 Nis 2026 | 12 | 54 |

---

## DOSYA HARİTASI

```
templates/sektor_deep_dive/
├── template.html                              # Boş şablon (placeholder'lı)
├── SCHEMA.md                                  # Veri yapısı detayı
└── ornek_veri_merkezi_zinciri_2026-04-19.html # Tam örnek (referans)

docs/
└── SEKTOR_DEEP_DIVE_SKILL.md                  # Bu dosya (skill ana dokümantasyonu)

reports/research/                              # Üretilen raporlar buraya
├── DC_CHAIN_2026-04-19.html
├── DEFENSE_CHAIN_2026-XX-XX.html
└── ...
```

---

## OLASI TEMALAR (gelecek raporlar)

Aşağıdaki temalar bu skill'e uygundur:

1. **Yapay zeka tedarik zinciri** (chip → bellek → ağ → optik → soğutma) — yapıldı (DC zinciri)
2. **Otomotiv elektrifikasyon** (lityum → katot → batarya → BMS → motor → şarj altyapısı)
3. **Savunma sanayisi** (mühimmat → drone → uydu → siber → MRO)
4. **Yeşil enerji geçişi** (güneş paneli → invertör → şebeke depolama → hidrojen → emisyon ticareti)
5. **Biotech pipeline** (GLP-1 → CGM → onkoloji → gen tedavisi → CDMO)
6. **Robotik** (sensör → aktüatör → kontrol → simülasyon → entegratör)
7. **Quantum computing** (donanım → kontrol elektroniği → kriyojeni → yazılım → uygulama)
8. **Nadir toprak/kritik mineral** (madencilik → işleme → ayrıştırma → mıknatıs → geri dönüşüm)
9. **Yarıiletken üretim** (litografi → ölçüm → maske → fotorezist → paketleme)
10. **Uzay ekonomisi** (fırlatma → uydu üretimi → yer istasyonu → veri analitiği → savunma)

---

## VERSİYON GEÇMİŞİ

- **v1.0 (27 nis 2026):** İlk yayın. Veri merkezi zinciri raporu (19 nis 2026) referans alınarak template ve şema oluşturuldu.
