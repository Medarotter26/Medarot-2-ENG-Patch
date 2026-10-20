INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Variable width font renderer for the main script.
;
; Characters are drawn into a row of tiles for each line of the text box, 18 tiles per line:
;  * Mode 1 (rendered tiles): the window maps tiles $C3-$E6 (VRAM $8C30).
;  * Mode 0 (text box in the tilemap): the box cells are mapped to private tiles: VRAM bank 1
;    tiles $C3-$E6 on the Game Boy Color; on the original Game Boy, 36 font tiles that aren't
;    on screen, taken from the string tile pool (W_VWFBoxTiles lists them).
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
  ; Preserves bc: callers of the text init expect what the original left there
  push bc
  ld a, BANK(VWFMapMode0BoxInternal)
  ld hl, VWFMapMode0BoxInternal
  call VWFFarCall
  pop bc
  ret

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
  call VWFDmgBox
  jr z, .dmgBox
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

.dmgBox
  ld c, 0
.dmgTile
  ld a, c
  call VWFTileAddrByIndex
  ld b, 16
.dmgClear
  di
.dmgWait
  ldh a, [rSTAT]
  and 2
  jr nz, .dmgWait
  xor a
  ld [hli], a
  ei
  dec b
  jr nz, .dmgClear
  inc c
  ld a, c
  cp VWF_LINE_TILES * 2
  jr nz, .dmgTile
  ret

VWFDmgBox:
  ; Returns z when drawing the mode 0 box on the original Game Boy. Clobbers a
  ld a, [W_HardwareType]
  cp $11
  jr z, .no
  ld a, [W_TextMode]
  or a
  ret
.no
  or 1
  ret

VWFTileAddrByIndex:
  ; a = tile of the box (0-35). Returns hl = its address. Preserves bc, de
  push de
  push bc
  ld c, a
  call VWFDmgBox
  jr nz, .contiguous
  ld hl, W_VWFBoxTiles
  ld b, 0
  add hl, bc
  ld c, [hl]
  ld de, $9000
  jr .add
.contiguous
  call VWFGetTileBase
  ld d, h
  ld e, l
.add
  ld l, c
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, de
  pop bc
  pop de
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
  push hl
  ld a, VWF_LINE_TILES * 2 - 1
  call VWFTileAddrByIndex
  pop de
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
  ; Maps the cells of the two text lines of the mode 0 box to its private tiles
  ld a, [W_HardwareType]
  cp $11
  jr nz, .dmg
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

.dmg
  ; Cells that already show a string pool tile keep it, the others get a free one
  ld hl, $9C41
  ld de, W_VWFBoxTiles
  call .dmgLine
  ld hl, $9C81
  call .dmgLine
  jp VWFClearTilesInternal
.dmgLine
  ld b, VWF_LINE_TILES
.dmgCell
  di
.dmgWait
  ldh a, [rSTAT]
  and 2
  jr nz, .dmgWait
  ld a, [hl]
  ei
  or a
  jr z, .dmgAlloc
  cp DMG_STR_LAST + 1
  jr c, .dmgKeep
.dmgAlloc
  push bc
  push de
  push hl
  call StrAllocTile
  pop hl
  pop de
  pop bc
  ld c, a
  di
.dmgWaitMap
  ldh a, [rSTAT]
  and 2
  jr nz, .dmgWaitMap
  ld [hl], c
  ei
  ld a, c
.dmgKeep
  ld [de], a
  inc de
  inc hl
  dec b
  jr nz, .dmgCell
  ret

VWFGetTileBase:
  ; hl = address of the first tile of the drawing area (contiguous tiles)
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
  call VWFTileAddrByIndex
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
