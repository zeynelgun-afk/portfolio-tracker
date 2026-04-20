# SİSTEMİN KENDİNİ GELİŞTİRME MEKANİZMALARI
> **oluşturulma**: 11 nisan 2026

---

## GENEL TABLO

| Mekanizma | Script | Çalışma sıklığı | Ne yapıyor |
|---|---|---|---|
| Trade öğrenme | `learning_engine.py` | Her kapanış sonrası | Kapanan trade'lerden ders çıkarır, K-kural istatistikleri tutar |
| Kaynak skoru | `learning_engine.py` | Her Twitter taraması | @CheddarFlow gibi hesapların tahmin doğruluğunu izler |
| Kural güncelleme | `rule_updater.py` | Haftalık | Backtest kanıtıyla parametreleri PLAYBOOK'ta değiştirir, git push |
| Prompt evrimi | `darwin_evolution.py` | 5 işlem gününde 1 | En zayıf K-kuralını bulur, yeni prompt versiyonu dener, 14 gün test |
| Tahmin takibi | `prediction_logger.py` | Her analizde | Claude'un tahminlerini kaydeder, gerçekleşmeyi ölçer |
| **Tema yönetimi** | **`theme_manager.py`** | **Her Pazar** | **Tema performansını ölçer, Claude API'ye karar aldırır, repo'yu günceller** |
| Dry-run | `dry_run_manager.py` | Sürekli | Önerilen değişiklikleri gerçek para kullanmadan test eder |

---

## API ÜZERINDEN CLAUDE — REPOyu GÜNCELLEYEBİLİR Mİ?

**Evet, doğrudan.**

`rule_updater.py` bunu halihazırda yapıyor:
```python
update_playbook_param(param, old_value, new_value, rationale)
# → TRADING_PLAYBOOK.md dosyasını günceller
# → git add + commit + push atar
# → Değişiklik GitHub'da görünür
```

Yeni `theme_manager.py` da aynı şekilde:
```python
apply_theme_change(decision)
# → THEMATIC_SYSTEM.md dosyasına yeni tema ekler / eski temayı çıkarır
# → git commit + push
# → Bir sonraki seansta yeni tema aktif
```

**Güvenlik katmanları:**
- Kilitli kurallar değiştirilemiyor (K-13 VIX seviyeleri, K-14 mantığı)
- Haftalık max 1 değişiklik
- Tema değişimi için güven skoru ≥7/10 gerekiyor
- Her değişiklik git geçmişinde izlenebilir

---

## TEMA HAFTALIK İNCELEME AKIŞI

```
Her Pazar 06:00 UTC — GitHub Actions tetiklenir
            │
            ├── ADIM 1: FMP API → 7 tema ETF'inin son 4 hafta RS hesabı
            │
            ├── ADIM 2: Claude API'ye sorulur:
            │     "Bu performansla ne yapmalıyız? Yeni tema var mı?"
            │     Sistem prompt: Karar JSON formatında — sadece JSON yaz
            │
            ├── ADIM 3: Karar değerlendirmesi
            │     • DEGISIKLIK_YOK: Hiçbir şey yapma
            │     • UYARI: Zayıf temayı izlemeye al, değiştirme
            │     • YENİ_TEMA: Güven ≥7 ise THEMATIC_SYSTEM.md'ye ekle + git push
            │     • TEMA_CIKAR: Güven ≥7 ise temayı listeden çıkar + git push
            │
            └── ADIM 4: Sonucu agent/memory/theme_weekly_reviews.json'a yaz
```

---

## KURAL GÜNCELLEMESİ NASIL ÇALIŞIYOR

Şu an değiştirilebilir 5 parametre var:

| Parametre | Mevcut | Min | Max | Açıklama |
|---|---|---|---|---|
| `rsi_k11_katman1` | 70 | 65 | 75 | K-11 Katman 1 RSI eşiği |
| `rsi_k11_katman2` | 80 | 73 | 82 | K-11 Katman 2 RSI eşiği |
| `atr_katsayi` | 2.0 | 1.5 | 3.0 | Trailing stop ATR çarpanı |
| `swing_max_gun` | 15 | 7 | 30 | Swing max tutma süresi |
| `vix_tam_pozisyon` | 22 | 18 | 24 | VIX altında tam pozisyon eşiği |

