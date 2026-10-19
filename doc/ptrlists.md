# Medarot 2 (Kuwagata) – non-dialog text lists

ROM: `baserom_kuwagata.gbc` (header title `MEDAROT2KWGA2NJ`), MBC5.
Real address = `bank * 0x4000 + (addr - 0x4000)`.
Dumped by `scripts/dump_ptrlists.py` into `text/ptrlists/<List>.csv`
(`python3 scripts/dump_ptrlists.py ../baserom_kuwagata.gbc scripts/res text/ptrlists`).

All strings in this document use the main charmap (`scripts/res/charmap_jp.tbl`) and
are terminated by **`0xC0`**. One character = one 8x8 tile when printed (voiced kana
draw their dakuten in the row *above* the text; see `PutString` below).

## Summary

| List | Location | Slots / real entries | Structure | Max JP len | Max usable len (where shown) |
|---|---|---|---|---|---|
| PartsHead | 22:4691 (ptr) | 256 / 153 | fixed 17 B: Model[7] Name[9] IsFemale[1] | 6 / 8 | Model 6, Name 8 |
| PartsRArm | 22:52BA (ptr) | 256 / 153 | same | 6 / 8 | Model 6, Name 8 |
| PartsLArm | 22:5EE4 (ptr) | 256 / 153 | same | 6 / 8 | Model 6, Name 8 |
| PartsLegs | 22:6B0D (ptr) | 256 / 153 | same | 6 / 8 | Model 6, Name 8 |
| Attributes | 21:65C0 (ptr) | 48 / 32 | var, C0 | 6 | 6 (7-byte copy, centred in 6) |
| Skills | 21:66B8 (ptr) | 16 / 8 | var, C0 | 5 | 5 (6-byte copy) |
| Movement | 21:66FD (ptr) | 16 / 7 | var, C0 | 4 | 5 (6-byte copy) |
| Medals | 22:79D6 (ptr) | 64 / 61 | var, C0 | 6 | 6 (7-byte copy, centred in 6) |
| Personalities | 21:6D5E (ptr) | 16 / 6 | var, C0 | 6 | 6 (7-byte copy) |
| Medaforce | 21:6DA0 (ptr) | 96 / 96 | 5 data bytes + var name | 8 | 8 (9-byte copy) |
| Medarotters | 20:4601 (ptr) | 256 / 256 | 3 data bytes + var name | 8 | 8 (12-byte copy, centred in 8) |
| Terrain | 22:7B70 (ptr) | 16 / 11 | var, C0 | 5 | 6 (7-byte copy, centred in 6) |
| Medarots | 22:4000 (ptr) | 256 / 151 | var, C0 | 8 | 8 (9-byte copy, centred in 8) |
| Attacks | 22:7BC5 (ptr) | 80 / 77 | var, C0 | 5 | 5 (6-byte copy) |
| Items | 22:7736 (ptr) | 56 / 56 | fixed 10 B: Name[9] Flags[1] | 8 | 8 (9-byte copy to $c462) |
| Credits | 04:52D9 (ptr) | 65 / 65 | VRAM addr[2] + var text + delay[1] | 14 | 20 − column |
| DebugMenu | 1A:53F9 (fixed) | 23 | 12-byte stride, FF padded | 10 | 11 |
| StatNames | 07:6EF8 (fixed) | 7 | 5-byte stride | 4 | 4 |
| SkillsFixed | 05:60D4 (fixed) | 8 | 8-byte stride, 00 padded | 5 | 7 |
| PartTypes04 | 04:5CEE (fixed) | 4 | 8-byte stride, FF padded | 5 | **5** (6-byte copy) |
| PartTypes05/0E/0F/11/13/16/1B | see below (fixed) | 4 each | 8-byte stride, 00 padded | 5 | 7 (8-byte copy) |
| Unknown08 | 21:673E (ptr) | 64 / 60 | 24 data bytes | – | data |
| Unknown0B | 32:46B6 (ptr) | 256 / 192 | 30 data bytes | – | data |
| Unknown0C | 20:4000 (ptr) | 256 / 256 | 4 data bytes | – | data |
| Unknown0E | 20:514B (ptr) | 256 / 256 | 23 data bytes (enemy teams?) | – | data |
| Unknown10 | 32:5F36 (ptr) | 256 / 109 | 1 data byte | – | data |

