#!/usr/bin/env python3
"""Swing entry scan ciktisini JSON'a donusturur.

Cikti formati:
  [ 1/34] CAT... GiRiS (tenkan_bounce)
  [ 2/34] WDC... -
"""
import json, re, sys
from datetime import datetime

entry_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/swing_entry.txt'
out_file   = sys.argv[2] if len(sys.argv) > 2 else 'data/swing_entry_signals.json'

try:
    result = open(entry_file, encoding='utf-8').read()
except FileNotFoundError:
    result = ''

# [ X/Y] SYM... GiRiS pattern
SIGNAL_PAT = re.compile(
    r'\[\s*\d+/\d+\]\s+([A-Z]{1,6})\.{2,}.*GİRİŞ',
    re.UNICODE
)

giris_sinyalleri = []
for line in result.split('\n'):
    m = SIGNAL_PAT.search(line)
    if m:
        sym = m.group(1).strip()
        if sym and sym not in giris_sinyalleri:
            giris_sinyalleri.append(sym)

# Detay bilgileri de cek (fiyat, stop, hedef, RSI)
detaylar = []
detail_lines = result.split('\n')
i = 0
while i < len(detail_lines):
    line = detail_lines[i]
    # "CAT    $ 790.66 $ 730.35   7.6% $ 941.43   73 ..." formatı
    m = re.match(r'^([A-Z]{1,6})\s+\$\s*([\d.]+)\s+\$\s*([\d.]+)\s+([\d.]+)%\s+\$\s*([\d.]+)\s+(\d+)', line)
    if m:
        sym = m.group(1)
        if sym in giris_sinyalleri:
            # Sonraki satırda Adet bilgisi var
            adet_line = detail_lines[i+1] if i+1 < len(detail_lines) else ''
            adet_m = re.search(r'Adet:\s*(\d+)', adet_line)
            adet = int(adet_m.group(1)) if adet_m else None
            detaylar.append({
                'sembol':  sym,
                'fiyat':   float(m.group(2)),
                'stop':    float(m.group(3)),
                'stop_pct': float(m.group(4)),
                'hedef':   float(m.group(5)),
                'rsi':     int(m.group(6)),
                'adet':    adet,
            })
    i += 1

data = {
    'tarih':            datetime.now().isoformat(),
    'toplam_taranan':   0,
    'giris_sayisi':     len(giris_sinyalleri),
    'giris_sinyalleri': giris_sinyalleri,
    'detaylar':         detaylar,
    'ham_cikti':        result,
}

# toplam_taranan bul
m_total = re.search(r'\[SwingEntry\]\s+(\d+)\s+hisse taranıyor', result)
if m_total:
    data['toplam_taranan'] = int(m_total.group(1))

with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Taranan: {data["toplam_taranan"]} | Sinyal: {len(giris_sinyalleri)} → {giris_sinyalleri}')
for d in detaylar:
    print(f'  {d["sembol"]:6} fiyat:${d["fiyat"]:.2f} stop:${d["stop"]:.2f} ({d["stop_pct"]}%) hedef:${d["hedef"]:.2f} RSI:{d["rsi"]} adet:{d["adet"]}')
