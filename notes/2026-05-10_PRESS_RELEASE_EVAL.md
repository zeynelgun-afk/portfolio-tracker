# Press Release Pipeline Değerlendirmesi — 10 Mayıs 2026

**Tarih:** 10 Mayıs 2026 (Cumartesi)
**Kapsam:** `bilanco-sonrasi-us` skill'inde 8-K SEC.gov direct fetch yerine `news/press-releases` kullanımının değerlendirilmesi
**Bağlam:** 10 Mayıs FMP audit Aksiyon 3
**Kaynak:** finzora ai

---

## 1. Yönetici Özeti

`bilanco-sonrasi-us` skill'i şu an `sec-filings-search` + SEC.gov direct fetch yolu ile 8-K Exhibit 99.1 press release'lerini çekip guidance phrase analizi yapıyor. FMP `news/press-releases` endpoint'inin alternatif olarak kullanılması düşünüldü. Canlı karşılaştırmalı test sonucu net: **mevcut SEC.gov akışı korunmalı**, içerik kapsamı `news/press-releases`'den belirgin şekilde üstün.

Test sırasında bonus bir bulgu çıktı: `news/press-releases` parametresi `?symbols=` (çoğul) ZORUNLU, tekil `?symbol=` parametresi sessizce IGNORE ediliyor. Bu durum 10 Mayıs sabahki audit testimde fark edilmemişti çünkü AAPL ile test edilmiş, AAPL "latest press releases" listesinde zaten vardı. Skill ve memory düzeltildi.

`news/press-releases` mevcut akışı değiştirmek için yeterli değil ama hızlı triage (öneleme) için yardımcı katman olarak değerli — özellikle bir tickere ait Q1 2026 bilanço press release'inin yayınlanıp yayınlanmadığının hızlıca teyidi için.

---

## 2. Mevcut Akış (`bilanco-sonrasi-us` Aşama 4d)

`skills/bilanco-sonrasi-us/scripts/04_post_earnings_signals.py` içindeki `press_release_signal()` fonksiyonu şu adımları izliyor:

1. FMP `sec-filings-search/symbol?symbol=X&from=...&to=...` ile bilanço tarihinden ±2 gün içindeki SEC dosyalarının metadata listesi çekilir
2. `formType in ("8-K", "6-K")` filtresi ile press release filing'i bulunur
3. `finalLink` alanından SEC.gov URL alınır (genelde `tem-ex99_1.htm` formatı, Exhibit 99.1 = press release)
4. `fetch_sec_url()` ile SEC.gov'a doğrudan HTTP GET (User-Agent zorunlu, fair-access policy)
5. `strip_html()` ile HTML temizlenir
6. Phrase analizi (transcript ile aynı RAISED/LOWERED/REAFFIRMED listesi)

### Avantajlar

- **Tam metin erişimi**: 8-K Exhibit 99.1 tipik 10,000-30,000 karakter (TEM 5 May örneği 29,700 char)
- **Resmi SEC kaynak**: Filing yönetmelikle düzenlenmiş, "official press release" statüsü
- **Foreign issuer desteği**: 6-K ABD dışı ihraççılar için (ARGX, NVO, AZN gibi) — SEC sisteminde yer alır
- **Bilanço gününde mevcut**: Transcript 12-48 saat gecikebilir, 8-K bilanço açıklamasıyla eş zamanlı dosyalanır

### Dezavantajlar

- **SEC.gov fair-access**: Container datacenter IP'lerinden bazen 403 dönüyor (Anthropic environment'ında userMemories notu var: "SEC.gov fetch ÇÖZÜLDÜ User-Agent fair-access 200 OK"). Yine de saatlik bir nadir başarısızlık olabilir.
- **2 ayrı API çağrısı**: FMP metadata (1) + SEC.gov fetch (2) → toplam latency 2-4 saniye
- **HTML parse karmaşıklığı**: Her şirket farklı HTML yapısı, `strip_html()` regex'leri zaman içinde edge case alıyor
- **Hata yüzeyi geniş**: `filings_yok`, `8-K/6-K_yok`, `link_yok`, `sec_fetch_basarisiz`, `icerik_cok_kisa` (5 farklı hata türü)

---

## 3. Alternatif: `news/press-releases`

### 3.1 Endpoint davranışı (canlı test)

