# HAFTALIK RAPOR ŞABLONU — YYYY-AA-GG

> **ZORUNLU İLK ADIM:** `python scripts/weekly_pre_check.py` çalıştır.
> Çıktısı: `data/weekly_pre_check.json` — rapordaki TÜM sayısal veriler buradan gelir.
> Hallüsine rakam = sıfır tolerans.

---

## 1. PORTFÖY ÖZETİ

> Kaynak: `weekly_pre_check.json → portfoy_ozet`

**Toplam Değer:** $[GENEL.toplam] (Başlangıç: $600,000, %[GENEL.pl_pct]) [KESİN]

| Bucket | Değer | P/L | Durum |
|--------|-------|-----|-------|
| Agresif | $[aggressive.toplam] | %[aggressive.pl_pct] | |
| Dengeli | $[balanced.toplam] | %[balanced.pl_pct] | |
| Temettü | $[dividend.toplam] | %[dividend.pl_pct] | |

**En İyi Pozisyon:** [sembol] +%[pnl_pct] — [portfoy]
**En Kötü Pozisyon:** [sembol] %[pnl_pct] — [durum notu]

---

## 2. BLOKAJ HATALARI (Varsa — önce bunları düzelt)

> Kaynak: `weekly_pre_check.json → blokaj_hatalari`

[HATA YOKSA: "Blokaj hatası yok."]
[HATA VARSA: Raporu yazmaya devam etme. Hatayı düzelt, script'i yeniden çalıştır.]

---

## 3. RİSK: KONSANTRASYON, KORELASYON, DRAWDOWN

> Kaynak: `weekly_pre_check.json → sektor_dagilimi`, `k17_alerts`

### K-17 Durumu
[k17_alerts boşsa: "K-17 ihlali yok."]
[k17_alerts doluysa: Uyarıları buraya yaz — yeni giriş yasak, mevcut azaltma değerlendir]

### Sektör Dağılımı (Pozisyon Bazlı)
> `sektor_dagilimi` bölümünden tablo oluştur

---

## 4. K-11 AKSİYONLAR

> Kaynak: `weekly_pre_check.json → k11_aksiyonlar`

[Boşsa: "K-11 tetiklenecek pozisyon yok."]

[Doluysa, her aksiyon için:]
- **[SEMBOL]** Tier[N] — [aksiyon] [öncelik]

---

## 5. EARNINGS TAKVİMİ + K-05/K-16 KARAR

> Kaynak: `weekly_pre_check.json → earnings_aksiyonlar`
>
> KURAL SEÇİCİ (rapora bakmadan önce oku):
> - kapsam = "swing" → K-05 (tam çıkış, ≤2g öncesi)
> - kapsam = "portfoy" → K-16 (skor bak, %0/%25/%50)
> - K-05 rakam "%30 değil" — TAM ÇIKIŞ
> - K-16 skor 0-1 → dokunma | 2-3 → %25 | 4-5 → %50

| Sembol | Kapsam | Kural | Earnings | Kalan | K-16 Skor | Aksiyon |
|--------|--------|-------|----------|-------|-----------|---------|
| [sembol] | [portfoy/swing] | [K-05/K-16] | [tarih] | [gün] | [skor/5 veya —] | [aksiyon] |

---

## 6. MAKRO VERİ

> Kaynak: `weekly_pre_check.json → macro`
>
> ⚠️ ASLA hafızadan yazma. Aşağıdaki alanları oku:
> - `macro.vix` → VIX değeri
> - `macro.isgucu_son_bilinen` → işsizlik oranı ve dönemi
> - `macro.nfp_tarihi` → bir sonraki NFP tarihi
> - `macro.spy`, `macro.qqq` → endeks değerleri

VIX: [macro.vix] ([macro.vix_not])
SPY: $[macro.spy.fiyat] | QQQ: $[macro.qqq.fiyat]
İşsizlik (son açıklanan): %[macro.isgucu_son_bilinen.deger] ([macro.isgucu_son_bilinen.donem])
NFP tarihi: [macro.nfp_tarihi] ([macro.nfp_gun_kaldi] gün)

### Önümüzdeki Hafta Makro Takvim
> Takvimi manuel ekle ama NFP/CPI için script çıktısını baz al

---

## 7. DARWIN EVRİM / K-KURAL FITNESS

> Kaynak: `scripts/k_rule_performance.py` (varsa)

---

## 8. BLIND SPOT ANALİZİ

> Script'in `uyarilar` bölümündeki otomatik tespitler buraya gelir.
> Ek manuel gözlemler eklenebilir.

---

## 9. GELECEK HAFTA 3 KRİTİK İZLEME NOKTASI

1. [k11_aksiyonlar'dan en yüksek öncelikli]
2. [earnings_aksiyonlar'dan en kritik]
3. [k17_alerts veya makro risk]

---

## 10. OTONOM AKSİYON KARARLARI

> Kaynak: k11_aksiyonlar + earnings_aksiyonlar + blokaj_hatalari
>
> SIRA:
> 1. Blokaj hatası varsa → önce düzelt
> 2. ACİL önceli aksiyonlar → en başa
> 3. YÜKSEK → sonra
> 4. ORTA/DÜŞÜK → izle listesi

| # | Sembol | Aksiyon | Gerekçe | Tür |
|---|--------|---------|---------|-----|
| 1 | | | | KESİN/İZLE |

---

## NOTLAR

- Rapor kaynağı: `data/weekly_pre_check.json` ([olusturulma tarihi])
- Script versiyonu: `scripts/weekly_pre_check.py`
- Sonraki kontrol: Gelecek Pazar sabahı aynı script
