# Adil Değer Skill v5.0 — Etap 5 Notu

**Tarih**: 11 Mayıs 2026
**Durum**: Etap 5 tamamlandı

## Yapılan Değişiklikler

### A. Markdown Rapor Üretici (`--md` flag)

`format_markdown_report(result, output_path)` yeni fonksiyonu eklendi. **12 bölümlü protokol uyumlu** rapor üretir:

1. **Yönetici Özeti** — Beklenen adil değer, potansiyel %, confidence, snapshot tablosu (15 metrik)
2. **9 Yöntem Bazlı Değerlendirme** — KULLANILABİLİR / KULLANILAMAZ tablosu
3. **Ağırlıklı Adil Değer Tablosu** — GROWTH veya BLENDED moduna göre
4. **Senaryo Matrisi** — Bear / Base / Bull + Beklenen Değer (ağırlıklı)
5. **Bear Case** — En az 5 madde (v5 sinyalleri + generic + belirsizlik etiketleri)
6. **Bull Case** — En az 5 madde (Altman Z güvenli + Piotroski güçlü + ROE + AI mega-cap + quality premium + normalizasyon)
7. **"Neden Yanlış Olabilirim"** — En az 5 madde (multiple seçimi sübjektif + DCF varsayım farkı + forward agresif + TTM temsiliyet + analyst coverage + capex + sektör spread + recency bias)
8. **v5.0 Yeni Sinyaller** — 6 alt bölüm:
   - 8.1 Risk Skorları (Altman Z + Piotroski)
   - 8.2 Analist Sentiment (sayılar + momentum)
   - 8.3 DCF Sanity Check (FMP DCF vs bizim DCF + fark %)
   - 8.4 Konsantrasyon Riski (Ürün + Coğrafya)
   - 8.5 Canlı Sektör P/E (statik vs canlı + sapma)
   - 8.6 Dinamik CAPM WACC
9. **Portföy Karar Matrisi** — 3 portföy (Dengeli, Agresif Büyüme, Değer+Temettü) otomatik kurallar
10. **Giriş Planı** — Fiyat, adil değer, giriş zonu, stop, hedefler, R/R, pozisyon, bekleme koşulları
11. **İzleme Tetikleyicileri** — En az 5-7 madde (kazanç, sektör PE, rating, konsantrasyon, bear medyan, bull medyan, VIX, normalizasyon)
12. **5 Yıllık Finansal Projeksiyon** [v5.0 YENİ] — P&L tablosu + Forward çarpanlar + normalizasyon yorumu

**Sonu**: Otomatik Karar + v5.0 Risk Uyarıları (Piotroski zayıf, downgrade momentum, kritik konsantrasyon, FMP DCF negatif) — kararı **override etmez** ama pozisyon büyüklüğü için uyarı verir.

CLI:
```bash
# Markdown rapor üret + chat'te göster + dosyaya yaz
python3 adil_deger.py NVDA --md

# Custom path
python3 adil_deger.py NVDA --md --md-out /custom/path/nvda.md

# Pre-IPO için
python3 adil_deger.py --pre-ipo input.json --md
```

Default output: `reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md`

### B. Y3-Y5 Revenue Decay Cap (AMD Aşırı Agresif Sorunu)

`projection_engine.project_revenue_5y()` içinde Y3-Y5 büyüme oranlarına **mutlak cap** eklendi:

```python
# Eski (cap'siz)
g_y3 = max(0.10, y1_y2_growth * 0.70)
g_y4 = max(0.08, y1_y2_growth * 0.50)
g_y5 = max(0.05, y1_y2_growth * 0.35)

# Yeni (cap'li)
g_y3 = min(max(0.10, y1_y2_growth * 0.55), 0.30)  # max %30
g_y4 = min(max(0.08, y1_y2_growth * 0.35), 0.22)  # max %22
g_y5 = min(max(0.05, y1_y2_growth * 0.20), 0.15)  # max %15
```

**AMD Karşılaştırma:**

| Yıl | Eski (Etap 4) | Yeni (Etap 5) |
|---|---|---|
| 2027 | $97.55B (%94) | $97.55B (%94) — analist 2y, değişmedi |
| 2028 | $161.66B (%66) | **$126.82B (%30 cap)** ✅ |
| 2029 | $237.54B (%47) | **$154.72B (%22 cap)** ✅ |
| 2030 | $315.60B (%33) | **$177.92B (%15 cap)** ✅ |

NVDA için: Y1-Y2 büyüme %36 olduğundan cap'e takılmadı, Y3+ değerleri makul kaldı.

### C. v5.0 Risk Uyarıları (Markdown Sonunda)

Otomatik Karar fiyata göre verilir (mevcut mantık). **YANINA**, 5 risk sinyaliyle uyarı listesi gelir:

```markdown
## Otomatik Karar
**🟢 GÜÇLÜ AL**
_Mevcut fiyat ayı medyanının altında. Güvenli marj yüksek._

### v5.0 Risk Uyarıları
- ⚠️ Piotroski 3/9 — fundamental kalite ZAYIF
- ⚠️ DOWNGRADE TRENDI -6 — analist sentiment'i kötüleşiyor
- ⚠️ Ürün konsantrasyonu KRİTİK: Server And Storage Systems %97
- ⚠️ FMP DCF NEGATİF ($-188) — modeli sorgula

_Otomatik karar yalnızca fiyat vs adil değer karşılaştırmasına dayanır. Yukarıdaki sinyaller pozisyon büyüklüğü ve giriş zamanlamasına etki etmeli._
```

