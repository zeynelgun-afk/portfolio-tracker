---
title: Adil Değer Raporlama Protokolü
description: "TICKER adil değer hesapla" komutu için zorunlu çıktı formatı, kayıt yolu ve içerik şartları. EMIR niteliğindedir.
tags:
  - valuation
  - protocol
  - skill
  - command
  - mandatory
related:
  - "[[VALUATION_SYSTEM_v6]]"
  - "[[VALUATION_FRAMEWORK_v5]]"
  - "[[FORWARD_VALUATION_METHOD]]"
  - "[[ADIL_DEGER_KULLANIM]]"
  - "[[ADIL_DEGER_V7_CATALYST]]"
  - "[[K_RULES_QUICK_REF]]"
updated: 2026-05-08
authority: EMIR (Zeynel onaylı, atlanması yasak)
---

# Adil Değer Raporlama Protokolü — EMIR

> **NİTELİK:** Bu doküman bir referans değil EMIR'dir. Zeynel "TICKER adil değer hesapla" dediğinde aşağıdaki adımların TAMAMI uygulanır. Atlanan adım bir disiplin ihlalidir.

---

## 1. Tetikleyici Komutlar

Aşağıdaki ifadelerden herhangi biri bu protokolü tetikler:

- `TICKER adil değer hesapla`
- `TICKER değerleme yap`
- `TICKER fair value hesapla`
- `TICKER için adil değer çıkar`
- `/deger TICKER` (Telegram bot komutu)

Her tetikleyicide bu protokol uygulanır. Kısa cevap, sadece sayı, tek satır özet **YASAK**. Tam rapor zorunlu.

### 1.1 Chat Çıktısı vs GitHub Kayıt — Net Ayrım

**GitHub kayıt HER ZAMAN tam yapılır.** Kullanıcı çıktıyı nasıl isterse istesin (kısa, sadece karar notu, tek satır vs.) `reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md` dosyası tam 11 bölümlü olarak yazılır, `data/research/index.json` güncellenir, commit + push yapılır.

**Chat çıktısı kullanıcı isteğine göre değişir:**

| Kullanıcı İsteği | Chat'te Göster | GitHub'a Yaz |
|---|---|---|
| Açık istek yok / "tam rapor" / "detaylı" | 11 bölümlü tam markdown | 11 bölümlü tam (zorunlu) |
| "Kısa olsun" / "sadece karar notu" / "özet" | Karar notu (sadece bölüm 9-10 özeti) | 11 bölümlü tam (zorunlu) |
| "HTML olarak ver" | HTML versiyonu (frontend-design skill) | hem .md hem .html (her ikisi zorunlu) |
| "Sadece adil değer rakamı" | Tek satır + minimal context | 11 bölümlü tam (zorunlu) |

**Sebep:** Tam rapor olmadan post-trade review yapılamaz, lessons çıkarılamaz, geriye dönük doğrulama imkansızlaşır. Chat ekran kısa olabilir; veri katmanı kısa olamaz.

**İSTİSNA YOK.** "Sadece kontrol etmek istiyorum, kaydetme" gibi istekler bile reddedilir — adil değer komutu çalışıyorsa kayıt yapılır. Kullanıcı kayıt istemiyorsa "deger TICKER" yerine "TICKER fiyat ne, mantıklı mı?" gibi gayri-resmi soru sorar.

---

## 2. Zorunlu Çıktı Yolu

Her adil değer hesabı GitHub'a kaydedilir. Sadece sohbet ekranında kalmaz.

| Yer | Yol | Açıklama |
|---|---|---|
| Rapor | `reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md` | Tam markdown rapor |
| İndeks | `data/research/index.json` | Yapılandırılmış kayıt (analizler dizisine ekle) |
| Commit mesajı | `[VALUATION] {TICKER} adil değer hesabı eklendi ({YYYY-MM-DD})` | Standart |
| Push | `git push origin main` | Hemen, beklemeden |

Kayıt yapılmadan tamamlandı sayılmaz.

---

## 3. Zorunlu Rapor Bölümleri (11 madde)

Aşağıdaki on bir bölüm sırasıyla bulunmalı. Atlanan bölüm, eksik rapor demektir.

### 3.1 Yönetici Özeti
- 2-3 paragraf öz
- Snapshot tablosu (fiyat, MCap, EV, beta, sektör, TTM/forward temel metrikler)
- Beklenen Adil Değer + yukarı/aşağı potansiyel + Confidence

