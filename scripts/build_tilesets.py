#!/bin/python
# Builds replacement tilesets from gfx/tilesets/ts_XXX.png (XXX = tileset index, hex).
# Each PNG is converted to 2bpp (white=0, light grey=1, dark grey=2, black=3), stored
# uncompressed in the expansion banks, and the tileset tables are repointed:
#   bank 0 $3A20 + 2*i: source address, bank $3B $682B + 4*i: source bank.
# Usage: build_tilesets.py <png dir> <out asm> <first bank> <last bank>
import glob
import os
import sys
from PIL import Image

png_dir, out_path, first_bank, last_bank = sys.argv[1:5]
first_bank, last_bank = int(first_bank, 0), int(last_bank, 0)

def png_to_2bpp(path):
    im = Image.open(path).convert('L')
    w, h = im.size
    assert w % 8 == 0 and h % 8 == 0, f'{path}: size must be a multiple of 8'
    px = im.load()
    out = bytearray()
    for ty in range(h // 8):
        for tx in range(w // 8):
            tile = bytearray()
            for y in range(8):
                lo = hi = 0
                for x in range(8):
                    v = px[tx * 8 + x, ty * 8 + y]
                    c = 3 - min(3, (v + 42) // 85)
                    lo |= (c & 1) << (7 - x)
                    hi |= (c >> 1) << (7 - x)
                tile += bytes([lo, hi])
            out += tile
    return bytes(out)

entries = []
for path in sorted(glob.glob(os.path.join(png_dir, 'ts_*.png'))):
    idx = int(os.path.basename(path)[3:6], 16)
    data = png_to_2bpp(path)
    # Optional: number of tiles to keep (trailing tiles of the image may be padding)
    count_path = path[:-4] + '.count'
    if os.path.exists(count_path):
        data = data[:int(open(count_path).read().strip(), 0) * 16]
    entries.append((idx, data))

bank, addr = first_bank, 0x4000
with open(out_path, 'w') as f:
    for idx, data in entries:
        size = len(data) + 3
        if addr + size > 0x8000:
            bank, addr = bank + 1, 0x4000
            assert bank <= last_bank, 'Out of tileset banks'
        f.write(f'SECTION "Tileset {idx:03X}", ROMX[${addr:04X}], BANK[${bank:02X}]\n')
        f.write(f'  db 0\n  dw ${len(data):04X}\n')
        for i in range(0, len(data), 16):
            f.write('  db ' + ', '.join(f'${b:02X}' for b in data[i:i + 16]) + '\n')
        f.write(f'SECTION "Tileset {idx:03X} Source", ROM0[${0x3A20 + idx * 2:04X}]\n  dw ${addr:04X}\n')
        f.write(f'SECTION "Tileset {idx:03X} Bank", ROMX[${0x682B + idx * 4:04X}], BANK[$3B]\n  db ${bank:02X}\n\n')
        addr += size
print(f'Tilesets: {len(entries)} replaced')