Uyarı tetikleyicileri:
- Piotroski ≤ 4
- Altman Z = İFLAS RİSKİ
- Analist momentum = downgrade
- Ürün konsantrasyonu ≥ %80
- FMP DCF NEGATİF

### D. Quality Premium Yuvarlama

Markdown raporda `quality_mult` değeri 14 ondalık yerine 2 ondalık.

## Geniş Test Sonuçları (5 Ticker)

| Ticker | Mod | Karar | Risk Uyarıları | Notlar |
|---|---|---|---|---|
| **NVDA** | GROWTH 4/5 | 🟢 AL ($259) | DOWNGRADE momentum, %90 Data Center | DCF $140 (FMP $247, -43%) |
| **KO** | BLENDED 80/20 | 🟡 İZLE | — (Piotroski 8/9 güçlü) | WACC %8, defansif |
| **AMD** | GROWTH 4/5 | 🟢 AL | — | DCF +%34 FMP'den yüksek, 2030 EPS $30 (eski $41) |
| **AVGO** | GROWTH 4/5 | 🔴 GEÇ ($430 vs $254 bull) | Asia Pacific %56 | Çok pahalı |
| **TEM** | BLENDED 1/5 | 🟠 PAHALI | Piotroski 3/9, Diagnostics %100, FMP DCF -$125 | Beta 4.0 (sınırda), spekülatif |
| **SMCI** | BLENDED 2/5 | 🟢 GÜÇLÜ AL ($35 vs $74) | Piotroski 3/9, DOWNGRADE, %97 konsantrasyon, FMP DCF -$188 | Karar agresif ama 4 risk uyarısı |
| **CBRS** | Pre-IPO | 5y projeksiyon | Pre-IPO uyarısı | Manuel JSON, IPO $155, 2028 P/E 52.6x |

## CV Dağılımı

- CV < %20 (yöntemler hizalı): NVDA Forward (0%), KO (BLENDED uyumlu)
- CV %20-35 (normal): KO Traditional
- CV %35-50 (tutarsızlık): NVDA Traditional (43%), AMD (40-44%)
- CV ≥ %50 (kritik): SMCI (77-86%) — yöntemler arası uçurum, raporda RİSK olarak işaretli

SMCI'da CV %86 olması mantıklı — Piotroski zayıf + downgrade + negatif FMP DCF arasında yöntemler birbiriyle uyuşmuyor. Skill bu durumu doğru tespit ediyor.

## Skill Kapsamı Özeti (v5.0 Final)

```
skills/adil-deger-9-yontem/
├── SKILL.md (v5.0)                          7 KB
├── scripts/
│   ├── adil_deger.py                       70 KB (~2200 satır)
│   ├── fmp_layer.py                        12 KB
│   ├── projection_engine.py                19 KB
│   └── test_data/cbrs_pre_ipo.json         1 KB
├── tests/
│   ├── test_cbrs_pre_ipo.py
│   └── test_nvda_live.py
├── notes/
│   ├── learnings.md                        15 KB
│   ├── v5_etap1_development.md
│   ├── v5_etap2_development.md
│   ├── v5_etap3_development.md
│   └── v5_etap5_development.md (bu dosya)
└── references/
    ├── 9-yontem-formuller.md (v5.0 notu)
    ├── sektor-medyanlari.md (v5.0 notu)
    ├── sektor-margin-profilleri.md (yeni)
    ├── fmp-endpoint-rehberi.md (yeni)
    ├── piyasa-rejimleri.md
    └── ornekler.md
```

**Toplam**: ~2200 satır ana kod + ~700 satır modül kod + 8 doküman dosyası.

## Sonraki Adımlar (Etap 6 — Gelecek)

1. **GitHub otomatik kayıt**: skill çalıştığında otomatik `reports/research/X_ADIL_DEGER_YYYY-MM-DD.md` + `data/research/index.json` güncelleme + commit + push
2. **Y3-Y5 decay tuning**: AVGO, SMCI gibi durumlar için profil bazlı decay (mature için daha sert)
3. **Pre-IPO canlı IPO calendar enrichment**: FMP `ipos-calendar` ile JSON'daki bilgileri otomatik doğrula
4. **HTML rapor üretici**: `--html` flag, frontend-design skill bridge
5. **Telegram bot entegrasyonu**: `/deger TICKER` komutu otomatik rapor + Telegram push
6. **Multi-year analyst estimates entegrasyonu**: 1y, 2y, 3y forward EPS/Revenue (şu an sadece 2y kullanılıyor)
7. **Profile delta-based projection**: SECTOR_MARGIN_PROFILES'i TTM gerçek üzerine delta olarak yorumla (her şirket için kalibre)
8. **Sektör multiple history tracking**: SECTOR_MULTIPLES tablosunu canlı veriden 3 aylık snapshot'larla otomatik güncelleme

Kaynak: finzora ai
