# K-Kurallari Backtest Dersleri — 28 Nis 2026

189 islem, 41 farkli gun, 2 ayda toplanan veri. Her K-kuralinin gercek getirisi olculdu.

## Ozet Tablo

| Kural | Sayi | 5g | 20g | Karar |
|---|---|---|---|---|
| K-06 stop | 16 | -1.79% | +5.86% | Marjinal — short-term dogru, long-term yumusatilabilir |
| K-05 earnings | 7 | **-5.12%** | **-8.68%** | **GUCLU — kurali genislet** |
| K-09 trailing | 3 | +3.25% | +2.22% | Az veri |
| K-11 RSI partial | 16 | +2.30% | -3.52% | Marjinal — kismi cikis stratejisi dogru |
| Swing-Giris | 17 | -0.76% | -11.03% | **ZAYIF — filtre sikilastirmali** |
| Tema alis | 8 | +7.45% | -0.86% | **MUKEMMEL — 5-10g'de cik** |

## Onemli Bulgular

### 1. K-05 (earnings oncesi cikis) — KURALI GENISLET
7 satistan 5 gun sonra ortalama **-5.12%**, 20 gun sonra **-8.68%**.
Earnings oncesi cikis disiplini gercekten kayip onluyor. Mevcut kural T-2
(2 gun once) zorunlu cikis. Gelecekte test edilebilir:
- T-3 (3 gun once) zorunlu cikis daha guvenli mi?
- Earnings beat/miss gecmisine gore kural esnetilebilir mi?

### 2. K-11 (RSI 70+ kismi kar al) — DOGRU AMA TIMING DARLASTIRILMALI
16 satistan 5 gun sonra +2.30% (yani devam etmis), 20 gun sonra -3.52%.
Bu pattern: K-11 kismi (genelde %25-30) cikis stratejisi tamamen dogru.
%75 pozisyon devam ettigi icin yukselen momentum yakalaniyor, %25 kar
kilitli. Mevcut kural saglam.

Ozel durum: SM stock'unda 5 farkli K-11 satisi yapilmis, her seferinde
kismi cikis. 5g sonra +%8-10 yukselse de 20g'de duzeltme yapip toparladi.
Sistem dogru calistigini gosteriyor.

### 3. Swing-Giris filtresi — ZAYIF
17 girisin 20g sonra ortalama **-11.03%** ile kapaniyor. Sinyal turune
gore performans:

- **tenkan_bounce (4)**: +8.23% 10g — IYI sinyal
- **ichimoku (2)**: +7.90% 10g — IYI sinyal
- **oversold_bounce (3)**: +2.77% 5g, -6.28% 20g — Kisa vadeli
- **diger (4)**: -4.87% 20g — KOTU (kriz rallisi alimlari)

**KRIZ RALLISI ALIMLARI HATALI** — 2 Mart Iran krizi gunu HAL/KTOS/CEG
alimlarinin 20g sonra ortalama -%11. Memory'deki "wait >=1 day + RSI
confirmation" dersi gerçek veriyle dogrulandi. KTOS 20g sonra -32.3%!

### 4. Tema alis — MUKEMMEL AMA CIKIS GEREK
8 alimda 5g sonra +7.45%, 10g sonra +6.39%, 20g sonra -0.86%. Yani
**5-10. gun arasi pik yapip duzelyor**. Bu kural hizla uygulanmali:
mevcut tutus suresi (15-20g) cok uzun. Onerim:
- Tema alimlarinin 10. gunu **otomatik kar kilidi** (mevcut +5% gibi)
- 15. gun zorunlu cikis (su an yok, eklensin)

## Sistem Onerileri (Veri Bazli)

1. **Crisis rally chase yasagi** (K-yeni): Iran/savas/buyuk haber gunu
   alim YOK. Sadece T+1 ve sonrasi, RSI<35 + ichimoku 3/4 ile.
   Tahmini etki: KTOS, HAL, CEG gibi -%32'ye kadar dusen pozisyonlar
   hic acilmazdi.

2. **Tema alis 15g zorunlu cikis** (K-15c): Tema-bazli alimlarda 15.
   gunde otomatik tam cikis. Mevcut sistemde sadece K-06 stop ve
   K-11 RSI ile cikiyor; tema thesis'i 10. gunde ortaya cikiyor.

3. **K-06 ATR stopu gevsetme** (mevcut sistem ATR×1.5):
   - VRT, COHR, MRVL gibi 5 vakada ATR×%0.08 ile stop yendi
   - 20g sonra +%28, +%30, +%47 yukseldi
   - Belki ATR×2.0 daha iyi olurdu, ama POWL (-65%) ve CELH (-34%)
     vakalarinda hizli stop sart

4. **oversold_bounce sinyalini disable et veya ek filtre ekle**:
   3 alimdan 2'si 20g sonra negatif. Bu sinyal kuvvetli degil.

