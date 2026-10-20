#!/usr/bin/env python3
"""Builds the English versions of the tilesets that have Japanese text drawn into them.

usage: python3 scripts/tools/make_gfx.py [tileset ...]      (default: all)

Reads the original (decompressed) tilesets from doc/tilesets/ts_XXX.png and writes
gfx/tilesets/ts_XXX.png + ts_XXX.count, which `make` turns into the replacement tilesets
(scripts/build_tilesets.py).  Everything is generated, so the results are reproducible:
edit this script, not the PNGs.

The English is rendered with the fonts of the Medarot 3 translation (VWF fonts from
../medarot3/gfx/tilesets/patch, widths from its vwf.asm) or the Medarot 1 fixed-width font
the game patch uses for menus (gfx/patch/M1FixedFont.png).

Words are drawn into "strips": the list of tiles the tilemap shows side by side for that
word (in screen order).  Many Japanese labels share tiles between words (e.g. the same る
tile in もどる and おわる); `Canvas` remembers what each tile was set to and refuses to
write a different content into a tile that another word already uses, so such conflicts
are caught at build time and the layout has to be designed around them.
"""
import os
import re
import sys

from PIL import Image

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SRC_DIR = os.path.join(ROOT, 'doc', 'tilesets')
OUT_DIR = os.path.join(ROOT, 'gfx', 'tilesets')
M3 = os.path.abspath(os.path.join(ROOT, '..', 'medarot3'))
M3_PATCH_GFX = os.path.join(M3, 'gfx', 'tilesets', 'patch')
M3_VWF_ASM = os.path.join(M3, 'game', 'src', 'patch', 'vwf.asm')

WHITE, LIGHT, DARK, BLACK = 0, 1, 2, 3


def tileset_info():
    info = {}
    with open(os.path.join(SRC_DIR, 'index.txt')) as f:
        for line in f:
            p = line.split()
            if not p:
                continue
            fields = dict(x.split('=') for x in p[1:])
            info[int(p[0], 16)] = {'vram': int(fields['vram'], 16), 'tiles': int(fields['tiles'])}
    return info


INFO = tileset_info()


# ---------------------------------------------------------------------------------------
# Fonts

