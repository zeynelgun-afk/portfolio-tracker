# Bilanço Sonrası Tarama — Bilinen Tuzaklar

Bu doküman bugüne kadar (Mayıs 2026'a kadar) edinilen ve bu skill'in tasarımına yansıyan tuzakları sistematik olarak listeler.

## 1. Day-1 Chasing Yasak (Crisis Rally Day-1)

**Kural**: Bilanço sonrası ilk gün almak FORBIDDEN. Min 1 gün cooldown + RSI confirmation gerekli.

**Kaynak**: KTOS, CEG, HAL, LASR örneklerinde 5/5 day-1 girişi loser oldu (hafıza notu).

**Pipeline'a yansıması**: Skill çıktısı "AL" değil "izlemeye al + Pazartesi pre-market kontrol" sonucu verir. Pre-market kontrol sonrası ikinci gün giriş tavsiye edilir.

## 2. L2P PEG Distortion (Zarardan Kâra Geçiş)

**Sorun**: TTM EPS düşük baz oluşturduğunda PEG ve Forward P/E yöntemleri aşırı yüksek "fair value" hesaplar.

**Örnek**: BILL Q1 fiscal'de zarardan kâra geçti, PEG fair value $99 hesaplandı (gerçek fiyat $14). Bu yüzden L2P hisselerde PEG ağırlığı 0'a indirilir, kalan 3 yöntemle yeniden hesaplanır.

**Pipeline'a yansıması**: `03_valuation.py` içinde `loss_to_profit_yoy` flag'i kontrol edilir, varsa `fair_value_adj` PEG hariç hesaplanır. Final sıralamada `upside_pct_adj` kullanılır.

## 3. Outlier YoY %500+ (IPO/M&A Artefaktı)

**Sorun**: Yeni IPO veya recent M&A sonrası şirketlerin "Q1 2025"i fiilen yoksa veya çok küçükse, YoY büyüme istatistiksel olarak abartılı çıkar.

**Örnek**: AHR (American Healthcare REIT) %120,279 YoY revenue gösterdi — IPO Şubat 2024, dolayısıyla 1 yıl önce çok küçük bir şirketti. Bu gerçek momentum değil.

**Pipeline'a yansıması**: `02_growth_filter.py` içinde `yoy_rev > 500` filtresi outlier'ları siler.

## 4. Fiscal Year vs Calendar Year (Quarter Tuzağı)

**Sorun**: Calendar Q1 (Ocak-Mart) bilanço açıklayan şirketin transcript'i `quarter=1` ile çekildiğinde, eğer şirketin fiscal year-end Haziran ise bu aslında **Fiscal Q3** transkriptidir, FMP `quarter=1` ile farklı bir dönem getirir.

**Örnek**: BILL fiscal year Temmuz-Haziran. 7 Mayıs 2026 bilançosu = Q3 FY26. `quarter=1` çağrısı 6 ay önceki Temmuz-Eylül 2025 transkriptini döndürür. Doğru çağrı: `quarter=3`.

**Pipeline'a yansıması**: `04_post_earnings_signals.py` içinde `NON_CALENDAR_FISCAL` mapping. Bilinen şirketler: BILL, CRM, ORCL, NKE, CSCO, WMT. Belirsizse önce `earnings-transcript-list` endpoint'inden mevcut dönemleri kontrol et.

## 5. Pre-Market Yanıltıcı Olabilir

**Sorun**: %5+ pre-market hareketi açılışta tersine dönebilir, intraday'de büyük volatilite görülür.

**Örnek**: 8 Mayıs 2026'da FIS pre-market %-5.9 düştü ama intraday toparlanma ihtimali var. Pre-market thin liquidity'de büyük hareket küçük volume'le.

**Pipeline'a yansıması**: Skill çıktısı pre-market'e değil, açılış sonrası ilk 30 dakikaya bakılarak karar verilmesini önerir.

## 6. Sayısal Guidance Vermeyen Sektörler

**Sorun**: Energy drink, beverage, restaurant chain, otelcilik gibi sektörler nadiren spesifik forward EPS/revenue guidance verir. Bu eksikliği "zayıf sinyal" olarak yorumlamak hata.

**Örnek**: CELH Q1 2026 transcript'inde sadece nitel "Q2 side-step, Q3 stair step" dedi. Bu sektörel norm, "guidance vermedi" diye 1 yıldız eksilmesi adil değil.

**Pipeline'a yansıması**: `05_finalize.py` içinde transcript verdict `QUALITATIVE_ONLY` kategorisi var. Bu kategori için yıldız verilmez ama eleme de yapılmaz. Sektör bazında nuance manuel raporda eklenmeli.

## 7. Smart Money Tek Başına Yetmez

**Sorun**: Druckenmiller veya Buffett'ın bir hissede pozisyonu olmaması o hissenin "kötü" olduğunu göstermez. Smart money'nin sektör/tema tercihleri farklılık gösterir.

**Örnek**: Top 5'imiz (VST, BILL, CON, CELH, FIS) — Druckenmiller portföyünde YOK. Onun pozisyonları CPNG, TEVA, CLF, COGT gibi farklı isimler. Ama VST'de **broad institutional birikim +7.3M shares Q4** var, bu daha geniş bir onay sinyali.

**Pipeline'a yansıması**: `04_post_earnings_signals.py` `numberOf13FsharesChange` (broad institutional) ve smart money portföyünü AYRI sinyaller olarak değerlendirir. Smart money yokluğu eleme nedeni değil.

## 8. Strong Earnings ≠ Otomatik Rally ("Sell the News")

**Sorun**: Beat olsa bile, beklenti ZATEN yüksek fiyatlamada idiyse, bilanço sonrası "sell the news" tepkisi gelir.

**Örnek**: MU, RKLB beat etti ama bilanço sonrası satıldı. Beklentiler "perfection priced" durumdaydı.

**Pipeline'a yansıması**: Skill upside hesabı analyst target consensus baz alır — bu zaten beklentiyi yansıtır. Ama "guidance raise" sinyali bu sorunun panzehiri (BILL örneği): beklentinin de ÜZERİNDE rakam veren şirket "sell the news" riskini düşürür.

## 9. 13F Gecikme (45 Gün)

**Sorun**: SEC kuralı gereği 13F çeyrek kapanışından 45 gün sonra dosyalar. Q4 2025 verisi 14 Şubat 2026 sonrası gelir, Q1 2026 verisi 15 Mayıs 2026 sonrası gelir.

**Pipeline'a yansıması**: Bilanço çeyreğinin BİR ÖNCEKİ çeyreği 13F için kullanılır. `run_pipeline.py` `derive_13f_period()` fonksiyonu otomatik türetir. Mayıs 2026'da Q1 bilanço sonrası tarama yapıyorsak, 13F için Q4 2025 veri kullanılır.

## 10. Aynı Sektör Aynı Gün Çoklu Giriş (Korelasyon Riski)

**Sorun**: Top 5'in birden fazlası aynı sektörde ise (örn. 3 tane Tech), portföyde diversifiye yanılsamasıyla aslında konsantre risk birikir.

**Örnek**: Eğer skill çıktısı 5 hissesi de Tech sektöründe yer alıyorsa, sektörel düzeltmede hepsi aynı anda düşer.

**Pipeline'a yansıması**: Skill çıktısı sektör başlığı içerir; rapor template'i bu noktayı "Neden Yanlış Olabilirim" bölümünde manuel uyarı olarak ekler. İdeal olarak final 5'te en az 3 farklı sektör olmalı (mevcut Top 5'te Utilities, Tech/FinTech, Tech/SaaS, Healthcare, Consumer Defensive var — bu açıdan iyi).