### 3.2 9 Yöntem Bazlı Değerlendirme
Adil Değer v3.7.2'nin dokuz yöntemi hepsi tek tek incelenir:

1. Net P/E TTM
2. Forward P/E (NTM)
3. EV/EBIT
4. EV/EBITDA
5. EV/Revenue
6. P/FCF
7. ROE bazlı
8. Graham Number
9. DCF

Her yöntem için **iki kategoriden birine** giriliyor:
- **KULLANILABİLİR** — hesaplandı, sonuç verildi
- **KULLANILAMAZ** — hesaplanamaz; sebep yazılır (örn. "TTM EPS negatif")

Eğer 4'ten fazla yöntem kullanılamıyorsa: forward bazlı versiyonları zorlanır (Forward EV/EBITDA, Forward P/FCF, Forward EV/Rev).

### 3.3 Ağırlıklı Adil Değer Tablosu
| Yöntem | Adil Değer | Ağırlık | Katkı |
|---|---|---|---|
| ... | ... | ... | ... |
| **Toplam** | | | **{ağırlıklı sonuç}** |

Ağırlıklar şirket profiline göre belirlenir (sektör + büyüme + kâr durumu). Gerekçe bir cümleyle yazılır.

### 3.4 Senaryo Matrisi
| Senaryo | Adil Değer | Mevcut Fiyata Göre | Olasılık |
|---|---|---|---|
| Bear | ... | -%X | %25-35 |
| Base | ... | +%X | %40-50 |
| Bull | ... | +%X | %20-30 |
| **Beklenen Değer** | | | |

Olasılıklar sübjektif, fakat **gerekçesiz olamaz**. Her olasılığın yanında bir cümle gerekçe.

### 3.5 Bear Case (Detaylı, en az 5 madde)
**KURAL:** Bear case bull case'den daha az detaylı **OLAMAZ**. K kuralı: tek taraflı analiz yasak. Confirmation bias engellemesi.

Her madde: gerçek bir veri/risk + somut sayı + kaynağı.

Konular: borç profili, marj sıkışması, müşteri konsantrasyon, regülasyon riski, multiple compression, insider satışı, sektör rotasyonu, makro hassasiyet, vb.

### 3.6 Bull Case (Detaylı, en az 5 madde)
Aynı format. Bear ile **eşit ağırlık**.

### 3.7 "Neden Yanlış Olabilirim" Notu (ZORUNLU, en az 5 madde)
**K kuralı: her stratejik karar bu bölümü içermeli.**

Konular:
- Multiple seçimi sübjektifliği
- Analyst coverage zayıflığı
- Capex / FCF varsayımları
- Sektör multiple aralığının geniş olması
- TTM verilerin temsiliyeti
- Recency bias
- Forward varsayımların yumuşaklığı

### 3.8 Belirsizlik Etiketleri
Rapor boyunca her önemli iddia yanında etiket:

| Etiket | Anlam |
|---|---|
| **KESİN** | FMP'den alınmış doğrudan veri |
| **MUHTEMEL** | Veriden çıkarım, makul varsayım |
| **SPEKÜLATİF** | Yorum, marjinal sapmaya açık |

Spekülatif olanı kesin gibi sunmak yasak.

### 3.9 Portföy Karar Matrisi (3 portföy)
| Portföy | Uygunluk | Gerekçe + Maks Ağırlık |
|---|---|---|
| Dengeli (100K) | uygun / uygun_kosullu / uygun_degil | ... |
| Agresif Büyüme (400K) | uygun / uygun_kosullu / uygun_degil | ... |
| Değer + Temettü (100K) | uygun / uygun_kosullu / uygun_degil | ... |

### 3.10 Giriş Planı
| Parametre | Değer |
|---|---|
| Mevcut Fiyat | ... |
| Beklenen Adil Değer | ... |
| İdeal Giriş Zonu | ... |
| Stop Loss | ... |
| Hedef 1 (base) | ... |
| Hedef 2 (bull) | ... |
| R/R Oranı | ... |
| Pozisyon Boyutu | ... |
| Bekle Koşulları (en az 2) | ... |

### 3.11 İzleme Tetikleyicileri (en az 5 madde)
Konkretemin: tarih, sayı, koşul. "İlginç gelişmeler" gibi muğlak ifadeler yasak.

