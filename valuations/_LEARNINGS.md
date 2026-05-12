# Değerleme Dersleri — Birikimli Notlar

## LQDA - 12 Mayıs 2026

### Skill İyileştirme Notları (Adil Değer 9 Yöntem v4.1)

**Sorun 1: Rule of 40 biotech için yanlış uygulanıyor**
- LQDA için Rule of 40 yöntemi $652.40 sonucu verdi
- Bu yöntem SaaS/yazılım şirketleri için tasarlanmış (revenue growth + FCF margin > 40)
- Healthcare/Biotechnology sektöründe Rule of 40 yorumu yapılmamalı
- Ana medyan bu tek yöntemden $327 oldu, ana karar matrisi yanılttı

**Çözüm önerisi:** Skill v5.0'da Rule of 40 sektör filtresi eklenmeli (sadece tech_software ve communication için).

**Sorun 2: Forward outlier flag inflection biotech için yanlış**
- EPS_FWD/EPS_TTM = 26.98x → outlier flag aktif → Forward P/E + EV/FWD + PEG ELİMİNE edildi
- Ancak LQDA'da bu oran gerçek inflection noktasını yansıtıyor (TTM kısmı zararlı çeyrekler içeriyor, FWD karlılığı)
- Gerçek değerlemede en önemli yöntem (Forward P/E) elendi

**Çözüm önerisi:** Skill v5.0'da inflection point tespit kuralı eklenmeli — son 2 çeyrek pozitif EPS varsa Forward outlier flag iptal.

**Sorun 3: DCF yanlış sonuç (yetersiz veri)**
- 4 yıllık normalize FCF kullanılıyor, ancak son 8 çeyrekten 4'ü negatif 4'ü pozitif
- Negatif geçmiş veri DCF'i bastırıyor → $2-7 saçma sonuç
- Inflection biotech'lerde DCF için forward-only FCF kullanılmalı

**Çözüm önerisi:** Skill v5.0 GROWTH modunda DCF için projeksiyon yıllarını forward (2026-2030 analist tahmini) bazlı yapmalı.

### Genel Değerleme Kuralı

**Healthcare growth biotech (inflection point sonrası) için ideal yöntemler:**
1. Forward P/E (2026E + 2027E, P/E 20-30x aralık)
2. EV/Forward Revenue (P/S 8-12x sektör tipik)
3. Analist konsensüs (en güvenilir referans)
4. Margin of safety: Bilanço (cash/debt) + pazar payı verisi

**Kullanılmamalı:**
- Rule of 40
- Traditional TTM P/E (zararlı geçmiş çeyrekler bozuyor)
- EV/EBITDA TTM (negatif bozuyor)
- Graham Number (büyüme şirketlerinde uygun değil)

### LQDA Özet Veri Kütüphanesi

| Metrik | Değer | Tarih |
|---|---|---|
| Fiyat | $55.30 | 12 May 2026 |
| Q1 2026 Revenue | $132.9M | Q1 |
| Q1 2026 NI | $52.9M | Q1 |
| Q1 2026 FCF | $50.2M | Q1 |
| 2026E EPS | $3.09 | Analist |
| 2026E Revenue | $681M | Analist |
| Analist hedef medyan | $62 | 12 May |
| Adil değer (manuel) | $68 (medyan) | finzora ai |
| Karar | AL ($20K agresif) | finzora ai |

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

---

**Hazırlayan:** finzora ai  
**Versiyon:** 1.0
