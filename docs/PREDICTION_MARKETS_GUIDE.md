---
title: Tahmin Piyasaları Rehberi
description: prediction_logger: tahminlerin loglanması, 14g+ skorlama, hit rate analizi.
tags:
  - prediction
  - markets
  - logging
related:
  - "[[Index]]"
  - "[[OBSERVABILITY]]"
  - "[[SELF_IMPROVEMENT_SYSTEM]]"
---

# 📊 PREDICTION MARKETS KULLANIM REHBERİ

> **Eklenme Tarihi:** 21 Şubat 2026  
> **Memory Referansı:** Günlük ve haftalık rutin

---

## 🎯 ANA PLATFORMLAR

### Kalshi (Primer Kaynak) ✅
- **Kullanım:** Fed/ekonomik kararlar
- **Doğruluk:** %100 track record (Fed 2022-2024)
- **Güvenilirlik:** En yüksek (%78 overall)
- **Link:** https://kalshi.com

### Polymarket (Sekonder Sinyal) ⚠️
- **Kullanım:** Jeopolitik/viral events
- **Doğruluk:** %67 overall
- **Risk:** Whale manipulation
- **Link:** https://polymarket.com

---

## 📅 GÜNLÜK RUTİN

### SABAH (Piyasa Açılışından Önce)

```
1. Kalshi Fed Rate Probabilities
   → https://kalshi.com/markets/kxfeddecision
   → Değişim var mı?
   → Son 24h volume ne?

2. Polymarket Iran/Tariff Markets
   → Iran escalation odds
   → Tariff refund odds
   → Volume spike var mı?

3. Portföy Alignment
   → Enerji pozisyonları (Iran odds yükseliyorsa güçlü)
   → Defensive (Fed rate hold'da güvenli)
```

---

## 📈 HAFTALIK RAPOR

### "Prediction Markets Pulse" Bölümü (Pazar)

```markdown
## 🎲 Prediction Markets Pulse

### Fed Rate Probabilities (Kalshi)
- Şubat FOMC: %100 HOLD (3.50%-3.75%)
- Mart cut odds: %XX
- Değişim: [↑↓] %X (geçen haftaya göre)

### Jeopolitik Risk (Polymarket)
- Iran escalation: %XX
- Tariff refund odds: %XX
- 7-gün volume: $XXM

### Portföy Etkisi
- [Enerji/Defensive alignment analizi]
```

---

## ⚡ AKSİYON TETİKLEYİCİLERİ

| Tetikleyici | Threshold | Aksiyon |
|-------------|-----------|---------|
| **Fed Rate Cut Odds** | >%30 | Defensive azalt, cyclical ekle |
| **Iran Escalation** | >%50 | Enerji pozisyonlarını artır (XLE, SM, KOS) |
| **Tariff Refund** | >%60 | Import-heavy stocks sat (bizde yok ama kontrol et) |

---

## ✅ KONTROL LİSTESİ

### Her Sabah
- [ ] Kalshi Fed odds kontrol
- [ ] Polymarket volume spike var mı
- [ ] Odds değişimi >%10 ise not al

### Her Pazar
- [ ] Haftalık probability değişimlerini topla
- [ ] "Prediction Markets Pulse" bölümünü yaz
- [ ] Portföy alignment kontrol et

---

## 🚨 DİKKAT EDİLECEKLER

1. **Volume Mutlaka Kontrol Et**
   - <$10K → Güvenilmez
   - $1M+ → Güvenilir
   - $10M+ → Çok güvenilir

2. **Confirmation Bias'tan Kaçın**
   - Market görüşünü doğrulamıyorsa DİNLE
   - Özellikle Kalshi Fed kararlarında

3. **Whale Manipulation (Polymarket)**
   - Ani %10+ swing → Dikkatli ol
   - Volume vs odds değişimi kontrol et

4. **Supplement, Not Replace**
   - Diğer kaynaklarla kombine et
   - FMP data, news, technical analysis ile birlikte kullan

---

## 📊 ÖRNEK KULLANIM

### Senaryo: Iran Escalation Odds %35 → %55 (24h)

**Analiz:**
1. Polymarket volume: $2M → $8M (4x artış) ✅
2. Threshold: >%50 ✅
3. Portföy: Enerji pozisyonları mevcut (SM, KOS, XLE)

**Aksiyon:**
- ✅ Mevcut enerji pozisyonlarını TUT
- ✅ Kar realizasyonu planını ertele
- ⚠️ Stop-loss'ları kontrol et (petrol düşerse)

---

**Son Güncelleme:** 21 Şubat 2026  
**Durum:** Aktif
