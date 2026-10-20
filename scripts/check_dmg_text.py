#!/bin/python
# Lists single-box description texts (<SFF>, no box breaks in the Japanese) that need more than
# two lines with the fixed width font used on the original Game Boy. Give those a short version
# in the DMG column (5th column) of text/dialog/TextSectionNN.csv.
import csv
import glob
import os
import sys

sys.path.append(os.path.dirname(__file__))
from textcodec import Codec

codec = Codec(widths_path=os.path.join(os.path.dirname(__file__), '..', 'build', 'gfx', 'VWFFont.widths'))
problems = 0
for path in sorted(glob.glob(os.path.join(os.path.dirname(__file__), '..', 'text', 'dialog', '*.csv'))):
    for row in list(csv.reader(open(path, encoding='utf-8')))[1:]:
        if len(row) < 4 or not row[3] or '<SFF>' not in row[2] or '<CF>' in row[2]:
            continue
        text = row[4] if len(row) > 4 and row[4] else row[3]
        if 0xC4 in codec.layout(text, fixed=True):
            problems += 1
            print(f'{os.path.basename(path)} {row[0]}: {text}')
print(f'{problems} texts need a DMG version')
