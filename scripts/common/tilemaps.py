"""Tilemap codec for Medarot 2 (tilemap loader at $0B2A / attribute loader at $0C6E).

Tilemap tables
--------------
The byte table at $0C52 holds one ROM bank per tilemap table (table 0 -> bank $34,
table 1 -> bank $35).  Each such bank starts with 256 little-endian pointers ($4000 + index*2)
to the tilemap data.  (The attribute maps use the same layout with the bank table at $0DA1.)

Data format
-----------
First byte: header.  $FF = empty tilemap.  If (header & 3) == 0 the map is "raw":
    $FF        end
    $FE        next row (x back to the starting column, y + 1)
    $FD        skip one tile (leave VRAM untouched)
    $FC tt nn  write tile tt nn times
    other      write that tile, x + 1 (x wraps inside the 32-tile VRAM row)
Otherwise the map is "compressed" and writes a linear stream of tiles (32 tiles per VRAM row,
no row commands).  Command byte cc:
    $FF                end
    %00nnnnnn d...     nnnnnn+1 literal tiles
    %01nnnnnn tt       tt repeated nnnnnn+2 times
    %10nnnnnn tt       tt, tt+1, tt+2 ... (nnnnnn+2 tiles)
    %11nnnnnn tt       tt, tt-1, tt-2 ... (nnnnnn+2 tiles)
"""

BANK_TABLE = 0x0C52
ATTR_BANK_TABLE = 0x0DA1
NUM_TABLES = 2
ENTRIES = 256
VRAM_WIDTH = 32
SCREEN_WIDTH = 20


def table_bank(rom, table):
    return rom[BANK_TABLE + table]


def table_pointers(rom, table):
    base = table_bank(rom, table) * 0x4000
    return [rom[base + 2 * i] | rom[base + 2 * i + 1] << 8 for i in range(ENTRIES)]


class Tilemap:
    """Decoded tilemap.

    raw maps:        cells[(x, y)] = tile, absent = not drawn
    compressed maps: tiles = linear list; cells derived with 32 tiles per row
    """

    def __init__(self, header, compressed, cells, length=None, size=0):
        self.header = header
        self.compressed = compressed
        self.cells = cells
        self.length = length  # number of tiles for compressed maps
        self.size = size      # encoded size in bytes (including header and terminator)

    @property
    def width(self):
        return max((x for x, y in self.cells), default=-1) + 1

    @property
    def height(self):
        return max((y for x, y in self.cells), default=-1) + 1

    def copy(self):
        return Tilemap(self.header, self.compressed, dict(self.cells), self.length, self.size)


