#!/usr/bin/env python3
"""Dump the menu/screen tilemaps that contain Japanese text to editable text files.

usage: python3 scripts/dump_tilemaps.py baserom_kuwagata.gbc text/tilemaps [--all] [--force]

Every tilemap of every table referenced by the bank table at $0C52 is decoded. Tilemaps that
contain kana text are written to <out>/<table>_<index>.txt (see doc/tilemaps.md).  Tilemaps
whose kana-range tiles are really screen graphics (title logos, portraits, character-select
art...) are listed in GRAPHICS and skipped unless --all is given.

Existing files are not overwritten (so translations are never lost) unless --force is given.
"""
import os
import sys
import unicodedata

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import tilemaps as T  # noqa: E402
import utils  # noqa: E402

RES = os.path.join(os.path.dirname(__file__), 'res')

# Tilemaps that use tiles $01-$7F for screen-specific graphics instead of the font.
# (Checked by hand: the "text" they decode to is nonsense / sequential tile numbers.)
GRAPHICS = {
    0: {0x02, 0x05, 0x06, *range(0x57, 0x6D), 0x71, 0x72, 0x73, 0x74},
    1: {0x42, 0x43, 0x6B, 0x6C, *range(0x72, 0x7B), *range(0x7C, 0x8E), 0x8F, 0x98, 0x9B,
        *range(0xA0, 0xAC), 0xAC, 0xB1, 0xB3, 0xB9, 0xBC, 0xBD, 0xBF, 0xC8, 0xCF, 0xD3, 0xD5,
        0xDE, 0xDF, 0xE0, 0xE2, 0xE3, 0xE4, 0xE5, 0xE6},
}

# What the tilemaps are, as far as can be told from their contents
DESCRIPTIONS = {
    (0, 0x12): 'Saving message ("Saving!")',
    (0, 0x24): 'Records screen: Medals/Parts obtained, free battle time, wins/battles',
    (0, 0x26): 'Medarot order screen: "SELECT button: swap order"',
    (0, 0x29): 'Item menu: Use / View',
    (0, 0x2A): 'Medarot status header labels: Medarot / Medal / Parts',
    (0, 0x2C): 'Parts label: Head parts',
    (0, 0x2D): 'Parts label: Right arm parts',
    (0, 0x2E): 'Parts label: Left arm parts',
    (0, 0x2F): 'Parts label: Leg parts',
    (0, 0x30): 'Parts screen hint: "SELECT button: switch parts"',
    (0, 0x36): 'Parts stats labels: armor / uses / success / power',
    (0, 0x37): 'Parts stats labels: armor / charge / heat / success / power',
    (0, 0x38): 'Medal select screen (Medal selection / Level)',
    (0, 0x40): 'Medal status: ability values / remaining / compatibility / experience',
    (0, 0x41): 'Medal skills: proficiency',
    (0, 0x42): 'Medaforce screen: Medaforce / consumption / success / power',
    (0, 0x43): 'Medarot status frame (Medarot)',
    (0, 0x44): 'Parts detail frame (Type /)',
    (0, 0x52): 'Medarot select: "Please choose a Medarot"',
    (0, 0x53): 'Medarot select: "Choose Medarots or start the robattle"',
    (0, 0x54): 'Medarot menu: Make leader / View status / Back',
    (0, 0x55): 'Medarot menu: Add to team / View status / Start robattle / Back',
    (0, 0x56): 'Medarot menu: Remove from team / View status / Start robattle / Back',
    (0, 0x75): 'Medal screen hint: "button: details screen"',
    (0, 0x76): 'Medal screen frame (Level)',
    (0, 0x81): 'Link menu: Friendly robattle / Serious robattle / Trade parts / Trade medals / Disconnect',
    (0, 0x83): 'Link: "Transferring data! Please wait!"',
    (0, 0x87): 'Link trade: "Please choose the parts to trade"',
    (0, 0x88): 'Link trade menu: View / Yes / No',
    (0, 0x89): 'Link trade: "Is this part OK?"',
    (0, 0x94): 'Link battle frame (Level x2)',
    (0, 0x98): 'Yes / No menu',
    (0, 0x99): 'Link menu: Explanation / Connect / Quit',
    (1, 0x12): 'Debug: Message checker',
    (1, 0x15): 'Ad text? "Kitamura Lure, on sale!"',
    (1, 0x41): 'Debug/gallery? Character / Still / Anime',
    (1, 0x45): 'Yes / No menu',
    (1, 0x48): 'Title menu: Continue',
    (1, 0x49): 'Title menu: Transfer',
    (1, 0x50): 'Options: battle time setting (long / short)',
    (1, 0x51): 'Name entry: "Your name?"',
    (1, 0x52): 'Name entry: "Medarot\'s name?"',
    (1, 0x53): 'Name entry: katakana keyboard',
    (1, 0x54): 'Name entry: hiragana keyboard',
    (1, 0x59): 'Shop menu: Buy / Sell / Smile / Quit',
    (1, 0x5A): 'Shop menu: Buy / Sell / Smile / Password / Quit',
    (1, 0x5B): 'Shop: money window',
    (1, 0x62): 'Parts type menu: Head / Right arm / Left arm / Legs / Quit',
    (1, 0x63): 'Shop screen (money)',
    (1, 0x68): 'Shop: "How many will you buy? x" / "Owned x"',
    (1, 0x69): 'Shop: "Is this OK?"',
    (1, 0x6F): 'Menu: Get / Loose? / Back / (?)',
    (1, 0x7B): 'Shop: "How many will you sell? x" / "Owned x"',
    (1, 0xD6): 'Password output screen',
    (1, 0xD7): 'Password input screen',
    (1, 0xD8): 'Menu: Repair / Quit',
    (1, 0xD9): 'Menu: Increase / Give',
    (1, 0xDA): 'Title menu: New game',
    (1, 0xDB): 'Title menu: Settings',
    (1, 0xE1): 'Unknown screen (しょう)',
}


