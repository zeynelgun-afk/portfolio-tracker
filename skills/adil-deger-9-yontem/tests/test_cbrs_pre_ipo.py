#!/usr/bin/env python3
"""
CBRS Pre-IPO Test — Projection Engine v5.0
Manuel girdi ile (FMP'de yok) projeksiyon üret, raporu yazdır.
"""
import sys
sys.path.insert(0, '/home/claude/dev/adil_deger_v5/scripts')

from projection_engine import (
    SECTOR_MARGIN_PROFILES,
    detect_margin_profile,
    project_revenue_5y,
    project_pnl_5y,
    project_multiples_5y,
    detect_normalization_year,
    format_pnl_table_markdown,
    format_multiples_table_markdown,
    format_normalization_summary,
)

# CBRS Pre-IPO girdileri (S-1 belgesi + iş bağlantıları)
ticker = "CBRS"
revenue_ttm = 510e6  # $510M 2025 actual
revenue_yoy = 0.76
shares_basic = 224e6  # post-IPO basic
shares_diluted = 257e6  # warrant dahil
ipo_price = 155  # mid IPO range

# Manuel gelir projeksiyonu — TTM (2025) gerçek + 5 yıl forward
# Backlog dönüşüm takvimi destekli
custom_revenues = {
    2026: 1.2e9,   # backlog 15% / 2 yıl = $1.85B avg, 2026 düşük capacity
    2027: 2.7e9,   # backlog dönüşüm hızlanır + AWS Bedrock revenue
    2028: 5.5e9,   # backlog %43 dönüşüm zirvesi
    2029: 7.0e9,   # 2 GW opsiyon kısmen
    2030: 9.5e9,   # 2 GW tam + sovereign
}

# CBRS profili: AI saf oyuncu, hızla büyüyen, op marjı negatif
profile_key = detect_margin_profile(
    sector_key='semicon_design',
    current_op_margin=-0.28,
    revenue_yoy_growth=0.76,
)
print(f"Detected profile: {profile_key}")
print(f"Profile description: {SECTOR_MARGIN_PROFILES[profile_key]['description']}")
print()

# Revenue projection — TTM yılı = 2025 (son tamamlanmış yıl)
revenues = project_revenue_5y(revenue_ttm, revenue_yoy, custom_revenues=custom_revenues, ttm_year=2025)
print("Revenue trajectory:")
for y, r in revenues:
    print(f"  {y}: ${r/1e9:.2f}B")
print()

# P&L projection (OpenAI 1B kredi × 6% = $60M faiz)
pnl = project_pnl_5y(
    revenue_list=revenues,
    profile_key=profile_key,
    shares_basic=shares_basic,
    shares_diluted=shares_diluted,
    interest_expense_annual=60e6,
)

print("=" * 80)
print("CBRS - 5 YILLIK P&L PROJEKSİYONU")
print("=" * 80)
print()
print(format_pnl_table_markdown(pnl))
print()

# Multiples projection
mults = project_multiples_5y(
    pnl_table=pnl,
    current_price=ipo_price,
    shares_basic=shares_basic,
    current_cash=4.2e9,  # 702M pre + 3.5B raise
    current_debt=1e9,    # OpenAI kredi
)

print("=" * 80)
print("CBRS - 5 YILLIK FORWARD ÇARPANLAR")
print("=" * 80)
print()
print(format_multiples_table_markdown(mults, ipo_price))
print()

# Normalization year — semicon medyanı P/E ~28x
normalization = detect_normalization_year(mults, sector_median_pe=28, sector_median_ev_sales=8)

print("=" * 80)
print("NORMALİZASYON YORUMU")
print("=" * 80)
print()
print(format_normalization_summary(normalization, mults, sector_label='yarı iletken sektör'))
print()

print("✅ CBRS pre-IPO projection test başarılı")