---

## 4. Zorunlu index.json Şeması

`data/research/index.json` dosyasındaki `analizler` dizisine yeni giriş eklenir. Şema:

```json
{
  "id": "{TICKER}_ADIL_DEGER_{YYYY-MM-DD}",
  "ticker": "{TICKER}",
  "sirket": "{Tam adı}",
  "sektor": "{FMP sector / industry}",
  "analiz_tarihi": "{YYYY-MM-DD}",
  "bilanco_tarihi": "{varsa, sonraki kazanç tarihi}",
  "analiz_turu": "adil_deger_hesabi",
  "durum": "aktif_izleme",
  "dosya": "reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md",
  "kataliz": {
    "olay": "...",
    "tarih": "...",
    "aciklama": "..."
  },
  "adil_deger": {
    "yontem_v": "v3.7.2 forward-adapted",
    "kullanilabilir_yontem_sayisi": N,
    "kullanilamayan_yontem_sayisi": M,
    "kullanilamayan_sebebi": "...",
    "agirlikli_adil_deger": <rakam>,
    "iskontosuz_adil_deger": <rakam>,
    "confidence": "YUKSEK | ORTA | ORTA-DUSUK | DUSUK",
    "yontem_dagilimi": {
      "forward_pe": {"deger": ..., "agirlik": ..., "multiple_used": "..."},
      "forward_ev_ebitda": {"deger": ..., "agirlik": ..., "ebitda_marji_varsayim": "..."},
      "forward_ev_revenue": {"deger": ..., "agirlik": ..., "multiple": "..."},
      "forward_p_fcf": {"deger": ..., "agirlik": ..., "fcf_tahmin_m": "..."},
      "dcf_2_asama": {"deger": ..., "agirlik": ..., "wacc": ..., "buyume_asama1": ..., "terminal_buyume": ...}
    }
  },
  "on_beklenti": {
    "senaryo_boga": {"kosul": "...", "fiyat_hedef": ..., "getiri_pct": ...},
    "senaryo_baz":  {"kosul": "...", "fiyat_hedef": ..., "getiri_pct": ...},
    "senaryo_ayi":  {"kosul": "...", "fiyat_hedef": ..., "getiri_pct": ...},
    "olasiliklar": {"boga": 0.25, "baz": 0.50, "ayi": 0.25}
  },
  "analiz_fiyati": <rakam>,
  "temel_metrikler": {
    "pe_ttm": ..., "forward_pe": ..., "ev_ebitda_ttm": ..., "fiyat_satis_ttm": ...,
    "fiyat_defter": ..., "borclanma_ozkaynak": ..., "roe_ttm_pct": ...,
    "fcf_ttm_m": ..., "fcf_yield_ttm_pct": ..., "lt_borc_m": ..., "nakit_m": ...,
    "net_borc_m": ..., "beta": ..., "yillik_dip_zirve": [...],
    "piyasa_degeri_m": ..., "enterprise_value_m": ..., "hisse_adedi_m": ...
  },
  "portfoy_onerisi": {
    "dengeli": "uygun | uygun_kosullu | uygun_degil",
    "agresif": "uygun | uygun_kosullu | uygun_degil",
    "temettü": "uygun | uygun_kosullu | uygun_degil"
  },
  "giris_plani": {
    "ideal_zon": "X-Y",
    "stop_loss": ...,
    "hedef_1": ...,
    "hedef_2": ...,
    "r_r_orani": ...,
    "pozisyon_boyut_dolar": ...,
    "kosul": "..."
  },
  "izleme_tetikleyicileri": ["...", "..."],
  "neden_yanlis_olabilirim": ["...", "...", "...", "...", "..."],
  "gerceklesen": {
    "tespit_fiyati": ...,
    "simdiki_fiyat": ...,
    "fiyat_tepkisi_pct": 0,
    "tez_tuttu": null,
    "ders": null
  },
  "etiketler": ["...", "..."]
}
```

İndeks güncellenince `toplam_analiz`, `aktif_izleme`, `son_guncelleme` alanları yenilenir.

---

## 5. Veri Kaynak Hiyerarşisi

Adil değer hesabında veri sırasıyla şu kaynaklardan çekilir:

1. **FMP API stable/** (birincil)
   - `quote` — fiyat, volume, MCap, 52h range
   - `profile` — sektör, beta, açıklama
   - `ratios-ttm` — `priceToEarningsRatioTTM`, `priceToBookRatioTTM`, vb.
   - `key-metrics-ttm` — `enterpriseValueTTM`, `freeCashFlowYieldTTM`, vb.
   - `income-statement?period=annual&limit=4` — son 4 yıl gelir tablosu
   - `balance-sheet-statement?period=annual&limit=4` — bilanço
   - `cash-flow-statement?period=annual&limit=4` — nakit akış
   - `analyst-estimates?period=annual&limit=4` — `epsAvg`, `revenueAvg` (NOT: `estimatedEpsAvg` DEĞİL)
   - `enterprise-values?period=annual&limit=4` — geçmiş EV/MCap

2. **Web search** — sektör konsensüs multiple bandları için (peer karşılaştırma)

3. **Manuel/Hybrid** — kullanıcı override için

FMP'den dönen veriler şu nüanslara dikkat eder:
- `changePercentage` (NOT `changesPercentage`)
- `epsAvg` (NOT `estimatedEpsAvg`)
- `quote` liste döner — `[0]` erişimi + `isinstance(q, dict)` guard
- VIX için: `quote?symbol=^VIX` (VIXY proxy KULLANMA)

---

## 6. Yöntem Seçim Kuralları

Hangi yöntem hangi profilde ağırlıklandırılır:

| Profil | Tipik Ağırlık |
|---|---|
| Olgun, kârlı, düşük büyüme (utility, consumer staples) | Net P/E %25, Forward P/E %20, EV/EBITDA %20, P/FCF %15, DCF %15, Graham %5 |
| Yüksek büyüme, kârda (tech, AI semi) | Forward P/E %30, EV/Revenue %20, P/FCF %20, DCF %20, EV/EBITDA %10 |
| Hyper-growth, kârsız | Forward EV/Revenue %35, Forward P/FCF %25, DCF %25, Forward EV/EBITDA %15 |
| Cyclical (commodity, semi-cycle) | Mid-cycle P/E %30, EV/EBITDA mid-cycle %25, P/B %20, DCF %15, Forward P/E %10 |
| Hibrit (utility/AI growth, IPP) | Forward P/E %30, Forward EV/EBITDA %30, Forward EV/Rev %15, Forward P/FCF %10, DCF %15 |
| Finans (bank, BDC) | P/B %30, P/TBV %25, ROE-bazlı %20, Forward P/E %15, Dividend Discount %10 |

TTM zarar varsa: Net P/E, EV/EBIT, Graham, ROE bazlı **otomatik kullanılamaz** olarak işaretlenir, forward bazlı yöntemler ön plana çıkar.

---

## 7. Confidence Belirleme

| Confidence | Koşul |
|---|---|
| YUKSEK | 7+ yöntem kullanılabilir, yöntemler arası dağılım CV<%15, peer multiple aralığı dar |
| ORTA | 5-6 yöntem kullanılabilir, CV %15-25 |
| ORTA-DUSUK | 4-5 yöntem kullanılabilir, CV %25-35, forward bazlı baskın |
| DUSUK | <4 yöntem kullanılabilir veya CV>%35 |

Confidence raporun yönetici özetinde açıkça yer alır. ORTA-DUSUK ve DUSUK için kullanıcıya açık uyarı yapılır.

---

## 8. Yazım Kuralları (zorunlu)

Memory'deki rapor yazım kurallarına uygun:

- Ciddi Türkçe, cümleler BÜYÜK harfle başlar
- Em dash (—) yasak; tire (-) ve nokta-virgül (;) kullan
- Kaynak: "finzora ai" (başka isim yok)
- AI kokusu olan ifadeler ("son derece", "oldukça", "etkileyici bir şekilde") yasak
- Türkçe terim önce, İngilizce parantez içinde:
  - inference (çıkarım)
  - hyperscaler (büyük bulut sağlayıcı)
  - workload (iş yükü)
  - forward P/E (ileri F/K)
  - bear case / bull case (düşüş senaryosu / yükseliş senaryosu)
  - catalyst (tetikleyici)
  - multiple (çarpan)
  - peer (emsal)
  - exposure (maruziyet)
  - pure-play (saf oyuncu)
  - valuation (değerleme)
  - breakout (kırılım)
  - pullback (geri çekilme)
  - earnings (kazanç)
  - capex (sermaye yatırımı)
- Ticker İngilizce kalır
- Sayılar: virgül ondalık ayraç (3,79 ✅ / 3.79 ❌)
- Para birimi: "390 dolar" (✅) / "$390" (❌, sadece ticker yanında)

---

## 9. Karar Çıktısı

Her rapor sonunda dört seviyeli karar:

| Karar | Tanımı |
|---|---|
| **AL ŞİMDİ** | Mevcut fiyat <%5 adil değer altında; bekle koşulları geçerli; pozisyon planı uygulanabilir |
| **İZLE - GİRİŞ KOŞULLU** | Adil değer altında ama bekle koşulları aktif değil; takvim/teknik tetikleyici bekle |
| **HOLD (mevcut pozisyonda)** | Fair value civarında; mevcut sahipler tutar, yeni alım yok |
| **GEÇ / SAT** | Mevcut fiyat adil değer üstünde >%15; mevcut pozisyonlar trim/exit düşünülür |

Karar değişikliği için yeniden hesap yapılır.

---

## 10. Workflow Adımları (Claude için exec sırası)

1. Tetikleyici tanı: "TICKER adil değer hesapla" geldi
2. Saat kontrolü: `user_time_v0` çağır (hafta sonu = piyasa kapalı, kapanış verisi kullan)
3. FMP veri çek (10 endpoint, paralel mümkün): quote / profile / ratios-ttm / key-metrics-ttm / income / balance / cash-flow / analyst-estimates / financial-growth / enterprise-values
4. Yöntem seçimi: profil belirle (olgun/growth/cyclical/hybrid/finans) → ağırlık tablosu seç
5. TTM kâr durumu: zararsa kullanılamaz yöntemleri işaretle
6. Her kullanılabilir yöntem için ayrı hesap + ayrı kontrol
7. Ağırlıklı adil değer + iskonto hesabı
8. Senaryo matrisi (bear/base/bull) — her birine olasılık + gerekçe
9. Bear ve bull case yaz (eşit detay, en az 5 madde her biri)
10. "Neden yanlış olabilirim" notu (en az 5 madde)
11. Confidence belirle
12. Portföy karar matrisi
13. Giriş planı + bekle koşulları
14. İzleme tetikleyicileri
15. Markdown raporu yaz: `/home/claude/repo/reports/research/{TICKER}_ADIL_DEGER_{YYYY-MM-DD}.md`
16. `data/research/index.json` güncelle (analizler dizisine ekle, toplam/aktif/son_guncelleme yenile)
17. `git add` + `git commit` (mesaj formatı yukarıda) + `git push`
18. Sohbet ekranında özet + commit hash + GitHub link sun

Atlanan adım = disiplin ihlali.

---

## 11. Hata ve İstisna Durumları

| Durum | Yapılacak |
|---|---|
| FMP veri eksik (sembol bulunamadı) | Web search ile fallback; hala yoksa kullanıcıya bildir |
| Çok yeni IPO (TTM yok) | Sadece forward + DCF + EV/Rev kullan, confidence DUSUK |
| ADR / yabancı şirket | Currency conversion not'u ekle, peer karşılaştırma yerel pazar |
| Spin-off / yeni listing | "Tarihsel veri yetersiz" uyarısı, confidence DUSUK |
| Dual-class shares (GOOGL/GOOG, BRK.A/B) | Hangi sınıf hesaplanıyor açık yaz |
| Negatif equity | P/B kullanılamaz, ROE-bazlı kullanılamaz |
| Piyasa kapalı (Sat-Sun) | Cuma kapanış verileri ile, "{YYYY-MM-DD seans öncesi}" notu |

---

## 12. Referans: TLN Örneği

Bu protokolün eksiksiz uygulandığı ilk örnek:
- Rapor: `reports/research/TLN_ADIL_DEGER_2026-05-08.md`
- İndeks girişi: `data/research/index.json` ID: `TLN_ADIL_DEGER_2026-05-08`
- Commit: `11e3d9c`
- Tetikleyici: "TLN adil değer hesapla"
- Sonuç: 11 bölüm, 5 yöntem kullanılabilir, ağırlıklı 492 dolar, ORTA-DUSUK confidence

Yeni hesaplar bu örneğin formatına uyar.

---

**Son güncelleme:** 2026-05-08
**Yetki:** Zeynel onayı ile EMIR statüsünde
**Atlanan adım:** disiplin ihlali, post-trade review'da işlenir
