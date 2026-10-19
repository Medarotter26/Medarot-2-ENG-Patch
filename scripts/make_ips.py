#!/bin/python
# Creates an IPS patch (with the EOF truncation extension not needed since sizes only grow)
import sys
orig_path, mod_path, out_path = sys.argv[1:4]
orig = open(orig_path, 'rb').read()
mod = open(mod_path, 'rb').read()
out = bytearray(b'PATCH')
i = 0
n = len(mod)
while i < n:
    if i < len(orig) and orig[i] == mod[i]:
        i += 1
        continue
    start = i
    # Avoid the 'EOF' offset
    if start == 0x454F46:
        start -= 1
    end = i
    while end < n and end - start < 0xFFFF and not (end < len(orig) and orig[end] == mod[end]
                                                   and end + 1 < n and end + 1 < len(orig) and orig[end + 1] == mod[end + 1]):
        end += 1
    chunk = mod[start:end]
    # Use RLE for long runs of the same byte
    if len(chunk) > 8 and chunk.count(chunk[0]) == len(chunk):
        out += start.to_bytes(3, 'big') + b'\x00\x00' + len(chunk).to_bytes(2, 'big') + bytes([chunk[0]])
    else:
        out += start.to_bytes(3, 'big') + len(chunk).to_bytes(2, 'big') + chunk
    i = end
out += b'EOF'
open(out_path, 'wb').write(out)
