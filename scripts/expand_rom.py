#!/bin/python
# Pads a ROM to 4MB with 0xFF and updates the header ROM size
import sys
src, dst = sys.argv[1:3]
data = bytearray(open(src, 'rb').read())
data += b'\xFF' * (0x400000 - len(data))
data[0x148] = 0x07
open(dst, 'wb').write(data)