**KRİTİK PARAMETRE TUZAĞI**: `?symbol=` (tekil) ZORUNLU değil, sessizce IGNORE ediliyor. Doğru kullanım `?symbols=` (çoğul).

| Test | Param Formu | Sonuç |
|------|-------------|-------|
| `?symbol=VST` | tekil | 200 OK ama dönen 10 PR'ın **tümü AAPL** (filtre uygulanmadı, generic latest döndü) |
| `?symbols=VST` | çoğul | 200 OK, gerçek VST press release'leri filtreli |
| `?symbols=VST,CON,CELH` | multi-çoğul | 200 OK, tek call'da 3 ticker (VST 7 PR, CON 5 PR, CELH 3 PR) |

**İlk audit testinde nasıl yakalanmadı**: `?symbol=AAPL` testi yapıldı. AAPL'ın latest press release'lerinde zaten Apple vardı, filtre çalışmamış olsa da AAPL döndü. VST gibi düşük PR yoğunluklu ticker test edildiğinde tuzak görünür hale geldi.

### 3.2 Dönen alanlar (test verisi)

```json
{
  "symbol": "VST",
  "publishedDate": "2026-05-07 07:00:00",
  "publisher": "Business Wire",
  "title": "Vistra Reports First Quarter 2026 Results",
  "image": "https://images.financialmodelingprep.com/news/...",
  "site": "businesswire.com",
  "text": "VST 1Q 2026 Net Income from Ongoing Operations of $... [532 karakter]",
  "url": "https://www.businesswire.com/news/home/.../"
}
```

`text` alanı press release'in **özeti**, tam metin değil. Tipik uzunluk 500-1,500 karakter. Tam metin için `url` (businesswire / prnewswire / globenewswire) ayrı fetch edilmeli.

### 3.3 İçerik karşılaştırması

| Kaynak | Tipik uzunluk | Guidance phrase analizi için yeterli mi? |
|--------|---------------|-------------------------------------------|
| 8-K Exhibit 99.1 (SEC.gov fetch) | 10,000 - 30,000 char | EVET — tam metin, finansal detaylar, guidance bölümleri eksiksiz |
| `news/press-releases` `text` alanı | 500 - 1,500 char | KISMEN — başlık + ilk paragraf düzeyi. "Reports First Quarter 2026 Results" başlığı ile bilanço PR'ı tespit edilir ama detaylı RAISED/LOWERED/REAFFIRMED ayrımı için yetersiz |
| `news/press-releases` `url` → fetch | Aynı 8-K Ex99.1 (genelde) | EVET — businesswire/prnewswire 8-K Ex99.1'in dış yayınladığı versiyonu, içerik aynı |

`text` alanı sadece özet olduğu için derinlemesine guidance phrase analizi için yeterli değil. Mevcut SEC.gov akışını değiştirmek bu açıdan **net bir gerileme** olur.

---

## 4. Karar ve Öneri

### 4.1 Mevcut SEC.gov akışı korunmalı

Aşağıdaki nedenlerle değişiklik önerilmiyor:

1. **İçerik kapsamı**: 8-K Exhibit 99.1 tam metin, `news/press-releases` `text` özet. Guidance analizi için tam metin gerekli.
2. **Foreign issuer**: 6-K dosyaları SEC üzerinden alınıyor; `news/press-releases` foreign issuer kapsamı belirsiz (test edilmedi).
3. **Çalışıyor**: userMemories'de "SEC.gov fetch ÇÖZÜLDÜ User-Agent fair-access 200 OK" notu var, mevcut akış stabil.
4. **TEM örneği başarılı**: 5 May 2026 TEM bilançosunda transcript + 8-K çift teyit ile RAISED sinyali yakalandı (29,700 char), bu detay seviyesi `text` özet alanında imkansız.

### 4.2 `news/press-releases` yardımcı katman olarak eklenebilir

Mevcut akış değişmesin, ancak `news/press-releases` aşağıdaki üç senaryo için yardımcı olarak eklenmesi DEĞER katar:

#### Senaryo A: Bilanço PR yayınlanmış mı? (hızlı triage)

Aşama 4d başında `news/press-releases?symbols=X` çağrılır, bilanço dönemi tarihinde "First Quarter 2026 Results" / "Q1 Earnings" tipi başlık var mı kontrol edilir. Yoksa SEC fetch'e hiç gerek kalmaz, doğrudan `available=False, reason="bilanco_PR_yok"` döner. Bu, küçük şirketler veya geç dosyalama yapan ticker'lar için hatalı `sec-filings-search` fetch'lerini önler.

