#!/bin/python
# Builds the 1bpp VWF font (256 glyphs indexed by the English encoding) and its width table.
# Glyphs come from the Medarot 3 translation's VWF font (ASCII ordered), symbols missing from it
# are taken from Medarot 2's own font.
# Usage: build_font.py <M3Font.1bpp.png> <baserom> <charmap_en.tbl> <out .1bpp> <out .widths>
import os
import sys
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils

m3_png, rom_path, charmap_path, out_font, out_widths = sys.argv[1:6]

# Widths of the Medarot 3 VWF font (excluding the 1px spacing), ASCII order
M3_WIDTHS = [
    2, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6, 6, 7, 7,
    2, 1, 3, 5, 4, 5, 5, 2, 2, 2, 3, 5, 2, 4, 1, 4,
    4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 1, 2, 4, 4, 4, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5,
    5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 5, 2, 4, 2, 3, 4,
    2, 5, 4, 4, 4, 4, 4, 4, 4, 1, 2, 4, 1, 5, 4, 4,
    4, 4, 4, 4, 4, 4, 4, 5, 4, 4, 4, 3, 1, 3, 7, 7,
]

# Characters taken from the Medarot 3 font, mapped to their ASCII position in it
M3_SPECIAL = {'·': 0x1C, '♪': 0x1E, '¥': 0x1F, '♥': 0x7F, '“': ord('"'), '”': ord('"')}

im = Image.open(m3_png).convert('L')
def m3_glyph(idx):
    gx, gy = (idx % 16) * 8, (idx // 16) * 8
    rows = []
    for y in range(8):
        b = 0
        for x in range(8):
            if im.getpixel((gx + x, gy + y)) < 128:
                b |= 0x80 >> x
        rows.append(b)
    return rows

rom = open(rom_path, 'rb').read()
def m2_glyph(code):
    # Medarot 2 font: bank $3B, pointer table at $5AFB, 2bpp tiles
    base = utils.rom2realaddr(0x3B, 0x5AFB)
    ptr = rom[base + code * 2] | (rom[base + code * 2 + 1] << 8)
    addr = utils.rom2realaddr(0x3B, ptr)
    rows = []
    for y in range(8):
        lo, hi = rom[addr + y * 2], rom[addr + y * 2 + 1]
        rows.append(lo | hi)
    # Left align
    while rows and not any(r & 0x80 for r in rows) and any(rows):
        rows = [(r << 1) & 0xFF for r in rows]
    return rows

def measure(rows):
    w = 0
    for r in rows:
        for x in range(8):
            if r & (0x80 >> x):
                w = max(w, x + 1)
    return w

# Medarot 2 font codes for symbols that the Medarot 3 font lacks
M2_SYMBOLS = {'◈': 0x73, 'ᴱᴰ': 0x77, '↑': 0x78, '↓': 0x79, '←': 0x7A, '→': 0x7B, '×': 0x7C,
              'Ⓐ': 0x7E, 'Ⓑ': 0x7F, '゜': 0xF1, '゛': 0xF2, '▶': 0xF4, '▷': 0xF5}

charmap = utils.read_table(charmap_path)
font = [[0] * 8 for _ in range(256)]
widths = [0] * 256
for code, ch in charmap.items():
    if ch in M3_SPECIAL:
        idx = M3_SPECIAL[ch]
        font[code], widths[code] = m3_glyph(idx), M3_WIDTHS[idx]
    elif len(ch) == 1 and 0x20 <= ord(ch) < 0x7F:
        idx = ord(ch)
        font[code], widths[code] = m3_glyph(idx), M3_WIDTHS[idx]
    elif ch == '…':
        font[code] = [0, 0, 0, 0, 0, 0, 0b10101000, 0]
        widths[code] = 5
    elif ch == 'é':
        font[code] = [0b00100000, 0b01000000, 0b01100000, 0b10010000, 0b11110000, 0b10000000, 0b01110000, 0]
        widths[code] = 4
    elif ch in M2_SYMBOLS:
        g = m2_glyph(M2_SYMBOLS[ch])
        font[code], widths[code] = g, max(measure(g), 1)
    else:
        raise ValueError(f'No glyph for {code:02X}={ch}')

# Space is the M3 space width
widths[0x00] = M3_WIDTHS[0x20]

os.makedirs(os.path.dirname(out_font), exist_ok=True)
with open(out_font, 'wb') as f:
    for g in font:
        f.write(bytes(g))
with open(out_widths, 'wb') as f:
    f.write(bytes(widths))