"Max usable len" = what fits through the game's fixed-size copy (number of bytes
copied minus one for the terminator) / centring width. Anything longer is either
truncated without a terminator (garbage is printed until a stray `C0`) or makes the
centring routine underflow. See the per-list sections for the code addresses.

## Pointer-table conventions

* Each "ptr" list is a table of little-endian 16-bit pointers into the same bank,
  immediately followed by the data. The number of slots is
  `(first pointer − table address) / 2`.
* Unused trailing slots are filled with a single "dummy" pointer = the address just
  past the list's data (which is usually the next table). They are always contiguous at
  the end. The dumper treats the maximum pointer as dummy when it occurs more than once
  and does not output those slots (so CSV indices are the real game IDs, and
  `slots − real entries` dummies must be regenerated on reinsertion).
* Records are laid out back to back in pointer order. Exception: `PartsRArm[39]`
  (`DVLー12 ヘルマイト`, 22:5751) is followed by one stray `00` byte (stride 18 instead
  of 17); harmless, since all access is through pointers.

## Master list table (bank 0, $322B)

`$322B`: 20 entries of 3 bytes `[bank][ptr lo][ptr hi]` (ends right where
`Call_000_3267` begins). Accessed only by `GetListEntry` = `Call_000_31ff`
(home vector `$0270` → `$06D0`):

```
in:  b = list index (row below), c = number of bytes to copy,
     [$c55e] = entry index, [$c55f] = byte offset inside the entry
     bank  = table[b].bank ; hl = table[b].ptr ; hl = [hl + 2*[$c55e]] ; hl += [$c55f]
     copy c bytes  hl -> $c560
```

The copy is a **fixed byte count, not terminator-aware**: if a string is longer than
`c − 1` characters the terminator is not copied, and the following bytes of `$c560`
(16-byte buffer `$c560–$c56f`; `$c570` is a different buffer used by `$32F4`) are
whatever was there before.

| b | Address | List | Typical (c, offset) used by the game |
|---|---|---|---|
| 00 | 22:4691 | PartsHead | (9, 7) name, (7, 0) model, (10, 7) name+flag, (1, 16) IsFemale |
| 01 | 22:52BA | PartsRArm | same |
| 02 | 22:5EE4 | PartsLArm | same |
| 03 | 22:6B0D | PartsLegs | same |
| 04 | 21:65C0 | Attributes | (7, 0) |
| 05 | 21:66B8 | Skills | (6, 0) |
| 06 | 21:66FD | Movement | (6, 0) |
| 07 | 22:79D6 | Medals | (7, 0), once (9, 0) |
| 08 | 21:673E | Unknown08 | (16, 8), (12, 8), (4, 8), (4, 20), (1, 8), (1, 10) |
| 09 | 21:6D5E | Personalities | (7, 0) |
| 0A | 21:6DA0 | Medaforce | (9, 5) name, (14, 0) whole record, (4, 1), (1, 0), (1, 3) |
| 0B | 32:46B6 | Unknown0B | (1, 11), (1, 12), (1, 15), (1, 29) |
| 0C | 20:4000 | Unknown0C | (4, 0) |
| 0D | 20:4601 | Medarotters | (12, 0) |
| 0E | 20:514B | Unknown0E | (14, 0), (9, 14), (16, 0), (3, 14), (3, 17) |
| 0F | 22:7B70 | Terrain | (7, 0) |
| 10 | 32:5F36 | Unknown10 | (1, 0) |
| 11 | 22:4000 | Medarots | (9, 0) |
| 12 | 22:7BC5 | Attacks | (6, 0) |
| 13 | 22:7736 | Items | (1, 9) flags (names use `$31A4`, below) |

The list indices and bank layout match Medarot 3's "general pointer list" order.

### Other relevant home routines

