# SEKTÖR/TEMA ARAŞTIRMA AJANLARI v1.0
> **oluşturulma**: 11 nisan 2026
> **amaç**: Her tema için haberleri tarayan, hisse bulan, katalist tespit eden otonom ajan sistemi

---

## MIMARI

```
ORCHESTRATOR (Claude)
    │
    ├── TEMA_DETECTOR ─── Hangi tema öne çıkıyor?
    │
    ├── THEME_AGENT[tema_adı] ─── Her aktif tema için bir ajan
    │       ├── NEWS_SCANNER    → FMP news/stock + web_search → katalist haberleri
    │       ├── SUPPLY_CHAIN_MAPPER → Temadan yararlanan tüm katmanları listele  
    │       ├── STOCK_SCREENER  → FMP screener → teknik filtreler → shortlist
    │       └── CONVICTION_SCORER → Hisse başına güven skoru
    │
    └── PORTFOLIO_ALLOCATOR ─── Kimin hangi hisseye gireceğine karar ver
```

---

## AJAN TİPLERİ VE GÖREVLERİ

### 1. TEMA_DETECTOR
**Amaç:** Günlük olarak hangi tema öne çıkıyor, hangisi zayıflıyor?

**Kullandığı veri:**
- FMP `sector-performance-snapshot` (son 5 gün)
- ETF fiyat değişimleri: XLK, XLE, XLI, XLV, XLF, XLY, XLB, XLU
- Tema ETF'leri: BOTZ, ARKQ, CIBR, ITA, GDX, IBB
- VIX seviyesi (web_search)

**Çıktı:** `data/macro_intelligence.json` (macro_intelligence.py tarafından yazılır, her sabah)
```json
{
  "tarih": "2026-04-17T22:28:39+03:00",
  "vix": 17.8,
  "piyasa_modu": "risk-on",
  "aktif_kriz": {"tip": "yok", "guven": 0},
  "dominant_temalar": [
    {"tema_adi": "AI_altyapı", "güç_skoru": 9, "portföy": "aggressive", "aciliyet": "yüksek"},
    {"tema_adi": "savunma_uzay", "güç_skoru": 7, "portföy": "aggressive", "aciliyet": "orta"}
  ],
  "kaçınılacak_sektörler": ["Consumer Defensive", "Healthcare"],
  "genel_yorum": "...",
  "guncelleme": "2026-04-17T22:28:39"
}
```

---

### 2. NEWS_SCANNER
**Amaç:** Aktif tema için son 24-48 saatin kritik haberlerini topla ve önem sırala

**Kullandığı veri:**
- FMP `news/stock` → tema hisseleri için haberler
- FMP `fmp-articles` → genel piyasa
- `web_search` → "savunma harcamaları 2026" / "NATO bütçe" / tema-spesifik arama

**Çıktı:** Tema başına 5-10 haber, önem sıralı, 1-5 etki puanlı

**Karar ağacı:**
```
Haber geldi → Pozitif mi Negatif mi?
    │
    ├── POZİTİF:
    │     Doğrudan katalizör (sözleşme, onay, guidance): Etki=5
    │     Sektörel destek (bütçe artışı, politika): Etki=4
    │     Dolaylı (rakip zaafiyeti): Etki=2
    │
    └── NEGATİF:
          Temel bozulma (iptal, kayıp): Etki=-5 → tez sorgula
          Sektörel baskı (regülasyon, bütçe kesintisi): Etki=-3
          Geçici (tek olay): Etki=-1 → izle
```

---

### 3. SUPPLY_CHAIN_MAPPER
**Amaç:** Aktif temadaki tüm katmanları harita çıkar. Hangi şirket ne üretiyor/geliştiriyor?

**Örnek — SAVUNMA teması supply chain haritası:**
```
TIER 0 — Prim Contractors (doğrudan savunma geliri):
  LMT (F-35, THAAD), RTX (Patriot, Raytheon), NOC, GD, HII

TIER 1 — Platform/Sistem Tedarikçisi:
  KTOS (drone sistemleri), HEI (uçak parçaları), TDG
  AXON (taktiksel ekipman), CACI (yazılım/siber)

TIER 2 — Teknoloji/Alt Bileşen:
  PLTR (AI analitik, Gotham platform)
  LDOS, SAIC (devlet yazılımı)
  ANET (taktik ağ iletişimi)

TIER 3 — Hammadde/Destek:
  MP (nadir toprak, F-35 için gerekli)
  POWL (enerji altyapısı)
  ENSG (savunma tesisi)

SAVUNMA İÇİN DOLAYLU FAYDALANANLAR:
  Siber güvenlik: CRWD, PANW, FTNT (savaş = siber saldırı riski)
  Enerji: XOM, CVX (jeopolitik = petrol fiyatı)
```

