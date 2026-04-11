# Finzora AI — Episodik Bellek Sistemi (Katman 1)

## Nedir?

Her kapanan trade'den ders çıkaran ve yeni kararları bu derslerle besleyen bellek katmanı.
Sistem, geçmiş trade'leri vektör uzayında saklayarak benzer setup'larda tarihsel bağlamı
otomatik olarak sunuyor.

## Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `scripts/trade_memory.py` | Ana bellek motoru (indeksleme, sorgulama, TF-IDF) |
| `scripts/memory_update.py` | Güncelleme kontrolü ve prompt enjeksiyonu |
| `data/episodic_memory/trade_index.json` | Trade metadatası ve metin indeksi |
| `data/episodic_memory/tfidf_vectors.json` | TF-IDF vektörleri ve IDF ağırlıkları |

## Kullanım

### Bellekleri güncelle (her kapanan trade sonrası)

```bash
python3 scripts/trade_memory.py --rebuild
```

### Benzer geçmiş trade'leri sorgula

```bash
python3 scripts/trade_memory.py --query "teknoloji momentum breakout RSI"
python3 scripts/trade_memory.py --query "enerji stop loss savunma"
python3 scripts/trade_memory.py --query-trade SWING-020  # Belirli trade'e benzerler
```

### İstatistik raporu

```bash
python3 scripts/trade_memory.py --stats
```

### Sabah brifing bağlamı (PART 1 SABAH promptuna ekle)

```bash
python3 scripts/memory_update.py --morning
```

### Yeni trade adayı için bağlam

```bash
python3 scripts/memory_update.py --setup "NVDA breakout RSI 68 AI sektör güçlü"
```

## Python Entegrasyonu

Sabah ve seans promptlarına aşağıdaki şekilde enjekte et:

```python
from scripts.trade_memory import get_memory_for_prompt

# Swing taramada her aday için:
memory_context = get_memory_for_prompt(
    f"{sembol} {tarama_yontemi} {sektor} {rsi_durumu}",
    top_k=4
)
# memory_context'i Claude promptuna ekle
```

## Nasıl Çalışır?

1. **Trade → Metin**: Her kapanan trade, anlamlı bir metin belgesine çevrilir.
   Sektör, sonuç, PnL sınıfı, giriş tezi, ders dahildir.

2. **TF-IDF Vektörleme**: Her belge matematiksel bir vektöre dönüştürülür.
   İnsan dilindeki benzerliği yakalayan bu yöntem küçük veri setleri için idealdir.

3. **Kosinüs Benzerliği**: Yeni sorgu da vektöre çevrilir, tüm geçmiş trade'lerle
   karşılaştırılır, en benzer olanlar sıralanır.

4. **Prompt Enjeksiyonu**: Sonuçlar Claude'a bağlam olarak sunulur:
   - Benzer başarılı setup'lar → güven verisi
   - Benzer başarısız setup'lar → uyarı sinyali

## Otomasyon

`closed.json` her güncellendiğinde indeks otomatik yenilenir:

```bash
# Crontab veya post-commit hook'a ekle:
python3 scripts/memory_update.py  # Gerekirse günceller, yoksa atlar
```

## Gelecek Geliştirmeler

- [ ] Portföy trade'lerini (transactions.csv) de indekse ekle
- [ ] Sektör bazlı filtreleme (`--query "..." --sector teknoloji`)
- [ ] Tarih ağırlıklaması (eski trade'ler daha az ağırlık alır)
- [ ] Piyasa rejimi etiketleme (her trade için VIX ve SPY durumu)
