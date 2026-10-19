#!/bin/python
# Rebuilds the name lists from text/ptrlists/*.csv (see dump_ptrlists.py and doc/ptrlists.md)
# Usage: build_ptrlists.py <baserom> <ptrlists dir> <out asm> <relocation bank>
#
# Translated string fields (<Field>_EN, or <Field>_Short when present) replace the original.
# Untranslated fields keep the original bytes, except part model codes, which are always
# converted to the English encoding since the font is replaced.
# Lists are rebuilt in place when they fit; master-table lists that grow are moved to the
# relocation bank and the master table at $322B is repointed.
import csv
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils
from textcodec import Codec
from dump_ptrlists import LIST_MAP, TERM

MASTER_TABLE = 0x322B

# Maximum characters per string field (what the game's fixed-size copies allow)
LIMITS = {
    ('PartsHead', 'Name'): 8, ('PartsRArm', 'Name'): 8, ('PartsLArm', 'Name'): 8, ('PartsLegs', 'Name'): 8,
    ('PartsHead', 'Model'): 6, ('PartsRArm', 'Model'): 6, ('PartsLArm', 'Model'): 6, ('PartsLegs', 'Model'): 6,
    ('Medarots', 'Name'): 8, ('Items', 'Name'): 8, ('Medaforce', 'Name'): 8, ('Medarotters', 'Name'): 8,
    ('Medals', 'Name'): 6, ('Attributes', 'Name'): 6, ('Personalities', 'Name'): 6, ('Terrain', 'Name'): 6,
    ('Skills', 'Name'): 5, ('Movement', 'Name'): 5, ('Attacks', 'Name'): 5,
    ('SkillsFixed', 'Name'): 7, ('PartTypes04', 'Name'): 5, ('StatNames', 'Name'): 4, ('DebugMenu', 'Name'): 11,
    ('PartTypes05', 'Name'): 7, ('PartTypes0E', 'Name'): 7, ('PartTypes0F', 'Name'): 7, ('PartTypes11', 'Name'): 7,
    ('PartTypes13', 'Name'): 7, ('PartTypes16', 'Name'): 7, ('PartTypes1B', 'Name'): 7,
}

rom_path, list_dir, out_path, reloc_bank = sys.argv[1:5]
reloc_bank = int(reloc_bank, 0)
rom = open(rom_path, 'rb').read()
codec = Codec()
jp = utils.read_table(os.path.join(os.path.dirname(__file__), 'res', 'charmap_jp.tbl'))

errors = []

def model_to_en(raw):
    # Model codes use the Japanese A-Z ($CD-$E6), ー ($6D) and digits ($E7-$F0)
    out = bytearray()
    for b in raw:
        if 0xCD <= b <= 0xE6:
            out.append(0x01 + b - 0xCD)
        else:
            out.append(b)
    return bytes(out)

def parse_record(name, pos):
    """Returns a list of raw byte strings, one per field, and the record end."""
    fields = []
    for f in LIST_MAP[name]['fields']:
        if f[0] == 'hex':
            fields.append(rom[pos:pos + f[2]])
            pos += f[2]
        elif f[0] == 'word':
            fields.append(rom[pos:pos + 2])
            pos += 2
        else:
            _, label, length, term, pad = f
            if length is None:
                end = rom.index(term, pos)
                fields.append(rom[pos:end + 1])
                pos = end + 1
            else:
                fields.append(rom[pos:pos + length])
                pos += length
    return fields, pos

def encode_field(name, f, raw, row):
    """Builds the bytes of a string field from the csv row."""
    _, label, length, term, pad = f
    text = row.get(label + '_Short') or row.get(label + '_EN') or ''
    if not text:
        if label == 'Model':
            return model_to_en(raw)
        return raw
    data = codec.encode_raw(text)
    limit = LIMITS.get((name, label))
    if limit is not None and len(data) > limit:
        errors.append(f'{name}[{row["Index"]}] {label}: "{text}" is {len(data)} chars, limit {limit}')
    if length is None:
        return data + bytes([term])
    if len(data) + 1 > length:
        errors.append(f'{name}[{row["Index"]}] {label}: "{text}" does not fit in {length} bytes')
        data = data[:length - 1]
    return data + bytes([term]) + bytes([pad]) * (length - len(data) - 1)

def build_record(name, raw_fields, row):
    out = bytearray()
    for f, raw in zip(LIST_MAP[name]['fields'], raw_fields):
        if f[0] == 'str':
            out += encode_field(name, f, raw, row)
        else:
            out += raw
    return bytes(out)