**FMP API kullanımı:**
- `company-screener` → sektör + anahtar kelime filtresi
- `news/stock` → şirket başına son haberler
- `stock-peers` → benzer şirketler
- Web search → "[tema] supply chain companies 2026"

---

### 4. STOCK_SCREENER
**Amaç:** Supply chain haritasından teknik olarak uygun hisseleri bul

**Filtre sırası:**
```
1. Evren: Tema supply chain listesi (~30-60 hisse)
2. Temel filtre: mcap >$2B, günlük hacim >500K, fiyat >$10
3. K-19: XLP hisseleri çıkar (swing için)
4. Teknik filtre:
   a. Fiyat > SMA50 (K-04)
   b. RSI 40-70 (giriş bölgesi)
   c. Hacim son 5 gün ortalamasının 1.2x+ (momentum teyidi)
5. K-20: Sektör RS dead cat değil
6. VIX uyumu: K-13 v4.1 matrisine göre sektör izinli mi?
7. Ichimoku 4/4: Kumo üstü, TK bull, tenkan üstü, volume 1.3x
8. Skor hesapla → top 10 aday listesi
```

**Çıktı (tasarım aşaması, bu dosya henüz üretilmiyor):** `data/theme_stock_candidates.json`
*Not: Bu doküman bir tasarım spesifikasyonu. Pratikte bu rolü portfolio_scan_aggressive/balanced/dividend.py + swing_full_universe.py birleşimi görüyor. İleride ayrı bir STOCK_SCREENER ajanı kurulursa çıktı formatı bu şemaya benzer olacak.*
```json
{
  "tema": "SAVUNMA",
  "tarama_tarihi": "2026-04-11",
  "adaylar": [
    {
      "sembol": "KTOS",
      "katman": "tier_1",
      "skor": 82,
      "rsi": 58.3,
      "rs20": 4.2,
      "ichimoku": "4/4",
      "hedef_portfoy": ["agresif"],
      "not": "Drone savunma sözleşmesi yakın, ichimoku tam"
    }
  ]
}
```

---

### 5. CONVICTION_SCORER
**Amaç:** Her aday hisse için 0-100 güven puanı hesapla

**Bileşenler:**
```
Teknik güç           (0-25): RSI bölgesi + ichimoku + hacim + SMA pozisyonu
Tema uyumu           (0-25): Kaçıncı katman? Kataliz doğrudan mı?
Momentum             (0-20): RS20, price momentum 20g, earnings revizyon
Temel kalite         (0-15): Bilanço sağlığı, FCF pozitif mi, borç yükü
Risk faktörü         (0-15): K-15b skoru, earnings yakınlık, korelasyon riski
```

| Puan | Karar |
|------|-------|
| 80-100 | GÜÇLÜ — Agresif'te tam pozisyon, Dengeli'de pozisyon |
| 60-79 | İYİ — Agresif yarım-tam, Dengeli seçici |
| 40-59 | ZAYIF — Sadece Temettü filtresi geçiyorsa |
| <40 | GEÇ |

---

## ÇALIŞTIRMA ZAMANLARI

```
Her sabah (Part 1A öncesi, ~TR 13:30):
  → TEMA_DETECTOR çalışır
  → Aktif tema için NEWS_SCANNER çalışır
  → Değişim varsa SUPPLY_CHAIN_MAPPER + STOCK_SCREENER güncellenir

Haftalık (Pazar, weekly report içinde):
  → Tüm 7 tema için SUPPLY_CHAIN_MAPPER tam güncelleme
  → Yeni şirketler eklendi mi? (IPO, spin-off, acquisition)
  → Geçen hafta tema rotasyonu başarılı mıydı? (post-review)

Seans içi (isteğe bağlı, FAZ 2):
  → "Seans içi tema taraması" tetiklenirse STOCK_SCREENER tekrar çalışır
  → Tetikleyiciler: Büyük haber, %3+ tema ETF hareketi, VIX spike
```

---

## SEANS İÇİ TEMA TARAMASI

Seans sırasında aşağıdaki durumlar oluşursa Claude **anında** tema taraması yapar:

```
TETİKLEYİCİLER:
  1. Tema ETF'i gün içinde %2+ hareket etti
  2. Kritik haber geldi (savunma sözleşmesi, FDA onayı vb.)
  3. VIX aniden %10+ sıçradı (K-13 matrisi değişiyor)
  4. Portföyde stop tetiklendi → nakit oluştu → fırsat var mı?

PROSEDÜR (seans içi, 10 dakika):
  1. web_search → "[tema] news today" 
  2. FMP batch-quote → tema hisseleri anlık fiyat
  3. Shortlist'ten ichimoku kontrolü (top 5 aday)
  4. K-13 VIX uyumu → uygun mu?
  5. KARAR → giriş / bekle / geç
```

---

*finzora ai | sector agents v1.0 | 11 nisan 2026*
