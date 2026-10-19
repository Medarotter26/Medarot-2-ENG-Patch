import os

def rom2realaddr(bank, addr):
    if addr < 0x4000:
        return addr
    return bank * 0x4000 + (addr - 0x4000)

def real2romaddr(real):
    bank = real // 0x4000
    addr = real % 0x4000 + (0x4000 if bank else 0)
    return bank, addr

def read_table(path):
    t = {}
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.rstrip('\n')
            if not line or line.startswith('#'):
                continue
            k, v = line.split('=', 1)
            t[int(k, 16)] = v
    return t
