#!/usr/bin/env python3
"""
session_watchlist_scan.py — Finzora AI
Seans içi hafif tarayıcı: sadece watchlist + portföy pozisyonları
Süre: ~5-10 saniye | Seans içi her FAZ değişiminde çalıştır

Ne yapar:
  1. Watchlist hisselerini canlı fiyatla günceller
  2. Stop-loss mesafelerini hesaplar
  3. RSI değişimlerini kontrol eder (K-11/K-09 uyarısı)
  4. Sektör momentumunu özetler
  5. daily_full_scan.json'dan bugünkü en iyi adayları filtreler

Kullanım:
  python3 scripts/session_watchlist_scan.py              # standart
  python3 scripts/session_watchlist_scan.py --alert-only # sadece uyarılar
"""

import os
import json, urllib.request, time, argparse
from datetime import datetime

API_KEY = os.environ.get("FMP_API_KEY", "")
BASE    = 'https://financialmodelingprep.com/stable'

def fetch(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read())
    except:
        return None

def run(alert_only=False):
    t0 = time.time()

    # ── 1. Watchlist sembollerini yükle ─────────────────────────────────────
    with open('data/watchlist.json') as f:
        wl = json.load(f)
    watchlist_syms = [e.get('sembol', e.get('symbol','')) for e in wl.get('izleme_listesi', []) if e.get('sembol', e.get('symbol',''))]
    wl_map = {e.get('sembol', e.get('symbol','')): e for e in wl.get('izleme_listesi', [])}

    # ── 2. Portföy pozisyonlarını yükle ─────────────────────────────────────
    portfolio_positions = {}
    for pname, fname in [('dengeli','balanced'), ('agresif','aggressive'), ('temettu','dividend')]:
        try:
            with open(f'data/portfolios/{fname}.json') as f:
                p = json.load(f)
            for pos in p.get('pozisyonlar', []):
                sym = pos.get('sembol')
                if sym:
                    portfolio_positions[sym] = {
                        'portfoy': pname,
                        'maliyet': pos.get('maliyet_baz', 0),
                        'adet': pos.get('adet', 0),
                        'stop': pos.get('stop_loss'),
                        'hedef': pos.get('hedef_fiyat'),
                    }
        except:
            pass

    # ── 3. Aktif swing pozisyonlar ───────────────────────────────────────────
    swing_syms = []
    try:
        with open('data/swing/active.json') as f:
            sw = json.load(f)
        for t in sw.get('active_trades', []):
            swing_syms.append(t.get('symbol', ''))
    except:
        pass

    # ── 4. Tüm sembolleri birleştir ──────────────────────────────────────────
    all_syms = list(set(
        list(portfolio_positions.keys()) +
        watchlist_syms +
        swing_syms
    ))

    if not all_syms:
        print("Portföy ve watchlist boş.")
        return

    # ── 5. Batch fiyat ──────────────────────────────────────────────────────
    url = f'{BASE}/batch-quote?symbols={",".join(all_syms[:100])}&apikey={API_KEY}'
    quotes = fetch(url) or []
    q_map = {q['symbol']: q for q in quotes}

    now = datetime.now().strftime('%H:%M')

    # ── 6. PORTFÖY ÖZET ──────────────────────────────────────────────────────
    if not alert_only:
        print(f"\n{'─'*70}")
        print(f"⚡ SEANS İÇİ TARAMA — {now}")
        print(f"{'─'*70}")
        print(f"\n📦 PORTFÖY POZİSYONLARI")
        print(f"{'SYM':5} | {'PORTFÖY':8} | {'MALİYET':>8} | {'CANLI':>8} | {'K/Z%':>7} | {'STOP':>8} | {'MESAFE%':>8} | UYARI")
        print("─" * 80)

    alerts = []

    for sym, pos in portfolio_positions.items():
        q = q_map.get(sym, {})
        price = q.get('price', 0)
        prev  = q.get('previousClose', 0)
        chg   = ((price - prev) / prev * 100) if prev else 0
        maliyet = pos['maliyet']
        kz_pct = ((price - maliyet) / maliyet * 100) if maliyet else 0
        stop = pos.get('stop')
        stop_mesafe = ((price - stop) / stop * 100) if stop and price else None
        hedef = pos.get('hedef')
        hedef_mesafe = ((hedef - price) / price * 100) if hedef and price else None

        # Uyarı üret
        warn = ''
        if stop and price and price <= stop:
            warn = '🔴 K-06 STOP TETİK!'
            alerts.append(f"K-06: {sym} ${price:.2f} ≤ stop ${stop:.2f}")
        elif stop_mesafe is not None and 0 < stop_mesafe < 2:
            warn = '⚠️ K-09 STOP YAKIN'
            alerts.append(f"K-09: {sym} stop'a %{stop_mesafe:.1f} mesafe")
        elif kz_pct >= 15:
            warn = '💡 K-11 KÂR KİLİDİ'
        elif chg < -3:
            warn = '⚠️ BUGÜN -%{:.1f}'.format(abs(chg))

        if not alert_only:
            stop_s = f"${stop:.2f}" if stop else "—"
            mes_s  = f"%{stop_mesafe:.1f}" if stop_mesafe else "—"
            print(f"{sym:5} | {pos['portfoy']:8} | ${maliyet:>7.2f} | ${price:>7.2f} | {kz_pct:>+6.1f}% | {stop_s:>8} | {mes_s:>8} | {warn}")

    # ── 7. WATCHLIST GÜNCEL FİYATLAR ─────────────────────────────────────────
    if not alert_only:
        print(f"\n📋 İZLEME LİSTESİ")
        print(f"{'SYM':5} | {'CANLI':>8} | {'GÜN%':>6} | {'URG':>4} | {'PORTFÖY':>8} | TETİKLEYİCİ")
        print("─" * 75)

    for sym in watchlist_syms:
        q = q_map.get(sym, {})
        price = q.get('price', 0)
        prev  = q.get('previousClose', 0)
        chg   = ((price - prev) / prev * 100) if prev else 0
        info  = wl_map.get(sym, {})
        urg   = info.get('urgency', '?')
        ptf   = info.get('hedef_portfoy', '?')
        tetik = info.get('giris_tetikleyici', '')[:35]

        if not alert_only:
            print(f"{sym:5} | ${price:>7.2f} | {chg:>+5.1f}% | {urg:>4} | {ptf:>8} | {tetik}")

    # ── 8. GÜNÜN SCANI'NDAN TOP 5 ADAY ──────────────────────────────────────
    if not alert_only:
        try:
            with open('data/daily_full_scan.json') as f:
                scan = json.load(f)
            results = scan.get('sonuclar', [])
            K13_F = {'Energy','Utilities','Healthcare','Consumer Defensive',
                     'Communication Services','Financial Services'}
            # K04 + K13 faydalanıcı + düşmeyen + skor en yüksek
            prime = [r for r in results
                     if r.get('k04_pass') and r.get('sector') in K13_F
                     and not r.get('declining_eps') and r.get('score', 0) >= 14][:5]
            if prime:
                print(f"\n🌟 BUGÜNKÜ TARAMADAN TOP 5 (K04✅+K13🟢+skor≥14)")
                print(f"{'SYM':5} | {'P/E':>5} | {'PEG':>5} | {'RSI':>4} | {'ROIC':>5} | {'FCF':>5} | SEKTÖR")
                print("─" * 60)
                for r in prime:
                    fpe = f"{r['fwd_pe']:.0f}x" if r.get('fwd_pe') else "?"
                    pg  = f"{r['peg']:.2f}" if r.get('peg') else "?"
                    rsi = f"{r['rsi']:.0f}" if r.get('rsi') else "?"
                    roi = f"{r.get('roic',0):.0f}%"
                    fcf = f"{r.get('fcf_yield',0):.0f}%"
                    print(f"{r['symbol']:5} | {fpe:>5} | {pg:>5} | {rsi:>4} | {roi:>5} | {fcf:>5} | {r['sector'][:20]}")
            scan_date = scan.get('tarih', '?')
            print(f"\n  (Tarama tarihi: {scan_date} | {scan.get('toplam_taranan',0)} hisse tarandı)")
        except:
            print("\n  [Tarama verisi bulunamadı — sabah taraması çalıştırın]")

    # ── 9. ÖZET ──────────────────────────────────────────────────────────────
    elapsed = time.time() - t0
    print(f"\n{'─'*70}")

    if alerts:
        print(f"\n🚨 AKTİF UYARILAR ({len(alerts)} adet):")
        for a in alerts:
            print(f"  → {a}")
    else:
        print(f"✅ Uyarı yok. Tüm pozisyonlar güvende.")

    print(f"⏱  {elapsed:.1f}s | {len(all_syms)} sembol kontrol edildi | {now} TR\n")

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--alert-only', action='store_true', help='Sadece uyarıları göster')
    args = p.parse_args()
    run(alert_only=args.alert_only)
