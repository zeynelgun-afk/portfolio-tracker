#!/usr/bin/env python3
"""
Events.jsonl merge: iki JSONL dosyasını id bazlı tekilleştirerek birleştirir.

Kullanım:
  python scripts/_merge_events_jsonl.py <file1> <file2> > merged.jsonl

Agent workflow tarafından upstream ile lokal JSONL'yi birleştirmek için kullanılır.
"""

import sys
import json


def main():
    if len(sys.argv) < 2:
        print("Kullanım: _merge_events_jsonl.py <file1> [<file2> ...]", file=sys.stderr)
        return 1

    seen = set()
    for path in sys.argv[1:]:
        try:
            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        obj = json.loads(line)
                        eid = obj.get("id")
                        if eid and eid in seen:
                            continue
                        if eid:
                            seen.add(eid)
                        print(line)
                    except json.JSONDecodeError:
                        # Bozuk satır — yine de yaz (güvenli tarafta)
                        print(line)
        except FileNotFoundError:
            # Dosya yoksa atla
            continue

    return 0


if __name__ == "__main__":
    sys.exit(main())