* `$31A4` (vector `$0252`): `GetItemName` – bank $22, `hl = [$7736 + 2*a]`, copies
  **9 bytes** to `$c462` (fixed, not terminator-aware). Max 8 chars.
* `$30A3` (vector `$023A`): `PutString` – prints C0-terminated string at `hl` to
  VRAM `bc`, one tile per character; voiced kana are split by `$22E4` and the
  dakuten tile is written at `bc − $20` (row above).
* `$310F` (vector `$023D`): `CentreOffset` – counts chars up to `C0` and returns
  `(a − len) / 2`. Callers pass `a` = field width (6 or 8). A string longer than the
  width gives a negative (wrapped) offset → text drawn far off position.
* `$10B6` (vector `$024F`): pointer lookup `hl = [hl + 2*a]`.
* `$32F4` (vector `$0285`): copies 16-byte records from bank $21 tables
  (`$3330`: 21:4000/4970/52E0/5C50 = head/rarm/larm/legs part stats) into `$c570`
  – no text.

## RAM buffers that receive names (overflow risks)

Addresses in this section are ROM locations of the `call $0270` (or of the copy code).

| Buffer | Size | Filled at | Contents |
|---|---|---|---|
| `$c560` | 16 | `$31FF` | generic list copy (see c values above) |
| `$c462` | 9 | `$31A4` (printed from 07:474E) | item name |
| `$c4d4` | 12 | 05:569A (`b=0D, c=12`) | Medarotter record; name at `$c4d7`, centred in 8 at 05:5946, 11:4FCA |
| `$c4e0` / `$c4ee` | 14 / 9 | 05:56BB / 05:56DB (`b=0E`) | Unknown0E record pieces (data) |
| `$c50f` | 9 | 05:5D95 (`b=07, c=9`) → copy at 05:5D9C | medal name |
| `$c50f` | 8 | 05:59CA, 11:5409, 13:4CA9 (PartTypes tables) | part-type name |
| `$c518` | 9 | 05:6588 (`b=0A, c=9, off=5`) → 05:658E | Medaforce name |
| `$c518` | 8 | 05:60B3 → 05:60C3 (SkillsFixed) | skill name |
| `$cc9e` | 9 / 7 | 04:5CC1 (part name, 9 B), 18:40CC (Terrain, 7 B), 18:4D69 (Medarotter name, 9 B taken from `$c563`) | |
| `$cca9` | 6 | 04:5C94 → 04:5CA7 (PartTypes04) | part-type name (**max 5 chars**) |
| `$b33d` | 9 | 0D:4773 and many others (0D–1A) | Medarot name copied from a Medarot struct (+2) |
| `$b346` | 6 / 8 | 0F:5ADE (Skills, 6 B); 0E:5240, 0F:55F2, 16:44B7, 1B:4C3F (PartTypes, 8 B) | |
| `$b34f` | 6 | 0F:5B03 (Attacks, 6 B) | attack name |
| Medarot struct (`de`) | 9 each | 0D:4D42/4DB0/4E1E/4E8C and 12:5229/5297/5305/5373 (parts, +$60/+$80/+$A0/+$C0); 0D:4FED (Medarot name, +$02, next field at +$0B) | battle copies of the names |

Any English name longer than the copy size needs code changes (bigger copy counts and
relocated buffers); the Medarot-struct and SRAM slots are fixed-size.

## Per-list details