## 11. Analist Hedefi Bilanço Sonrası Gecikmeli Güncellenir

**Sorun**: FMP `price-target-consensus` endpoint'i bazen bilanço öncesi konsensüsü yansıtır. Analistler revize için 1-2 hafta alabilir.

**Örnek**: 8 Mayıs FIS bilançosu sonrasında 9 Mayıs sabahı henüz analist target revize haberi gelmemişti (`price-target-news` boş döndü). Konsensüs hedef hâlâ pre-earnings rakamı.

**Pipeline'a yansıması**: `04_post_earnings_signals.py` `price-target-news` haberlerini kullanarak yön sayar (raised vs lowered). Konsensüs hedef "stale" olsa bile haber yönü güncel sinyal verir. Bu nedenle hem konsensüs upside (Aşama 3) hem de revize yön (Aşama 4) AYRI sinyaller olarak skorlanır.

## 12. Transcript Yayın Gecikmesi

**Sorun**: FMP `earning-call-transcript` endpoint'i bilanço açıklamasından 12-48 saat sonra dolar. Aynı gün veya ertesi gün çağrı boş dönebilir.

**Örnek**: FIS 8 Mayıs Cuma sabahı bilanço açıkladı, 9 Mayıs Cumartesi sabahı transcript boştu. Pazartesi/Salı yeniden çekilmeli.

