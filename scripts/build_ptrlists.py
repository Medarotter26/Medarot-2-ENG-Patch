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

# Pixel width above which a name uses the narrow font (default: the whole field)
NARROW_THRESHOLD = {'PartsHead': 58, 'PartsRArm': 58, 'PartsLArm': 58, 'PartsLegs': 58}

NAME_TOKEN = 0xC8
STR_NARROW = 0xC9
widths = open(os.path.join(os.path.dirname(out_path), '..', 'gfx', 'VWFFont.widths'), 'rb').read()
narrow_widths = open(os.path.join(os.path.dirname(out_path), '..', 'gfx', 'VWFNarrowFont.widths'), 'rb').read()

def pixel_width(data, table):
    return sum(table[b] + 1 for b in data) - 1 if data else 0

# Names longer than the game's buffers are stored as tokens: NAME_TOKEN, list id, index.
# Master table lists use their master index as list id, the others get ids from $20.
LIST_IDS = {}
for _name, _l in LIST_MAP.items():
    if _l.get('master') is not None:
        LIST_IDS[_name] = _l['master']
_next_id = 0x20
for _name, _l in LIST_MAP.items():
    if _name not in LIST_IDS:
        LIST_IDS[_name] = _next_id
        _next_id += 1
token_names = {}  # list id -> {index: encoded full name}
token_names_dmg = {}  # list id -> {index: encoded short name for the original Game Boy}

def encode_field(name, f, raw, row):
    """Builds the bytes of a string field from the csv row."""
    _, label, length, term, pad = f
    text = row.get(label + '_EN') or ''
    if not text:
        if label == 'Model':
            return model_to_en(raw)
        return raw
    data = codec.encode_raw(text)
    limit = LIMITS.get((name, label))
    # Original Game Boy: fixed width font, so the name must fit `limit` characters
    dmg_text = row.get(label + '_DMG') or ''
    dmg = codec.encode_raw(dmg_text) if dmg_text else data
    if limit is not None and len(dmg) > limit:
        if dmg_text:
            errors.append(f'{name}[{row["Index"]}] {label}_DMG: "{dmg_text}" is {len(dmg)} chars, limit {limit}')
        dmg = dmg[:limit]
    if limit is not None and label == 'Name':
        # Names are drawn with the variable width font in a field of `limit` tiles. Some
        # screens have a marker right after the field, so leave a gap of a few pixels.
        threshold = NARROW_THRESHOLD.get(name, limit * 8)
        if pixel_width(data, widths) > threshold:
            if pixel_width(data, narrow_widths) > limit * 8:
                errors.append(f'{name}[{row["Index"]}] {label}: "{text}" is too wide even with the narrow font '
                              f'({pixel_width(data, narrow_widths)}px > {limit * 8}px)')
            data = bytes([STR_NARROW]) + data
    if limit is not None and (len(data) > limit or dmg != data.replace(bytes([STR_NARROW]), b'')):
        if label != 'Name' or len(data) > 22:
            errors.append(f'{name}[{row["Index"]}] {label}: "{text}" is {len(data)} chars, limit {limit}')
        list_id = LIST_IDS[name]
        index = int(row['Index'])
        token_names.setdefault(list_id, {})[index] = data
        token_names_dmg.setdefault(list_id, {})[index] = dmg
        data = bytes([NAME_TOKEN, list_id, index])
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

# Name token tables: NameTokenLists (Game Boy Color, full names) and NameTokenListsDMG
# (original Game Boy, short names), 64 entries of (bank, table address) each.
NAME_BANK_FIRST = reloc_bank + 1
with open(out_path, 'a') as f:
    bank, addr = NAME_BANK_FIRST, 0x4000 + 0x40 * 3 * 2
    chunks = []
    headers = []
    for label, tokens in (('NameTokenLists', token_names), ('NameTokenListsDMG', token_names_dmg)):
        lists = [None] * 0x40
        for list_id in sorted(tokens):
            names = tokens[list_id]
            count = max(names) + 1
            table_size = count * 2
            size = table_size + sum(len(n) + 1 for n in names.values())
            if addr + size > 0x8000:
                bank, addr = bank + 1, 0x4000
            lists[list_id] = (bank, addr)
            table = bytearray()
            blob = bytearray()
            for i in range(count):
                p = addr + table_size + len(blob)
                if i in names:
                    blob += names[i] + bytes([TERM])
                table += bytes([p & 0xFF, p >> 8]) if i in names else bytes([0, 0])
            chunks.append((bank, addr, bytes(table + blob)))
            addr += size
        headers.append((label, lists))
    f.write(f'SECTION "Name Token Lists", ROMX[$4000], BANK[${NAME_BANK_FIRST:02X}]\n')
    for label, lists in headers:
        f.write(f'{label}::\n')
        for entry in lists:
            b, a = entry if entry else (0, 0)
            f.write(f'  db ${b:02X}\n  dw ${a:04X}\n')
    for bank, addr, data in chunks:
        f.write(f'SECTION "Name Tokens {bank:02X}:{addr:04X}", ROMX[${addr:04X}], BANK[${bank:02X}]\n')
        for i in range(0, len(data), 16):
            f.write('  db ' + ', '.join(f'${b:02X}' for b in data[i:i + 16]) + '\n')

for e in errors:
    print('ERROR:', e, file=sys.stderr)
print(f'Lists: {len(sections)} rebuilt in place, {len(relocated)} relocated, {sum(len(v) for v in token_names.values())} name tokens')
sys.exit(1 if errors else 0)
