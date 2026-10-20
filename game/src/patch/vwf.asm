INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Variable width font renderer for the main script.
;
; Characters are drawn into a row of tiles for each line of the text box:
;  * Only mode 1 (rendered tiles) uses it: the window maps tiles $C3-$E6 (VRAM $8C30),
;    18 tiles per line. Mode 0 draws the fixed width font straight to the tilemap.
;
; Glyphs are 8x8 1bpp, left aligned, with a width table. One pixel of spacing is added after
; every character.

SECTION "VWF Trampolines", ROM0[$3EC6]
VWFReset::
  ld a, BANK(VWFResetInternal)
  ld hl, VWFResetInternal
  jr VWFFarCall

VWFNewLine::
  ld a, BANK(VWFNewLineInternal)
  ld hl, VWFNewLineInternal
  jr VWFFarCall

VWFClearTiles::
  ld a, BANK(VWFClearTilesInternal)
  ld hl, VWFClearTilesInternal
  jr VWFFarCall

VWFDrawCharacter::
  ; a = character
  ld [W_VWFChar], a
  ld a, BANK(VWFDrawCharacterInternal)
  ld hl, VWFDrawCharacterInternal
  ; Fall through

VWFFarCall:
  ; Calls a:hl, preserving the current bank. Clobbers all registers.
  push af
  ld a, [W_CurrentBank]
  ld [W_VWFSavedBank], a
  pop af
  rst $10
  call .jumpHL
  ld a, [W_VWFSavedBank]
  rst $10
  ret

.jumpHL
  jp hl

VWFTrampolinesEnd::
  ASSERT VWFTrampolinesEnd <= $4000, "VWF trampolines overflow bank 0"

SECTION "VWF Trampolines 2", ROM0[$2371]
VWFDrawArrow::
  ; a = character to draw in the last tile of the box (the 'next' arrow or a space)
  ld [W_VWFChar], a
  ld a, BANK(VWFDrawArrowInternal)
  ld hl, VWFDrawArrowInternal
  jp VWFFarCall

VWFMapMode0Box::
  ld a, [W_HardwareType]
  cp $11
  ret nz
  ld a, BANK(VWFMapMode0BoxInternal)
  ld hl, VWFMapMode0BoxInternal
  jp VWFFarCall

VWFTrampolines2End::
  ASSERT VWFTrampolines2End <= $23AE, "VWF trampolines 2 overflow into $23AE"

SECTION "VWF Renderer", ROMX[$4000], BANK[$80]
VWFFont::
  INCBIN "build/gfx/VWFFont.1bpp"
VWFFontEnd::

VWFWidths::
  INCBIN "build/gfx/VWFFont.widths"

VWFResetInternal:
  xor a
  ld [W_VWFX], a
  ld [W_VWFLine], a
  ; Fall through

VWFClearBuffers:
  ld hl, W_VWFTileBuffer
  ld b, 16
  xor a
.loop
  ld [hli], a
  dec b
  jr nz, .loop
  ret

VWFNewLineInternal:
  xor a
  ld [W_VWFX], a
  ld a, 1
  ld [W_VWFLine], a
  jr VWFClearBuffers

VWFClearTilesInternal:
  call VWFResetInternal
  call VWFGetTileBase
  ld bc, VWF_LINE_TILES * 2 * 16
.loop
  di
  call VWFSelectVRAMBank
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  xor a
  ld [hli], a
  ldh [rVBK], a
  ei
  dec bc
  ld a, b
  or c
  jr nz, .loop
  ret

VWFSelectVRAMBank:
  ; Mode 0 text is drawn into VRAM bank 1 tiles (CGB only). Preserves everything but flags.
  push af
  ld a, [W_TextMode]
  or a
  jr nz, .bank0
  ld a, 1
  ldh [rVBK], a
  pop af
  ret
.bank0
  xor a
  ldh [rVBK], a
  pop af
  ret

VWFDrawArrowInternal:
  ld a, [W_VWFChar]
  ld l, a
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  ld de, VWFFont
  add hl, de
  ld d, h
  ld e, l
  ld hl, VWF_MODE1_TILE_ADDRESS + (VWF_LINE_TILES * 2 - 1) * 16
  ld b, 8
.loop
  ld a, [de]
  inc de
  ld c, a
  di
  call VWFSelectVRAMBank
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, c
  ld [hli], a
  ld [hli], a
  xor a
  ldh [rVBK], a
  ei
  dec b
  jr nz, .loop
  ret

