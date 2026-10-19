#!/usr/bin/env python3
"""Build translated tilemaps (text/tilemaps/*.txt) into an asm file for the overlay build.

usage: python3 scripts/build_tilemaps.py baserom_kuwagata.gbc text/tilemaps build/tilemaps/tilemaps.asm

Only tilemaps with at least one non-empty EN: line are rebuilt; everything else stays
byte-identical to the original ROM.  Placement, per tilemap table:
  1. a re-encoded map that is not larger than the original is written over the original data;
  2. otherwise it goes in the free space at the end of the table's own bank and every pointer
     table entry that used the old address is repointed;
  (each table bank, $34 and $35, has ~6KB of zero padding after the original data, far more than
  all the text tilemaps put together; the build fails with a clear error if it ever runs out.
  Moving a table to another bank would not help: a table's bank is one byte at $0C52+table, so
  the whole table would have to move, and the original data alone fills ~10KB of the 16KB.)
"""
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
sys.path.append(os.path.dirname(__file__))
import tilemaps as T  # noqa: E402
from textcodec import Codec  # noqa: E402
from dump_tilemaps import jp_table, run_jp  # noqa: E402

HEADER_RE = re.compile(r'^\[(\d+)_([0-9A-Fa-f]{2})\]\s*$')
ENTRY_RE = re.compile(r'^@(!?)\s*(\d+)\s*,\s*(\d+)(?:\s+max\s+\d+)?\s*$')


class Entry:
    def __init__(self, line, force, row, col):
        self.line = line
        self.force = force
        self.row = row
        self.col = col
        self.jp = None
        self.en = None


def parse_file(path):
    key = None
    entries = []
    with open(path, encoding='utf-8-sig') as f:
        for n, line in enumerate(f, 1):
            line = line.rstrip('\r\n')
            if not line.strip() or line.startswith('#'):
                continue
            m = HEADER_RE.match(line)
            if m:
                key = (int(m.group(1)), int(m.group(2), 16))
                continue
            m = ENTRY_RE.match(line)
            if m:
                entries.append(Entry(n, m.group(1) == '!', int(m.group(2)), int(m.group(3))))
                continue
            if line.startswith('JP:') and entries:
                entries[-1].jp = line[3:].strip()
                continue
            if line.startswith('EN:') and entries:
                text = line[3:]
                if text.startswith(' '):
                    text = text[1:]
                entries[-1].en = text.rstrip()
                continue
            raise SystemExit(f'{path}:{n}: cannot parse line: {line!r}')
    if key is None:
        raise SystemExit(f'{path}: missing [table_index] header')
    return key, entries


def apply_entries(path, tmap, entries, jp, codec):
    runs = T.find_runs(tmap)
    jp_entries = [e for e in entries if e.jp is not None]
    if len(jp_entries) != len(runs):
        raise SystemExit(f'{path}: expected {len(runs)} JP entries, found {len(jp_entries)} '
                         '(re-dump the file and copy the translations over)')
    for e, run in zip(jp_entries, runs):
        expected = run_jp(jp, tmap, run).rstrip()
        if e.jp != expected:
            raise SystemExit(f'{path}:{e.line}: JP text {e.jp!r} does not match the ROM ({expected!r})')
        e.run = run
    todo = [e for e in entries if e.en]
    if not todo:
        return None
    new = tmap.copy()
    # Clear the original Japanese (and the dakuten above it) of every translated run
    for e in todo:
        run = getattr(e, 'run', None)
        if run is None:
            continue
        for i, t in enumerate(run.tiles):
            x = run.col + i
            if t is not None:
                new.cells[(x, run.row)] = 0x00
            if T.dakuten_above(tmap, run, i) is not None:
                new.cells[(x, run.row - 1)] = 0x00
        for x, y, t, rep in T.graphic_dakuten(tmap, run):
            new.cells[(x, y)] = rep
    # Write the English
    for e in todo:
        try:
            toks = codec.tokenize(e.en)
        except ValueError as err:
            raise SystemExit(f'{path}:{e.line}: {err}')
        tiles = []
        for tok in toks:
            if tok[0] != 'char':
                raise SystemExit(f'{path}:{e.line}: control codes are not allowed in tilemaps')
            tiles.append(tok[1])
        run = getattr(e, 'run', None)
        for i, tile in enumerate(tiles):
            x, y = e.col + i, e.row
            where = f'{path}:{e.line}: {e.en!r}: tile {i} at row {y}, col {x}'
            if x >= T.VRAM_WIDTH:
                raise SystemExit(f'{where} is past the edge of the tilemap')
            if tmap.compressed and y * T.VRAM_WIDTH + x >= tmap.length:
                raise SystemExit(f'{where} is outside the (compressed) tilemap')
            orig = tmap.cells.get((x, y))
            if not e.force:
                if tmap.compressed and x >= T.SCREEN_WIDTH:
                    raise SystemExit(f'{where} is off screen (use "@!" to force)')
                if T.is_graphics(orig):
                    raise SystemExit(f'{where} would overwrite graphics tile ${orig:02X} '
                                     f'(text too long? use "@!" to force)')
                if run is not None and x >= run.limit and orig is not None and orig != 0x00:
                    raise SystemExit(f'{where} would overwrite other text (use "@!" to force)')
                if orig is None and not (run is not None and run.col <= x < run.end):
                    print(f'warning: {where} writes over a tile the original leaves undrawn '
                          '(the game may print something there)', file=sys.stderr)
            new.cells[(x, y)] = tile
    return T.encode(new)


