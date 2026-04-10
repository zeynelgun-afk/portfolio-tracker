# SEANS PROMPT REFERANS DOKÜMANI

> bu dosya seans prompt'larının "referans" ve "versiyon" içeriğini barındırır.
> talimat değil bilgi amaçlı. prompt'lardan link ile erişilir.
> amaç: executable prompt'ların kısa ve odaklı kalmasını sağlamak.

---

## 1. seans öncesi vs seans içi fark

| | sabah raporu (TR ~14:00) | seans içi (FAZ 1/2/3) |
|---|---|---|
| **ne zaman** | NYSE açılmadan ~2.5 saat önce | NYSE açıldıktan sonra |
| **fiyat** | dünün kapanış fiyatı (final) | bugünün canlı fiyatı |
| **amaç** | değerlendirme + JSON güncelleme + plan | karar + uygulama |
| **çıktı** | rapor dosyası (.md) + JSON | trade emirleri + JSON + git |
| **ton** | "dün şu oldu, bugün şunu yapacağız" | "şu anda şunu yapıyoruz" |
| **rapor** | YAZILIR (`DAILY_SABAH_{TODAY}.md`) | **YAZILMAZ** |

### repoya giden rapor dosyaları (sadece 4 tür)

1. `DAILY_SABAH_YYYY-MM-DD.md` → piyasa açılmadan önce
2. `DAILY_REPORT_YYYY-MM-DD.md` → piyasa kapanışı sonrası
3. `WEEKLY_YYYY-MM-DD.md` → pazar günü
4. `MONTHLY_YYYY-MM.md` → ay sonu

seans içi analizler, kararlar, gözlemler **sadece chat'te kalır**. JSON/CSV değişiklikleri repoya gider, rapor dosyası asla.

---

## 2. seans fazları — ne zaman ne yapılır

```
FAZ 1: AÇILIŞ (TR 16:30-17:30) — ilk 60 dk
  → öncelik: ACİL KONTROL
  → prompt: docs/prompts/SESSION_PART1_ACILIS.md

FAZ 2: ORTA SEANS (TR 18:00-21:00) — ana seans
  → öncelik: ANALİZ + KARAR
  → prompt: docs/prompts/SESSION_PART2_ORTA.md

FAZ 3: POWER HOUR (TR 22:00-23:00) — son saat
  → öncelik: FİNAL AKSİYONLAR
  → prompt: docs/prompts/SESSION_PART3_POWER.md
```

---

## 3. tekrar çalıştırma — API optimizasyonu

aynı fazda 2. veya 3. kez çalıştırıldığında tam veri toplama gereksiz. **state handoff** ile önceki veriyi kullan.

```
İLK ÇALIŞTIRMA (FAZ 1):
  → tam veri toplama: ~25-30 FMP + 1-2 websearch + ~20 RapidAPI (twitter)
  
FAZ 2 (FAZ 1'den state okur):
  → batch-quote (1 call) + teknik göstergeler (45-60) + sektör (1) + PM (2-4 websearch)
  
FAZ 3 (FAZ 2'den state okur):
  → sadece batch-quote (1) + earnings calendar (1) + twitter delta (10-20)
  
TEKRAR ÇALIŞTIRMA (aynı faz):
  → sadece batch-quote (1 call — tüm fiyatlar)
  → tetiklenen pozisyon için RSI (1-5 call)
  → websearch sadece yeni haber varsa (0-5)
  → toplam: ~3-10 FMP
```

günlük toplam FMP bütçesi (tüm fazlar): ~130-150 call. dakikalık limit 2,500 — güvenli marj çok yüksek.

---

## 4. state handoff şeması — data/session_state.json