def decode(data, offset=0):
    o = offset
    header = data[o]
    o += 1
    if header == 0xFF:
        return Tilemap(header, False, {}, None, 1)
    cells = {}
    if header & 3 == 0:
        x = y = 0
        while True:
            b = data[o]
            o += 1
            if b == 0xFF:
                break
            if b == 0xFE:
                x = 0
                y += 1
            elif b == 0xFD:
                x += 1
            elif b == 0xFC:
                t, n = data[o], data[o + 1]
                o += 2
                for _ in range(n if n else 256):
                    cells[(x % VRAM_WIDTH, y)] = t
                    x += 1
            else:
                cells[(x % VRAM_WIDTH, y)] = b
                x += 1
        return Tilemap(header, False, cells, None, o - offset)
    tiles = []
    while True:
        b = data[o]
        o += 1
        if b == 0xFF:
            break
        mode, n = b >> 6, b & 0x3F
        if mode == 0:
            tiles += data[o:o + n + 1]
            o += n + 1
        else:
            t = data[o]
            o += 1
            step = (0, 0, 1, -1)[mode]
            for i in range(n + 2):
                tiles.append((t + step * i) & 0xFF)
    cells = {(i % VRAM_WIDTH, i // VRAM_WIDTH): t for i, t in enumerate(tiles)}
    return Tilemap(header, True, cells, len(tiles), o - offset)


def encode(tmap):
    if tmap.header == 0xFF:
        return bytes([0xFF])
    out = bytearray([tmap.header])
    if tmap.compressed:
        tiles = [tmap.cells.get((i % VRAM_WIDTH, i // VRAM_WIDTH), 0) for i in range(tmap.length)]
        out += compress(tiles)
        return bytes(out)
    rows = []
    for y in range(tmap.height):
        xs = [x for x, yy in tmap.cells if yy == y]
        row = []
        for x in range(max(xs) + 1 if xs else 0):
            row.append(tmap.cells.get((x, y)))
        rows.append(row)
    for y, row in enumerate(rows):
        if y:
            out.append(0xFE)
        i = 0
        while i < len(row):
            t = row[i]
            if t is None:
                out.append(0xFD)
                i += 1
                continue
            n = 1
            while i + n < len(row) and row[i + n] == t and n < 255:
                n += 1
            if n >= 4 or t >= 0xFC:
                out += bytes([0xFC, t, n])
                i += n
            else:
                out.append(t)
                i += 1
    out.append(0xFF)
    return bytes(out)


def compress(tiles):
    out = bytearray()
    lit = []

    def flush():
        while lit:
            chunk = lit[:64]
            del lit[:64]
            out.append(len(chunk) - 1)
            out.extend(chunk)

    i = 0
    while i < len(tiles):
        t = tiles[i]
        best_mode, best_len = 0, 1
        for mode, step, limit in ((1, 0, 65), (2, 1, 65), (3, -1, 64)):  # $FF can't be a dec command
            n = 1
            while i + n < len(tiles) and n < limit and tiles[i + n] == (t + step * n) & 0xFF:
                n += 1
            if n > best_len:
                best_mode, best_len = mode, n
        if best_len >= 3 or (best_len == 2 and not lit):
            flush()
            out += bytes([(best_mode << 6) | (best_len - 2), t])
            i += best_len
        else:
            lit.append(t)
            i += 1
    flush()
    out.append(0xFF)
    return bytes(out)


# --- Text runs -----------------------------------------------------------------------------

DAKUTEN = 0xF2
HANDAKUTEN = 0xF1


def is_kana(t):
    return t is not None and 0x01 <= t <= 0x6C


def is_text(t):
    """Tile that belongs to the font (kana, symbols, digits, dakuten) in menu screens."""
    return t is not None and (0x01 <= t <= 0x7F or 0xE7 <= t <= 0xF5)


def is_blank(t):
    return t is None or t == 0x00


def row_limit(tmap, y):
    """Exclusive right edge for text in row y."""
    if tmap.compressed:
        return SCREEN_WIDTH
    xs = [x for x, yy in tmap.cells if yy == y]
    return max(xs) + 1 if xs else 0


class Run:
    def __init__(self, row, col, end, limit, tiles):
        self.row = row        # tilemap row
        self.col = col        # first column of the original text
        self.end = end        # exclusive end column of the original text
        self.limit = limit    # exclusive column limit (next graphics/text tile or row end)
        self.tiles = tiles    # original tiles (None = not drawn)

    @property
    def max(self):
        return self.limit - self.col


def find_runs(tmap):
    """Text runs: horizontal sequences of font tiles containing at least one kana.
    Single blanks (tile $00 or undrawn) are part of a run; two or more end it."""
    runs = []
    for y in range(tmap.height):
        limit = row_limit(tmap, y)
        x = 0
        while x < limit:
            if not is_text(tmap.cells.get((x, y))):
                x += 1
                continue
            start = x
            end = x + 1
            x += 1
            while x < limit:
                t = tmap.cells.get((x, y))
                if is_text(t):
                    end = x + 1
                    x += 1
                elif is_blank(t) and x + 1 < limit and is_text(tmap.cells.get((x + 1, y))):
                    x += 1
                else:
                    break
            tiles = [tmap.cells.get((i, y)) for i in range(start, end)]
            if any(is_kana(t) for t in tiles):
                # available space: up to the next non-blank tile
                # (undrawn tiles in raw maps are usually filled in by the game: numbers, names)
                lim = end
                while lim < limit and tmap.cells.get((lim, y)) == 0x00:
                    lim += 1
                runs.append(Run(y, start, end, lim, tiles))
    return runs


def dakuten_above(tmap, run, i):
    if run.row == 0:
        return None
    t = tmap.cells.get((run.col + i, run.row - 1))
    return t if t in (DAKUTEN, HANDAKUTEN) else None
