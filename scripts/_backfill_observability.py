#!/usr/bin/env python3
"""
Backfill geçmiş veri → events.jsonl
=====================================
Observability kurulmadan önce gerçekleşmiş trade'leri ve swing kapanışlarını
events.jsonl dosyasına ekler. TEK SEFERLİK çalıştırılır.

Kaynaklar:
  - data/transactions.csv    → trade events (BUY/SELL)
  - data/swing/closed.json   → decision + trade events (her kapanan swing için)

Önemli:
  - Mevcut events.jsonl'e EKLER (üzerine yazmaz)
  - Event id'leri backfill-{hash} prefix'i ile — gerçek run event'lerinden ayırt edilebilir
  - Idempotent: aynı satır varsa atlar
"""

import csv
import json
import hashlib
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
EVENTS_JSONL = REPO_ROOT / "logs" / "events.jsonl"
TX_CSV = REPO_ROOT / "data" / "transactions.csv"
CLOSED_JSON = REPO_ROOT / "data" / "swing" / "closed.json"

EVENTS_JSONL.parent.mkdir(parents=True, exist_ok=True)


def _stable_id(prefix: str, *parts) -> str:
    """Input'lardan deterministik 12-karakter id üret."""
    raw = prefix + "|" + "|".join(str(p) for p in parts)
    return "bf-" + hashlib.md5(raw.encode()).hexdigest()[:9]


