#!/bin/python
# Dumps the non-dialog name/text lists of Medarot 2 (Kuwagata) into csv files.
# Usage (from the repo root):
#   python3 scripts/dump_ptrlists.py <baserom> <res dir> <output dir>
#   e.g. python3 scripts/dump_ptrlists.py ../baserom_kuwagata.gbc scripts/res text/ptrlists
#
# Every list is described in LIST_MAP below (see doc/ptrlists.md for the
# reverse-engineering notes behind each entry).
#
# List kinds:
#   'ptr'   - a table of little-endian 16-bit pointers (same bank) at `addr`.
#             The number of slots is (first pointer - addr) / 2.  Unused slots
#             at the end all point at the address just past the list data
#             ("dummy" pointer); they are detected as the maximum pointer value
#             when it occurs more than once, and are not dumped.
#   'fixed' - no pointer table: `count` records of `stride` bytes at `addr`.
#
# Field types (each field is a tuple):
#   ('str', label, length, terminator, pad)
#       length None  -> variable length, read up to and including terminator
#       length N     -> fixed N-byte field; text ends at terminator, the rest is
#                       `pad` (checked; a mismatch is reported on stderr)
#   ('hex', label, length)   -> raw bytes, printed as space separated hex
#   ('word', label)          -> 16-bit little-endian value, printed as hex
#
# CSV columns: Index, then per field its label; every string field gets an
# extra empty "<label>_EN" column for the translation.

import csv
import os
import sys
from collections import OrderedDict

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils

TERM = 0xC0

S = lambda label, length=None, pad=0x00, term=TERM: ('str', label, length, term, pad)
H = lambda label, length=1: ('hex', label, length)
W = lambda label: ('word', label)

