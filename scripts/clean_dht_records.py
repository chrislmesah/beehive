"""Clean existing data/dht_records.json by removing transient fields and
discarding incomplete records.

This script will:
 - Remove any top-level `error` keys from records.
 - Discard records where `temperature_c` or `humidity` is missing or null.

Run: python scripts/clean_dht_records.py
"""
from pathlib import Path
import json

ROOT = Path(__file__).resolve().parents[1]
RECORDS = ROOT / 'data' / 'dht_records.json'

if not RECORDS.exists():
    print('No records file found at', RECORDS)
    raise SystemExit(0)

with RECORDS.open('r', encoding='utf-8') as f:
    try:
        records = json.load(f)
    except Exception as e:
        print('Failed to parse JSON:', e)
        raise SystemExit(1)

cleaned = []
for r in records:
    # Skip incomplete records
    if r.get('temperature_c') is None or r.get('humidity') is None:
        continue
    # Remove transient keys
    r.pop('error', None)
    r.pop('motion_error', None)
    cleaned.append(r)

with RECORDS.open('w', encoding='utf-8') as f:
    json.dump(cleaned, f, indent=2, ensure_ascii=False)

print(f'Cleaned {len(records)} -> {len(cleaned)} records')
