# AGRESİF PORTFÖY STRATEJİSİ — AI TEDARİK ZİNCİRİ TEMATİK

> **sermaye**: $400,000
> **hedef**: yıllık %30+ getiri
> **max pozisyon**: 6
> **stop sistemi**: 2x ATR(14) trailing
> **son güncelleme**: 25 mart 2026

---

## FELSEFE

agresif portföy AI tedarik zinciri tematik yatırım stratejisi izler. NVIDIA herkesin bildiği katman. ama çipi üretmek için ekipman, kimyasal, gaz, wafer, soğutma, trafo, bakır, optik fiber lazım. bu alt katmanlar daha az kalabalık, daha ucuz ve AI büyümesinden doğrudan faydalanıyor.

**temel prensip**: "AI çip şirketi al" değil, "çipin üretilmesi için gereken her şeyi al"

claude proaktif düşünür: haberleri okur, sektörel trendleri saptar, tedarik zinciri katmanlarını tarar, uygun setup'a giriş yapar. zeynel'in söylemesini beklemez, watchlist'e ekleyip beklemez.

---

## AI TEDARİK ZİNCİRİ KATMANLARI

```
çip tasarımı:       NVDA, AMD, MRVL, AVGO, CRDO
çip ekipmanı:       ASML, AMAT, LRCX, KLAC, CAMT, ONTO
kimya/malzeme:      ENTG, MKSI, PLAB, CCMP, LIN, APD
optik bağlantı:     COHR, LITE, GLW, AAOI
güç altyapısı:      POWL, VRT, ETN, PWR, GNRC
soğutma/termal:     VRT, TT, JCI
veri merkezi REIT:  DLR, EQIX
enerji:             COP, XOM, CVX
nadir toprak:       MP, FCX, BHP
```

her sabah ve seans içinde bu katmanlar taranır. haber/earnings/kontrat duyurusu hangi katmanı etkiliyorsa o katman derinlemesine araştırılır.

---

## GİRİŞ KURALLARI

iki giriş tipi var:

### A) sinyal girişi (ideal)
1. ichimoku giriş sinyali var (kumo kırılımı veya kijun bounce)
2. hacim teyidi (en az 1.0x ortalama, ideal 1.2x+)
3. SMA200 üstünde
4. claude temel değerlendirmesi olumlu
→ tam veya yarım pozisyon (VIX'e göre)

### B) trend devam girişi (güçlü trend varken)
1. ichimoku 4/4 güçlü yükseliş (kumo üstü + tenkan>kijun + chikou pozitif + yeşil kumo)
2. OBV yükseliş (alıcılar aktif)
3. stop mesafesi >%5 (2x ATR uygun)
4. SMA200 üstünde
→ yarım pozisyon (spesifik sinyal yok ama trend güçlü)
→ sinyal gelince tamamla

### ortak koşullar
- K-13 v4.1 sektör bazlı VIX (faydalanıcı/duyarlı matris — detay: docs/TRADING_PLAYBOOK.md)
- 2x ATR(14) bazlı stop ve pozisyon boyutlandırma
- aynı alt sektörde 3'ten fazla pozisyon yok

---

## STOP SİSTEMİ — 2x ATR(14) TRAİLİNG

sabit yüzde stop kaldırıldı. her hissenin volatilitesine uygun dinamik stop:

```
stop = güncel fiyat - (2 x ATR(14))
```

**kurallar**:
- stop sadece yukarı güncellenir (aşağı çekilmez)
- her seans sonunda ATR yeniden hesaplanır
- fiyat yükseldikçe stop otomatik yükselir
- stop override yok (K-06)

---

## POZİSYON YÖNETİMİ

| kural | değer |
|-------|-------|
| max pozisyon | 6 |
| pozisyon büyüklüğü | $20K-$70K (yarım: $20K, tam: $40-70K) |
| nakit hedefi | %20-30 |
| tek sektör max | %50 |

**zayıfı kes, kazananı büyüt**: düşük performanslı pozisyonlar satılır, güçlü performans gösterenler büyütülür. "bekle düzelir" yaklaşımı yok.

---

## ÇIKIŞ KRİTERLERİ

1. **stop tetiklendi**: 2x ATR(14) altına kapanış → hemen sat
2. **tez bozuldu**: temel verilerde kötüleşme (earnings miss, guidance düşürme)
3. **daha iyi fırsat**: aynı katmanda daha güçlü alternatif çıktı → değiştir
4. **tema zayıfladı**: tema güç skoru 4/10 altına düştü → ağırlık azalt
5. **sektör yoğunlaşması**: tek sektör %50'yi aştı → en zayıfı sat

---

## PİYASA İSTİHBARATI ENTEGRASYONU

agresif portföy piyasa istihbarat sistemini (docs/MARKET_INTELLIGENCE.md) aktif kullanır:

- her haberin neden-sonuç zinciri (1./2./3. derece etki)
- birinci derece zaten fiyatlanmış olabilir, ikinci/üçüncü derecede alfa var
- tema güç skorları portföy ağırlıklarını belirler
- senaryo planlaması (FOMC, earnings, jeopolitik) önceden pozisyonlanma sağlar

---

*finzora ai | agresif portföy strateji v2.0 | 25 mart 2026*
