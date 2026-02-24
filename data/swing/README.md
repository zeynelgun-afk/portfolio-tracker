# SWING TRADE SİSTEMİ

> **son güncelleme**: 24 şubat 2026
> **versiyon**: 3.0

---

## dosyalar

| dosya | açıklama |
|-------|---------|
| `active.json` | açık pozisyonlar (max 10) |
| `closed.json` | kapatılmış trade'ler + istatistikler + dersler |

> ⚠️ watchlist artık `data/watchlist.json`'da (merkezi) — bu klasörde değil

---

## kurallar

detaylı kurallar: `docs/SWING_TRADE_RULES.md`

| kural | değer |
|-------|-------|
| max eşzamanlı pozisyon | 10 |
| stop-loss | %5 |
| kar hedefi | %10 |
| min R:R oranı | 2:1 |
| tavsiye tutma süresi | 7-10 gün |

## çıkış stratejisi (hibrit)

1. **hedef fiyata ulaşınca (+%10)**: %50 sat, kalan %50 trailing stop
2. **trailing stop**: zirveden -%5 (sadece yukarı güncellenir, asla aşağı çekilmez)
3. **stop-loss tetiklenince**: %100 sat, duygusal karar yok

## tarama yöntemleri

- RSI oversold (RSI < 30)
- earnings momentum (beat > %10)
- breakout (direnç kırılımı + hacim)
- sektör liderliği (RS > +1.0%)
- momentum (fiyat + hacim artışı)

---

> finzora ai
