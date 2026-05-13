# K-24 VCP Detector — Prototip Notu (13 May 2026)

## Bağlam
Tarık Taha Karagöz'ün paylaştığı Bora Hora swing analiz skili VCP (Volatility Contraction Pattern) odaklı. Skill ayrı bir dosya olarak değil, mevcut K-kural sistemine **K-24** olarak entegre edildi.

## Karar Gerekçesi
- Ayrı skill yapsaydık: 2 paralel swing karar yöntemi → karar matrisi bulanıklaşır
- K-24 olarak: Mevcut Ichimoku 4/4 + K-19/K-20 zincirinin sonuna kalite filtresi olarak ekleniyor

## Algoritmanın 5 Bileşeni
1. **Zigzag pivot tespiti**: %3+ swing'leri yakala (gürültü altı görmezden)
2. **Kontraksiyon çıkarımı**: H→L→H→L… dizisindeki her düşüş = 1 kontraksiyon
3. **VCP zinciri**: SON kontraksyondan geriye doğru, derinlik arttığı an dur. Bu "ardışık daralan zincir" gerçek VCP.
4. **Hacim kuruması**: Her kontraksyonun ortalama hacmi öncekinden düşük mü?
5. **Pivot yakınlığı + setup-bozuldu güvenliği**: Pivot'tan %5+ aşağıda olmak STRONG'u engeller

## Skor Bileşenleri (toplam 100)
| Bileşen | Puan | Şart |
|---|---|---|
| Zincir uzunluğu | 30 | 3+ ardışık daralan |
| Zincir uzunluğu (min) | 18 | 2 ardışık daralan |
| Daralma sırası | 25 | Zincir varsa otomatik |
| Hacim kuruması | 20 | Her zincirde azalma |
| Hacim (kısmi) | 10 | Sadece son düşük |
| Pivot yakın | 15 | abs(uzaklık) ≤ %3 |
| Pivot kırıldı | 8 | +%3 ile +%10 arası |
| Trend (SMA50>SMA200) | 10 | Stage 2 ön koşul |

## Karar Eşikleri
- **STRONG** (≥70): Tam pozisyon ($8-10K)
- **WEAK** (40-69): Yarım pozisyon ($5K) veya izleme
- **NONE** (<40): Giriş YOK

Güvenlik: Pivot'tan %5+ aşağıda → STRONG verilmez (max WEAK)

## Watchlist Test Sonuçları (13 May 2026)
| Ticker | Status | Skor | Pivot | Uzaklık | Yorum |
|---|---|---|---|---|---|
| CAT | WEAK | 68 | $931 | -2.06% | Pivot yakın, zincir kısa |
| LMT | WEAK | 75 | $636 | -18.19% | Zincir güçlü ama setup bozuk |
| MRK | WEAK | 75 | $124 | -9.38% | Zincir güçlü ama setup bozuk |
| NVDA | WEAK | 45 | $216 | +1.82% | Pivot yakın, zincir yok |
| WDC, KLAC, AMAT, MU, AAPL, PLTR | NONE | 30-35 | — | — | VCP yapısı yok |

**STRONG çıkan yok** — bu beklenen davranış. Minervini'nin kendisi haftada 1-2 STRONG VCP bulur. Yalancı pozitif üretmiyor olmamız iyi işaret.

## Sonraki Adımlar
1. **Backtest** (kritik öncelik): Son 6 ay swing trade'lerinde (active + closed.json) VCP ✅ olanların ortalama getiri farkını ölç. K-19/K-20 standart kurallarına +%2+ avantaj sağlıyorsa K-24 kalıcı hale gelir.
2. **Sabah swing taraması entegrasyonu**: `opportunity_finder.py`'ye `vcp_score` alanı ekle, watchlist raporuna kolon ekle
3. **Yarım pozisyon mekaniği**: K-24 WEAK durumunda `execution_engine.py` poz boyutunu otomatik 0.5x'le

## Bilinen Sınırlamalar
- `%3 min swing` sabit: çok volatil hisselerde (PLTR gibi) çok fazla pivot üretir, az volatil hisselerde (KO gibi) yetersiz olabilir. ATR-bazlı dinamik eşik gerekebilir.
- "Pivot" tanımı basit: zincirdeki en yüksek peak. Gerçek Minervini "the tightest point" kullanır — son kontraksyon peak'i daha doğru olabilir.
- Hacim kuruması binary (azaldı/azalmadı). Yüzdesel ağırlık daha kalibre olur.

## Dosyalar
- `agent/vcp_detector.py` — algoritma
- `docs/K_RULES_QUICK_REF.md` — K-24 tablo + detay bölümleri
- `notes/2026-05-13_K24_VCP_DETECTOR.md` — bu dosya

## Onay Bekleyen
- Backtest çalıştırma onayı
- WEAK durumunda yarım pozisyon mekaniği onayı
- Sabah swing taramasına entegrasyon onayı