def jp_table():
    table = utils.read_table(os.path.join(RES, 'charmap_jp.tbl'))
    return table


def fullwidth(s):
    return ''.join(chr(ord(c) + 0xFEE0) if '!' <= c <= '~' else c for c in s)


def tile_char(table, t):
    """Full-width rendering so the layout lines up with kana in a monospace font."""
    if t is None:
        return '\u3000'
    if t == 0:
        return '．'
    if T.is_text(t):
        return fullwidth(table.get(t, '?'))
    return '＃'


def run_jp(table, tmap, run):
    out = ''
    for i, t in enumerate(run.tiles):
        if T.is_blank(t):
            out += ' '
            continue
        c = table.get(t, '<$%02X>' % t)
        d = T.dakuten_above(tmap, run, i)
        if d is not None and len(c) == 1:
            merged = unicodedata.normalize('NFC', c + ('゙' if d == T.DAKUTEN else '゚'))
            if len(merged) == 1:
                c = merged
            else:
                c += table[d]
        out += c
    return out


def dump_map(table, t, index, aliases, bank, ptr, tmap):
    runs = T.find_runs(tmap)
    lines = []
    lines.append(f'# Tilemap {t}_{index:02X}: table {t} (bank ${bank:02X}), index ${index:02X}')
    if aliases:
        lines.append('# Also used by indices: ' + ', '.join(f'${a:02X}' for a in aliases))
    kind = 'compressed' if tmap.compressed else 'raw'
    lines.append(f'# Data: ${bank:02X}:{ptr:04X}, {kind} (header ${tmap.header:02X}), {tmap.size} bytes, '
                 f'{tmap.width}x{tmap.height} tiles')
    desc = DESCRIPTIONS.get((t, index))
    if desc:
        lines.append(f'# Screen: {desc}')
    lines.append('#')
    lines.append("# Layout ('＃' graphics tile, '．' blank tile $00, '　' not drawn, ゛゜ dakuten tiles):")
    width = min(tmap.width, T.SCREEN_WIDTH) if tmap.compressed else tmap.width
    lines.append('#      ' + fullwidth(''.join(str(x % 10) for x in range(width))))
    for y in range(tmap.height):
        row = ''.join(tile_char(table, tmap.cells.get((x, y))) for x in range(width))
        lines.append(f'#   {y:2d}|{row}|')
    lines.append('#')
    lines.append('# Fill in EN: lines (leave empty to keep the Japanese). "@ row,col max N" = position')
    lines.append('# where the text starts and tiles available there. See doc/tilemaps.md.')
    lines.append('')
    lines.append(f'[{t}_{index:02X}]')
    for run in runs:
        lines.append('')
        lines.append(f'@ {run.row},{run.col} max {run.max}')
        lines.append('JP: ' + run_jp(table, tmap, run).rstrip())
        lines.append('EN:')
    return '\n'.join(lines) + '\n'


def iter_maps(rom, include_all=False):
    for t in range(T.NUM_TABLES):
        bank = T.table_bank(rom, t)
        ptrs = T.table_pointers(rom, t)
        first = {}
        for i, p in enumerate(ptrs):
            first.setdefault(p, i)
        # The last entries of table 0 point to the end of the data (unused)
        end = max(ptrs)
        for p in sorted(first):
            index = first[p]
            aliases = [i for i, q in enumerate(ptrs) if q == p and i != index]
            tmap = T.decode(rom, bank * 0x4000 + p - 0x4000)
            if p == end and tmap.size > 0x400:
                continue
            if not T.find_runs(tmap):
                continue
            if not include_all and index in GRAPHICS.get(t, ()):
                continue
            yield t, index, aliases, bank, p, tmap


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    include_all = '--all' in sys.argv
    force = '--force' in sys.argv
    rom_path, out_dir = args[:2]
    rom = open(rom_path, 'rb').read()
    os.makedirs(out_dir, exist_ok=True)
    table = jp_table()
    count = skipped = 0
    for t, index, aliases, bank, p, tmap in iter_maps(rom, include_all):
        path = os.path.join(out_dir, f'{t}_{index:02X}.txt')
        if os.path.exists(path) and not force:
            skipped += 1
            continue
        with open(path, 'w', encoding='utf-8') as f:
            f.write(dump_map(table, t, index, aliases, bank, p, tmap))
        count += 1
    print(f'Dumped {count} tilemaps to {out_dir}' + (f' ({skipped} existing files kept)' if skipped else ''))


if __name__ == '__main__':
    main()
