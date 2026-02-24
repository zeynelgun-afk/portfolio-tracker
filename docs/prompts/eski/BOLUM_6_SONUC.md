# BÖLÜM 6: SONUÇ VE AKSİYON PLANI

> **amaç**: tüm bölümleri sentezle, yarının önceliklerini belirle
> **tahmini FMP call**: 0 (tüm veri önceki bölümlerden geliyor)
> **tahmini websearch**: 0

---

## ADIM 1 — GÜNÜN ÖZETİ

önceki 5 bölümden çıkan bilgileri sentezle:

```
TOPLA:
- bölüm 1'den: risk duyarlılığı, SPY trend, en önemli haber
- bölüm 2'den: portföy toplam değer/k/z, en iyi/en kötü hisse, uyarılar
- bölüm 3'ten: swing aksiyon gerektiren pozisyonlar, stop durumları
- bölüm 4'ten: yarın/bu hafta önemli earnings
- bölüm 5'ten: (sadece pazar) CANSLIM top 5 referansı
```

---

## ADIM 2 — RAPOR ÇIKTI FORMATI

```markdown
## 6. sonuç ve aksiyon planı

### günün özeti

**tarih**: [gün adı], [tarih]
**toplam portföy**: $XXX,XXX (+$XX,XXX / +%X.XX)
**günlük değişim**: [+/-$X,XXX] | SPY: [+/-%X.XX]
**risk ortamı**: [Risk-On 🟢 / Risk-Off 🔴 / Nötr ⚪]

**bir cümlede bugün**: [bugünü özetleyen tek cümle.
örnek: "tech satışına rağmen savunmacı pozisyonlar portföyü korudu,
temettü portföy +%16.6 ile liderliğini sürdürüyor"]

### portföy skor kartı

| portföy | değer | k/z % | günlük | trend | not |
|---------|-------|-------|--------|-------|-----|
| dengeli | $XXX,XXX | +%X.XX | ▲/▼ | [iyileşiyor/kötüleşiyor/stabil] | [1 kelime] |
| agresif | $XXX,XXX | -%X.XX | ▲/▼ | | |
| temettü | $XXX,XXX | +%XX.XX | ▲/▼ | | 🏆 |
| rotasyon | $XXX,XXX | +%X.XX | ▲/▼ | | |
| swing | X/10 aktif | +%X.XX ort | | | |

---

### 🔴 acil aksiyonlar (bugün/yarın yapılması gereken)

(bu bölüm boş olabilir — her gün acil aksiyon olmak zorunda değil)

1. **[AKSİYON]** — [SEMBOL] ([portföy/swing])
   - durum: [neden acil]
   - öneri: [somut aksiyon + fiyat seviyesi]
   - zamanlama: [yarın açılışta / kapanışa kadar / bu hafta]

2. ...

### 🟡 izlenmesi gerekenler (bu hafta)

1. **[SEMBOL]** — [kısa açıklama]
   - tetikleyici: [ne olursa aksiyon alınır]

2. ...

### 🟢 fırsatlar

1. **[SEMBOL]** — [kısa açıklama]
   - koşul: [hangi fiyat/RSI/olay gerçekleşirse giriş düşünülür]
   - hedef portföy: [agresif / swing / dengeli]

---

### yarının planı

**piyasa öncesi kontrol** (08:00-09:30 EST / 16:00-17:30 TR):
- [ ] [kontrol 1: örn. NEM pre-market fiyatı, stop tetiklendi mi?]
- [ ] [kontrol 2: örn. önemli earnings sonucu açıklandı mı?]
- [ ] [kontrol 3: örn. futures durumu, gap up/down riski]

**piyasa saatlerinde** (09:30-16:00 EST / 17:30-00:00 TR):
- [ ] [aksiyon 1: örn. NEM stop tetiklenirse kapat]
- [ ] [aksiyon 2: örn. SHOP $115 altına düşerse stop değerlendir]
- [ ] [aksiyon 3: varsa yeni giriş planı]

**kapanış sonrası**:
- [ ] fiyat güncellemesi + günlük rapor
- [ ] [varsa özel görev: earnings analizi, rebalance hesabı, vb.]

---

### haftalık bakış (sadece cuma raporu)

(pazartesi-perşembe raporlarında bu bölüm olmaz, sadece cuma günü ekle)

- haftanın en iyi hissesi: [SEMBOL] +%XX
- haftanın en kötü hissesi: [SEMBOL] -%XX
- haftalık toplam portföy değişimi: +/-$XX,XXX (+/-%X.XX)
- haftanın dersi: [1 cümle]
- gelecek hafta dikkat: [earnings, makro olay, teknik seviye]
```

---

## ADIM 3 — AKSİYON ÖNCELİKLENDİRME KURALLARI

```
ÖNCELİK SIRASI (yukarıdan aşağıya):

1. STOP TETİKLENEN POZİSYON      → hemen kapat, tartışma yok
2. HEDEFE ULAŞAN POZİSYON        → partial exit planını uygula
3. STOP'A ÇOK YAKIN (<%1)        → yarın açılışta karar ver
4. SÜRE AŞIMI + ZARAR            → tezi değerlendir, çıkış düşün
5. EARNINGS ÖNCESİ POZİSYON      → hedge veya küçült
6. RSI AŞIRI ALIM + BÜYÜK KAR    → kısmi kar al
7. RSI AŞIRI SATIM + GÜÇLÜ TREND → fırsat, giriş planla
8. WATCHLIST GİRİŞ KOŞULU SAĞLANDI → giriş planla
9. REBALANCE İHTİYACI             → hesapla, planla
10. YENİ ARAŞTIRMA                → not al, acele etme

her aksiyon önerisinde:
- somut fiyat seviyesi ver (sadece "izle" deme)
- hangi portföy/swing olduğunu belirt
- risk/ödül oranını hatırlat
```

---

## ADIM 4 — RAPOR SONU

```markdown
---

> rapor sonu | finzora ai | [tarih] [saat]
> sonraki güncelleme: [yarının tarihi] kapanış sonrası
```

---

## ADIM 5 — KALİTE KONTROL

- [ ] günün özeti tüm bölümlerden bilgi içeriyor mu?
- [ ] acil aksiyonlar gerçekten acil mi? (her gün acil aksiyon olmak zorunda değil)
- [ ] fırsatlar somut koşula bağlı mı? ("güzel hisse" değil, "$XX altına düşerse")
- [ ] yarının planı spesifik mi? (genel "piyasayı izle" değil)
- [ ] aksiyon önerilerinde fiyat seviyesi var mı?
- [ ] cuma günü haftalık bakış eklendi mi?
- [ ] rapor sonu satırı var mı?
