#!/bin/python
# Builds the 1bpp VWF font (256 glyphs indexed by the English encoding) and its width table.
# Glyphs come from the Medarot 3 translation's VWF font (ASCII ordered), symbols missing from it
# are taken from Medarot 2's own font.
# Also builds the fixed width 2bpp font for codes $00-$7F (replacing the font in bank $3B)
# Usage: build_font.py <M3Font.1bpp.png> <baserom> <charmap_en.tbl> <out .1bpp> <out .widths> <out fixed .2bpp>
import os
import sys
from PIL import Image

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils

m3_png, rom_path, charmap_path, out_font, out_widths, out_fixed = sys.argv[1:7]

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

# Narrow font (used for names that would not fit their field otherwise)
M3_NARROW_WIDTHS = [
    2, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7,
    7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 7, 6, 5, 6, 5,
    2, 1, 3, 5, 4, 5, 5, 2, 2, 2, 3, 5, 2, 4, 1, 4,
    4, 2, 4, 4, 4, 4, 4, 4, 4, 4, 1, 2, 4, 4, 4, 4,
    5, 4, 4, 4, 4, 4, 4, 4, 4, 3, 4, 4, 4, 5, 4, 4,
    4, 4, 4, 4, 5, 4, 5, 5, 5, 5, 4, 2, 4, 2, 3, 4,
    2, 3, 3, 3, 3, 3, 2, 3, 3, 1, 2, 3, 1, 5, 3, 3,
    3, 3, 3, 3, 3, 3, 4, 5, 4, 3, 3, 3, 1, 3, 6, 7,
]
narrow_im = Image.open(os.path.join(os.path.dirname(m3_png), 'M3NarrowFont.1bpp.png')).convert('L')
narrow = [list(g) for g in font]
narrow_widths = list(widths)
for code, ch in charmap.items():
    idx = M3_SPECIAL.get(ch, ord(ch) if len(ch) == 1 and 0x20 <= ord(ch) < 0x7F else None)
    if idx is None:
        continue
    gx, gy = (idx % 16) * 8, (idx // 16) * 8
    rows = []
    for y in range(8):
        b = 0
        for x in range(8):
            if narrow_im.getpixel((gx + x, gy + y)) < 128:
                b |= 0x80 >> x
        rows.append(b)
    narrow[code], narrow_widths[code] = rows, M3_NARROW_WIDTHS[idx]
narrow_widths[0x00] = M3_NARROW_WIDTHS[0x20]
base = os.path.splitext(out_font)[0]
with open(base.replace('VWFFont', 'VWFNarrowFont') + '.1bpp', 'wb') as f:
    for g in narrow:
        f.write(bytes(g))
with open(base.replace('VWFFont', 'VWFNarrowFont') + '.widths', 'wb') as f:
    f.write(bytes(narrow_widths))

os.makedirs(os.path.dirname(out_font), exist_ok=True)
with open(out_font, 'wb') as f:
    for g in font:
        f.write(bytes(g))
with open(out_widths, 'wb') as f:
    f.write(bytes(widths))

# Fixed width font: one glyph per tile. Letters and most punctuation come from the Medarot 1
# translation's 8x8 font, everything else from the VWF glyphs offset by one pixel.
M1_ORDER = (list('ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz') +
            ['"', '#', '%', '&', "'", ',', '-', '.', '/', ':', '~', '(', ')', '*', '+', '^', '_', '`',
             '←', '…', '@', '♥', '♦', '♣', '♠', '·', '¥', '$', ';'])
m1 = Image.open(os.path.join(os.path.dirname(m3_png), 'M1FixedFont.png')).convert('L')
def m1_glyph(idx):
    gx, gy = (idx % 16) * 8, (idx // 16) * 8
    rows = []
    for y in range(8):
        b = 0
        for x in range(8):
            if m1.getpixel((gx + x, gy + y)) < 128:
                b |= 0x80 >> x
        rows.append(b)
    return rows
with open(out_fixed, 'wb') as f:
    for code in range(0x80):
        ch = charmap.get(code)
        if ch in ('“', '”'):
            ch = '"'
        if ch in M1_ORDER:
            g = m1_glyph(M1_ORDER.index(ch))
        elif code == 0x73:
            # ◆ marker after names in status screens: 7 pixels wide with a blank left column,
            # so names that fill their field don't touch it
            g = [0x08, 0x1C, 0x3E, 0x7F, 0x7F, 0x3E, 0x1C, 0x08]
        else:
            g = font[code]
            if code in charmap and widths[code] <= 6:
                g = [r >> 1 for r in g]
        for r in g:
            f.write(bytes([r, r]))
