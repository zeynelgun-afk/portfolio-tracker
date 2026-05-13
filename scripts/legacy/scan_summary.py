#!/usr/bin/env python3
"""Sabah tarama sonuçlarının özetini ekrana yazar."""
import json
import os

lines = []
for mode in ['balanced', 'dividend', 'aggressive']:
    fname = f'data/daily_scan_{mode}.json'
    if os.path.exists(fname):
        try:
            with open(fname) as f:
                d = json.load(f)
            ekle = d.get('ekle_adaylari', '?')
            izle = d.get('izle_adaylari', '?')
            lines.append(f"{mode}: {ekle} EKLE / {izle} İZLE")
        except Exception as e:
            lines.append(f"{mode}: hata ({e})")

if lines:
    print("=== TARAMA ÖZET ===")
    for l in lines:
        print(f"  {l}")
else:
    print("Tarama çıktısı bulunamadı.")