VWFMapMode0BoxInternal:
  ; Maps the cells of the two text lines of the mode 0 box to VRAM bank 1 tiles $C3-$E6
  call VWFClearTilesInternal
  ld hl, $9C41
  ld b, VWF_MODE1_FIRST_TILE
  call .line
  ld hl, $9C81
.line
  ld c, VWF_LINE_TILES
.cell
  di
.waitTile
  ldh a, [rSTAT]
  and 2
  jr nz, .waitTile
  ld [hl], b
  ld a, 1
  ldh [rVBK], a
.waitAttr
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAttr
  ld a, [hl]
  or $08
  ld d, a
.waitAttr2
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAttr2
  ld [hl], d
  xor a
  ldh [rVBK], a
  ei
  inc hl
  inc b
  dec c
  jr nz, .cell
  ret

VWFGetTileBase:
  ; hl = address of the first tile of the drawing area
  ld hl, VWF_MODE1_TILE_ADDRESS
  ret

VWFGetTileAddress:
  ; a = tile index on the current line
  ; Returns hl = address of the tile, carry set if the tile is out of range
  cp VWF_LINE_TILES
  ccf
  ret c
  ld c, a
  ld a, [W_VWFLine]
  or a
  ld a, c
  jr z, .gotIndex
  add VWF_LINE_TILES

.gotIndex
  ld l, a
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  ld b, h
  ld c, l
  push bc
  call VWFGetTileBase
  pop bc
  add hl, bc
  and a
  ret

VWFWriteTile:
  ; a = tile index on the current line, de = 1bpp source (8 bytes)
  call VWFGetTileAddress
  ret c
  ld b, 8
.loop
  ld a, [de]
  inc de
  ld c, a
  di
  call VWFSelectVRAMBank
.wait
  ldh a, [rSTAT]
  and $02
  jr nz, .wait
  ld a, c
  ld [hli], a
  ld [hli], a
  xor a
  ldh [rVBK], a
  ei
  dec b
  jr nz, .loop
  ret

VWFDrawCharacterInternal:
  ; Ignore characters past the end of the line
  ld a, [W_VWFX]
  cp VWF_LINE_TILES * 8
  ret nc

  ; de = glyph address
  ld a, [W_VWFChar]
  ld l, a
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  ld de, VWFFont
  add hl, de
  ld d, h
  ld e, l

  ; Combine the glyph with the current tile, spilling over into the second buffer
  ld a, [W_VWFX]
  and 7
  ld c, a ; c = shift
  ld hl, W_VWFTileBuffer
  ld b, 8
.rowLoop
  push bc
  ld a, [de]
  inc de
  ld b, a ; b = left part
  ld a, c
  or a
  ld c, 0 ; c = right part
  jr z, .shifted
.shiftLoop
  srl b
  rr c
  dec a
  jr nz, .shiftLoop
.shifted
  ld a, [hl]
  or b
  ld [hl], a
  push hl
  ld a, l
  add 8
  ld l, a
  jr nc, .noCarry
  inc h
.noCarry
  ld [hl], c
  pop hl
  inc hl
  pop bc
  dec b
  jr nz, .rowLoop

  ; Draw the current tile
  ld a, [W_VWFX]
  srl a
  srl a
  srl a
  ld de, W_VWFTileBuffer
  call VWFWriteTile

  ; Advance by the width of the character plus spacing
  ld a, [W_VWFChar]
  ld l, a
  ld h, 0
  ld de, VWFWidths
  add hl, de
  ld a, [W_VWFX]
  ld b, a
  add [hl]
  inc a
  ld [W_VWFX], a
  ; Did we move to the next tile?
  xor b
  and $F8
  ret z

  ; The overflow buffer becomes the current tile
  ld hl, W_VWFTileBuffer2
  ld de, W_VWFTileBuffer
  ld b, 8
.copyLoop
  ld a, [hl]
  ld [hli], a
  ld [de], a
  inc de
  dec b
  jr nz, .copyLoop
  ld hl, W_VWFTileBuffer2
  ld b, 8
  xor a
.clearLoop
  ld [hli], a
  dec b
  jr nz, .clearLoop

  ; Draw the new tile, in case the character spilled into it
  ld a, [W_VWFX]
  cp VWF_LINE_TILES * 8
  ret nc
  srl a
  srl a
  srl a
  ld de, W_VWFTileBuffer
  jp VWFWriteTile
