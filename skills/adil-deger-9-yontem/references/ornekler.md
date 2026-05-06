# Adil Değer Analiz Örnekleri

Skill'in nasıl kullanıldığını gösteren referans örnekler. Yeni analizler `notes/usage_log.csv`'ye gider.

## AMKR (Amkor Technology) - 6 Mayıs 2026

### Bağlam
- Mevcut Fiyat: $74.45
- Sektör: Semiconductors → semicon_osat preset
- 1 yıllık performans: +%297
- Son bilanço: Q1 2026, beat ama -%8.6 satış sonrası düşüş

### 9 Yöntem × 3 Senaryo Sonuçları

| Yöntem | Ayı | Normal | Boğa |
|---|---|---|---|
| Net P/E | $22.2 | $31.7 | $39.6 |
| Forward P/E (2027E) | $28.6 | $39.7 | $48.4 |
| EV/EBIT | $26.0 | $36.5 | $44.4 |
| EV/EBITDA | $40.4 | $54.3 | $65.1 |
| EV/Revenue | $36.5 | $58.0 | $75.7 |
| P/FCF | $19.0 | $27.5 | $34.0 |
| Justified P-B | $13.2 | $25.7 | $35.0 |
| Graham | $21.4 | $26.7 | $29.8 |
| DCF | $32.0 | $50.0 | $68.0 |

### Eder Aralıkları (Median ± IQR/2)

- 🐻 **Ayı:** $21 - $32
- ⚖️ **Normal:** $27 - $50
- 🐂 **Boğa:** $35 - $66

### Mevcut Fiyat: $74.45
- Boğa eder üst sınırına göre +%13 pahalı
- Normal eder üst sınırına göre +%49 pahalı
- Ayı eder üst sınırına göre +%133 pahalı

### Karar
**GEÇ / İZLE** — Mevcut fiyattan giriş yok. $50-55 seviyesinde tekrar değerlendirilir.

### Öğrenmeler
- OSAT preset'i yeni eklendi, 10 yıl tarihsel medyan ile doğrulandı (P/E 18, EV/EBITDA 11)
- Capital intensive şirketlerde P/FCF her zaman düşük çıkıyor (capex normalize bile çare olmuyor)
- AI tedarik zinciri primli olduğunda EV/Revenue boğa multiplier 1.30 yetersiz olabilir, NVDA gibi premium taşıyorlarda 1.40 düşünülebilir
- Q1 2026'da gross margin Q4'ten %16.7 → %14.2'ye düşmüş, sezonsal ama momentum kaybı sinyali

## Şablon (Yeni Örnek Eklerken)

```markdown
## [TICKER] - YYYY-MM-DD

### Bağlam
- Mevcut Fiyat: $X
- Sektör: [auto-detected preset]
- 1 yıllık performans: %Y
- Son bilanço: [özet]

### Eder Aralıkları
- 🐻 Ayı: $A - $B
- ⚖️ Normal: $C - $D
- 🐂 Boğa: $E - $F

### Karar
[GİR / İZLE / GEÇ + neden]

### Öğrenmeler
- [skill geliştirme notları]
```