def asm_bytes(data):
    out = []
    for i in range(0, len(data), 16):
        out.append('\tdb ' + ', '.join(f'${b:02X}' for b in data[i:i + 16]))
    return '\n'.join(out)


def free_start(rom, bank, ptrs):
    data = rom[bank * 0x4000:(bank + 1) * 0x4000]
    last = max(i for i, b in enumerate(data) if b != 0)
    start = max(0x4000 + last + 1, max(ptrs) + 1)
    return (start + 15) & ~15


def build_table(rom, t, changes):
    """changes: {address: new bytes}. Returns asm text."""
    bank = T.table_bank(rom, t)
    base = bank * 0x4000
    ptrs = T.table_pointers(rom, t)
    end_ptr = max(ptrs)
    maps = {}
    for p in sorted(set(ptrs)):
        tm = T.decode(rom, base + p - 0x4000)
        if p == end_ptr and tm.size > 0x400:
            continue  # unused entries point at the end of the data
        maps[p] = tm
    addrs = sorted(maps)
    overlapping = set()
    for a, b in zip(addrs, addrs[1:]):
        if a + maps[a].size > b:
            overlapping.update((a, b))

    lines = [f'; Tilemap table {t} (original bank ${bank:02X})']
    in_place, appended = {}, {}
    free = free_start(rom, bank, ptrs)
    pos = free
    for p, data in sorted(changes.items()):
        if len(data) <= maps[p].size and p not in overlapping:
            in_place[p] = data
        else:
            appended[p] = (pos, data)
            pos += len(data)
    if pos > 0x8000:
        raise SystemExit(f'Tilemap table {t}: translated tilemaps need ${pos - free:X} bytes of free space '
                         f'but bank ${bank:02X} only has ${0x8000 - free:X} (shorten the translations)')

    for p, data in in_place.items():
        idx = ptrs.index(p)
        lines.append(f'SECTION "Tilemap {t}_{idx:02X}", ROMX[${p:04X}], BANK[${bank:02X}]')
        lines.append(asm_bytes(data))
    if appended:
        lines.append(f'SECTION "Tilemaps {t} Expanded", ROMX[${free:04X}], BANK[${bank:02X}]')
        for p, (addr, data) in appended.items():
            idx = ptrs.index(p)
            lines.append(f'Tilemap{t}_{idx:02X}:: ; was ${p:04X}')
            lines.append(asm_bytes(data))
        for i, p in enumerate(ptrs):
            if p in appended:
                lines.append(f'SECTION "Tilemap {t} Pointer {i:02X}", ROMX[${0x4000 + 2 * i:04X}], '
                             f'BANK[${bank:02X}]')
                lines.append(f'\tdw Tilemap{t}_{ptrs.index(p):02X}')
    return '\n'.join(lines) + '\n'


def main():
    rom_path, in_dir, out_path = sys.argv[1:4]
    rom = open(rom_path, 'rb').read()
    codec = Codec(charmap='charmap_en.tbl')
    jp = jp_table()
    changes = {t: {} for t in range(T.NUM_TABLES)}
    files = sorted(f for f in os.listdir(in_dir) if f.endswith('.txt')) if os.path.isdir(in_dir) else []
    for name in files:
        path = os.path.join(in_dir, name)
        (t, idx), entries = parse_file(path)
        if t >= T.NUM_TABLES:
            raise SystemExit(f'{path}: no tilemap table {t}')
        bank = T.table_bank(rom, t)
        p = T.table_pointers(rom, t)[idx]
        tmap = T.decode(rom, bank * 0x4000 + p - 0x4000)
        data = apply_entries(path, tmap, entries, jp, codec)
        if data is None:
            continue
        original = rom[bank * 0x4000 + p - 0x4000:][:tmap.size]
        if data != original:
            changes[t][p] = data
    out = ['; Generated by scripts/build_tilemaps.py from text/tilemaps -- do not edit', '']
    for t in range(T.NUM_TABLES):
        if changes[t]:
            out.append(build_table(rom, t, changes[t]))
    os.makedirs(os.path.dirname(out_path) or '.', exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out))
    n = sum(len(c) for c in changes.values())
    print(f'Tilemaps: {n} translated' + ''.join(f', table {t}: {len(changes[t])}' for t in changes if changes[t]))


if __name__ == '__main__':
    main()
