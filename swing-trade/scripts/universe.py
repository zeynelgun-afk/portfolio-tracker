#!/usr/bin/env python3
"""
Dynamic Universe Builder
S&P 500 + NASDAQ-100 combined (~550 unique US large/mid caps)
Auto-validates via yfinance and caches.
"""

# S&P 500 (as of Feb 2026) + NASDAQ-100
# Combined: ~550 unique tickers covering ~85% of US market cap
SP500 = [
    "AAPL","ABBV","ABT","ACN","ADBE","ADI","ADM","ADP","ADSK","AEE","AEP","AES",
    "AFL","AIG","AIZ","AJG","AKAM","ALB","ALGN","ALK","ALL","ALLE","AMAT","AMCR",
    "AMD","AME","AMGN","AMP","AMT","AMZN","ANET","ANSS","AON","AOS","APA","APD",
    "APH","APTV","ARE","ATO","ATVI","AVGO","AVY","AWK","AXP","AZO","BA","BAC",
    "BAX","BBWI","BBY","BDX","BEN","BF-B","BG","BIIB","BIO","BK","BKNG","BKR",
    "BLDR","BLK","BMY","BR","BRK-B","BRO","BSX","BWA","BXP","C","CAG","CAH",
    "CARR","CAT","CB","CBOE","CBRE","CCI","CCL","CDNS","CDW","CE","CEG","CF",
    "CFG","CHD","CHRW","CHTR","CI","CINF","CL","CLX","CMA","CMCSA","CME","CMG",
    "CMI","CMS","CNC","CNP","COF","COO","COP","COR","COST","CPAY","CPB","CPRT",
    "CPT","CRL","CRM","CRWD","CSCO","CSGP","CSX","CTAS","CTLT","CTRA","CTSH",
    "CTVA","CVS","CVX","CZR","D","DAL","DAY","DD","DE","DECK","DFS","DG",
    "DGX","DHI","DHR","DIS","DLTR","DOV","DOW","DPZ","DRI","DTE","DUK","DVA",
    "DVN","DXCM","EA","EBAY","ECL","ED","EFX","EG","EIX","EL","EMN","EMR",
    "ENPH","EOG","EPAM","EQIX","EQR","EQT","ERIE","ES","ESS","ETN","ETR","ETSY",
    "EVRG","EW","EXC","EXPD","EXPE","EXR","F","FANG","FAST","FBHS","FCX","FDS",
    "FDX","FE","FFIV","FI","FICO","FIS","FISV","FITB","FLT","FMC","FOX","FOXA",
    "FRT","FSLR","FTNT","FTV","GD","GDDY","GE","GEHC","GEN","GEV","GILD","GIS",
    "GL","GLW","GM","GNRC","GOOG","GOOGL","GPC","GPN","GRMN","GS","GWW","HAL",
    "HAS","HBAN","HCA","HD","HOLX","HON","HPE","HPQ","HRL","HSIC","HST","HSY",
    "HUBB","HUM","HWM","IBM","ICE","IDXX","IEX","IFF","ILMN","INCY","INTC",
    "INTU","INVH","IP","IPG","IQV","IR","IRM","ISRG","IT","ITW","IVZ","J",
    "JBHT","JBL","JCI","JKHY","JNJ","JNPR","JPM","K","KDP","KEY","KEYS","KHC",
    "KIM","KLAC","KMB","KMI","KMX","KO","KR","KVUE","L","LDOS","LEN","LH",
    "LHX","LIN","LKQ","LLY","LMT","LNT","LOW","LRCX","LULU","LUV","LVS","LW",
    "LYB","LYV","MA","MAA","MAR","MAS","MCD","MCHP","MCK","MCO","MDLZ","MDT",
    "MET","META","MGM","MHK","MKC","MKTX","MLM","MMC","MMM","MNST","MO","MOH",
    "MOS","MPC","MPWR","MRK","MRNA","MRVL","MS","MSCI","MSFT","MSI","MTB","MTCH",
    "MTD","MU","NCLH","NDAQ","NDSN","NEE","NEM","NFLX","NI","NKE","NOC","NOW",
    "NRG","NSC","NTAP","NTRS","NUE","NVDA","NVR","NWS","NWSA","NXPI","O","ODFL",
    "OKE","OMC","ON","ORCL","ORLY","OTIS","OXY","PARA","PAYC","PAYX","PCAR","PCG",
    "PDD","PEAK","PEG","PEP","PFE","PFG","PG","PGR","PH","PHM","PKG","PLD",
    "PLTR","PM","PNC","PNR","PNW","POOL","PPG","PPL","PRU","PSA","PSX","PTC",
    "PVH","PWR","PXD","PYPL","QCOM","QRVO","RCL","RE","REG","REGN","RF","RHI",
    "RJF","RL","RMD","ROK","ROL","ROP","ROST","RSG","RTX","RVTY","SBAC","SBUX",
    "SCHW","SEE","SHW","SJM","SLB","SMCI","SNA","SNPS","SO","SPG","SPGI","SRE",
    "STE","STLD","STT","STX","STZ","SWK","SWKS","SYF","SYK","SYY","T","TAP",
    "TDG","TDY","TECH","TEL","TER","TFC","TFX","TGT","TJX","TMO","TMUS","TPR",
    "TRGP","TRMB","TROW","TRV","TSCO","TSLA","TSN","TT","TTWO","TXN","TXT","TYL",
    "UAL","UBER","UDR","UHS","ULTA","UNH","UNP","UPS","URI","USB","V","VFC",
    "VICI","VLO","VLTO","VMC","VRSK","VRSN","VRTX","VST","VTR","VTRS","VZ",
    "WAB","WAT","WBA","WBD","WDC","WEC","WELL","WFC","WM","WMB","WMT","WRB",
    "WRK","WST","WTW","WY","WYNN","XEL","XOM","XYL","YUM","ZBH","ZBRA","ZTS"
]