```json
{
  "tarih": "YYYY-MM-DD",
  "son_guncelleme": "ISO-8601",
  
  "faz1": {
    "zaman": "HH:MM",
    "spy": {"fiyat": 0, "degisim_pct": 0},
    "qqq": {"fiyat": 0, "degisim_pct": 0},
    "dia": {"fiyat": 0, "degisim_pct": 0},
    "iwm": {"fiyat": 0, "degisim_pct": 0},
    "vixy": {"fiyat": 0, "degisim_pct": 0},  // ETF — sadece yön
    "vix_level": 0.0,  // gerçek VIX (Yahoo ^VIX, get_vix_level())
    "uso": {"fiyat": 0, "degisim_pct": 0},
    "gld": {"fiyat": 0, "degisim_pct": 0},
    "usdtry": {"fiyat": 0},
    "risk_ortami": "RISK-ON | RISK-OFF | MIXED",
    "gap_raporu": [
      {"sembol": "", "gap_pct": 0, "sinif": "gap-up | gap-down | normal"}
    ],
    "acil_aksiyonlar": [
      {"tip": "K-06 stop", "sembol": "", "aciklama": ""}
    ],
    "bmo_earnings": [
      {"sembol": "", "sonuc": "beat | miss | in-line", "etki": ""}
    ],
    "twitter_ozet": [
      {"hesap": "", "son_tweet_id": "", "portfoy_iliskili": [], "not": ""}
    ],
    "k06_tetikler": [],
    "k09_tetikler": [],
    "sabah_plani_uygulandi": true,
    "faz2_icin_notlar": []
  },
  
  "faz2": {
    "zaman": "HH:MM",
    "spy_delta": 0,
    "risk_ortami_delta": "",
    "teknik_durum": {
      "SYMBOL": {"rsi": 0, "sma50_altı_ustu": "", "sma200_altı_ustu": "", "durum": ""}
    },
    "sektor_rs": {
      "enerji": 0,
      "teknoloji": 0
    },
    "pm_delta": {
      "fed_rate_cut": {"sabah": 0, "guncel": 0, "delta": 0},
      "iran_escalation": {"sabah": 0, "guncel": 0, "delta": 0}
    },
    "kararlar": {
      "alis": [{"sembol": "", "fiyat": 0, "adet": 0, "neden": "", "k_rules": []}],
      "satis": [{"sembol": "", "fiyat": 0, "adet": 0, "neden": "", "k_rules": []}],
      "tut": [],
      "izle": []
    },
    "yeni_adaylar": [
      {"sembol": "", "tema": "", "ichimoku": "4/4", "stop": 0, "hedef": 0, "karar": "giriş | bekle | geç"}
    ],
    "go_no_go_sonuclari": {
      "SYMBOL": {"gecenler": 14, "toplam": 16, "failed": ["K-17", "K-18"]}
    },
    "faz3_icin_notlar": []
  },
  
  "faz3": {
    "zaman": "HH:MM",
    "spy_kapanisa_yakin": 0,
    "aksiyonlar": {
      "kar_alma": [],
      "trailing_guncelleme": [],
      "final_satis": []
    },
    "amc_earnings": [],
    "twitter_delta": [],
    "after_hours_izleme": [],
    "yarin_flag_listesi": [
      {"tip": "amc_earnings", "sembol": "", "not": ""},
      {"tip": "gap_riski", "sembol": "", "neden": ""},
      {"tip": "stop_yakin_gece", "sembol": "", "mesafe_pct": 0}
    ]
  },
  
  "seans_ozet": {
    "tarih": "YYYY-MM-DD",
    "toplam_trade_sayisi": 0,
    "net_kar_zarar": 0,
    "aktif_pozisyon_sayisi": 0,
    "nakit_oran": 0
  }
}
```

### state handoff kuralları

1. **`session_state.json` GIT'e commit EDİLMEZ**. `.gitignore`'a eklenmeli. local çalışma dosyası.
2. her faz kendi bloğunu yazar, önceki bloklara dokunmaz.
3. yeni gün başında dosya sıfırlanır (yarın FAZ1 SABAH ilk blok yazarken).
4. `yarin_flag_listesi[]` bir sonraki gün FAZ1 SABAH promptu tarafından okunur.

---

## 5. seans içinde yapma listesi (SEN KARAR VER kuralı)

**otomatik yapılan işlemler** (hepsi onay beklemez):
- yeni pozisyon açma/kapatma (playbook kurallarına uygunsa)
- kısmi kâr alma (K-11 tetiklenirse)
- stop-loss satışı (K-06, override yasak)
- trailing stop güncelleme (K-07, sadece yukarı)
- K-09 erken çıkış (3+ negatif kontrol)
- fiyat güncellemesi
- watchlist güncellemesi
- portföy rebalance kararları
- tutulan_gun artırma, ağırlık yüzdesi hesaplama

**yapma!**
- stop-loss'u aşağı çekme (ASLA)
- duygusal karar (panik satış, FOMO alış)
- sabah planında olmayan büyük pozisyon açma (önce analiz ve K-rule çapraz kontrol)
- aynı alt sektörde 3'ten fazla swing pozisyonu (K-17 ihlali)
- portföy ruhuyla uyuşmayan hisse ekleme (temettü portföyüne growth stock gibi)
- nakit oranını %5 altına düşürme (acil fırsat hariç)
- seans içinde rapor dosyası (.md) yazıp repoya push (KURAL İHLALİ)

---

## 6. self-validation katmanları

### katman 1: FMP çağrısı sonrası
```
✓ yanıt boş değil mi?
✓ fiyatlar mantıklı mı? (> 0, < 100K, |değişim| < %50)
✓ |changesPercentage| > %20 → haber teyidi yap
```