**Pipeline'a yansıması**: `04_post_earnings_signals.py` transcript yokluğunu `verdict: QUALITATIVE_ONLY veya {available: False}` olarak işaretler. Yıldız hesabında transcript-bazlı yıldız atlanır. Skill 1-2 gün sonra yeniden çalıştırılmaya uygun (idempotent).

## 13. Foreign Issuer 6-K (Transcript Format Farklı)

**Sorun**: ABD dışı şirketler (ARGX Belçika, NVO Danimarka, AZN UK gibi ADR'ler) 8-K yerine 6-K dosyalar. Bunların FMP transcript verisi de farklı yapıda olabilir veya bazıları transcript yapmaz.

**Örnek**: ARGX Q1 2026 için FMP'de transcript YOK (Q4 2025 var). Bu eksiklik ARGX'i "kötü" yapmaz, sadece sinyal eksik.

**Pipeline'a yansıması**: Skill çıktısında "Bekleme Listesi" kategorisi, foreign issuer'lar buraya alınır. Yıldız hesabında transcript yokluğu eleme nedeni değil.

## 14. Capitulation Sinyali Bazen Dipten Dönüş (Fallen Angel)

**Sorun**: 8+ analistin aynı anda hedef düşürmesi normalde "yapısal sorun" sinyali ama bazen "aşırı tepki dibi" olur. Sonraki 2-3 hafta içinde dipten dönüş gelebilir.

**Örnek**: HUBS 8 Mayıs'ta 13/13 analist downgrade aldı. Bu "kapitülasyon" — gerçek dip olabilir. 2-3 hafta sonra yeniden değerlendirme yapılabilir.

**Pipeline'a yansıması**: `05_finalize.py` `CAPITULATION` verdict'ini eler ama `eliminated` listesinde "fallen angel adayı" olarak takipte tutulur. Manuel rapor "Sonraki Adımlar" bölümünde bu hisselerin 2-3 hafta sonra yeniden değerlendirilmesi önerilir.

## 16. Yetersiz Miktarda Raise = Analyst Hayal Kırıklığı

**Sorun**: Şirket transcript'te "we raised our guidance" dese bile, raise miktarı Q1 beat'in altındaysa analistler "effective lower" yorumlar. Yani RAISED guidance ≠ analyst tepkisi pozitif.

**Örnek**: HUBS Q1 2026 — Q1 beat $18M, FY guidance raise sadece $9M (beat'in yarısı). Analistler "%50 below the beat raise = soft" diye yorumladı, 12 broker hedef düşürdü (CAPITULATION).

**Pipeline'a yansıması**: Skill HUBS'ı `eliminated` listesine alıyor çünkü analyst CAPITULATION verdict'i transcript RAISED'a baskın. Doğru karar — analyst yön net negatifse, transcript RAISED olsa bile shortlist'ten çıkar.

**Gelecek geliştirme**: Transcript verdict'i RAISED + analyst NET_LOWER birlikte tespit edilirse "WEAK_RAISE" alt kategorisi oluşturulabilir. Bu durumda hisse 2-3 hafta sonra "fallen angel" adayı olarak yeniden değerlendirilir.

## 17. Smart Money Tek Yatırımcıya Bakma

**Sorun**: Skill başlangıçta sadece 5 büyük yatırımcıya bakıyordu (Druckenmiller, Buffett, Burry, Tepper, Ackman). Eksik tarama smart money sinyalini kaçırabilir.

**Örnek**: VST için ilk tarama Druckenmiller/Buffett/Burry'de yoktu, "smart money tezimizi onaylamıyor" dedik. Tepper'ı eklediğimizde **VST'nin Tepper portföyünde olduğunu** keşfettik (Q4 2025).

**Pipeline'a yansıması**: `04_post_earnings_signals.py` `SMART_MONEY` dict'i Tepper'ı içeriyor (5'li set yeterli). Ama daha kapsamlı için `references/smart_money_ciks.md`'deki 18 yatırımcının hepsi taranabilir (5 yerine 18 API call ekstra, kabul edilebilir).

**İdeal**: Pipeline `--smart-money-set` argümanı ile genişletilebilir, default 5 yatırımcı, opsiyonel "expanded" modda 15+ yatırımcı.
