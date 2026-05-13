---
title: K-Kuralları Hızlı Referans (Sadeleştirilmiş v2)
description: 13 Mayıs 2026 sadeleştirmesi sonrası aktif K-kurallarının özeti
tags:
  - k-rules
  - trading
  - reference
related:
  - "[[../notes/2026-05-13_SIMPLIFICATION]]"
---

# K-KURALLARI — SADELEŞTİRİLMİŞ REFERANS

> 13 Mayıs 2026 sadeleştirmesi sonrası. Önceki kapsamlı versiyon: `docs/archive/2026-05-13_pre_simplification/K_RULES_QUICK_REF.md`

## FELSEFE

Zeynel "kâtip ol, yönetici olma" dedi. Bu yüzden:
- Otomatik karar dayatan kurallar **KALDIRILDI**.
- Sadece bilgi/uyarı veren kurallar **AKTİF**.
- Disiplin notları kişisel hatırlatma seviyesinde, manuel olarak tetiklenir.

Pozisyon büyüklüğü, sektör ağırlığı, satış zamanlaması kararı Zeynel'e aittir. Claude kayıt tutar, analiz yapar, sorulan soruya cevap verir; aksiyon dayatmaz.

---

## 🟢 AKTİF UYARI KURALLARI (2 kural)

### K-13 — VIX kriz protokolü
- **Tetik:** VIX > 30, ya da jeopolitik şok haberi (savaş, FED acil kararı, sistemik kriz)
- **Aksiyon:** Zeynel'e DM uyarı (`telegram_notify.py --dm`)
- **Karar dayatmaz.** Mesaj formatı: "VIX 32, ortam değişti, mevcut pozisyonları gözden geçirmek isteyebilirsin"

### K-23 — Portföy drawdown alarmı
- **Tetik:** Toplam portföy değeri başlangıca göre -%10 / -%15 / -%20 eşiklerini geçtiğinde
- **Aksiyon:** Zeynel'e DM uyarı, eşik bazlı
- **Karar dayatmaz.** Farkındalık amaçlı, "şu an drawdown -%12, izle"

---

## 🟡 KİŞİSEL DİSİPLİN — KURAL DEĞİL, HATIRLATICI

Zeynel "X hissesini analiz et" veya "bu pozisyona ne dersin" dediğinde, eğer pozisyon aşağıdaki pattern'lere uyuyorsa Claude **analiz içinde** hatırlatır. Otomatik tetik yok, proaktif mesaj yok.

- **K-19 — XLP dışlama hatırlatıcısı:** Tüketici defansif (XLP) sektörü tarihsel olarak momentum dezavantajlı. Analiz sırasında "XLP içinde, momentum zayıf olabilir" denir.
- **K-20 — Dead cat bounce:** Düşüş trendinden çıkmış görünen RS sıçramalarının çoğu gerçek dönüş değildir. Analiz sırasında uyarılır.
- **K-21 — VIX 5g %20+ swing girişi tehlikesi:** Volatilite hızlı yükseliyorsa swing girişi kanıtlanmış zarar.
- **K-ZST — 10 gün zirve alımı:** Son 10 günde fiyat zirvesinde alım = chasing riski.
- **Day-1 chasing yasağı:** Yeni hisse alımında intraday regular session close + RSI teyidi şartı. **KTOS/CEG/HAL/LASR 5/5 zarar kanıtı.** Pre-market gap-up tek başına yasak tetiklemez ama analiz sırasında bilgi olarak raporlanır.

---

## 🔴 KALDIRILAN KURALLAR

13 Mayıs 2026 sadeleştirmesinde kaldırıldı (otomatik karar dayattıkları için):
- **K-11** (RSI bazlı kademeli kâr alma — Katman 1/2/3)
- **K-12** (sektör/tema ağırlık tavanı, dinamik tema)
- **K-15c** (tema alımı süre limiti)
- **K-22** (nakit %10 üstü zorunlu kullanım)

Önceki kapsamlı dokümantasyon: `docs/archive/2026-05-13_pre_simplification/K_RULES_QUICK_REF.md`

---

## CLAUDE'UN YENİ ROLÜ

- **Kayıt tut:** Yeni pozisyon → `data/portfolio.json` `positions` listesine ekle (symbol, sector, entry_date, entry_price, shares, entry_reason, stop_loss zorunlu, target opsiyonel)
- **Kapanış kaydı:** Pozisyon kapandığında `closed` listesine taşı (exit_date, exit_price, exit_reason eklenir)
- **Sorulduğunda analiz yap:** Adil değer, teknik, fundamental, sektör — Zeynel sorduğunda. Proaktif değil.
- **Uyarı ver:** K-13 ve K-23 tetiklendiğinde, karar dayatmadan.
- **Disiplin hatırlat:** Pozisyon analizi içinde K-19/20/21/ZST/day-1 pattern'leri varsa not düş.
