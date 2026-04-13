#!/usr/bin/env python3
"""Swing entry scan çıktısını JSON'a dönüştürür."""
import json, sys
from datetime import datetime

entry_file = sys.argv[1] if len(sys.argv) > 1 else '/tmp/swing_entry.txt'
out_file   = sys.argv[2] if len(sys.argv) > 2 else 'data/swing_entry_signals.json'

try:
    result = open(entry_file).read()
except FileNotFoundError:
    result = ''

data = {
    'tarih':           datetime.now().isoformat(),
    'ham_cikti':       result,
    'giris_sinyalleri': []
}
for line in result.split('\n'):
    if ('GİRİŞ' in line or 'GIRIS' in line) and ('✅' in line or 'ok' in line.lower()):
        parts = line.strip().split()
        if parts:
            data['giris_sinyalleri'].append(parts[0])

with open(out_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Sinyaller: {data["giris_sinyalleri"]}')
