# finzora ai - instagram api kurulum rehberi

## hizli kurulum (tek komut)

```bash
cd portfolio-tracker
python scripts/instagram_setup.py
```

script seni adim adim yonlendirecek:
1. graph api explorer dan token al
2. yapistir
3. script tokeni uzatir, instagram id'ni bulur, config'i kaydeder
4. opsiyonel test paylasimi yapar

## meta app bilgileri

| alan | deger |
|------|-------|
| app id | 1521966196161302 |
| app name | claude |
| facebook sayfasi | finzora (758837067309184) |
| instagram | @zeynelgun01 |

## paylasim tipleri

```bash
python scripts/instagram_publisher.py --type piyasa
python scripts/instagram_publisher.py --type performans
python scripts/instagram_publisher.py --type egitim
python scripts/instagram_publisher.py --type telegram
python scripts/instagram_publisher.py --type piyasa --dry-run
```

## token yenileme (her 60 gunde)

```bash
python scripts/instagram_setup.py
```

## sorun giderme

### instagram_business_account bos donuyor
- instagram hesabi business/professional mi kontrol et
- instagram, finzora facebook sayfasina bagli mi kontrol et
- tokeni instagram baglandiktan sonra olustur

### content publish izni yok
- developers.facebook.com > claude > permissions and features
- instagram_content_publish aktif et
