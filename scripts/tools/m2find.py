import sys, re, os
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'common'))
import utils
tbl = utils.read_table(os.path.join(os.path.dirname(__file__), '..', 'res', 'charmap_jp.tbl'))
rev = {}
for k, v in tbl.items(): rev.setdefault(v, k)
rom = open(sys.argv[1], 'rb').read()
def enc(s): return bytes(rev[c] for c in s)
def dec(b): return ''.join(tbl.get(x, f'[{x:02X}]') for x in b)
if __name__ == '__main__':
    for w in sys.argv[2:]:
        hits = [m.start() for m in re.finditer(re.escape(enc(w)), rom)]
        print(w, len(hits))
        for h in hits[:12]:
            print(f'  {h:06X} ({h//0x4000:02X}:{h%0x4000+0x4000:04X})', dec(rom[h-24:h+40]))