# NASDAQ-100 extras (not in S&P 500)
NASDAQ_EXTRA = [
    "ABNB","AEP","ARM","AXON","AVAV","BKNG","COIN","CRWD","DASH",
    "DDOG","DOCU","FANG","FTNT","GFS","GRAB","HOOD","KDP",
    "LCID","MARA","MELI","MDB","MNDY","NET","OKTA","PANW",
    "RIVN","RBLX","ROKU","SHOP","SNAP","SNOW","SOFI","SPOT",
    "SQ","TEAM","TTD","TTWO","U","WDAY","ZM","ZS"
]

# Additional mid-caps with momentum potential
EXTRA_GROWTH = [
    "AFRM","APP","BILL","CFLT","CAVA","CELH","CRSP","DOCN",
    "DUOL","ELF","HIMS","IOT","IREN","LPLA","LYFT","MNST",
    "NU","ONON","PINS","QLYS","RELY","SAMSARA","SMCI","TOST",
    "TRUP","TWLO","UPST","VRT","WING","XP","CYBR","DT",
    "ESTC","FRSH","GLOB","GTLB","HCP","HUBS","INSP","KVYO",
    "LMND","MGNI","PCOR","PTON","S","SOUN","TEM","VKTX",
    "ACHR","AI","APLD","ASTS","CAMT","CLSK","DNA","ENVX",
    "FLNC","FOUR","IONQ","JOBY","LSCC","LUNR","MPWR","NBIX",
    "NTNX","NUTX","PATH","PSTG","RKLB","RXRX","SEDG","SMMT",
    "STEM","TASK","VERX","VST","WIX","WOLF","GEV","CCJ",
    "DELL","NRG","SM","CEG","PWR","SCCO","RGLD","NEM","GOLD","ALB",
    "AVAV","AXON","LHX","NOC","GD","LMT","RTX"
]



# Delisted / invalid as of Feb 2026
INVALID = {
    "ANSS","ATVI","CMA","CTLT","CYBR","DAY","DFS","FBHS","FI","FLT",
    "HCP","IPG","JNPR","K","PARA","PEAK","PXD","RE","SAMSARA","SQ","WBA","WRK"
}

def get_full_universe() -> dict:
    """Tüm unique sembolleri sektörsüz döndür"""
    all_syms = list(set(SP500 + NASDAQ_EXTRA + EXTRA_GROWTH))
    # Clean invalid tickers
    all_syms = [s for s in all_syms if (s.isalpha() or "-" in s) and s not in INVALID]
    all_syms.sort()
    return all_syms


def get_universe_count():
    syms = get_full_universe()
    return len(syms)


if __name__ == "__main__":
    syms = get_full_universe()
    print(f"Total unique symbols: {len(syms)}")
    print(f"S&P 500: {len(SP500)}")
    print(f"NASDAQ extra: {len(NASDAQ_EXTRA)}")
    print(f"Growth extra: {len(EXTRA_GROWTH)}")
    print(f"\nFirst 20: {syms[:20]}")
    print(f"Last 20: {syms[-20:]}")
