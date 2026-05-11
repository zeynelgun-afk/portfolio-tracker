#!/usr/bin/env python3
"""
NVDA Live FMP + Projection Engine Test — v5.0
"""
import sys
sys.path.insert(0, '/home/claude/dev/adil_deger_v5/scripts')

from fmp_layer import (
    get_ratios_ttm,
    get_key_metrics_ttm,
    get_live_pe_for_sector_key,
    get_financial_scores,
    interpret_altman_z,
    interpret_piotroski,
    get_grades_consensus,
    get_grades_historical,
    detect_upgrade_momentum,
    get_fmp_dcf,
    get_revenue_product_segmentation,
    detect_concentration_risk,
    get_10y_treasury_rate,
    calculate_dynamic_wacc,
    is_ticker_pre_ipo,
)
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
import requests

KEY = "g1GFJZtV5rCP49UCir4WuP56VjhmA6F8"
BASE = "https://financialmodelingprep.com/stable"
HEADERS = {"User-Agent": "finzora-ai-skill-test/5.0"}

def get(ep, **kw):
    return requests.get(f"{BASE}/{ep}", params={**kw, "apikey": KEY}, headers=HEADERS, timeout=30).json()

ticker = "NVDA"

print("=" * 80)
print(f"  {ticker} — Live FMP + Projection Engine v5.0")
print("=" * 80)

# 1. Temel TTM rakamlar (canlı FMP)
print("\n[1] Quote + TTM oranlar...")
quote = get("quote", symbol=ticker)[0]
ratios = get_ratios_ttm(ticker)
keymet = get_key_metrics_ttm(ticker)
profile = get("profile", symbol=ticker)[0]

print(f"  Price: ${quote['price']} | MCap: ${quote['marketCap']/1e9:.1f}B")
print(f"  P/E TTM (FMP): {ratios['priceToEarningsRatioTTM']:.2f}")
print(f"  EV/EBITDA TTM (FMP): {ratios.get('enterpriseValueMultipleTTM') or keymet.get('evToEBITDATTM', 0):.2f}")
print(f"  ROE TTM (FMP): {ratios['returnOnEquityTTM']*100:.1f}%")
print(f"  Net Margin TTM (FMP): {ratios['netProfitMarginTTM']*100:.1f}%")
print(f"  Op Margin TTM (FMP): {ratios['operatingProfitMarginTTM']*100:.1f}%")
print(f"  Gross Margin TTM (FMP): {ratios['grossProfitMarginTTM']*100:.1f}%")
print(f"  Beta: {profile.get('beta')}")

# 2. Canlı sektör P/E
print("\n[2] Canlı sektör/industry P/E...")
pe, source = get_live_pe_for_sector_key('semicon_design', static_fallback_pe=28)
print(f"  Semicon Design P/E: {pe:.2f}x (kaynak: {source})")

# 3. Risk skorları (Altman Z + Piotroski)
print("\n[3] Risk skorları...")
scores = get_financial_scores(ticker)
if scores:
    z, z_lbl, z_emoji = interpret_altman_z(scores.get('altmanZScore'))
    p, p_lbl, p_emoji = interpret_piotroski(scores.get('piotroskiScore'))
    print(f"  Altman Z: {z:.2f} → {z_emoji} {z_lbl}")
    print(f"  Piotroski: {p}/9 → {p_emoji} {p_lbl}")

# 4. Analist sentiment
print("\n[4] Analist sentiment...")
consensus = get_grades_consensus(ticker)
if consensus:
    print(f"  StrongBuy: {consensus.get('strongBuy')} | Buy: {consensus.get('buy')} | Hold: {consensus.get('hold')} | Sell: {consensus.get('sell')} | StrongSell: {consensus.get('strongSell')}")
    print(f"  Konsensüs: {consensus.get('consensus')}")

historical_grades = get_grades_historical(ticker)
momentum = detect_upgrade_momentum(historical_grades, lookback_months=6)
if momentum:
    print(f"  Son 6 ay momentum: {momentum['label']}")

# 5. FMP'nin kendi DCF'i
print("\n[5] FMP DCF (bizim hesapla karşılaştırma için)...")
fmp_dcf = get_fmp_dcf(ticker)
fmp_dcf_levered = get_fmp_dcf(ticker, levered=True)
if fmp_dcf:
    print(f"  FMP DCF: ${fmp_dcf.get('dcf', 0):.2f} (Stock: ${fmp_dcf.get('Stock Price', 0):.2f})")