# Master list table in bank 0 at $322B: 20 entries of [bank][ptr lo][ptr hi],
# read by the routine at $31FF (home vector $0270).  'master' is the index the
# game passes in register b.
LIST_MAP = OrderedDict([
    # name             kind     bank  addr    master  fields / extra
    ('PartsHead',     dict(kind='ptr', bank=0x22, addr=0x4691, master=0x00,
                           fields=[S('Model', 7), S('Name', 9), H('IsFemale')])),
    ('PartsRArm',     dict(kind='ptr', bank=0x22, addr=0x52BA, master=0x01,
                           fields=[S('Model', 7), S('Name', 9), H('IsFemale')])),
    ('PartsLArm',     dict(kind='ptr', bank=0x22, addr=0x5EE4, master=0x02,
                           fields=[S('Model', 7), S('Name', 9), H('IsFemale')])),
    ('PartsLegs',     dict(kind='ptr', bank=0x22, addr=0x6B0D, master=0x03,
                           fields=[S('Model', 7), S('Name', 9), H('IsFemale')])),
    ('Attributes',    dict(kind='ptr', bank=0x21, addr=0x65C0, master=0x04,
                           fields=[S('Name')])),
    ('Skills',        dict(kind='ptr', bank=0x21, addr=0x66B8, master=0x05,
                           fields=[S('Name')])),
    ('Movement',      dict(kind='ptr', bank=0x21, addr=0x66FD, master=0x06,
                           fields=[S('Name')])),
    ('Medals',        dict(kind='ptr', bank=0x22, addr=0x79D6, master=0x07,
                           fields=[S('Name')])),
    ('Unknown08',     dict(kind='ptr', bank=0x21, addr=0x673E, master=0x08,
                           fields=[H('Data', 24)])),
    ('Personalities', dict(kind='ptr', bank=0x21, addr=0x6D5E, master=0x09,
                           fields=[S('Name')])),
    ('Medaforce',     dict(kind='ptr', bank=0x21, addr=0x6DA0, master=0x0A,
                           fields=[H('Data', 5), S('Name')])),
    ('Unknown0B',     dict(kind='ptr', bank=0x32, addr=0x46B6, master=0x0B,
                           fields=[H('Data', 30)])),
    ('Unknown0C',     dict(kind='ptr', bank=0x20, addr=0x4000, master=0x0C,
                           fields=[H('Data', 4)])),
    ('Medarotters',   dict(kind='ptr', bank=0x20, addr=0x4601, master=0x0D,
                           fields=[H('Data', 3), S('Name')])),
    ('Unknown0E',     dict(kind='ptr', bank=0x20, addr=0x514B, master=0x0E,
                           fields=[H('Data', 23)])),
    ('Terrain',       dict(kind='ptr', bank=0x22, addr=0x7B70, master=0x0F,
                           fields=[S('Name')])),
    ('Unknown10',     dict(kind='ptr', bank=0x32, addr=0x5F36, master=0x10,
                           fields=[H('Data', 1)])),
    ('Medarots',      dict(kind='ptr', bank=0x22, addr=0x4000, master=0x11,
                           fields=[S('Name')])),
    ('Attacks',       dict(kind='ptr', bank=0x22, addr=0x7BC5, master=0x12,
                           fields=[S('Name')])),
    ('Items',         dict(kind='ptr', bank=0x22, addr=0x7736, master=0x13,
                           fields=[S('Name', 9), H('Flags')])),

    # Lists that are not in the master table
    ('Credits',       dict(kind='ptr', bank=0x04, addr=0x52D9, master=None,
                           fields=[W('VRAMAddr'), S('Text'), H('Delay')])),
    ('DebugMenu',     dict(kind='fixed', bank=0x1A, addr=0x53F9, count=23, stride=12,
                           fields=[S('Name', 12, pad=0xFF)])),
    ('StatNames',     dict(kind='fixed', bank=0x07, addr=0x6EF8, count=7, stride=5,
                           fields=[S('Name', 5)])),
    ('SkillsFixed',   dict(kind='fixed', bank=0x05, addr=0x60D4, count=8, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes04',   dict(kind='fixed', bank=0x04, addr=0x5CEE, count=4, stride=8,
                           fields=[S('Name', 8, pad=0xFF)])),
    # Identical copies of the part-type names (8-byte, 00-padded) in several banks
    ('PartTypes05',   dict(kind='fixed', bank=0x05, addr=0x59EB, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes0E',   dict(kind='fixed', bank=0x0E, addr=0x5261, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes0F',   dict(kind='fixed', bank=0x0F, addr=0x5613, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes11',   dict(kind='fixed', bank=0x11, addr=0x542A, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes13',   dict(kind='fixed', bank=0x13, addr=0x4CC9, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes16',   dict(kind='fixed', bank=0x16, addr=0x44D8, count=4, stride=8,
                           fields=[S('Name', 8)])),
    ('PartTypes1B',   dict(kind='fixed', bank=0x1B, addr=0x4C60, count=4, stride=8,
                           fields=[S('Name', 8)])),
])


def main():
    rom_path, res_path, out_path = sys.argv[1:4]
    rom = open(rom_path, 'rb').read()
    table = utils.read_table(os.path.join(res_path, 'charmap_jp.tbl'))
    os.makedirs(out_path, exist_ok=True)
    warnings = 0

    def decode(bs):
        return ''.join(table[b] if b in table else f'[{b:02X}]' for b in bs)

    def read_record(name, idx, pos):
        """Reads one record at real address pos, returns list of csv cells."""
        nonlocal warnings
        cells = []
        for f in LIST_MAP[name]['fields']:
            if f[0] == 'hex':
                n = f[2]
                cells.append(' '.join(f'{b:02X}' for b in rom[pos:pos + n]))
                pos += n
            elif f[0] == 'word':
                cells.append(f'{rom[pos] | (rom[pos + 1] << 8):04X}')
                pos += 2
            else:
                _, label, length, term, pad = f
                if length is None:
                    end = rom.index(term, pos)
                    cells.append(decode(rom[pos:end]))
                    pos = end + 1
                else:
                    field = rom[pos:pos + length]
                    if term not in field:
                        print(f'WARNING: {name}[{idx}] {label}: no terminator in fixed field', file=sys.stderr)
                        warnings += 1
                        cells.append(decode(field))
                    else:
                        t = field.index(term)
                        cells.append(decode(field[:t]))
                        if any(b != pad for b in field[t + 1:]):
                            print(f'WARNING: {name}[{idx}] {label}: unexpected padding {field[t+1:].hex()}', file=sys.stderr)
                            warnings += 1
                    pos += length
                cells.append('')  # translation column
        return cells

    for name, l in LIST_MAP.items():
        bank, addr = l['bank'], l['addr']
        base = utils.rom2realaddr(bank, addr)
        rows = []
        if l['kind'] == 'ptr':
            first = rom[base] | (rom[base + 1] << 8)
            slots = (first - addr) // 2
            ptrs = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8) for i in range(slots)]
            dummy = max(ptrs) if ptrs.count(max(ptrs)) > 1 else None
            for i, p in enumerate(ptrs):
                if p == dummy:
                    continue
                rows.append([i] + read_record(name, i, utils.rom2realaddr(bank, p)))
        else:
            for i in range(l['count']):
                rows.append([i] + read_record(name, i, base + i * l['stride']))

        header = ['Index']
        for f in l['fields']:
            header.append(f[1])
            if f[0] == 'str':
                header.append(f[1] + '_EN')
        with open(os.path.join(out_path, f'{name}.csv'), 'w', encoding='utf-8', newline='') as out:
            writer = csv.writer(out, lineterminator='\n')
            writer.writerow(header)
            writer.writerows(rows)
        print(f'{name}: {len(rows)} entries ({bank:02X}:{addr:04X})')

    if warnings:
        print(f'{warnings} warning(s)', file=sys.stderr)


if __name__ == '__main__':
    main()
