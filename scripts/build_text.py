#!/bin/python
# Builds the main script text banks from text/dialog/*.csv
# Usage: build_text.py <baserom> <dialog dir> <font widths> <out dir> <first bank> <last bank>
#
# Each section gets an index table of 3-byte entries (bank, address) followed by its text,
# packed into banks starting at <first bank>. Untranslated entries keep the original bytes.
import csv
import os
import sys

sys.path.append(os.path.dirname(__file__))
sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils
from textcodec import Codec

TEXT_BANK_TABLE = 0x237e
TEXT_BANK_COUNT = 19
BANK_SIZE = 0x4000
MAX_ORIGINAL_LENGTH = 0x400

rom_path, dialog_dir, widths_path, out_dir, first_bank, last_bank = sys.argv[1:7]
first_bank, last_bank = int(first_bank, 0), int(last_bank, 0)
rom = open(rom_path, 'rb').read()
codec = Codec(widths_path=widths_path)

def original_bytes(bank, ptr):
    addr = utils.rom2realaddr(bank, ptr)
    i = addr
    while True:
        b = rom[i]
        if b == 0xC1:
            i += 2
            break
        i += {0xC3: 2, 0xC5: 3, 0xC7: 2}.get(b, 1)
    return rom[addr:i]

def encode_translation(text):
    data = bytearray(codec.layout(text))
    if len(data) < 2 or data[-2] != 0xC1:
        data += b'\xC1\x00'
    return bytes(data)

class Packer:
    def __init__(self):
        self.banks = {}
        self.bank = first_bank
        self.banks[self.bank] = bytearray()

    def reserve(self, size):
        if len(self.banks[self.bank]) + size > BANK_SIZE:
            self.bank += 1
            if self.bank > last_bank:
                raise Exception('Out of text banks')
            self.banks[self.bank] = bytearray()
        addr = 0x4000 + len(self.banks[self.bank])
        self.banks[self.bank] += bytes(size)
        return self.bank, addr

    def write(self, bank, addr, data):
        off = addr - 0x4000
        self.banks[bank][off:off + len(data)] = data

    def add(self, data):
        bank, addr = self.reserve(len(data))
        self.write(bank, addr, data)
        return bank, addr

packer = Packer()
section_entries = []
stats = []
orig_banks = rom[TEXT_BANK_TABLE:TEXT_BANK_TABLE + TEXT_BANK_COUNT]
for section in range(TEXT_BANK_COUNT):
    path = os.path.join(dialog_dir, f'TextSection{section:02}.csv')
    with open(path, encoding='utf-8') as f:
        rows = list(csv.reader(f))[1:]
    count = len(rows)
    tbank, taddr = packer.reserve(count * 3)
    section_entries.append((tbank, taddr))
    table = bytearray()
    placed = {}
    translated = 0
    for row in rows:
        idx = int(row[0], 16)
        ptr = int(row[1], 16)
        original = row[2]
        tr = row[3] if len(row) > 3 else ''
        if original.startswith('@') and not tr:
            loc = placed[int(original[1:], 16)]
        else:
            if tr:
                data = encode_translation(tr)
                translated += 1
            else:
                data = original_bytes(orig_banks[section], ptr)
                if len(data) > MAX_ORIGINAL_LENGTH:
                    # Pointers into non-text data, never displayed
                    data = b'\xC1\x00'
            loc = packer.add(data)
        placed[idx] = loc
        table += bytes([loc[0], loc[1] & 0xFF, loc[1] >> 8])
    packer.write(tbank, taddr, table)
    stats.append((section, count, translated))

os.makedirs(out_dir, exist_ok=True)
with open(os.path.join(out_dir, 'section_table.asm'), 'w') as f:
    for bank, addr in section_entries:
        f.write(f'  db ${bank:02X}\n  dw ${addr:04X}\n')
with open(os.path.join(out_dir, 'text_data.asm'), 'w') as f:
    for bank, data in sorted(packer.banks.items()):
        name = f'text_bank_{bank:02X}.bin'
        with open(os.path.join(out_dir, name), 'wb') as b:
            b.write(data)
        f.write(f'SECTION "Text Bank {bank:02X}", ROMX[$4000], BANK[${bank:02X}]\n')
        f.write(f'  INCBIN "{os.path.join(out_dir, name)}"\n\n')
total = sum(s[1] for s in stats)
done = sum(s[2] for s in stats)
print(f'Text: {done}/{total} entries translated, banks {first_bank:02X}-{packer.bank:02X} used '
      f'({len(packer.banks[packer.bank])} bytes in last bank)')
