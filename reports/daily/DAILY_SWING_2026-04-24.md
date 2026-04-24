# swing raporu — 2026-04-24

> finzora ai | sabah raporundan otomatik ayristirildi
> kaynak: DAILY_SABAH_2026-04-24.md — 3-rapor gorsel ayristirma, token maliyeti yok

## 0. PİYASA İSTİHBARATI

**Aktif temalar:**
- **AI momentum devam** [KESİN]: XLK +2.03%, MU ilk kez $500 üstü, INTC +27% (Q1 beat), NVDA/AMD call sweep akışları. AI_BOOM rejimi ORTA güvenle devam.
- **Altın nefes alıyor** [KESİN]: NEM +7.2% (Q1 beat + güçlü FCF), GLD +0.70%. Safe-haven trade kısmen geri.
- **Sell in May söylemi** [SPEKÜLATİF]: Twitter'da May-Oct zayıf dönem uyarıları dolaşıyor; ancak geçmiş veri YTD pozitif başlandığında Mayıs ortalaması +19.9% diyor — iki yönlü kullanılıyor.
- **29 Nisan Fed** [KESİN]: Faiz beklentisi sabit (14.75), basın toplantısı yüksek etkili — haftanın ana olayı.

**Haber etki zinciri:**
- INTC +27% → yarı iletken sentiment olumlu → MU/CAMT rüzgarı [MUHTEMEL]
- NEM Q1 beat → mevcut pozisyonda +7.2% bugün, P/L +8.7% [KESİN]
- CPRX +6.7% sıçrama ama portföyde Bugün -3.7% — veri bloğunda çelişki, stop %2.9 kritik [KESİN uyarı]

---

## 0.5 DÜN SEANS SONU NOTLARI

Session_state flag'i veri bloğunda yok. Öğrenmeler bölümü son 4 gün neredeyse boş (sadece "rapor sonu" notları). RAG'den çıkarılan son aktif durum:
- 23 Nisan: CAMT izle (fair value -%76 PAH sorgulanıyor), O ve MO için K-06 otomatik stop uyarısı aktif
- 22 Nisan: MO stop %1.4 uzaklıkta → bugün %4.6'ya genişledi (fiyat stop'tan uzaklaştı, iyi haber)
- 21 Nisan: VRT portföyden çıkarıldı (earnings öncesi +9.1% kârla K-05 zorunlu çıkış)

[KAYNAK_YOK] Detaylı flag listesi mevcut değil.

---

## 1. PİYASA GÖRÜNÜMÜ

### Endeks Tablosu
| Endeks | Fiyat | Değişim | Not |
|---|---|---|---|
| SPY | $711.38 | +0.41% | Yeni zirve bölgesi [KESİN] |
| QQQ | $659.99 | +1.32% | AI/tech lider [KESİN] |
| GLD | $434.44 | N/A (kaynak: FMP seans-içi % vermedi) | NEM rallisi altın gücünü teyit [MUHTEMEL] |
| TLT | $86.78 | N/A (kaynak: FMP seans-içi % vermedi) | Tahvil zayıf, risk-on [MUHTEMEL] |
| VIX | 18.67 | -3.31% | NORMAL bant, K-13 savunmacı tetik yok [KESİN] |

### Ön Piyasa Gapleri (14:49 TR çekimi)
| Ticker | Gap% | Durum | Not |
|---|---|---|---|
| ALAB | +8.0% | OLASI_GİRİŞ | Trend devamı, portföyde yok |
| NEM | +7.0% | OLASI_GİRİŞ | **PORTFÖYDE** — seansta +7.2% teyit |
| KLAC | +4.6% | OLASI_GİRİŞ | **SWING'de** — P/L +9.3% |
| MU | +4.5% | OLASI_GİRİŞ | **AGG'de** — seansta +4.6% teyit, $500 üstü |
| LLY | -4.5% | SAT_KONTROL | Portföyde yok |

### Sektör Liderleri (günlük)
- 🟢 XLK +2.03% (AI/tech)
- 🟢 GLD +0.70%
- 🟢 XLY +0.40%, XLU +0.18%, XLP +0.12%
- Defansif + büyüme birlikte yeşil → sağlıklı geniş katılım [MUHTEMEL]

