#!/bin/python
# Applies translations from a JSON file {"<Index hex>": "<English>"} to a dialog csv.
# Usage: apply_translations.py <csv> <json>
import csv
import json
import sys

path, js = sys.argv[1:3]
tr = json.load(open(js, encoding='utf-8'))
tr = {k.upper().zfill(3): v for k, v in tr.items()}
with open(path, encoding='utf-8') as f:
    rows = list(csv.reader(f))
n = 0
for r in rows[1:]:
    if r[0].upper() in tr:
        r[3] = tr[r[0].upper()]
        n += 1
with open(path, 'w', encoding='utf-8', newline='') as f:
    csv.writer(f, lineterminator='\n').writerows(rows)
print(f'Applied {n} translations to {path}')
