# Text encoding helpers shared by the build scripts
import os
import re
import sys

sys.path.append(os.path.join(os.path.dirname(__file__), 'common'))
import utils

RES = os.path.join(os.path.dirname(__file__), 'res')

LINE_WIDTH = (18 * 8, 17 * 8)  # Pixels per line; the last tile of line 2 holds the 'next' arrow
LINES_PER_BOX = 2
SPACING = 1

# Widths assumed for strings pulled from RAM (<&XXXX>), in pixels
DEFAULT_RAM_WIDTH = 8 * 6

TOKEN_RE = re.compile(r'<([^<>]*)>|(.)', re.S)

class Codec:
    def __init__(self, charmap='charmap_en.tbl', widths_path=None):
        self.table = utils.read_table(os.path.join(RES, charmap))
        self.rev = {}
        for k, v in self.table.items():
            self.rev.setdefault(v, k)
        # Convenience aliases
        for a, b in {'「': '“', '」': '”', '…': '…', '—': '-', '–': '-', '’': "'", '‘': "'", 'ー': '-'}.items():
            if b in self.rev and a not in self.rev:
                self.rev[a] = self.rev[b]
        self.widths = None
        if widths_path:
            self.widths = open(widths_path, 'rb').read()
        self.ram_widths = {}
        p = os.path.join(RES, 'ram_widths.tbl')
        if os.path.exists(p):
            for k, v in utils.read_table(p).items():
                self.ram_widths[k] = int(v)

    def tokenize(self, text):
        """Returns a list of tokens: ('char', code) or ('cc', name, bytes)."""
        out = []
        for m in TOKEN_RE.finditer(text):
            tag, ch = m.group(1), m.group(2)
            if tag is None:
                if ch == '\n':
                    out.append(('cc', 'CR', b''))
                    continue
                if ch not in self.rev:
                    raise ValueError(f'Unknown character {ch!r} in {text!r}')
                out.append(('char', self.rev[ch]))
                continue
            if tag == 'CR':
                out.append(('cc', 'CR', b''))
            elif tag == 'CF':
                out.append(('cc', 'CF', bytes([0xC4])))
            elif tag == 'CC':
                out.append(('cc', 'CC', bytes([0xC6])))
            elif tag.startswith('S'):
                out.append(('cc', 'S', bytes([0xC3, int(tag[1:], 16)])))
            elif tag.startswith('&'):
                addr = int(tag[1:], 16)
                out.append(('cc', '&', bytes([0xC5, addr & 0xFF, addr >> 8]), addr))
            elif tag.startswith('@'):
                out.append(('cc', '@', bytes([0xC7, int(tag[1:], 16)])))
            elif tag.startswith('*'):
                out.append(('cc', '*', bytes([0xC1, int(tag[1:], 16)])))
            elif tag.startswith('$'):
                out.append(('char', int(tag[1:], 16)))
            else:
                raise ValueError(f'Unknown tag <{tag}> in {text!r}')
        return out

    def char_width(self, code):
        return self.widths[code] + SPACING

    def token_width(self, tok):
        if tok[0] == 'char':
            return self.char_width(tok[1])
        if tok[1] == '&':
            return self.ram_widths.get(tok[3], DEFAULT_RAM_WIDTH)
        return 0

    def layout(self, text):
        """Encode English text, wrapping lines and inserting box breaks as needed."""
        toks = self.tokenize(text)
        out = bytearray()
        ended = False
        # Split into boxes on explicit box breaks
        boxes = [[]]
        for t in toks:
            if t[0] == 'cc' and t[1] in ('CF', 'CC'):
                boxes[-1].append(t)
                boxes.append([])
            else:
                boxes[-1].append(t)
        for box in boxes:
            out += self.layout_box(box)
        if not out or out[-2:-1] != b'\xC1':
            # Ensure there is a terminator
            if 0xC1 not in out[-2:-1]:
                pass
        return bytes(out)

    def layout_box(self, toks):
        # Separate trailing box-break / end codes
        tail = []
        while toks and toks[-1][0] == 'cc' and toks[-1][1] in ('CF', 'CC', '*'):
            tail.insert(0, toks.pop())
        # Words: split on spaces (char 0x00) and explicit CR
        words = []  # list of (tokens, is_forced_break_before)
        cur = []
        forced = False
        for t in toks:
            if t[0] == 'char' and t[1] == 0x00:
                if cur:
                    words.append((cur, forced))
                    forced = False
                cur = []
            elif t[0] == 'cc' and t[1] == 'CR':
                if cur:
                    words.append((cur, forced))
                cur = []
                forced = True
            else:
                cur.append(t)
        if cur:
            words.append((cur, forced))
        space_w = self.char_width(0x00)

        lines = [[]]
        width = 0
        for w, forced_break in words:
            ww = sum(self.token_width(t) for t in w)
            limit = LINE_WIDTH[(len(lines) - 1) % LINES_PER_BOX]
            if lines[-1] and (forced_break or width + space_w + ww > limit):
                lines.append([])
                width = 0
                limit = LINE_WIDTH[(len(lines) - 1) % LINES_PER_BOX]
            elif not lines[-1] and forced_break and width == 0 and len(lines) > 1:
                pass
            if lines[-1]:
                lines[-1].append(('char', 0x00))
                width += space_w
            if ww > limit:
                # A single word too long for a line, split it
                for t in w:
                    tw = self.token_width(t)
                    if width + tw > limit and lines[-1]:
                        lines.append([])
                        width = 0
                    lines[-1].append(t)
                    width += tw
                continue
            lines[-1].extend(w)
            width += ww

        out = bytearray()
        for i, line in enumerate(lines):
            if i > 0:
                if i % LINES_PER_BOX == 0:
                    out.append(0xC4)  # Wait and start a new box
                else:
                    out.append(0xC2)
            for t in line:
                if t[0] == 'char':
                    out.append(t[1])
                else:
                    out += t[2]
        for t in tail:
            out += t[2]
        return out

    def encode_raw(self, text):
        """Encode without layout (used for lists and Japanese fallbacks)."""
        out = bytearray()
        for t in self.tokenize(text):
            if t[0] == 'char':
                out.append(t[1])
            elif t[1] == 'CR':
                out.append(0xC2)
            else:
                out += t[2]
        return bytes(out)