**Uygulama akışı:**
```
Haftalık analiz → Claude BACKTEST GEREKLİ önerisi üretir
      ↓
rule_updater.py → Güvenlik kontrolü (kilitli mı? aralıkta mı? backtest yeterli mi?)
      ↓
Geçtiyse → 14 gün DRY-RUN (gerçek para yok)
      ↓
14 gün sonra dry-run sonucu iyi → PLAYBOOK güncellendi + git push
      ↓
Kötüyse → git revert → eski değere geri dön
```

---

## DARWIN EVRİMİ — PROMPT VERSIYONLAMA

`darwin_evolution.py` şu 4 kuralın prompt'unu evrimleştiriyor:
- K-11 trailing stop mantığı
- K-11 kısmi kâr alma tetikleyicisi
- K-13 VIX eşik davranışı
- K-04 giriş filtresi

Her 5 işlem gününde:
1. Fitness skoru hesapla: `win_rate × avg_pnl`
2. En düşük fitness'lı kuralı seç
3. Claude API'ye "bu kuralın daha iyi versiyonunu yaz" de
4. Yeni versiyonu 14 gün dene (dry-run)
5. İyileşme var → commit | Kötüleşme → revert

---

## KAYNAK GÜVENİLİRLİK SKORU

Twitter hesapları için:
```python
update_source_scores("CheddarFlow", tahmin="NVDA yükseliyor", sonuc="Yükseldi", correct=True)
# → Skor artar
# → Sonraki seanslarda Claude bu hesaba daha fazla ağırlık verir
```

Yüksek skorlu kaynaklar (>%70 doğru) → Claude analizde öncelik verir
Düşük skorlu kaynaklar (<50%) → Otomatik olarak ihmal edilir

---

## EKSİKLER / GELECEK GELİŞTİRMELER

1. **Tema performansı → portföy sonucuna bağlama:** Hangi tema ne kadar kar getirdi? Şu an ölçülmüyor.
2. **Multi-agent debate:** Bir Claude "bu hisseyi al" derken, başka bir Claude "neden yanlış" tartışması. `adversarial_debate.py` var ama aktif değil.
3. **Conviction scorer otomasyonu:** Manuel hesaplanan conviction skoru FMP verisiyle otomatik hesaplanmalı.
4. **Portfolio × tema başarı matrisi:** "AI teması açıkken Agresif portföy ne kazandı?" sorusu cevaplandırılmalı.

---

*finzora ai | self improvement system | 11 nisan 2026*

---

## DÜZELTMELER (11 Nisan 2026)

### Eksik 1 — Tema Performansı → Portföy Sonucuna Bağlandı ✅

**`agent/tema_portfolio_tracker.py`** — Yeni oluşturuldu.

Her trade açılışında `tag_trade_with_theme()` çağrılır, aktif tema kaydedilir. Trade kapanınca P&L hangi temaya ait olduğu bilinir. Haftalık `run_weekly()` içinde matris güncellenir.

Çıktı: `agent/memory/tema_portfolio_matrix.json`
```json
{
  "AI_ALTYAPI": {
    "agresif": {"ortalama_pnl": 4.2, "win_rate": 67, "trade_sayisi": 9},
    "swing":   {"ortalama_pnl": 8.3, "win_rate": 55, "trade_sayisi": 20}
  }
}
```

### Eksik 2 — Multi-Agent Debate Aktive Edildi ✅

`orchestrator.py` güncellendi. Eski: sadece LOW güven veya SAT kararında debate. Yeni: AL dahil tüm önemli kararlar tartışılır.

```python
debate_tetik = (
    cio_karar.get("guven") in ("LOW", "MEDIUM") or
    cio_karar_tip in ("ACIL_CIK", "SAT", "KISMI_CIK", "AL", "KISMI_EKLE")
)
```

### Eksik 3 — Conviction Scorer Otomasyonu ✅

**`agent/conviction_scorer.py`** — Yeni oluşturuldu. 5 bileşen, tamamen FMP API:

| Bileşen | Max | FMP Endpoint |
|---------|-----|---|
| Teknik güç | 25 | historical-price-eod + RSI hesabı |
| Tema uyumu | 25 | agent/memory/theme_scores.json × katman ağırlığı |
| Momentum | 20 | stock-price-change + analyst-estimates |
| Temel kalite | 15 | key-metrics-ttm + ratios-ttm |
| Risk faktörü | 15 | cash-flow-statement + earnings-calendar |

Kullanım: `python conviction_scorer.py NVDA LMT XOM`

