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


def layout(width, *parts):
    """Bitmap of `width` px with several pieces placed at fixed x: parts = (x, text, font)."""
    rows = [[0] * width for _ in range(8)]
    for x, text, font in parts:
        bm = text_bitmap(text, font)
        assert x + bitmap_width(bm) <= width, f'"{text}" does not fit at x={x}'
        for y in range(8):
            for i, v in enumerate(bm[y]):
                if v:
                    rows[y][x + i] = 1
    return rows


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

    def block(self, tile_rows, bitmap, x, y, fg=BLACK, clear=None, bg=WHITE, shadow=None, shadow_dir=(0, 1)):
        """Draws a bitmap over a block of tiles (tile_rows: list of rows of BG tile ids).

        clear: (x0, x1, y0, y1) pixel box filled with bg first.  shadow: colour of a drop
        shadow offset by shadow_dir (drawn under the text).
        """
        th = len(tile_rows) * 8
        rows = []
        for tr in tile_rows:
            rows += self.strip(tr)
        if clear:
            x0, x1, y0, y1 = clear
            for yy in range(y0, y1):
                for xx in range(x0, x1):
                    rows[yy][xx] = bg
        if shadow is not None:
            dx, dy = shadow_dir
            for yy, r in enumerate(bitmap):
                for xx, v in enumerate(r):
                    if v and 0 <= y + yy + dy < th:
                        rows[y + yy + dy][x + xx + dx] = shadow
        for yy, r in enumerate(bitmap):
            for xx, v in enumerate(r):
                if v:
                    rows[y + yy][x + xx] = fg
        for i, tr in enumerate(tile_rows):
            self.put_strip(tr, rows[i * 8:i * 8 + 8])

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

@tileset(0x003)
def ts_003(c):
    # Start menu (tilemap 0_13): メダロッチ B7-BB / アイテム BC-BF / セーブ C0-C2.
    # (The ゛ above ダ and ブ is the font tile $F2 in the tilemap itself, not part of this
    # tileset.)  B4-B6 (はい/いいえ: B4 B5 / B5 B5 B6) are left alone: "Yes" cannot be
    # drawn in one tile, see the yes/no notes for tileset 004.
    c.word([0xB7, 0xB8, 0xB9, 0xBA, 0xBB], 'Medarotch', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0xBC, 0xBD, 0xBE, 0xBF], 'Items', bg=WHITE, clear='all', x=0)
    c.word([0xC0, 0xC1, 0xC2], 'Save', bg=WHITE, clear='all', x=0)


@tileset(0x006)
def ts_006(c):
    # Test mode (tilemap 1_44).  Title テストモード: tiles 83-8A (top) / 8D-94 (bottom), black
    # text with a dark grey shadow below, across the tile boundary.
    title = text_bitmap('TEST MODE', 'bold', space=4)
    w = bitmap_width(title)
    c.block([list(range(0x83, 0x8B)), list(range(0x8D, 0x95))], title, (64 - w) // 2, 4,
            fg=BLACK, clear=(0, 64, 4, 12), bg=WHITE, shadow=DARK)
    # Menu (box interiors are white, text black):
    #   サウンド         9B 9C 9D 9E                   (ド's ゛ in frame tile 97)
    #   エフェクト        A2 A3 A4 A5 9E
    #   セーブデータをけす AF B0 A3 B1 B0 B2 B3 B4 B5    (゛ of ブ/デ in frame tiles AE)
    #   おわる           B6 B7 B8
    # Shared tiles 9E, A3 and B0 (twice in the same line!) make full-length labels
    # impossible without changing the tilemap; this layout keeps all shared tiles blank
    # (found by trying all combinations of a few candidate wordings and offsets).
    E = [[0] * 8 for _ in range(8)]
    for t in (0x9E, 0xA3, 0xB0, 0xA2, 0xAF, 0xB1):
        c.set_tile(t, E)
    c.word([0x9B, 0x9C, 0x9D], 'Music', bg=WHITE, clear='all', x=0)
    c.word([0xA4, 0xA5], 'SFX', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0xB2, 0xB3, 0xB4, 0xB5], 'Erase All', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0xB6, 0xB7, 0xB8], 'Exit', bg=WHITE, clear='all', x=0)
    c.copy_tile(0x97, 0x96)
    c.copy_tile(0xAE, 0xAD)


def sign(c, top, bottom, text, font='vwf'):
    """TV/billboard style sign: 2 tile rows, white interior (x 7..w-7, y 3..12), black text
    with a dark grey drop shadow (+1,+1), like the original kana."""
    w = len(top) * 8
    bm = text_bitmap(text, font, space=3)
    tw = bitmap_width(bm)
    x = (w - tw - 1) // 2
    assert x >= 7 and x + tw + 1 <= w - 7, f'sign "{text}" too wide ({tw}px)'
    c.block([top, bottom], bm, x, 4, fg=BLACK, clear=(7, w - 7, 3, 13), bg=WHITE, shadow=DARK,
            shadow_dir=(1, 1))