### katman 2: JSON güncelleme sonrası
```
✓ sayısal tutarlılık (yatirim, guncel_deger, kar_zarar, nakit)
✓ trailing stop sadece yukarı gitmiş
✓ ağırlık toplamı ≈ %100
```

### katman 3: karar önerisi sonrası
```
✓ "SAT" için somut neden var mı? (stop, tez, veri)
✓ "AL" için RSI/SMA/momentum destekliyor mu?
✓ portföy kurallarıyla uyumlu mu?
✓ nakit yeterli mi?
✓ GO/NO-GO 16 madde geçti mi?
✓ düşünce zinciri yazıldı mı? (VERİ + KURAL + KARŞIT)
✓ bilişsel önyargı kontrolü yapıldı mı?
✓ yakınlık yanılgısı (recency bias)?
✓ FOMO mantığıyla mı öneriyor?
```

detay: `docs/DECISION_FRAMEWORK.md`

---

## 7. versiyon geçmişi

### v1.0 (9 nisan 2026) — üçe bölme
- SESSION_ACTION_PROMPT.md v2.3 (1093 satır, 5 aşama × 3 faz tek dosya) silindi
- 3 ayrı prompt oluşturuldu: FAZ 1 AÇILIŞ, FAZ 2 ORTA, FAZ 3 POWER
- K-kurallar `K_RULES_QUICK_REF.md` tek kaynağa taşındı (prompt içinde tekrar kaldırıldı)
- referans/versiyon içeriği bu dosyaya (`SESSION_REFERENCE.md`) taşındı
- state handoff sistemi `data/session_state.json` şemasıyla netleştirildi
- her faz kendi FMP bütçesine sahip (FAZ1 ~30 / FAZ2 ~60 / FAZ3 ~15)

### v2.3 geçmişi (referans — eski birleşik prompt)
- 8 nisan 2026: agresif max 6→10 poz, temettü max 6→15 poz, K-13b giriş stop netleşti, K-14→K-07 trailing etiket, stop formül tek kaynak K-06, K-15a mevcut poz bağlam düzeltildi
- 7 nisan 2026: K-01/K-03/K-08 kaldırıldı, K-script notify sistemi ters çevrildi
- 6 nisan 2026: K-13 v4.1 dinamik sektör bazlı VIX

---

## 8. eskiden v2.1'den kaldırılan swing kuralları

v2.1 → v2.3 geçişinde kaldırılan/değişen kurallar:
- **"kijun altı kapanış" otomatik çıkış**: KALDIRILDI (chandelier aldı)
- **"TK cross aşağı" otomatik çıkış**: KALDIRILDI (sadece rapor sinyali)
- **stop hesaplama**: kijun → chandelier (K-07 kâr kilidi)

---

## 9. telegram bildirim kuralları

**gönderilir** (git push'tan SONRA):
- `--type action`: alış/satış/stop/kar alma
- `--type report --file ...SEANS_ONCESI.md`: sabah raporu
- `--type report --file ...KAPANIS.md`: kapanış raporu
- `--type alert`: stop yakınlık warning/critical (K-09)
- `--type session --theme "..."`: faz sonu özet (opsiyonel)
- `--type photo --image ... --caption ...`: risk paneli görseli

**gönderilmez**:
- sistem/kural güncellemeleri
- K-script info severity alert'leri (`_QUIET_MODE=True` varsayılan)
- haftalık/aylık raporlar (aksi belirtilmedikçe)
- seans içi analiz notları

---

## 10. referans dosyaları

| dosya | amaç |
|---|---|
| `docs/K_RULES_QUICK_REF.md` | 17 K-kural tek sayfa özet |
| `docs/TRADING_PLAYBOOK.md` | K-kural tam detay + gerekçe + geçmiş |
| `docs/SWING_SYSTEM_V2.md` | swing v2.3 sistem detayı |
| `docs/DECISION_FRAMEWORK.md` | GO/NO-GO, düşünce zinciri, önyargı listesi |
| `docs/MARKET_INTELLIGENCE.md` | 1/2/3 derece etki zinciri |
| `docs/PREDICTION_MARKETS_GUIDE.md` | Kalshi/Polymarket sinyalleri |
| `docs/PORTFOLIO_DATA_SKILL.md` | JSON şema + güncelleme akışı |
| `docs/POST_TRADE_REVIEW.md` | closed.json zorunlu alanlar (process_score vb.) |
| `docs/DIVIDEND_SYSTEM.md` | temettü 5 katmanlı puanlama |
| `docs/AGGRESSIVE_V2_THESIS.md` | AI tedarik zinciri tezi |

---

> son güncelleme: 9 nisan 2026 v1.0 | finzora ai