class Font:
    """8x8 glyph font: glyph(c) -> list of rows (each a list of 0/1), width = len(row)."""

    def __init__(self, png, widths=None, fixed_width=None, charmap=None):
        im = Image.open(png).convert('RGBA')
        self.px = im.load()
        self.cols = im.size[0] // 8
        self.widths = widths
        self.fixed_width = fixed_width
        self.charmap = charmap  # char -> glyph index (default: ASCII code)
        self.overrides = {}

    def index(self, c):
        if self.charmap is not None:
            return self.charmap[c]
        return ord(c)

    def width(self, c):
        if c in self.overrides:
            return len(self.overrides[c][0])
        if self.fixed_width:
            return self.fixed_width
        return self.widths[self.index(c)]

    def glyph(self, c):
        if c in self.overrides:
            return self.overrides[c]
        i = self.index(c)
        x0, y0 = (i % self.cols) * 8, (i // self.cols) * 8
        w = self.width(c)
        rows = []
        for y in range(8):
            row = []
            for x in range(w):
                r, g, b, a = self.px[x0 + x, y0 + y]
                row.append(1 if a > 128 and r < 128 else 0)
            rows.append(row)
        return rows


def read_width_table(label):
    """Reads a 256-entry `db` width table that follows `label::` in the M3 vwf.asm."""
    text = open(M3_VWF_ASM).read()
    start = text.index(label + '::')
    widths = []
    for line in text[start:].splitlines()[1:]:
        line = line.split(';')[0].strip()
        if not line.startswith('db'):
            if widths:
                break
            continue
        widths += [int(x) for x in line[2:].split(',')]
        if len(widths) >= 256:
            break
    return widths


def load_fonts():
    fonts = {
        'vwf': Font(os.path.join(M3_PATCH_GFX, 'Font.1bpp.png'), read_width_table('VWFDrawLetterTable')),
        'narrow': Font(os.path.join(M3_PATCH_GFX, 'NarrowFont.1bpp.png'),
                       read_width_table('VWFDrawNarrowLetterTable')),
        'bold': Font(os.path.join(M3_PATCH_GFX, 'BoldFont.1bpp.png'), read_width_table('VWFDrawBoldLetterTable')),
    }
    # Medarot 1 fixed-width font (the game's menu font in this patch); layout: see charmap_en.tbl
    charmap = {}
    for line in open(os.path.join(ROOT, 'scripts', 'res', 'charmap_en.tbl'), encoding='utf-8'):
        line = line.rstrip('\n')
        m = re.match(r'^([0-9A-Fa-f]{2})=(.)$', line)
        if m and int(m.group(1), 16) < 0x80:
            charmap.setdefault(m.group(2), int(m.group(1), 16))
    fixed = Font(os.path.join(ROOT, 'gfx', 'patch', 'M1FixedFont.png'), fixed_width=8, charmap=charmap)
    fonts['fixed'] = fixed
    return fonts


FONTS = load_fonts()


def text_bitmap(text, font='vwf', spacing=1, space=None):
    """Renders text into rows of 0/1 (8 rows).  `space`: width of ' ' (default: font's)."""
    f = FONTS[font] if isinstance(font, str) else font
    rows = [[] for _ in range(8)]
    first = True
    for c in text:
        if not first:
            for r in rows:
                r += [0] * spacing
        first = False
        if c == ' ' and space is not None:
            for r in rows:
                r += [0] * space
            continue
        g = f.glyph(c)
        for y in range(8):
            rows[y] += g[y]
    return rows


def bitmap_width(bm):
    return len(bm[0])


def scale_bitmap(bm, sx=1, sy=1):
    out = []
    for row in bm:
        r = [v for v in row for _ in range(sx)]
        for _ in range(sy):
            out.append(list(r))
    return out


def outline_bitmap(bm):
    """Returns the 1px (8-neighbour) outline mask around a bitmap (same size + 2 each way)."""
    h, w = len(bm), len(bm[0])
    out = [[0] * (w + 2) for _ in range(h + 2)]
    for y in range(h):
        for x in range(w):
            if bm[y][x]:
                for dy in (-1, 0, 1):
                    for dx in (-1, 0, 1):
                        out[y + 1 + dy][x + 1 + dx] = 1
    for y in range(h):
        for x in range(w):
            if bm[y][x]:
                out[y + 1][x + 1] = 0
    return out


# ---------------------------------------------------------------------------------------
# Tileset canvas

class Canvas:
    def __init__(self, index):
        self.index = index
        self.path = os.path.join(SRC_DIR, f'ts_{index:03X}.png')
        im = Image.open(self.path).convert('L')
        self.w, self.h = im.size
        px = im.load()
        self.px = [[3 - min(3, (px[x, y] + 42) // 85) for x in range(self.w)] for y in range(self.h)]
        self.orig = [list(r) for r in self.px]
        self.vram = INFO[index]['vram']
        self.count = INFO[index]['tiles']
        self.locked = {}  # tile -> pixel tuple fixed by a previous word

    # Tile ids are given as the tile numbers the tilemaps use (VRAM id), converted here.
    def tile_no(self, tid):
        """Tileset-relative tile number of a BG tile id ($80-$FF: $8800 area, $00-$7F: $9000)."""
        addr = 0x8800 + (tid - 0x80) * 16 if tid >= 0x80 else 0x9000 + tid * 16
        n = (addr - self.vram) // 16
        assert 0 <= n < self.count, f'tile ${tid:02X} not in tileset {self.index:03X}'
        return n

    def tile_xy(self, tid):
        n = self.tile_no(tid)
        return (n % (self.w // 8)) * 8, (n // (self.w // 8)) * 8

    def get_tile(self, tid, orig=False):
        src = self.orig if orig else self.px
        x0, y0 = self.tile_xy(tid)
        return [src[y0 + y][x0:x0 + 8] for y in range(8)]

    def set_tile(self, tid, rows, force=False):
        key = tuple(tuple(r) for r in rows)
        if tid in self.locked and self.locked[tid] != key and not force:
            raise ValueError(f'tileset {self.index:03X}: tile ${tid:02X} is shared and would get '
                             f'two different contents')
        self.locked[tid] = key
        x0, y0 = self.tile_xy(tid)
        for y in range(8):
            self.px[y0 + y][x0:x0 + 8] = list(rows[y])

    def copy_tile(self, dst, src):
        """Make tile `dst` a copy of the original tile `src` (e.g. remove a dakuten)."""
        self.set_tile(dst, self.get_tile(src, orig=True))

    def strip(self, tiles, orig=True):
        rows = [[] for _ in range(8)]
        for t in tiles:
            for y, r in enumerate(self.get_tile(t, orig)):
                rows[y] += r
        return rows

    def put_strip(self, tiles, rows):
        for i, t in enumerate(tiles):
            self.set_tile(t, [r[i * 8:i * 8 + 8] for r in rows])

    def word(self, tiles, text, font='vwf', fg=BLACK, bg=None, x=None, y=0, clear='fg',
             spacing=1, space=None, bitmap=None, align='center', shadow=None, base=None):
        """Draws `text` over the strip of `tiles` (BG tile ids, in screen order).

        clear: 'fg'  -> every pixel of colour fg in the strip becomes bg (removes the kana)
               'all' -> the whole strip is filled with bg
               None  -> nothing is cleared
               (x0, x1, y0, y1) -> only that pixel box is filled with bg
        bg: background colour (default: the most common colour of the strip).
        x: left pixel of the text (default: aligned per `align`).  y: top row of the glyphs.
        base: start from this strip (list of rows) instead of the original tiles.
        """
        rows = [list(r) for r in (base if base is not None else self.strip(tiles))]
        width = len(rows[0])
        if bg is None:
            counts = {}
            for r in rows:
                for v in r:
                    if v != fg:
                        counts[v] = counts.get(v, 0) + 1
            bg = max(counts, key=counts.get) if counts else WHITE
        if clear == 'fg':
            rows = [[bg if v == fg else v for v in r] for r in rows]
        elif clear == 'all':
            rows = [[bg] * width for _ in rows]
        elif clear:
            x0, x1, y0, y1 = clear
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    rows[yy][xx] = bg
        bm = bitmap if bitmap is not None else text_bitmap(text, font, spacing, space)
        w = bitmap_width(bm)
        if x is None:
            if align == 'center':
                x = (width - w) // 2
            elif align == 'right':
                x = width - w
            else:
                x = 0
        assert x >= 0 and x + w <= width, (
            f'tileset {self.index:03X}: "{text}" is {w}px wide, does not fit at x={x} in {width}px')
        if shadow is not None:
            for yy, r in enumerate(bm):
                for xx, v in enumerate(r):
                    if v and 0 <= y + yy + 1 < 8 and x + xx + 1 < width:
                        rows[y + yy + 1][x + xx + 1] = shadow
        for yy, r in enumerate(bm):
            for xx, v in enumerate(r):
                if v and 0 <= y + yy < len(rows):
                    rows[y + yy][x + xx] = fg
        self.put_strip(tiles, rows)
        return rows

    def save(self, count=None):
        os.makedirs(OUT_DIR, exist_ok=True)
        im = Image.new('L', (self.w, self.h))
        im.putdata([255 - v * 85 for r in self.px for v in r])
        base = os.path.join(OUT_DIR, f'ts_{self.index:03X}')
        im.save(base + '.png')
        with open(base + '.count', 'w') as f:
            f.write(f'{count if count is not None else self.count}\n')
        print(f'wrote {base}.png')


# ---------------------------------------------------------------------------------------
# Tilesets

TILESETS = {}


def tileset(index):
    def deco(fn):
        TILESETS[index] = fn
        return fn
    return deco

@tileset(0x00A)
def ts_00A(c):
    # Setup screen, battle speed slider: Long / ふつう / Short (tiles $C8-$CB in the window)
    c.word([0xC8, 0xC9, 0xCA, 0xCB], 'Normal', fg=BLACK, bg=WHITE, clear='all')


@tileset(0x00B)
def ts_00B(c):
    # Name entry buttons: ひらがな / カタカナ (page toggle), もどる (delete), おわる (done).
    # The る tile $91 is shared by もどる and おわる, so it is left blank and the English
    # words are drawn in the first two tiles of each button.
    c.word([0x94, 0x95, 0x96, 0x97], 'Page 1', bg=WHITE, clear='all')
    c.word([0x98, 0x99, 0x9A, 0x9B], 'Page 2', bg=WHITE, clear='all')
    c.word([0x92, 0x93, 0x91], 'Back', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0x8F, 0x90, 0x91], 'Done', font='narrow', bg=WHITE, clear='all', x=0)
    c.copy_tile(0x8E, 0x87)  # frame tile with the dakuten of が/ど -> plain frame


@tileset(0x011)
def ts_011(c):
    # Item screen header: アイテム
    c.word([0x89, 0x8A, 0x8B, 0x8C], 'Items', bg=LIGHT, clear='fg')


def main():
    wanted = [int(a, 16) for a in sys.argv[1:]] or sorted(TILESETS)
    for i in wanted:
        c = Canvas(i)
        TILESETS[i](c)
        c.save()


if __name__ == '__main__':
    main()