def read_rows(name):
    path = os.path.join(list_dir, f'{name}.csv')
    with open(path, encoding='utf-8') as f:
        return {int(r['Index']): r for r in csv.DictReader(f)}

sections = []
relocated = []
reloc_addr = 0x4000
reloc_data = bytearray()

for name, l in LIST_MAP.items():
    if not any(f[0] == 'str' for f in l['fields']):
        continue
    rows = read_rows(name)
    bank, addr = l['bank'], l['addr']
    base = utils.rom2realaddr(bank, addr)
    if l['kind'] == 'fixed':
        out = bytearray()
        for i in range(l['count']):
            raw, _ = parse_record(name, base + i * l['stride'])
            rec = build_record(name, raw, rows.get(i, {'Index': str(i)}))
            if len(rec) != l['stride']:
                errors.append(f'{name}[{i}]: record size changed')
            out += rec
        if out != rom[base:base + len(out)]:
            sections.append((name, bank, addr, bytes(out)))
        continue

    first = rom[base] | (rom[base + 1] << 8)
    slots = (first - addr) // 2
    ptrs = [rom[base + 2 * i] | (rom[base + 2 * i + 1] << 8) for i in range(slots)]
    dummy = max(ptrs) if ptrs.count(max(ptrs)) > 1 else None
    data_end = max(ptrs) if dummy is not None else None
    records = {}
    for i, p in enumerate(ptrs):
        if p == dummy:
            continue
        raw, end = parse_record(name, utils.rom2realaddr(bank, p))
        records[i] = build_record(name, raw, rows.get(i, {'Index': str(i)}))
        if data_end is None or (dummy is None and end > utils.rom2realaddr(bank, data_end)):
            data_end = utils.real2romaddr(end)[1]
    # Original span: from the table to the end of the data
    span = data_end - addr

    def assemble(at):
        table = bytearray()
        blob = bytearray()
        offsets = {}
        data_start = at + slots * 2
        for i in sorted(records):
            offsets[i] = data_start + len(blob)
            blob += records[i]
        for i in range(slots):
            if i in offsets:
                p = offsets[i]
            else:
                p = dummy if at == addr else data_start + len(blob)
            table += bytes([p & 0xFF, p >> 8])
        return bytes(table + blob)

    out = assemble(addr)
    if len(out) <= span:
        if out != rom[base:base + len(out)]:
            sections.append((name, bank, addr, out))
    elif l.get('master') is not None:
        out = assemble(reloc_addr)
        relocated.append((name, l['master'], reloc_addr))
        reloc_data += out
        reloc_addr += len(out)
        if reloc_addr > 0x8000:
            errors.append('Relocation bank overflow')
    else:
        errors.append(f'{name}: rebuilt list ({len(out)} bytes) does not fit in place ({span} bytes)')

with open(out_path, 'w') as f:
    for name, bank, addr, data in sections:
        f.write(f'SECTION "List {name}", ROMX[${addr:04X}], BANK[${bank:02X}]\n')
        for i in range(0, len(data), 16):
            f.write('  db ' + ', '.join(f'${b:02X}' for b in data[i:i + 16]) + '\n')
        f.write('\n')
    if relocated:
        f.write(f'SECTION "Relocated Lists", ROMX[$4000], BANK[${reloc_bank:02X}]\n')
        for i in range(0, len(reloc_data), 16):
            f.write('  db ' + ', '.join(f'${b:02X}' for b in reloc_data[i:i + 16]) + '\n')
        f.write('\n')
        for name, master, at in relocated:
            f.write(f'SECTION "Master List Entry {name}", ROM0[${MASTER_TABLE + master * 3:04X}]\n')
            f.write(f'  db ${reloc_bank:02X}\n  dw ${at:04X}\n\n')
            if name == 'Items':
                # GetItemName ($31A4) reads the item list directly
                f.write('SECTION "Item Name Bank", ROM0[$31A6]\n')
                f.write(f'  db ${reloc_bank:02X}\n')
                f.write('SECTION "Item Name Address", ROM0[$31AA]\n')
                f.write(f'  dw ${at:04X}\n\n')

for e in errors:
    print('ERROR:', e, file=sys.stderr)
print(f'Lists: {len(sections)} rebuilt in place, {len(relocated)} relocated')
sys.exit(1 if errors else 0)
