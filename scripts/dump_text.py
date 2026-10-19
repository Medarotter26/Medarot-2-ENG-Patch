#!/bin/python
# Dumps the main script text banks of Medarot 2 into csv files.
# Usage: dump_text.py <baserom> <res dir> <output dir>
import csv
import os
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils

TEXT_BANK_TABLE = 0x237e
TEXT_BANK_COUNT = 19

rom_path, res_path, out_path = sys.argv[1:4]
rom = open(rom_path, 'rb').read()
table = utils.read_table(os.path.join(res_path, 'charmap_jp.tbl'))

def decode(addr):
    """Decode a string starting at real address `addr`. Returns (text, length)."""
    out = ''
    i = addr
    while True:
        b = rom[i]
        if b == 0xC1:
            p = rom[i + 1]
            out += f'<*{p:02X}>' if p else ''
            i += 2
            break
        elif b == 0xC2:
            out += '<CR>'  # Second line
            i += 1
        elif b == 0xC3:
            out += f'<S{rom[i+1]:02X}>'  # Speed
            i += 2
        elif b == 0xC4:
            out += '<CF>'  # Wait for input, new box
            i += 1
        elif b == 0xC5:
            out += f'<&{rom[i+1] | (rom[i+2] << 8):04X}>'  # Text from RAM
            i += 3
        elif b == 0xC6:
            out += '<CC>'  # New box, no input
            i += 1
        elif b == 0xC7:
            out += f'<@{rom[i+1]:02X}>'  # Portrait
            i += 2
        elif b in table:
            out += table[b]
            i += 1
        else:
            out += f'<${b:02X}>'
            i += 1
    return out, i - addr

os.makedirs(out_path, exist_ok=True)
banks = rom[TEXT_BANK_TABLE:TEXT_BANK_TABLE + TEXT_BANK_COUNT]
for section, bank in enumerate(banks):
    base = utils.rom2realaddr(bank, 0x4000)
    first = rom[base] | (rom[base + 1] << 8)
    count = (first - 0x4000) // 2
    seen = {}
    rows = []
    for idx in range(count):
        ptr = rom[base + idx * 2] | (rom[base + idx * 2 + 1] << 8)
        real = utils.rom2realaddr(bank, ptr)
        if ptr in seen:
            rows.append([f'{idx:03X}', f'0x{ptr:04X}', f'@{seen[ptr]:03X}', ''])
            continue
        seen[ptr] = idx
        text, _ = decode(real)
        rows.append([f'{idx:03X}', f'0x{ptr:04X}', text, ''])
    with open(os.path.join(out_path, f'TextSection{section:02}.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['Index', 'Pointer', 'Original', 'Translated'])
        w.writerows(rows)
    print(f'Section {section:02} bank {bank:02X}: {count} entries')
