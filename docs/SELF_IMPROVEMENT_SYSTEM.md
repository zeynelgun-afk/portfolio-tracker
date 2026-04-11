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