def _existing_ids() -> set:
    """Zaten yazılmış event id'lerini oku."""
    ids = set()
    if not EVENTS_JSONL.exists():
        return ids
    with EVENTS_JSONL.open(encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                if "id" in obj:
                    ids.add(obj["id"])
            except Exception:
                pass
    return ids


def _append(event: dict) -> None:
    """Bir event'i JSONL'ye ekle."""
    with EVENTS_JSONL.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def backfill_transactions(existing_ids: set) -> tuple[int, int]:
    """
    transactions.csv → trade events.
    Returns: (eklenen, atlanan)
    """
    if not TX_CSV.exists():
        print(f"Atla: {TX_CSV} yok")
        return 0, 0

    added, skipped = 0, 0
    with TX_CSV.open(encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # ID: tarih+action+sembol+shares+price → benzersiz
            eid = _stable_id(
                "tx",
                row.get("date", ""),
                row.get("action", ""),
                row.get("symbol", ""),
                row.get("shares", ""),
                row.get("price", ""),
            )
            if eid in existing_ids:
                skipped += 1
                continue

            # Tarih → ISO 8601 (gün bazlı, saat yok)
            date_str = row.get("date", "")
            try:
                ts_iso = datetime.strptime(date_str, "%Y-%m-%d").isoformat() + "Z"
            except ValueError:
                ts_iso = datetime.now().isoformat() + "Z"

            try:
                shares = float(row.get("shares", 0) or 0)
                price = float(row.get("price", 0) or 0)
                total = float(row.get("total", 0) or 0)
            except ValueError:
                skipped += 1
                continue

            event = {
                "id": eid,
                "ts": ts_iso,
                "type": "trade",
                "backfill": True,
                "action": row.get("action", ""),
                "sembol": row.get("symbol", ""),
                "shares": shares,
                "price": price,
                "total": total,
                "reason": row.get("reason", ""),
                "success": 1,
            }
            _append(event)
            existing_ids.add(eid)
            added += 1

    return added, skipped


def backfill_closed_swings(existing_ids: set) -> tuple[int, int]:
    """
    data/swing/closed.json → decision + trade events.
    Her kapatılan swing için giriş+çıkış kaydı.
    """
    if not CLOSED_JSON.exists():
        print(f"Atla: {CLOSED_JSON} yok")
        return 0, 0

    try:
        data = json.loads(CLOSED_JSON.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Hata: closed.json okunamadı: {e}")
        return 0, 0

    kapatilan = data.get("kapatilan_pozisyonlar", [])
    added, skipped = 0, 0

    for p in kapatilan:
        sembol = p.get("sembol", "")
        entry_date = p.get("giris_tarihi", "")
        exit_date = p.get("cikis_tarihi", "")
        # adet int veya string olabilir; normalize et
        _raw_shares = p.get("adet", 0)
        try:
            shares = float(_raw_shares) if _raw_shares else 0
        except (ValueError, TypeError):
            shares = 0
        entry_price = p.get("giris_fiyati", 0)
        exit_price = p.get("cikis_fiyati", 0)
        reason = p.get("cikis_nedeni", "") or p.get("giris_nedeni", "")
        pnl_pct = p.get("kar_zarar_yuzde", 0)
        lessons = p.get("dersler") or p.get("lessons", "")

        # Giriş (BUY) event
        if entry_date and entry_price:
            eid = _stable_id("swing_in", entry_date, sembol, entry_price)
            if eid not in existing_ids:
                try:
                    ts = datetime.strptime(entry_date, "%Y-%m-%d").isoformat() + "Z"
                except ValueError:
                    ts = datetime.now().isoformat() + "Z"
                _append({
                    "id": eid,
                    "ts": ts,
                    "type": "trade",
                    "backfill": True,
                    "action": "BUY",
                    "portfoy": "swing",
                    "sembol": sembol,
                    "shares": shares,
                    "price": entry_price,
                    "total": round(shares * entry_price, 2),
                    "reason": p.get("giris_nedeni", "")[:300],
                    "success": 1,
                })
                existing_ids.add(eid)
                added += 1
            else:
                skipped += 1

        # Çıkış (SELL) event
        if exit_date and exit_price:
            eid = _stable_id("swing_out", exit_date, sembol, exit_price)
            if eid not in existing_ids:
                try:
                    ts = datetime.strptime(exit_date, "%Y-%m-%d").isoformat() + "Z"
                except ValueError:
                    ts = datetime.now().isoformat() + "Z"
                _append({
                    "id": eid,
                    "ts": ts,
                    "type": "trade",
                    "backfill": True,
                    "action": "SELL",
                    "portfoy": "swing",
                    "sembol": sembol,
                    "shares": shares,
                    "price": exit_price,
                    "total": shares * exit_price if isinstance(shares, (int, float)) else 0,
                    "reason": f"{reason[:150]} | PnL: {pnl_pct}%",
                    "pnl_pct": pnl_pct,
                    "lessons": lessons[:500] if isinstance(lessons, str) else "",
                    "success": 1,
                })
                existing_ids.add(eid)
                added += 1
            else:
                skipped += 1

    return added, skipped


def rebuild_sqlite():
    """SQLite DB'yi JSONL'den yeniden kur."""
    import sys
    sys.path.insert(0, str(REPO_ROOT / "agent"))
    try:
        from observability import _index_to_sqlite, DB_PATH
        # Eski DB'yi sil
        DB_PATH.unlink(missing_ok=True)
        count = 0
        with EVENTS_JSONL.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                    _index_to_sqlite(event)
                    count += 1
                except Exception as e:
                    print(f"Atla (parse hatası): {e}")
        print(f"SQLite yeniden kuruldu: {count} event")
    except Exception as e:
        print(f"SQLite rebuild atlandı: {e}")


def main():
    print("=" * 60)
    print("Backfill observability events")
    print("=" * 60)

    existing = _existing_ids()
    print(f"\nMevcut event id sayısı: {len(existing)}")

    print("\n--- transactions.csv ---")
    added_tx, skipped_tx = backfill_transactions(existing)
    print(f"Eklenen: {added_tx}, Atlanan (zaten var): {skipped_tx}")

    print("\n--- swing/closed.json ---")
    added_sw, skipped_sw = backfill_closed_swings(existing)
    print(f"Eklenen: {added_sw}, Atlanan: {skipped_sw}")

    total_added = added_tx + added_sw
    print(f"\nToplam eklenen event: {total_added}")
    print(f"events.jsonl yeni satır sayısı:", sum(1 for _ in EVENTS_JSONL.open()) if EVENTS_JSONL.exists() else 0)

    if total_added > 0:
        print("\n--- SQLite rebuild ---")
        rebuild_sqlite()


if __name__ == "__main__":
    main()