### Eksik 4 — Portfolio × Tema Başarı Matrisi ✅

`tema_portfolio_tracker.py` içindeki `analyze_trades_by_theme()` fonksiyonu:
- `data/swing/closed.json` tarar
- `data/transactions.csv` tarar
- Her trade için entry tarihinde aktif temayı bulur
- Tema × portföy bazında P&L, win rate, trade sayısı hesaplar
- Haftalık orchestrator içinde otomatik çalışır

**Kalan tek eksik:** Tema etiketi geriye dönük olarak eski trade'lere uygulanamaz (tema o tarihte kaydedilmemişti). Yeni trade'lerden itibaren doğru çalışır.

---

## GÜNCEL DURUM

| Mekanizma | Durum |
|---|---|
| Trade öğrenme | ✅ Çalışıyor |
| Kaynak skoru | ✅ Çalışıyor |
| Kural güncelleme | ✅ Çalışıyor |
| Prompt evrimi (Darwin) | ✅ Çalışıyor |
| Tahmin takibi | ✅ Çalışıyor |
| Tema yönetimi (haftalık) | ✅ YENİ — Çalışıyor |
| Conviction scorer | ✅ YENİ — Çalışıyor |
| Adversarial debate | ✅ GENİŞLETİLDİ — BUY dahil |
| Tema × Portföy matrisi | ✅ YENİ — Çalışıyor |

---

## DÜZELTMELER (v2) — 11 Nisan 2026

### Hata 1 — Kilitli Kural Kaldırıldı ✅
`rule_updater.py` içindeki `LOCKED_RULES` dict'i silindi.
Bunun yerine **Tiered Confidence (Kademeli Güven)** sistemi eklendi:

| Tier | Parametreler | Min Trade | Min Güven | Max Değişim |
|------|-------------|-----------|-----------|-------------|
| Normal | RSI, ATR, swing günü | 10 | 6/10 | %30 |
| Critical | K-13 VIX, K-14 drawdown, K-17 korel. | 30 | 8/10 | %20 |

Hiçbir kural değişemez değil — kritik kurallar **daha zor** değişir.

### Hata 2 — Fitness Formülü Belge ↔ Kod Uyuşmazlığı ✅
Belge `win_rate × avg_pnl` yazıyordu, kod `Sharpe × win_rate` kullanıyordu.
Belge güncellendi: **Fitness = `Sharpe × win_rate` = `(avg_pnl / std_dev) × win_rate`**

### Hata 3 — Çakışan Darwin Testleri ✅
`find_weakest_rule()` güncellendi: `pending_test=True` olan kurallar seçim listesinden dışlanır.
Sonuç: K-11 test altındayken Darwin K-04 seçer, aynı kural çift teste girmez.
Tüm kurallar test altındaysa döngü ertelenir, geçerli bir mesaj döner.

### Hata 4 — Tahmin Skoru / Gerçek Trade Çıkışı Uyuşmazlığı ✅
`prediction_logger.py`'e `score_pending_predictions_v2()` eklendi.
Her score_window için önce `transactions.csv` kontrol edilir.
3. günde stop-loss olan trade → 5. günde fiyat iyileşse de gerçek exit P/L ile skorlanır.

### Hata 5 — Takvim Günü vs. İş Günü ✅
`darwin_evolution.py`'e `is_trading_day()` ve `count_trading_days_since()` eklendi.
Hafta sonu Darwin çalışmaz. "5 gün" artık takvim günü değil iş günüdür.

### Hata 6 — AI Teması Tek ETF Proxy ✅
`theme_manager.py`'de `THEME_ETFS` → `THEME_BASKETS` (ağırlıklı ETF sepeti):
```
AI_ALTYAPI: SMH(%25) + GRID(%20) + BOTZ(%20) + SOXX(%15) + PAVE(%10) + FAN(%10)
```
Ayrıca iki katmanlı ölçüm:
1. Gerçek trade P/L (`tema_portfolio_matrix.json`) — öncelikli
2. ETF sepeti composite RS — veri yoksa yedek

### Hata 7 — L3 Digest Gecikmesi ✅
`darwin_evolution.py` içinde `_update_k_rules_digest()` artık:
- Her evrim başlangıcında (pending_test=True kaydında)
- Her değerlendirme sonucunda (COMMIT veya REVERT)
anlık çağrılıyor. "Haftalık" bekleme yok.

---

*finzora ai | self improvement system v2 | 11 nisan 2026*
