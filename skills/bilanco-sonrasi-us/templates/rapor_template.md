# Bilanço Sonrası ABD Fırsat Tarama Raporu

**Tarih**: {YYYY-MM-DD} {Pazartesi/Salı/.../Cumartesi}
**Tarama dönemi**: {tarih_baslangic} ve {tarih_bitis} ABD bilanço açıklamaları
**Pipeline versiyonu**: bilanco-sonrasi-us v1.0
**Kaynak**: finzora ai

---

## Tarama Özeti

| Aşama | Giriş | Çıkış | Filtre Açıklaması |
|-------|-------|-------|-------------------|
| 1 — Earnings + Mid-Cap+ | {us_total} ABD bilanço | {midcap_count} mid-cap+ | mcap≥$2B, fiyat≥$10, NYSE/NASDAQ/AMEX |
| 2 — YoY/QoQ İyileşme | {midcap_count} | {growth_count} | YoY rev≥8%, en az 3/4 kriter, outlier elendi |
| 3 — Adil Değer Sağlamlık | {growth_count} | {valued_count} | Analyst hedef ZATEN +25%+ + 1 fundamental teyit |
| 4 — Post-Earnings Sinyaller | {valued_count} | {valued_count} | Transcript + 13F + analist revize zenginleştirme |
| 5 — Final Sıralama | {valued_count} | **{final_count}** | Yıldız skor (5 madde), eleme kriterleri |

---

## TOP {N} — Yıldız Skorlu Final Sıralama

| # | Sym | ★ | Sektör | Fiyat | Hedef | Üst Pot. | Anahtar Sinyal |
|---|-----|---|--------|-------|-------|----------|----------------|
| 1 | **{sym1}** | ★★★★★ | {sektor1} | ${fiyat1} | ${hedef1} | +{up1}% | {anahtar_sinyal1} |
| 2 | **{sym2}** | ★★★★☆ | {sektor2} | ${fiyat2} | ${hedef2} | +{up2}% | {anahtar_sinyal2} |
| 3 | ... | | | | | | |

---

## Top 5 Detaylı Hisse Öneri Formatı

### 1) {SYMBOL} — {Şirket Adı} ({yıldız}) — {Sektör}

**Bilanço Sonuçları ({tarih})**:
- Revenue ${rev}M vs konsensüs ${rev_est}M (beat/miss %{rev_diff})
- EPS ${eps} vs konsensüs ${eps_est} (beat/miss %{eps_diff})
- YoY revenue +/-{yoy_rev}%
- QoQ revenue +/-{qoq_rev}%
- {L2P notu varsa: "Net income L2P (Q1 2025: zarar, Q1 2026: kâr)"}

**Şirket Guidance** ({transcript_durumu}):
- {transcript_cumle_1}
- {transcript_cumle_2}
- {transcript_cumle_3}
- Verdict: {RAISED / REAFFIRMED / QUALITATIVE_ONLY / LOWERED}

**Analist Tepkisi (post-earnings, {kac_revize} revizyon)**:
- {analist_1}: ${eski_hedef} → ${yeni_hedef} ({yön})
- {analist_2}: ${eski_hedef} → ${yeni_hedef} ({yön})
- Verdict: {STRONG_RAISE / NET_RAISE / MIXED / NET_LOWER / CAPITULATION}

**13F Kurumsal Görünüm (Q{q-1} {y-1})**:
- {investor_count} kurumsal yatırımcı (Δ {investor_change})
- 13F shares Δ {shares_change}M
- Toplam yatırım: ${total_invested}B
- Verdict: {STRONG_ACCUMULATION / ACCUMULATION / CONSOLIDATION / ROTATION / DISTRIBUTION}

**Smart Money**: {portfoyunde_var_mi: Druckenmiller, Buffett, ...}

**Hisse Öneri Formatı (zorunlu 4 alan)**:

- **Tetikleyici**: {bilanco_ozelinde_tetikleyici_olay}
- **Veri dayanağı**: FMP analist hedef ${hedef}, {forward_pe_veri}, {ev_ebitda_veri}, {transcript_dogrulama}
- **Risk (bear case) / stop**: {bear_case}, stop seviyesi: ${stop_seviye} (-%{stop_pct})
- **Hangi portföye uygun**: {Aggressive / Dengeli / Dividend / Swing} — {portfoy_gerekce}

---

## Shortlist'ten ÇIKARILANLAR (Fallen Angel Adayları)

Aşağıdaki hisseler bilanço sonrası analist downgrade dalgasına maruz kaldı veya transcript'te LOWERED guidance verdi. 2-3 hafta sonra "kapitulasyon dibi" sinyali için yeniden değerlendirilebilir:

- **{SYMBOL}** ({sektor}): {kac_lowered}/{toplam} analist DÜŞÜRME ({brokers}) — {gerekce}
- ...

---

## Bekleme Listesi (Veri Eksik)

- **{SYMBOL}** (foreign issuer 6-K, transcript yok): {durum}
- **{SYMBOL}** (henüz analist revize gelmedi, FIS gibi): {durum}

---

## Tematik / Sektörel Notlar

{sektor_konsantrasyon_uyarisi}

{ortak_tema_varsa}

---

## Veri Kaynakları (FMP Ultimate Plan)

| Kaynak | Endpoint | Kullanım |
|--------|----------|----------|
| Earnings calendar | `earnings-calendar` | Bilanço açıklayanlar listesi |
| Şirket profili | `profile` | Mcap, fiyat, exchange, sektör |
| Çeyreklik mali tablo | `income-statement?period=quarter` | YoY/QoQ büyüme analizi |
| Analist konsensüs hedef | `price-target-consensus` | Adil değer 4 yöntem #1 |
| Analist revize haberleri | `price-target-news` | Yön sayımı (raised vs lowered) |
| Analist tahmin | `analyst-estimates` | Forward EPS, NTM revenue |
| Telekonferans transcript | `earning-call-transcript` | CFO/CEO doğrudan guidance sözleri |
| 13F kurumsal özet | `institutional-ownership/symbol-positions-summary` | Kurumsal birikim trendi |
| 13F yatırımcı holdings | `institutional-ownership/extract` | Smart money portföy kontrolü |

---

## KESİN / MUHTEMEL / SPEKÜLATİF

- **KESİN**: {kesin_veriler_listesi}
- **MUHTEMEL**: {muhtemel_yorumlar}
- **SPEKÜLATİF**: {spekulatif_iddialar}

---

## Neden Yanlış Olabilirim (Zorunlu Bölüm)

1. {risk_1: pre-market yanıltıcı olabilir}
2. {risk_2: guidance raise zaten fiyatlanmış olabilir}
3. {risk_3: smart money yokluğu yapısal olabilir}
4. {risk_4: sektör konsantrasyon riski}
5. {risk_5: 13F gecikme nedeniyle Q-1 verisi eski}
6. {risk_6: transcript yorumlama hatası — yöntem conservative olabilir}
7. {risk_7: capitulation aslında dipten dönüş olabilir (HUBS/TOST)}

---

## Sonraki Adımlar

1. **Pre-market kontrolü ({tarih}, 14:00 TR civarı)** — Top {N} hisselerin gap up/down hareketi
2. **Top 3 için tam adil değer raporu** — `skills/adil-deger-9-yontem/` skill ile 11-bölüm rapor
3. **Pozisyon zamanlaması** — Day-1 chasing yasak, min 1 gün cooldown + RSI confirmation
4. **2-3 hafta sonra fallen angel takip** — Eliminated listesindeki hisseler için yeniden tarama
5. **Smart money tracker güncellemesi** — Bilanço çeyreğinin 13F'i 45 gün sonra geldiğinde tarama yenilenebilir

**Kaynak**: finzora ai
