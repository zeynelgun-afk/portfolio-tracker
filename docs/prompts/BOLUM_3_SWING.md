# BÖLÜM 3: SWING TRADE DURUMU

> **amaç**: aktif swing pozisyonların stop/hedef kontrolü, süre takibi, aksiyon kararları
> **tahmini FMP call**: ~15-20 (swing sembolleri bölüm 2'de zaten çekilmişse 0)
> **tahmini websearch**: 0-2 (sadece önemli haber varsa)

---

## ADIM 1 — VERİ TOPLAMA

swing sembollerinin çoğu bölüm 2'de zaten çekilmiş olacak.
eğer çekilmediyse (portföyde olmayan swing hisseleri):

```python
# swing'e özel semboller (portföylerde olmayan)
# mevcut: NEM, UNH, LMT, GE, DUK, DVA — hiçbiri 4 portföyde yok
# bu semboller bölüm 2'nin benzersiz listesine DAHİL EDİLMELİ
# böylece ekstra call gerekmez

# eğer bölüm 2'de dahil edilmediyse:
batch-quote → symbols=NEM,UNH,LMT,GE,DUK,DVA
# + RSI, SMA50, SMA200 (sembol başı 3 call)
```

**⚠️ optimizasyon**: bölüm 2'deki benzersiz sembol listesini oluştururken
swing aktif pozisyonlarını da dahil et. böylece bölüm 3 için ekstra call gerekmez.

---

## ADIM 2 — HER POZİSYON İÇİN KONTROL

```python
for pozisyon in aktif_pozisyonlar:
    # active.json'dan oku:
    giris_fiyati = pozisyon['giris_fiyati']
    stop_loss = pozisyon['stop_loss']
    hedef_fiyat = pozisyon['hedef_fiyat']
    giris_tarihi = pozisyon['giris_tarihi']
    
    # FMP'den gelen güncel veri:
    guncel_fiyat = fmp_quote[symbol]['price']
    rsi = fmp_rsi[symbol]
    
    # hesaplamalar:
    kar_zarar_pct = ((guncel_fiyat - giris_fiyati) / giris_fiyati) * 100
    stop_mesafe = guncel_fiyat - stop_loss
    stop_mesafe_pct = (stop_mesafe / guncel_fiyat) * 100
    hedef_mesafe = hedef_fiyat - guncel_fiyat
    hedef_mesafe_pct = (hedef_mesafe / guncel_fiyat) * 100
    tutulan_gun = (bugun - giris_tarihi).days
    # max süre sınırı yok, tavsiye 7-10 gün
```

---

## ADIM 3 — UYARI VE AKSİYON KURALLARI

```
STOP-LOSS KONTROL:
  fiyat ≤ stop_loss                    → 🔴 STOP TETİKLENDİ — pozisyonu kapat
  stop mesafe < %1 (veya < $1.50)      → 🔴 STOP ÇOK YAKIN — yarın açılışta karar ver
  stop mesafe %1-%3                    → 🟡 stop yakın, izle
  stop mesafe > %3                     → 🟢 güvenli

HEDEF KONTROL:
  fiyat ≥ hedef_fiyat                  → 🎯 HEDEFE ULAŞTI — partial exit planını uygula
  hedef mesafe < %2                    → 🟢 hedefe yakın, trailing stop sıkılaştır
  hedef mesafe %2-%5                   → normal, bekle

SÜRE TAKİBİ (zorunlu değil, bilgilendirme):
  tutulan_gun > 14                     → ℹ️ uzun süredir tutuluyor, tezi yeniden değerlendir
  tutulan_gun > 10                     → ℹ️ tavsiye süre aşıldı (7-10 gün)
  tutulan_gun ≤ 10                     → normal

RSI KONTROL (swing özel):
  RSI > 75 + kar > %5                  → momentum aşırı, kısmi kar al
  RSI < 30 + zarar > %3               → zayıflık devam, stop sıkılaştır

BİLEŞİK AKSİYON KARARLARI:
  stop yakın + zarar büyüyor           → "güçlü çıkış sinyali, yarın kapat"
  hedefe yakın + RSI > 65              → "partial exit: %50 sat, kalan trailing stop"
  zarar > %3 + tutulan > 10 gün       → "tez çalışmıyor, çıkış düşün"
  kar > %7 + süre < 5 gün             → "erken hedef, trailing stop ile kal"
```

---

## ADIM 4 — TRAİLİNG STOP GÜNCELLEME

```
trailing stop kuralı (her pozisyon için):

eğer pozisyon karda ve zirve yaptıysa:
  yeni_trailing_stop = zirve_fiyat × 0.95  (zirveden -%5)
  
  eğer yeni_trailing_stop > mevcut_stop_loss:
    stop_loss = yeni_trailing_stop  ← GÜNCELLE (active.json'da)
    durum notu ekle: "trailing stop yükseltildi: $XX.XX → $YY.YY"
  
  eğer yeni_trailing_stop ≤ mevcut_stop_loss:
    değişiklik yapma (stop sadece yukarı hareket eder)

zirve tespiti:
  son 5 günün en yüksek fiyatı (FMP historical-price-eod/light ile)
  veya batch-quote'taki dayHigh değerini izle
```

---

## ADIM 5 — RAPOR ÇIKTI FORMATI

```markdown
## 3. swing trade durumu

**aktif: X/10 slot | ortalama k/z: +%X.XX | boş slot: X**

### pozisyon tablosu

| id | sembol | giriş | güncel | k/z % | gün | stop | stop mesafe | hedef | hedef mesafe | RSI | durum |
|----|--------|-------|--------|-------|-----|------|-------------|-------|-------------|-----|-------|
| 010 | NEM | $118.12 | $124.25 | +5.19% | 12 | $122.50 | $1.75 (1.4%) | $129.93 | $5.68 (4.6%) | XX | 🔴/🟡/🟢 |
| ... | | | | | | | | | | | | |

### aksiyon gerektiren pozisyonlar

(sadece uyarı olan pozisyonları listele, her biri için somut öneri)

🔴 **acil aksiyon:**
- **[SEMBOL]** (SWING-XXX) — [durum açıklaması]
  - **öneri**: [somut aksiyon: kapat / trailing stop güncelle / partial exit]
  - **gerekçe**: [neden bu aksiyonu öneriyorsun]

🟡 **izlenmesi gereken:**
- **[SEMBOL]** (SWING-XXX) — [durum]
  - yarın dikkat: [ne olursa aksiyon alınır]

🟢 **iyi giden:**
- **[SEMBOL]** (SWING-XXX) — [kısa durum notu]

### trailing stop güncellemeleri

(bugün güncellenen stop'lar varsa listele)
| sembol | eski stop | yeni stop | sebep |
|--------|-----------|-----------|-------|

### watchlist'ten fırsat

(data/swing/watchlist.json'dan urgency="high" olanları kontrol et)
- **[SEMBOL]** — hedef giriş: $XX-XX, güncel: $XX.XX, [giriş koşulu sağlandı mı?]

### swing istatistik

| metrik | değer |
|--------|-------|
| aktif pozisyon | X/10 |
| ortalama k/z | +%X.XX |
| en iyi | SEMBOL +%X.XX |
| en kötü | SEMBOL -%X.XX |
| stop tetiklenen (bugün) | X adet |
| hedefe ulaşan (bugün) | X adet |
| ortalama tutma süresi | X gün |
```

---

## ADIM 6 — JSON GÜNCELLEME

rapor yazıldıktan sonra `data/swing/active.json` güncelle:
1. `guncel_fiyat` → FMP'den gelen fiyat
2. `guncel_kar_zarar_yuzde` → yeniden hesapla
3. `tutulan_gun` → bugüne göre güncelle
4. `stop_loss` → trailing stop değiştiyse güncelle
5. `durum` → güncel durum metni
6. `son_guncelleme` → datetime.now().isoformat()

eğer stop tetiklendiyse:
1. pozisyonu `active.json`'dan kaldır
2. `closed.json`'a taşı (tüm zorunlu alanlarla: cikis_tarihi, cikis_fiyati, sonuc, ders)
3. `data/transactions.csv`'ye SELL satırı ekle
4. git commit: `[SWING-ÇIKIŞ] SEMBOL @FİYAT - Stop tetiklendi / Hedefe ulaştı`

---

## ADIM 7 — KALİTE KONTROL

- [ ] tüm aktif pozisyonların fiyatı güncellendi mi?
- [ ] stop mesafe hesaplamaları doğru mu?
- [ ] 15 gün kuralını aşan pozisyon var mı?
- [ ] trailing stop sadece yukarı mı hareket etti? (aşağı çekilmediyse OK)
- [ ] stop tetiklenen pozisyon closed.json'a taşındı mı?
- [ ] watchlist'teki high urgency adaylar kontrol edildi mi?
- [ ] swing istatistik (ortalama, en iyi, en kötü) doğru mu?
