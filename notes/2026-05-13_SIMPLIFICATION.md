---
title: 13 Mayıs 2026 — Sistem Sadeleştirmesi
description: 3 portföy + swing → tek portfolio.json migration kaydı
tags:
  - migration
  - sadeleştirme
  - sistem
---

# 13 MAYIS 2026 — SİSTEM SADELEŞTİRMESİ

## MOTİVASYON

Zeynel: "Sistemin tamamı fazla kurumsal hissettiriyor. Sadece hisse adı, sektör, giriş nedeni, giriş fiyatı belirtsin. Kaç adet alacağına ve ne kadar yer kaplaması gerektiğine karar vermesin."

Claude'un rolü "portföy yöneticisi"nden "kâtip + analist"e indirildi: pozisyon büyüklüğü, sektör ağırlığı, sleeve dağılımı, otomatik satış zamanlaması kararı artık Zeynel'e ait.

## DEĞİŞİKLİKLER

### 1. Portföy yapısı: 3 portföy + swing → tek dosya

- **ESKİ:** `data/portfolios/balanced.json` ($100K) + `aggressive.json` ($400K) + `dividend.json` ($100K) + `data/swing/active.json` (max 5)
- **YENİ:** `data/portfolio.json` (tek liste, sleeve/tema disiplini yok)

### 2. Pozisyon şeması — minimal

Eski şemada ~25 alan vardı (canlı fiyat, ATR, RSI, ağırlık, tema, stop_faz, durum, vs.). Yeni şemada **sadece 8 alan**:

```json
{
  "symbol": "TICKER",
  "sector": "Sektör adı",
  "entry_date": "YYYY-MM-DD",
  "entry_price": 0.00,
  "shares": 0,
  "entry_reason": "Detaylı giriş tezi",
  "stop_loss": 0.00,      // ZORUNLU
  "target": null          // OPSİYONEL
}
```

Kapanışta eklenir: `exit_date`, `exit_price`, `exit_reason`, `pnl_pct`, `lessons` (opsiyonel).

**Çıkarılan alanlar (FMP'den canlı çekilir):** `guncel_fiyat`, `guncel_deger`, `kar_zarar`, `kar_zarar_yuzde`, `gunluk_degisim_yuzde`, `agirlik_yuzde`, `rsi`, `atr14`.
**Çıkarılan alanlar (sleeve/otomasyon mantığı):** `tema`, `stop_faz`, `zirve_fiyat`, `stop_mesafe_pct`, `durum`, `cb_kaynak`, `chandelier_stop`, `k11_aktif`, `k11_profit_lock`.

### 3. K kuralları sadeleştirildi

**KALDIRILAN (otomatik karar dayatan):**
- K-11 (RSI bazlı kademeli kâr alma)
- K-12 (sektör/tema ağırlık tavanı, dinamik tema)
- K-15c (tema alımı süre limiti)
- K-22 (nakit %10 üstü zorunlu kullanım)

**AKTİF UYARI (karar dayatmaz, DM uyarı):**
- K-13 (VIX kriz protokolü)
- K-23 (portföy drawdown alarmı)

**KİŞİSEL DİSİPLİN (analiz sırasında hatırlatıcı, otomatik tetik yok):**
- K-19 (XLP dışlama)
- K-20 (RS dead cat bounce)
- K-21 (VIX 5g %20 swing yasağı)
- K-ZST (10g zirve alımı)
- Day-1 chasing yasağı

Detay: `docs/K_RULES_QUICK_REF.md` (yeni minimal versiyon).

### 4. Çakışma birleştirme

Migration sırasında 3 sembol birleşti (aynı sembol farklı portföylerdeydi):

| Sembol | Önce | Sonra |
|--------|------|-------|
| DINO | 217 hisse @ $69.10 + 806 hisse @ $72.86 | 1023 hisse @ $72.06 |
| AMAT | long 139 @ $385.52 + swing 10 @ $442.48 | 149 hisse @ $389.34 |
| KLAC | long 20 @ $1731.61 + swing 3 @ $1870.52 | 23 hisse @ $1749.73 |

Ağırlıklı ortalama maliyet hesaplandı, entry_reason'da `[BİRLEŞTİRİLDİ — N giriş]` etiketi var.

### 5. Stop=giriş düzeltmesi

Eski sistemde 4 pozisyonun `stop_loss`'u `entry_price`'a eşitti (fiilen stop yok). Yeni şemada stop_loss zorunlu olduğu için migration sırasında **entry_price × 0.95** otomatik kondu:

| Sembol | Eski stop | Yeni stop |
|--------|-----------|-----------|
| PSA | $299.15 | $284.19 |
| CVS | $83.27 | $79.11 |
| DINO ve KLAC | (birleşme sonrası swing kaydının gerçek stop'u kullanıldı) | — |

Etiket: `entry_reason` alanında `[STOP %5 OTOMATİK]` notu.

### 6. Arşivlenenler

`data/archive/2026-05-13_pre_simplification/` altına git mv ile taşındı:
- `portfolios/balanced.json`, `aggressive.json`, `dividend.json`
- `swing/` klasörünün tamamı (active, closed, watchlist, status, README)

`docs/archive/2026-05-13_pre_simplification/` altına taşındı:
- Eski 541 satırlık `K_RULES_QUICK_REF.md`

### 7. Migration script

`scripts/migrate_2026_05_13.py` — tek seferlik script, tekrar çalıştırılması gerekmiyor. Referans/audit için repoda saklıyor.

## SONUÇ

| Metrik | Önce | Sonra |
|--------|------|-------|
| Aktif portföy dosyası | 4 (balanced, aggressive, dividend, swing/active) | 1 (portfolio.json) |
| Açık pozisyon | 15 long + 5 swing = 20 | 17 (çakışma birleşti) |
| Kapalı pozisyon (geçmiş) | 34 (swing closed) | 34 (taşındı) |
| Pozisyon başına alan sayısı | ~25 | 8 |
| Aktif K-kural | 11 | 2 (uyarı) + 5 (disiplin hatırlatıcı) |
| Otomatik karar dayatan kural | 9 | 0 |
| Stop_loss zorunluluğu | Esnek | Zorunlu (yeni alımlarda) |
| Target zorunluluğu | Zorunlu | Opsiyonel |

## SONRAKI ADIMLAR

Sadeleştirme öncesi sistemde çalışan ve artık değişmesi gereken otomatik scriptler/zamanlayıcılar:
- `agent/` klasörü altındaki morning/monitor/closing scriptleri — 3 portföy JSON'unu okuyordu, tek dosyaya bakacak şekilde güncellenmeli (sonraki commit)
- `scripts/risk_panel_generator.py` — portföy değer hesaplaması tek dosyadan yapılmalı
- Telegram bot komutları (`/portfoy /agresif /dengeli /temettu /swing`) — tek `/portfoy` komutuyla sadeleştir
- `transactions.csv` — eski format korunabilir, sadece kayıt amaçlı

Bu güncellemeler ayrı commit'lerde, Zeynel onayıyla yapılacak.