### VIX / K-13
VIX 18.67 NORMAL bantta, savunmacı allokasyon tetiği yok. [KESİN]

---

## 3. SWING DURUMU — 5/5

Tümü yeşil, GEV +13.7% lider. KLAC +9.3%, CAT +4.8%, AMAT +3.7%, RPRX +2.5%. Yeni slot yok.

## 4. GÜNÜN PLANI

### HEMEN
1. **MU STOP_GÜNCELLE** [K-07/K-11]: Hedef aşıldı, trailing stop devreye al. Mevcut stop $437 civarı → $475'e yükselt (fiyat $503.83'ten %5.7 uzak). %21 kârı korumak öncelik.
2. **COHR STOP_GÜNCELLE** [K-07]: Hedef $330 aşıldı ($337.64), stop $317.16 → $325'e yükselt (%3.7 uzak ama trailing mantığı).
3. **ANET STOP_GÜNCELLE** [K-07]: Hedef $165 aşıldı, stop $164.42 → $170'e yükselt.

### İZLE (acil takip)
4. **CPRX**: Stop %2.9, bugün -3.7%. K-06 tetiklenirse otomatik çık, override yok.
5. **O**: Stop %3.1, K-06 tetikte otomatik.
6. **ABBV**: Stop %3.4 + earnings 4 gün. K-06 tetik + K-05 yeni giriş yasağı.
7. **MO**: Earnings 6 gün, stop %4.6 — rahat bant.
8. **OKE**: Earnings 3 gün (Pazartesi). K-05 aktif, mevcut pozisyon tutulur.

### PASİF (bugün aksiyon yok)
- Tech konsantrasyonu %57.4 → yeni AI/tech girişi K-17'den YASAK [KESİN]
- Swing 5/5 dolu, yeni giriş yok
- Fed öncesi Cuma — büyük yeni pozisyon açmak akıllıca değil [MUHTEMEL]

---

```json
{
  "kararlar": [
    {
      "tip": "STOP_GÜNCELLE",
      "portfoy": "aggressive",
      "sembol": "MU",
      "pct": 0,
      "neden": "Hedef $470 aşıldı ($503.83), K-07 trailing stop sıkılaştırma, %21 kâr koruma",
      "hedef_fiyat": 540.0,
      "stop": 475.0,
      "tutar": 0,
      "aciliyet": "hemen",
      "dondur_al": null
    },
    {
      "tip": "STOP_GÜNCELLE",
      "portfoy": "aggressive",
      "sembol": "COHR",
      "pct": 0,
      "neden": "Hedef $330 aşıldı, K-07 trailing stop yukarı",
      "hedef_fiyat": 360.0,
      "stop": 325.0,
      "tutar": 0,
      "aciliyet": "hemen",
      "dondur_al": null
    },
    {
      "tip": "STOP_GÜNCELLE",
      "portfoy": "aggressive",
      "sembol": "ANET",
      "pct": 0,
      "neden": "Hedef $165 aşıldı ($177.94), K-07 trailing + insider satış dikkat",
      "hedef_fiyat": 190.0,
      "stop": 170.0,
      "tutar": 0,
      "aciliyet": "hemen",
      "dondur_al": null
    },
    {
      "tip": "İZLE",
      "portfoy": "balanced",
      "sembol": "CPRX",
      "pct": 0,
      "neden": "Stop %2.9 kritik, K-06 tetikte otomatik çıkış, override yasak",
      "hedef_fiyat": 28.0,
      "stop": 25.89,
      "tutar": 0,
      "aciliyet": "hemen",
      "dondur_al": null
    },
    {
      "tip": "İZLE",
      "portfoy": "dividend",
      "sembol": "O",
      "pct": 0,
      "neden": "Stop %3.1, K-06 otomatik tetik bandında",
      "hedef_fiyat": 67.0,
      "stop": 61.90,
      "tutar": 0,
      "aciliyet": "hemen",
      "dondur_al": null
    },
    {
      "tip": "İZLE",
      "portfoy": "dividend",
      "sembol": "ABBV",
      "pct
