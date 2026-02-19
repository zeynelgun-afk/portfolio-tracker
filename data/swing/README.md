# 📊 SWING TRADE SİSTEMİ

Bu klasör swing trade simülasyonunun tüm verilerini içerir.

## 📁 Dosya Yapısı

### `active.json` - Aktif Pozisyonlar
Şu anda açık olan swing pozisyonları. Her pozisyon için:
- Giriş fiyatı, tarih
- Güncel fiyat, K/Z %
- Hedef ve stop seviyeleri
- Giriş nedeni, tez, katalızör
- Risk faktörleri
- Durum notları

**Format:** Türkçe JSON

### `closed.json` - Kapatılmış Pozisyonlar
Tamamlanmış trade'ler ve istatistikler. İçerir:
- Tüm kapatılmış pozisyonlar
- Giriş/çıkış fiyatları ve tarihleri
- K/Z % ve tutulan gün
- Çıkış nedeni ve öğrenilen dersler
- Genel istatistikler (kazanma oranı, ortalama, vb.)

**Format:** Türkçe JSON

### `watchlist.json` - İzleme Listesi
Potansiyel swing adayları ve hariç tutulanlar.
- Aday hisseler (momentum, sektör, notlar)
- Hariç tutulanlar ve nedenleri

**Format:** Türkçe JSON

### `OZET_XX_SUBAT.md` - Periyodik Özet Raporlar
Kapsamlı özet raporlar (haftalık/aylık):
- Aktif pozisyonlar tablosu
- Kapatılan pozisyonlar özeti
- Performans istatistikleri
- Öğrenilen dersler
- Sektör dağılımı
- Tez örnekleri
- Sonraki adımlar

**Format:** Türkçe Markdown

### `DERSLER_SABLON.md` - Ders Çıkarma Şablonu
Her kapatılan pozisyon için detaylı analiz şablonu.

**Format:** Türkçe Markdown

## 🎯 Swing Trade Kuralları

### Giriş Kriterleri:
- Minimum momentum: +5% (5 gün)
- R:R oranı: Minimum 2:1
- Max pozisyon: 10 eşzamanlı
- Sektör çeşitlendirmesi zorunlu

### Çıkış Kriterleri:
- **Target hit:** +10% → Hemen sat
- **Stop-loss hit:** -5% → Hemen kes
- **Zaman çerçevesi:** 10+ gün → Değerlendir
- **Trailing stop:** +5% karlı → Break-even'e çek

### Zaman Çerçevesi:
- Hedef: 7-10 gün
- Maximum: 12-15 gün
- 10+ gün → Action item

### Günlük Rutin (Her İşlem Günü):
1. ✅ Fiyatları güncelle
2. ✅ Stop/target kontrol et
3. ✅ Timeframe kontrol et
4. ✅ Action items uygula

## 📈 Performans Hedefleri

- **Kazanma Oranı:** >60%
- **Ortalama Kazanç:** >+8%
- **Ortalama Kayıp:** <-6%
- **Risk/Ödül:** >2:1

## 🔄 Güncelleme Sıklığı

- **active.json:** Her işlem günü (fiyat güncellemesi)
- **closed.json:** Pozisyon kapatıldığında
- **watchlist.json:** Haftalık veya yeni aday çıktığında
- **Özet raporlar:** Haftalık veya büyük değişikliklerde

## 📚 Daha Fazla Bilgi

Ana portfolyo bilgileri için `/data/portfolios/` klasörüne bakın.

---

**Son Güncelleme:** 18 Şubat 2026  
**Dil:** Türkçe
