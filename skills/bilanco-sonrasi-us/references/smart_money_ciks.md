# Smart Money CIK Referans Tablosu

Bu yatırımcıların 13F dosyaları FMP `institutional-ownership/extract` endpoint'inden çekilebilir. CIK'lar SEC EDGAR'dan teyit edilmiştir.

## Legendary Macro & Hedge Fund Yöneticileri

| Yatırımcı | Firma | CIK | Notlar |
|-----------|-------|-----|--------|
| Stanley Druckenmiller | Duquesne Family Office | `0001536411` | Macro odaklı, sektör rotasyonu, momentum + value blend. Hafıza notlarındaki "Druckenmiller multiplier 0.5–2.5x" sisteminin kaynağı |
| Warren Buffett | Berkshire Hathaway | `0001067983` | Klasik value, mega-cap blue chip, uzun vadeli (genelde 5+ yıl tutuş) |
| Charlie Munger | Daily Journal Corp (kişisel) | `0000783412` | Kasım 2023'te vefat, holdings hâlâ aktif (aile şirketi) |
| Michael Burry | Scion Asset Management | `0001649339` | Contrarian, sıkça short pozisyon, Q4 2025 13F küçük portföy |
| David Tepper | Appaloosa Management | `0001656456` | Distressed + macro, hızlı rotasyon yapan profil |
| Bill Ackman | Pershing Square Capital | `0001336528` | Konsantre portföy (8-10 isim), aktivist + value |
| Ray Dalio | Bridgewater Associates | `0001350694` | Risk parity, geniş portföy (200+ pozisyon), all-weather |
| Howard Marks | Oaktree Capital | `0000949509` | Distressed debt + value equity karışımı |
| Daniel Loeb | Third Point | `0001040273` | Aktivist + special situations |
| Seth Klarman | Baupost Group | `0001061768` | Deep value, deep contrarian, sabırlı kapital |
| Ken Griffin | Citadel Advisors | `0001423053` | Quant + multi-strategy, geniş portföy |
| Paul Tudor Jones | Tudor Investment Corp | `0000916641` | Macro, momentum, kısa-orta vade |
| Steven Cohen | Point72 Asset Management | `0001603466` | Multi-strategy, kısa vade, sıkça rotasyon |

## Tematik / Sektör Uzmanı

| Yatırımcı | Firma | CIK | Tema |
|-----------|-------|-----|------|
| Cathie Wood | ARK Invest (yöneticisi) | `0001697748` | Disruptive innovation, AI, biotech, fintech (yüksek beta) |
| Chase Coleman | Tiger Global Management | `0001167483` | Tech & internet growth, geç-stage VC alışkanlığı |
| Philippe Laffont | Coatue Management | `0001135730` | Tech + crossover, genelde mega-cap |
| Stephen Mandel | Lone Pine Capital | `0001061768` | Tech + healthcare growth, konsantre 30-40 pozisyon |
| Andreas Halvorsen | Viking Global | `0001103804` | Tiger cub, growth + healthcare |

## Kullanım Örneği

```python
# scripts/04_post_earnings_signals.py içinde otomatik kullanılır
SMART_MONEY = {
    "Druckenmiller": "0001536411",
    "Buffett": "0001067983",
    # ...
}

# Manuel çağrı
holdings = fmp_get("institutional-ownership/extract",
                   {"cik": "0001536411", "year": "2025", "quarter": "4"})
# Her kayıt: symbol, shares, securityCusip, nameOfIssuer
```

## CIK Bulma Yöntemi (yeni bir yatırımcı eklemek için)

1. SEC EDGAR Full-Text Search: https://efts.sec.gov/LATEST/search-index?q=%22{firma_adi}%22&forms=13F-HR
2. Sonuçlardan firma sayfasını aç, CIK header'da görünür
3. CIK'ı 10 haneye tamamla (öne sıfır ekleyerek): `0001536411`

## 13F Gecikme Kuralı

SEC kuralı gereği fonlar 13F'i çeyrek kapanışından **45 takvim günü sonra** dosyalar:
- Q1 (Mart kapanış) → 15 Mayıs civarı yayında
- Q2 (Haziran kapanış) → 14 Ağustos civarı
- Q3 (Eylül kapanış) → 14 Kasım civarı
- Q4 (Aralık kapanış) → 14 Şubat civarı

Bu nedenle bilanço sonrası tarama yaparken **bilanço çeyreğinin BİR ÖNCEKİ çeyreği** 13F için kullanılmalı. Örnek:
- 9 Mayıs 2026'da Q1 2026 bilanço sonrası tarama yapıyorsak → 13F için Q4 2025 verisi kullan (Q1 2026 13F'i 15 Mayıs sonrası gelir)
- Pipeline `run_pipeline.py` bunu otomatik türetir (`--13f-quarter` argümanı manuel override için)

## Önemli Kısıtlar

1. **13F sadece long pozisyonları gösterir** — short, opsiyon, türev, cash pozisyonu yansımaz
2. **45 gün gecikme** = veri eski olabilir, fon zaten satmış olabilir
3. **Buy-side'da zorlama yok** — yöneticinin neden aldığı ve ne kadar kaldıracaktı bilinmez
4. **Konsantre fonlarda smart money sinyali daha kuvvetli** — Ackman'ın 8 pozisyonundan biri olmak vs Citadel'ın 5000 pozisyonundan biri olmak farklı sinyal