@tileset(0x020)
def ts_020(c):
    # Sign on the "Weekly Medarot" TV show set: メダロットこうざ (tiles 80-8A / 8B-95)
    sign(c, list(range(0x80, 0x8B)), list(range(0x8B, 0x96)), 'Medarot Class')


@tileset(0x023)
def ts_023(c):
    # Title sign of the TV show: しゅうかんメダロット (tiles 90-9D / 9E-AB)
    sign(c, list(range(0x90, 0x9E)), list(range(0x9E, 0xAC)), 'Weekly Medarot')


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


def yen_tile():
    """The ¥ glyph of the translated digits tileset 001 (gfx/tilesets/ts_001.png, tile 12)."""
    im = Image.open(os.path.join(OUT_DIR, 'ts_001.png')).convert('L')
    return [[3 - min(3, (im.getpixel((12 * 8 + x, y)) + 42) // 85) for x in range(8)] for y in range(8)]


@tileset(0x00C)
def ts_00C(c):
    # Shop "buy parts" list header: あたま / みぎうで / ひだりうで / きゃくぶ, and 円.
    # Strips (BG tile ids):  Head  = D8 D9 DA         R.Arm = DB DC DD DE
    #                        L.Arm = DF D9 E0 DD DE   Legs  = DC E1 E2 E3
    # Shared: D9 (Head/L.Arm), DC (R.Arm/Legs), DD DE (both arms).  So: DD DE = "Arm",
    # DC is blank (Legs is drawn in E1-E3), D9 holds just the "e" of both "Head" and "Left".
    L, B = LIGHT, BLACK
    c.word([0xDD, 0xDE], 'Arm', font='narrow', bg=L, clear='all', x=2)
    c.word([0xDC], '', bitmap=[[0] * 8 for _ in range(8)], bg=L, clear='all')
    c.word([0xE1, 0xE2, 0xE3], 'Legs', bg=L, clear='all')
    c.word([0xDB], 'R.', bg=L, clear='all', align='right')
    c.word([0xD8, 0xD9, 0xDA], None, bitmap=layout(24, (3, 'H', 'vwf'), (10, 'e', 'vwf'), (16, 'ad', 'narrow')),
           bg=L, clear='all', x=0)
    c.word([0xDF, 0xD9, 0xE0], None, bitmap=layout(24, (3, 'L', 'vwf'), (10, 'e', 'vwf'), (16, 'ft', 'narrow')),
           bg=L, clear='all', x=0)
    c.copy_tile(0xE4, 0xC1)  # border tile with the dakuten of ぎ/で/だ/ぶ -> plain border
    # 円 -> ¥ (same glyph as the replaced digits tileset 001 uses)
    c.set_tile(0xE5, yen_tile())


BLANK_TILE = [[0] * 8 for _ in range(8)]


@tileset(0x013)
def ts_013(c):
    # Parts list header (2 tile rows; the kana sit across the tile boundary):
    #   けいしき  cols 1-4 : top 97 99 9B 9D / bottom 98 9A 9C 9E
    #   パーツめい cols 8-12: top 9F (00) A2 A4 99 / bottom A0 A1 A3 A5 9A
    #   こすう    cols 16-18: top A6 A8 AA / bottom A7 A9 AB
    # The top tile of column 9 is the blank font tile, so the English is drawn entirely in
    # the bottom tiles.  99/9A (い) is shared by columns 2 and 12, so it stays blank:
    # "ID" goes into columns 3-4 (centred over the 6-character model code below it).
    for t in (0x97, 0x99, 0x9B, 0x9D, 0x9F, 0xA2, 0xA4, 0xA6, 0xA8, 0xAA, 0x9A, 0x98):
        c.set_tile(t, BLANK_TILE)
    c.word([0x9C, 0x9E], 'ID', bg=WHITE, clear='all')
    c.word([0xA0, 0xA1, 0xA3, 0xA5], 'Name', bg=WHITE, clear='all')
    c.word([0xA7, 0xA9, 0xAB], 'Qty', bg=WHITE, clear='all')


@tileset(0x01D)
def ts_01D(c):
    # Medal screen, Medaforce page: じゅくれんど (top 98 00 9B 9D 9F A1 / bottom 99 9A 9C 9E A0 A2;
    # the top tile of the 2nd column is the blank font tile) -> "Proficiency" in the bottom row,
    # above the "/Success" label that the tilemap text puts below it.
    for t in (0x98, 0x9B, 0x9D, 0x9F, 0xA1):
        c.set_tile(t, BLANK_TILE)
    c.word([0x99, 0x9A, 0x9C, 0x9E, 0xA0, 0xA2], 'Proficiency', font='narrow', bg=WHITE, clear='all', x=0)


@tileset(0x027)
def ts_027(c):
    # Medaroad Race title (race select screen): メダロードレース in tiles CC-D3, black with a
    # dark grey drop shadow on white.
    bm = text_bitmap('Medaroad Race', 'narrow', space=3)
    w = bitmap_width(bm)
    c.block([list(range(0xCC, 0xD4))], bm, (64 - w - 1) // 2, 0, fg=BLACK, clear=(0, 64, 0, 8), bg=WHITE,
            shadow=DARK, shadow_dir=(1, 1))
    # the frame tiles above the title carry the ゛ of ダ and ド -> plain frame tile D7
    c.copy_tile(0xD4, 0xD7)
    c.copy_tile(0xD5, 0xD7)


@tileset(0x089)
def ts_089(c):
    # Link screen label (tilemap 0_77): つうしん (AF-B2) above NET (B3-B5) -> "Link" / "NET"
    c.word([0xAF, 0xB0, 0xB1, 0xB2], 'Link', bg=LIGHT, clear='fg', align='right')


@tileset(0x08C)
def ts_08C(c):
    # Same label in one row: つうしんNET (A5-AB) -> "Link NET"
    c.word([0xA5, 0xA6, 0xA7, 0xA8, 0xA9, 0xAA, 0xAB], 'Link NET', bg=LIGHT, clear='fg', x=1)


@tileset(0x0B7)
def ts_0B7(c):
    # Paint shop (loaded over font tiles 63-7F).  Tilemap strips:
    #   main menu (1_E2): せつめいをきく 69 6A 6B 6C 6D 6E 6F / ペイント 70-73 /
    #                     いろをもどす 6C 74 6D 75 76 77 / やめる 78 6B 79;  おかね 66 67 68
    #   colour screen (1_E3): カラーせんたく 7A 7B 7C 69 7D 7E 6F / カラー No.(0B6) /(7F)
    #   yes/no box (1_E4): はい 63 64 / いいえ 64 64 65  -> left in Japanese (see tileset 004)
    # Layout found by an exhaustive search over wordings/offsets (scratch solver):
    #   "Guide" (69-6B) and "Bye" (78 6B 79) share their "e" in 6B; 6C/6D stay blank, so the
    #   restore item is drawn in 75-77; the colour screen title reuses "Guide" -> "Color Guide".
    guide = c.word([0x69, 0x6A, 0x6B], 'Guide', font='narrow', bg=WHITE, clear='all', x=2)
    c.word([0x78, 0x6B, 0x79], 'Bye', font='narrow', bg=WHITE, clear='all', x=0)
    for t in (0x6C, 0x6D, 0x6E, 0x6F, 0x74):
        c.set_tile(t, BLANK_TILE)
    c.word([0x75, 0x76, 0x77], 'Reset', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0x70, 0x71, 0x72, 0x73], 'Paint', font='narrow', bg=WHITE, clear='all', x=0)
    c.word([0x66, 0x67, 0x68], 'Cash', bg=WHITE, clear='all', x=0)
    c.word([0x7A, 0x7B, 0x7C], 'Color', font='narrow', bg=WHITE, clear='all', x=1)
    c.put_strip([0x7D, 0x7E], [r[8:24] for r in guide])  # "...ide" of "Guide" after 69
    c.word([0x7F], '/', bg=WHITE, clear='all', align='center')


@tileset(0x011)
def ts_011(c):
    # Item screen header: アイテム
    c.word([0x89, 0x8A, 0x8B, 0x8C], 'Items', bg=LIGHT, clear='fg')

def kerned(parts):
    """Bitmap from (text, font, gap_before) pieces: lets single letter gaps be tightened."""
    rows = [[] for _ in range(8)]
    for text, font, gap in parts:
        g = text_bitmap(text, font)
        for y in range(8):
            rows[y] += [0] * gap + g[y]
    return rows


@tileset(0x0B5)
def ts_0B5(c):
    # Boot credits screen (tilemap 1_E5): キャラクターデザイン (CB-D4, ゛ in CA CA above) /
    # ほるま りん (D5 D6 D7, blank font tile, D9 DA).  Name kept in the original order
    # (Horuma | Rin); "Horuma" has to fit 24px, so it uses a 3px H set without a gap before the o.
    c.set_tile(0xCA, BLANK_TILE)
    c.word(list(range(0xCB, 0xD5)), 'Character Design', bg=WHITE, clear='all')
    h3 = [[r[0], r[1] | r[2], r[3]] for r in text_bitmap('H', 'narrow')]  # 3px wide H
    FONTS['narrow'].overrides['\x01'] = h3
    horuma = kerned([('\x01', 'narrow', 0), ('oruma', 'narrow', 0)])
    c.word([0xD5, 0xD6, 0xD7], None, bitmap=horuma, bg=WHITE, clear='all', align='right')
    c.word([0xD9, 0xDA], 'Rin', font='narrow', bg=WHITE, clear='all', align='left')



def main():
    wanted = [int(a, 16) for a in sys.argv[1:]] or sorted(TILESETS)
    for i in wanted:
        c = Canvas(i)
        TILESETS[i](c)
        c.save()


if __name__ == '__main__':
    main()