if fmp_dcf_levered:
    print(f"  FMP Levered DCF: ${fmp_dcf_levered.get('dcf', 0):.2f}")

# 6. Revenue segmentation (müşteri konsantrasyon)
print("\n[6] Revenue product segmentation (konsantrasyon riski)...")
segs = get_revenue_product_segmentation(ticker)
risk = detect_concentration_risk(segs)
if risk:
    print(f"  {risk['label']}")
    print(f"  Top segment: {risk['top_segment']} ({risk['top_share_pct']}%)")
    print(f"  Top 2 toplam: {risk['top2_share_pct']}%")
    print(f"  Fiscal year: {risk['fiscal_year']}")

# 7. Dinamik WACC
print("\n[7] Dinamik WACC (10y Treasury bazlı)...")
rf = get_10y_treasury_rate()
if rf:
    print(f"  10y Treasury: {rf*100:.2f}%")
wacc, wacc_source = calculate_dynamic_wacc(beta=profile.get('beta', 1.6))
print(f"  WACC: {wacc*100:.2f}% ({wacc_source})")

# 8. IPO calendar tespiti
print("\n[8] Pre-IPO tespiti...")
ipo_info = is_ticker_pre_ipo(ticker)
if ipo_info:
    print(f"  PRE-IPO: {ipo_info}")
else:
    print(f"  Halka açık (pre-IPO değil)")

# 9. Projection engine — NVDA mature profile
print("\n[9] 5-yıllık projection engine...")

# NVDA için canlı veriden değerleri al
revenue_ttm = ratios.get('priceToEarningsRatioTTM')  # placeholder; gerçek revenue lazım
# Income statement'tan al
income = get("income-statement", symbol=ticker, period="annual", limit=2)
if income:
    revenue_ttm = income[0]['revenue']
    revenue_prev = income[1]['revenue']
    revenue_yoy = (revenue_ttm / revenue_prev) - 1
    print(f"  Revenue TTM (annual): ${revenue_ttm/1e9:.2f}B (YoY +{revenue_yoy*100:.1f}%)")

shares_basic = profile.get('sharesOutstanding') or (quote['marketCap'] / quote['price'])
print(f"  Shares: {shares_basic/1e9:.2f}B")

# Profile tespit
profile_key = detect_margin_profile(
    sector_key='semicon_design',
    current_op_margin=ratios['operatingProfitMarginTTM'],
    revenue_yoy_growth=revenue_yoy,
)
print(f"  Profile: {profile_key}")

# Revenue projection (analist konsensüs yoktur şimdilik - büyüme oranı bazlı)
revenues = project_revenue_5y(
    revenue_ttm=revenue_ttm,
    revenue_yoy_growth=revenue_yoy,
    ttm_year=2025,  # NVDA FY ending Jan 2025 = "2025 fiscal"
)
print("\n  Revenue trajectory:")
for y, r in revenues:
    print(f"    {y}: ${r/1e9:.2f}B")

# P&L projection
pnl = project_pnl_5y(
    revenue_list=revenues,
    profile_key=profile_key,
    shares_basic=shares_basic,
)

print()
print("=" * 80)
print(f"NVDA — 5 YILLIK P&L PROJEKSİYONU ({profile_key})")
print("=" * 80)
print(format_pnl_table_markdown(pnl))

# Multiples
mults = project_multiples_5y(
    pnl_table=pnl,
    current_price=quote['price'],
    shares_basic=shares_basic,
    current_cash=keymet.get('cashAndShortTermInvestmentsTTM', 0) or 40e9,
    current_debt=keymet.get('totalDebtTTM', 0) or 10e9,
)

print()
print("=" * 80)
print(f"NVDA — 5 YILLIK FORWARD ÇARPANLAR")
print("=" * 80)
print(format_multiples_table_markdown(mults, quote['price']))

# Normalization
norm = detect_normalization_year(mults, sector_median_pe=pe, sector_median_ev_sales=8)
print()
print("=" * 80)
print(f"NORMALİZASYON YORUMU")
print("=" * 80)
print(format_normalization_summary(norm, mults, sector_label=f'semicon medyanı {pe:.0f}x'))

print("\n✅ NVDA live test tamamlandı")