```python
def has_earnings_pr(symbol, earn_date_str):
    """Hızlı triage: bilanço dönemi PR yayınlanmış mı?"""
    prs = fmp_get("news/press-releases", {"symbols": symbol, "limit": 20})
    if not prs:
        return False
    earn_d = datetime.strptime(earn_date_str, "%Y-%m-%d").date()
    earnings_keywords = ["earnings", "quarter", "results", "reports first", 
                         "reports second", "reports third", "reports fourth"]
    for pr in prs:
        pr_date = datetime.strptime(pr["publishedDate"][:10], "%Y-%m-%d").date()
        if abs((pr_date - earn_d).days) <= 2:
            title_lower = pr["title"].lower()
            if any(k in title_lower for k in earnings_keywords):
                return True
    return False
```

#### Senaryo B: Multi-ticker batch tarama

50 hisse için tek call'da press release listesi çekmek (Aşama 1 sonrası `01_filtered_midcap.json` genelde 150-300 hisse içeriyor, 5-6 batch'le 100% kapsam). Bu, "hangi hisseler bu hafta bilanço PR'ı yayınladı" sorusunu hızlıca cevaplar.

```python
# 30 ticker'lık batch
batch = "VST,CON,CELH,TEM,BILL,FIS,..."  # 30 ticker
prs = fmp_get("news/press-releases", {"symbols": batch, "limit": 200})
# Sonra symbol'a göre group ve filter
```

#### Senaryo C: SEC.gov 403 fallback

SEC.gov fetch fair-access policy 403 dönerse, `news/press-releases` `url` alanı businesswire/prnewswire'dan içerik fetch edilebilir (datacenter IP filtreleme bu sitelerde daha gevşek). Bu, mevcut "sec_fetch_basarisiz" hata yolu için fallback olur.

### 4.3 Aksiyon kararı

- ✅ **`docs/FMP_SKILL.md` güncellendi** (10 May akşam): `news/press-releases` parametre tuzağı (sadece `symbols`) ve content kapsamı (özet 500-1500 char) net dökümante edildi.
- ✅ **Memory #21 güncellendi**: "ZORUNLU symbols ÇOĞUL (tekil symbol IGNORE)" notu eklendi.
- ⏸️ **`bilanco-sonrasi-us` skill'inde değişiklik YAPILMADI**: Mevcut SEC.gov akışı doğru karar, derinlemesine içerik kapsamı için tek seçenek.
- 📝 **TODO (orta öncelik)**: Senaryo A (hızlı triage) `04_post_earnings_signals.py` başına eklenebilir. ~30 satır kod, mevcut akışın önüne 1 ek call ekler ama 8-K/6-K bulunamayan ticker'lar için gereksiz SEC fetch'leri önler. Pazartesi sonrası test edilerek eklenebilir.

---

## 5. Yan Bulgu — İlk Audit Testinin Yanılgısı

10 Mayıs sabah audit raporunda yazılmıştı:

> 200 | news/press-releases | symbols=AAPL → AAPL ✅
> 200 | news/press-releases | symbol=AAPL → AAPL ✅

İkinci satır YANILTICI sonuç verdi. Status 200 ve dönen ticker AAPL olunca filtre çalışıyor sandım, oysa filtre çalışmasaydı bile AAPL "latest" listesinde olduğundan dönüş aynı görünürdü.

**Test prensibi (geriye dönük öğrenme)**: Sessiz parametre IGNORE'unu yakalamak için **düşük yoğunluklu** bir ticker ile test gerekli. AAPL/MSFT gibi yüksek-haber yoğunluklu ticker'lar latest listesinde zaten yer aldıkları için yanlış pozitif teyit verir. Test ticker olarak orta cap (örn VST, COIN, CELH) kullanılmalı.

Bu prensip Aksiyon 4 (test suite) içinde test case design rule'u olarak yer alacak.

---

**Rapor hazırlama tarihi:** 10 Mayıs 2026
**Test edilen ticker'lar:** VST, CON, CELH, TEM
**Skill etkilenmedi:** `bilanco-sonrasi-us` mevcut akış korundu
**Doküman değişiklikleri:** `docs/FMP_SKILL.md` v3 + Memory #21
**Kaynak:** finzora ai
