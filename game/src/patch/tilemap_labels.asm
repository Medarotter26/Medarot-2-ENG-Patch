INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Menu labels in tilemaps are drawn with the variable width font.
;
; The tilemap builder leaves the cells of translated labels blank and lists the labels
; (row, column, string) per tilemap. After a tilemap is loaded, its labels are drawn with
; PutString. Drawing switches the cells' attributes to VRAM bank 1, so when an attribute map
; is loaded afterwards, recently drawn labels get their attributes fixed again.

SECTION "Tilemap Load BG Hook Entry", ROM0[$0B1F]
  jp TilemapLoadBGHook

SECTION "Tilemap Load Window Hook Entry", ROM0[$0B2A]
  jp TilemapLoadWindowHook

SECTION "Attribute Load BG Hook Entry", ROM0[$0C54]
  jp AttrLoadBGHook

SECTION "Attribute Load Window Hook Entry", ROM0[$0C6E]
  jp AttrLoadWindowHook

SECTION "Tilemap Label Hooks", ROM0[$3F08]
TilemapLoadBGHook:
  push af
  ld a, $98
  jr TilemapLoadHook

TilemapLoadWindowHook:
  push af
  ld a, $9C
  ; Fall through

TilemapLoadHook:
  ; a = table, e = tilemap index, b = x, c = y
  ld [W_TmBase], a
  pop af
  ld [W_TmTable], a
  push af
  ld a, e
  ld [W_TmIndex], a
  ld a, b
  and $1F
  ld [W_TmX], a
  ld a, c
  and $1F
  ld [W_TmY], a
  pop af
  call .original
  jp TilemapDrawLabels

.original
  ; Same as the original entry points, then continue into the original loader
  push af
  ld a, [W_TmBase]
  ld h, a
  ld l, 0
  cp $98
  ld a, 0
  jr z, .bg
  inc a
.bg
  ld [$C41E], a
  jp $0B33

AttrFixLabels:
  ld a, BANK(AttrFixLabelsFar)
  ld hl, AttrFixLabelsFar
  jp StrFarCall

AttrLoadBGHook:
  call .original
  jp AttrFixLabels
.original
  push af
  ld a, [$DD26]
  jp $0C58

AttrLoadWindowHook:
  call .original
  jp AttrFixLabels
.original
  push af
  ld a, [$DD26]
  jp $0C72

TilemapDrawLabels:
  ld a, [W_CurrentBank]
  ld [W_TmSavedBank], a
  ld a, BANK(TilemapLabelIndex)
  rst $10
  ; hl = TilemapLabelIndex + table * 512 + index * 2
  ld a, [W_TmIndex]
  ld l, a
  ld a, [W_TmTable]
  ld h, a
  add hl, hl
  ld de, TilemapLabelIndex
  add hl, de
  ld a, [hli]
  ld h, [hl]
  ld l, a
  or h
  jr z, .done

.loop
  ld a, [hli]
  cp $FF
  jr z, .done
  ; Destination = base + (y + row) * 32 + x + column
  ld b, a
  ld a, [W_TmY]
  add b
  ld e, a
  ld d, 0
  ld a, [hli]
  ld b, a
  ld a, [W_TmX]
  add b
  push hl
  ld l, e
  ld h, d
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  add l
  ld l, a
  ld a, [W_TmBase]
  add h
  ld b, a
  ld c, l
  pop hl
  push hl
  push bc
  call PutString
  pop bc
  ld a, c
  ld [W_TmPtr], a
  ld a, b
  ld [W_TmPtr + 1], a
  ld a, BANK(LabelRingAdd)
  ld hl, LabelRingAdd
  call StrFarCall
  pop hl
  ; Skip the string
.skip
  ld a, [hli]
  cp STR_TERMINATOR
  jr nz, .skip
  jr .loop

.done
  ld a, [W_TmSavedBank]
  rst $10
  ret

TilemapLabelHooksEnd::
  ASSERT TilemapLabelHooksEnd <= $4000, "Tilemap label hooks overflow bank 0"


SECTION "Tilemap Label Ring", ROMX[$6F00], BANK[$80]
LabelRingAdd:
  ; Remembers the label just drawn at [W_TmPtr] (W_StrTemp = tiles used)
  ld a, [W_HardwareType]
  cp $11
  ret nz
  ld a, [W_StrTemp]
  or a
  ret z
  ld a, [W_LabelRingPos]
  inc a
  and LABEL_RING_SIZE - 1
  ld [W_LabelRingPos], a
  add a
  add a
  ld e, a
  ld d, 0
  ld hl, W_LabelRing
  add hl, de
  ld a, [W_TmPtr]
  ld [hli], a
  ld c, a
  ld a, [W_TmPtr + 1]
  ld [hli], a
  ld b, a
  ld a, [W_StrTemp]
  ld [hli], a
  ; First tile index
  di
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, [bc]
  ei
  ld [hl], a
  ret

AttrFixLabelsFar:
  ; Sets the VRAM bank 1 attribute bit again on the cells of labels that are still shown
  ld a, [W_HardwareType]
  cp $11
  ret nz
  ld hl, W_LabelRing
  ld c, LABEL_RING_SIZE
.entry
  push bc
  ld a, [hli]
  ld e, a
  ld a, [hli]
  ld d, a
  ld a, [hli]
  ld b, a ; tiles
  ld a, [hli]
  push hl
  ld c, a ; first tile
  ld a, b
  or a
  jr z, .next
  ; Is the label's first tile still mapped there?
  di
.waitTile
  ldh a, [rSTAT]
  and 2
  jr nz, .waitTile
  ld a, [de]
  ei
  cp c
  jr nz, .next
  ld h, d
  ld l, e
.cell
  di
  ld a, 1
  ldh [rVBK], a
.waitAttr
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAttr
  ld a, [hl]
  or $08
  ld c, a
.waitAttr2
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAttr2
  ld [hl], c
  xor a
  ldh [rVBK], a
  ei
  inc hl
  dec b
  jr nz, .cell
.next
  pop hl
  pop bc
  dec c
  jr nz, .entry
  ret
