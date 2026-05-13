# Değerleme Dersleri — Birikimli Notlar

## LQDA - 12 Mayıs 2026 (DÜZELTİLMİŞ)

### Skill Düzeltmeleri Uygulandı (v5.1)

**ÖNEMLİ DÜZELTME:** İlk LQDA değerleme raporunda /mnt klasöründeki eski v4.1 versiyonu kullanılmış. GitHub'daki production versiyonu zaten v5.0 idi. v5.1 ile bu süreç tamamlandı:

**Sorun 1: Rule of 40 biotech için yanlış uygulanıyor** ❌ İLK NOTUM YANLIŞTI
- İlk notum: "Rule of 40 sektör filtresi eklenmeli"
- **Gerçek:** Rule of 40 **zaten v5.0'da kaldırılmış** (sadeleştirme adımı, 4 yöntem çıkarıldı)
- /mnt'deki eski v4.1 paketinin Rule of 40 içerdiğini görüp yanılmışım
- **Ders:** GitHub'daki canlı production versiyonu kontrol et, /mnt'deki upload edilmiş paket eski olabilir

**Sorun 2: Forward outlier flag inflection biotech için yanlış tetikleniyor** ✅ DÜZELTİLDİ (v5.1)
- v5.0 davranışı: EPS_FWD/EPS_TTM > 2.5x → tüm Forward yöntemleri ELENİR
- LQDA örneği: ratio 21.56x → Forward P/E + PEG + EV/FWD Revenue + EV/FWD EBITDA hepsi N/A
- v5.1 düzeltmesi: Son 2 çeyrek POZİTİF EPS + önceki 2 çeyrek NEGATİF EPS varsa → "inflection point" → outlier flag iptal
- LQDA testi: Q4-25 +$0.17, Q1-26 +$0.60 (pozitif) + Q3-25 -$0.04, Q2-25 -$0.49 (negatif) → inflection_point=True
- v5.1 ile sonuç: Forward P/E $94-160, EV/FWD Revenue $60-120 hesaplandı, manuel hesaplarla uyumlu

**Sorun 3: DCF inflection biotech için sağlıksız** ⏳ İLERİDE DÜZELTİLECEK (v5.2 önerisi)
- DCF normalize FCF kullanıyor (4 yıl ortalama, negatif geçmiş çeyrekler dahil)
- Inflection point sonrası DCF için forward-only FCF projeksiyon daha uygun
- Şu an için manuel doğrulama gerekli

### Genel Değerleme Kuralı (Güncel)

**Healthcare growth biotech (inflection point sonrası) için ideal yöntemler:**
1. Forward P/E (2026E + 2027E, P/E 20-30x aralık) ✅ v5.1'de çalışıyor
2. EV/Forward Revenue (P/S 8-12x sektör tipik) ✅ v5.1'de çalışıyor
3. Analist konsensüs (en güvenilir referans)
4. Margin of safety: Bilanço (cash/debt) + pazar payı verisi

**Kullanılmamalı (v5.0 sonrası sadeleştirildi):**
- ~~Rule of 40~~ (v5.0'da kaldırıldı, SaaS metriği)
- ~~Graham Number~~ (v5.0'da kaldırıldı)
- ~~EV/EBIT~~ (v5.0'da kaldırıldı)
- ~~Justified P/B~~ (v5.0'da kaldırıldı)
- Traditional TTM P/E (zararlı geçmiş çeyrekler bozar — sadece inflection sonrası)
- EV/EBITDA TTM (negatif TTM EBITDA bozar)

### LQDA Özet Veri Kütüphanesi

| Metrik | Değer | Tarih |
|---|---|---|
| Fiyat | $56.60 | 12 May 2026 |
| RSI | 85.2 (aşırı alım) | 12 May |
| Q1 2026 Revenue | $132.9M | Q1 |
| Q1 2026 NI | $52.9M | Q1 |
| Q1 2026 FCF | $50.2M | Q1 |
| 2026E EPS | $3.09 | Analist |
| 2026E Revenue | $681M | Analist |
| Analist hedef medyan | $62 | 12 May |
| v5.1 Forward P/E (normal) | $130.88 | Skill |
| v5.1 EV/FWD Rev (normal) | $92.56 | Skill |
| Manuel adil değer medyan | $68 | finzora ai |
| Karar | İZLEME ($45-50 girişe bekle) | finzora ai |

### Patent Davası Zaman Çizelgesi

| Tarih | Olay |
|---|---|
| 2020 | UTHR ilk dava ('793, '901, '066) |
| Temmuz 2022 | PTAB '793 patenti geçersiz ilan etti |
| Aralık 2023 | Federal Circuit PTAB kararını onayladı |
| Mayıs 2024 | Mayıs 2025 PDUFA tarihi belirlendi |
| Ekim 2024 | SCOTUS UTHR petition'ını reddetti |
| Mayıs 2025 | UTHR '782 patent yeni davası |
| Mayıs 2025 | FDA YUTREPIA final onayı |
| Q3-Q4 2025 | Revenue rampa başladı |
| Q1 2026 | Tam karlılık inflection point |

### Mayıs 2026 Analist Aktivitesi

| Tarih | Firma | Önceki PT | Yeni PT |
|---|---|---|---|
| 12 May | H.C. Wainwright | $55 | $67 (+%22) |
| 12 May | Wells Fargo | $51 | $62 (+%22) |
| 11 May | Jefferies | $57 | $60 (+%5) |

Memory'deki analist takip sistemi STRONG_BUY tetikledi (3 raise / 2 gün / 0 lower / 0 dg).

---

**Hazırlayan:** finzora ai  
**Versiyon:** 2.0 (12 May 2026, v5.1 sonrası düzeltme)