### Parts (Head / RArm / LArm / Legs) – 22:4691, 22:52BA, 22:5EE4, 22:6B0D
* Pointer table (256 slots, 153 used, slots 153–255 = dummy → next table).
* Record, 17 bytes fixed width:
  `Model[7]` = 6 chars (`AAAー11` style) + `C0`;
  `Name[9]`  = up to 8 chars + `C0`, `00` padded;
  `IsFemale[1]` (`00`/`01`; 33 entries per slot are `01`, e.g. `PLNー11` = Lady
  Booster's parts).
* Reads: name `c=9, off=7` (04:5CC1, 05:524C, 05:55EA, 07:6567, 07:6AA9,
  08:4ABF/4AED/4B1B/4B49, 0D:4D42.., 0E:6EB9, 11:5466, 12:5229.., 13:4B61 – centred
  in 8 at 13:4B69, 13:4CFA); model `c=7, off=0` (07:6487, 13:4B87); name+flag `c=10,
  off=7` (04:7412, 04:7788, inventory lists); IsFemale `c=1, off=16` (07:661D,
  07:6FA5.., 08:4D71.., 0D:4FD7, 18:6D63).
* **Max 8 chars name, 6 chars model.**
* Entries 101/102 are hiragana "prototype" Rokusho/Metabee parts; entry 101's model is
  `KGWー0x` (typo for KWG in the original data). Entries 151/152 are
  `BAYー03 ーーーーーーーー` placeholders.

### Medarots – 22:4000
* 256 slots, 151 used (151–255 → 22:4691). Variable length, `C0`.
* Read with `b=$11, c=9, off=0` at 0D:4FED and stored at Medarot struct +2 (9 bytes,
  next field at +$0B); later copied to SRAM `$b33d` and centred in 8 from the struct
  (08:48F6, 08:5A8F, 08:6D6F, 08:6DD0, 18:4581). **Max 8.**

### Medals – 22:79D6
* 64 slots, 61 used (61–63 → 22:7B70 = Terrain table). Variable, `C0`.
* Entries 0–31 katakana (0 = クワガタ, 1 = カブト …), 32–60 the same names in
  hiragana (probably used as default nicknames / alternate display).
* Read with `c=7` at 08:4A07, 08:5AB5, 08:63F9, 11:5400, 13:4D36 (centred in 6 at
  13:4D3E), 13:50EA; with `c=9` → `$c50f` at 05:5D95. **Max 6.**

### Items – 22:7736
* 56 slots, all used. Fixed 10-byte records: `Name[9]` (≤8 chars + C0, 00 pad) +
  `Flags[1]`.
* Name via `$31A4` → `$c462` (9 bytes), printed at 07:474E; flags via `$31FF`
  `b=$13, c=1, off=9` (07:4B70). **Max 8.**

### Attributes – 21:65C0
* 48 slots, 32 used. Variable, `C0`. `c=7` at 05:6146 (centred in 6 at 05:614E),
  07:6AD0, 08:64DA (centred in 6 at 08:64E2), 08:66F0. **Max 6.**

### Skills – 21:66B8
* 16 slots, 8 used. `c=6` at 07:6AEA, 08:6A60, 0F:5ADE (→ `$b346`). **Max 5.**
* `SkillsFixed` (05:60D4) is a second copy of the same 8 names in 8-byte, 00-padded
  slots, copied 8 bytes to `$c518` by 05:60AF (max 7).

### Movement – 21:66FD
* 16 slots, 7 used. `c=6` at 07:6B06. **Max 5.**

### Personalities – 21:6D5E
* 16 slots, 6 used. `c=7` at 08:671A. **Max 6.**

### Terrain – 22:7B70
* 16 slots, 11 used (11–15 → 22:7BC5). `c=7` at 05:56FC and 11:4F1D (both centred in 6),
  18:40CC (→ `$cc9e`, 7 B). **Max 6.**

### Attacks – 22:7BC5
* 80 slots, 77 used (77–79 → 22:7DFC, end of data). `c=6` at 0F:5B03 (→ `$b34f`).
  **Max 5.**

### Medaforce – 21:6DA0
* 96 slots, all used. Record: 5 data bytes + variable name + `C0`.
* Name `c=9, off=5`: 05:6588 (→ `$c518`), 08:6927/6955/6983 (printed at
  $9881/$98E1/$9941). Whole record `c=14, off=0`: 0D:7366.., 12:785A.., 1B:510E
  (also caps the name at 8). **Max 8.**

### Medarotters – 20:4601
* 256 slots, all used (many duplicates, e.g. アリカ ×3 – one per encounter).
  Record: 3 data bytes + variable name + `C0`.
* Read with `c=12, off=0` into `$c4d4` (05:569A); name at `$c4d7`, centred in 8
  (05:5946, 11:4FCA); 18:4D69 copies 9 bytes of the name to `$cc9e`. **Max 8.**

### Credits – 04:52D9
* 65 pointers. Record: `VRAMAddr` (LE word, BG-map address, e.g. `9904`), text +
  `C0`, then 1 byte (`Delay`, stored to `$c3ea`). Read by `Call_004_52a6`
  (04:52A6), printed with `PutString` at `VRAMAddr`. Max length = 20 minus the
  starting column (`VRAMAddr & $1F`).

### Small fixed tables embedded in code banks
* **DebugMenu** 1A:53F9 – 23 × 12 bytes (`C0` + `FF` padding). Read at 1A:50EC
  (index `[$cc01]*12`, 8 rows printed from $9842, +$40 per row). Max 11.
* **StatNames** 07:6EF8 – 7 × 5 bytes (そうこう/すいしん/きどう/かくとう/しゃげき/
  さくてき/いんペい; きどう is padded with a `00` space). Read by `Call_007_6ebd`
  (07:6EBD; index `[$cc02]*5`, 5 rows via `PutString` from $984B). **Max 4**
  without moving the data.
* **PartTypes** (あたま/みぎうで/ひだリうで/きゃくぶ), 4 × 8 bytes each:
  04:5CEE (`FF` pad; read at 04:5C94, **6** bytes copied to `$cca9` → max 5);
  05:59EB (05:59CA), 11:542A (11:5409), 13:4CC9 (13:4CA9) → `$c50f`, 8 B;
  0E:5261 (0E:5240), 0F:5613 (0F:55F2), 16:44D8 (16:44B7), 1B:4C60 (1B:4C3F) →
  `$b346`, 8 B. Max 7 except the bank-04 copy. All copies must be translated together.

### Data-only master lists (dumped as hex for completeness)
* **Unknown08** 21:673E – 60 × 24 bytes.
* **Unknown0B** 32:46B6 – 192 × 30 bytes (per-Medarot data?; bytes 11/12/15/29 read
  individually).
* **Unknown0C** 20:4000 – 256 × 4 bytes (per-Medarotter, read `c=4` at 05:5653).
* **Unknown0E** 20:514B – 256 × 23 bytes: per-Medarotter enemy team (Medarot/part IDs,
  levels …), read at 05:56BB/56DB, 18:6CBC.. In Medarot 3 the equivalent table is where
  Kabuto/Kuwagata differ.
* **Unknown10** 32:5F36 – 109 × 1 byte (19:52F8).

## Version-specific content (Kuwagata)

* Only the Kuwagata ROM is available, so no byte-level diff against Kabuto was possible.
* The text lists themselves contain **both** versions' protagonists: parts 31 `KWG-0x`
  (Rokusho line) and 32 `KBT-0x` (Metabee line), 37/38 the `-1x` variants, 101/102 the
  hiragana prototype versions (`KGW` typo); Medarots 31 ヘッドシザース / 32 メタルビートル
  and 101 ろくしょう / 102 めたびー; Medals 0 クワガタ / 1 カブト. Nothing in the name
  lists is obviously exclusive to this version; the Kuwagata entry is listed before the
  Kabuto one in every pair (whether the Kabuto ROM swaps this order is unverified).
* By analogy with Medarot 3 (where `Medarotters` and the enemy-team table differ per
  version), any version difference is most likely in Unknown0E / Medarotters data
  bytes rather than in strings. Compare against a Kabuto ROM before sharing CSVs
  between versions.

## Not covered here

* Dialog (text banks via table `$237E`: 0x23, 0x24, 0x6F–0x7E, 0x3A).
* Menu/status screens drawn from (compressed) tilemaps with `FE`/`FF` control bytes,
  e.g. banks 0x34/0x35 (`[FE]そうこう[FE]…かいすう…せいこう…いリょく`, はい/いいえ/
  やめる), and the name-entry keyboards in banks 0x27–0x2C. Those need a tilemap
  dumper, not a list dumper.
