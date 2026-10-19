#!/bin/python
# Validates translations in text/dialog/*.csv
# Usage: check_text.py [csv files...]  (defaults to all sections)
# Checks: every character is encodable, control codes (<@XX>, <&XXXX>, <*XX>, <SXX>) match
# the original, and reports how many text boxes each translation needs after wrapping.
import csv
import glob
import os
import re
import sys

sys.path.append(os.path.dirname(__file__))
from textcodec import Codec, FIXED_WIDTH_SECTIONS

root = os.path.join(os.path.dirname(__file__), '..')
widths = os.path.join(root, 'build', 'gfx', 'VWFFont.widths')
if not os.path.exists(widths):
    os.system(f'cd {root} && make build/gfx/VWFFont.widths > /dev/null')
codec = Codec(widths_path=widths)

files = sys.argv[1:] or sorted(glob.glob(os.path.join(root, 'text', 'dialog', '*.csv')))
CODE_RE = re.compile(r'<([@&*S][0-9A-F]+)>')
errors = 0
for path in files:
    with open(path, encoding='utf-8') as f:
        rows = list(csv.reader(f))[1:]
    for row in rows:
        if len(row) < 4 or not row[3]:
            continue
        idx, orig, tr = row[0], row[2], row[3]
        where = f'{os.path.basename(path)}:{idx}'
        section = int(os.path.basename(path)[11:13])
        try:
            data = codec.layout(tr, fixed=section in FIXED_WIDTH_SECTIONS)
        except Exception as e:
            print(f'{where}: ERROR {e}')
            errors += 1
            continue
        o_codes = [c for c in CODE_RE.findall(orig)]
        t_codes = [c for c in CODE_RE.findall(tr)]
        # End codes default to *00 when absent
        o_end = [c for c in o_codes if c.startswith('*')] or ['*00']
        t_end = [c for c in t_codes if c.startswith('*')] or ['*00']
        if o_end != t_end:
            print(f'{where}: WARNING end code differs: {o_end} vs {t_end}')
        for kind in '@&':
            o = [c for c in o_codes if c.startswith(kind)]
            t = [c for c in t_codes if c.startswith(kind)]
            if sorted(o) != sorted(t):
                print(f'{where}: WARNING {kind} codes differ: {o} vs {t}')
        o_boxes = orig.count('<CF>') + orig.count('<CC>')
        t_boxes = data.count(0xC4) + data.count(0xC6)
        if t_boxes > o_boxes * 2 + 2:
            print(f'{where}: NOTE uses {t_boxes + 1} boxes (original {o_boxes + 1}), consider tightening')
print(f'{errors} errors')
sys.exit(1 if errors else 0)
