INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Variable width strings for menus.
;
; The original game draws strings one character per tile, using the font tiles. Here strings
; are rendered with the variable width font into private tiles in VRAM bank 1 (which the game
; never uses for tiles), and the tilemap attributes of the cells are switched to bank 1.
;
; A cell that already shows a bank 1 tile keeps its tile, so redrawing a string at the same
; place (e.g. scrolling lists) reuses tiles. New cells take the next tile from a ring.
;
; Long names are stored in the name lists as tokens (see build_ptrlists.py) and expanded here.
; On a DMG there is no VRAM bank 1, so strings are drawn with the fixed width font instead.

DEF rVBK_ EQU $FF4F

SECTION "PutString", ROM0[$30A3]
PutString::
  ; hl = string, bc = tilemap address
  push de
  ld a, c
  ld [W_StrDest], a
  ld a, b
  ld [W_StrDest + 1], a
  call StrCopyResolve
  ld a, BANK(VWFRenderStringRemember)
  ld hl, VWFRenderStringRemember
  call StrFarCall
  pop de
  ret

PutStringPadded::
  ; hl = string, bc = tilemap address, e = field width in tiles
  ; Like PutString, then blanks the rest of the field.
  push de
  ld a, c
  ld [W_StrDest], a
  ld a, b
  ld [W_StrDest + 1], a
  ld a, e
  ld [W_StrCenterWidth], a
  call StrCopyResolve
  ld a, BANK(VWFRenderStringPadded)
  ld hl, VWFRenderStringPadded
  call StrFarCall
  pop de
  ret

GetCenteringOffset::
  ; hl = string, a = width of the field in tiles
  ; Returns a = tiles to skip to center the string
  push hl
  push bc
  push de
  ld [W_StrCenterWidth], a
  call StrCopyResolve
  ld a, BANK(VWFMeasureStringTiles)
  ld hl, VWFMeasureStringTiles
  call StrFarCall
  ld a, [W_StrTemp]
  ld b, a
  ld a, [W_StrCenterWidth]
  sub b
  jr nc, .fits
  xor a
.fits
  srl a
  pop de
  pop bc
  pop hl
  ret

PutStringEnd::
  ASSERT PutStringEnd <= $3123, "PutString overflows into $3123"

SECTION "Centering Vector", ROM0[$065E]
  jp GetCenteringOffset

SECTION "String Helpers", ROM0[$2180]
StrFarCall::
  ; Calls a:hl preserving the current bank. Clobbers everything.
  push af
  ld a, [W_CurrentBank]
  ld [W_StrSavedBank], a
  pop af
  rst $10
  call .jumpHL
  ld a, [W_StrSavedBank]
  rst $10
  ret

.jumpHL
  jp hl

StrCopyResolve::
  ; Copies the $C0 terminated string at hl (current bank or RAM) to W_StrBuffer,
  ; expanding name tokens.
  ld de, W_StrBuffer
  ; Fall through

StrCopyResolveTo::
  ; Same, to de (buffers are 24 bytes)
  ld b, 23
  ; Fall through

StrCopyResolveN::
  ; Same, reading at most b bytes
  ld a, [W_CurrentBank]
  ld [W_StrSavedBank], a

.loop
  ld a, [hli]
  cp NAME_TOKEN
  jr z, .token
  ld [de], a
  inc de
  cp STR_TERMINATOR
  ret z
  dec b
  jr nz, .loop

.truncate
  ld a, STR_TERMINATOR
  ld [de], a
  ret

.token
  ; Look up the full name: NameTokenLists[list] = (bank, table), table[index] = string
  push hl
  ld a, [hli] ; list
  ld c, a
  ld a, [hl] ; index
  push af
  ld a, BANK(NameTokenLists)
  rst $10
  ld hl, NameTokenLists
  ld a, c
  add a
  add c
  add l
  ld l, a
  jr nc, .noCarry
  inc h
.noCarry
  ld a, [hli]
  ld c, a ; bank of the list's table
  ld a, [hli]
  ld h, [hl]
  ld l, a
  ld a, c
  rst $10
  pop af
  add a
  add l
  ld l, a
  jr nc, .noCarry2
  inc h
.noCarry2
  ld a, [hli]
  ld h, [hl]
  ld l, a

.copyName
  ld a, [hli]
  cp STR_TERMINATOR
  jr z, .nameDone
  ld [de], a
  inc de
  dec b
  jr nz, .copyName
  pop hl
  ld a, [W_StrSavedBank]
  rst $10
  jr .truncate

.nameDone
  pop hl
  inc hl
  inc hl
  ld a, [W_StrSavedBank]
  rst $10
  jr .loop

StringHelpersEnd::
  ASSERT StringHelpersEnd <= $22E4, "String helpers overflow into $22E4"

SECTION "VWF String Renderer", ROMX[$6000], BANK[$80]
VWFMeasureStringTiles::
  ; W_StrTemp = number of tiles W_StrBuffer takes
  ld hl, W_StrBuffer
  ld b, 0
  ld de, VWFWidths
.loop
  ld a, [hli]
  cp STR_TERMINATOR
  jr z, .done
  cp STR_NARROW
  jr nz, .notNarrow
  ld de, VWFNarrowWidths
  jr .loop
.notNarrow
  push hl
  push de
  ld l, a
  ld h, 0
  add hl, de
  pop de
  ld a, [hl]
  inc a
  add b
  ld b, a
  pop hl
  jr .loop
.done
  ; Remove the spacing after the last character, round up to tiles
  ld a, b
  or a
  jr z, .store
  dec a
  ld [W_StrTemp + 1], a
  add 7
  srl a
  srl a
  srl a
.store
  ld [W_StrTemp], a
  ret

; W_StrTemp + 1 = width in pixels (only valid when the string isn't empty)

VWFRenderString::
  xor a
  ld [W_StrMode], a
  ld a, [W_HardwareType]
  cp $11
  jp nz, .fixedWidth

  xor a
  ld [W_StrX], a
  ld [W_StrTile], a
  ld [W_StrNarrow], a
  call StrClearBuffers
  ld hl, W_StrBuffer
.loop
  ld a, [hli]
  cp STR_TERMINATOR
  jr z, .done
  cp STR_NARROW
  jr nz, .draw
  ld [W_StrNarrow], a
  jr .loop
.draw
  push hl
  call StrDrawChar
  pop hl
  ld a, [W_StrTile]
  cp STR_MAX_TILES
  ret nc
  jr .loop

.done
  ; Record the number of tiles used, draw the last partial tile
  ld a, [W_StrTile]
  ld [W_StrTemp], a
  ld a, [W_StrX]
  and 7
  ret z
  ld hl, W_StrTemp
  inc [hl]
  jp StrFlushTile

.fixedWidth
  ld a, [W_StrDest]
  ld e, a
  ld a, [W_StrDest + 1]
  ld d, a
  ld hl, W_StrBuffer
.fixedLoop
  ld a, [hli]
  cp STR_TERMINATOR
  ret z
  cp STR_NARROW
  jr z, .fixedLoop
  ld b, a
  di
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, b
  ld [de], a
  ei
  inc de
  jr .fixedLoop

VWFRenderStringRemember::
  ; Draws the string and remembers it, so attribute map loads don't hide it
  call VWFRenderString
  jr StrRemember

StrRemember:
  ld a, [W_StrDest]
  ld [W_TmPtr], a
  ld a, [W_StrDest + 1]
  ld [W_TmPtr + 1], a
  jp LabelRingAdd

VWFRenderStringPadded::
  ; The original printers also cleared the row above (where dakuten went)
  ld a, [W_StrDest]
  sub $20
  ld l, a
  ld a, [W_StrDest + 1]
  sbc 0
  ld h, a
  ld a, [W_StrCenterWidth]
  ld b, a
.clearAbove
  di
.waitAbove
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAbove
  xor a
  ld [hli], a
  ei
  dec b
  jr nz, .clearAbove
  call VWFRenderString
  ld a, [W_HardwareType]
  cp $11
  ret nz
  call StrRemember
  ; Blank the cells after the string (W_StrTemp = tiles used)
  ld a, [W_StrDest]
  ld l, a
  ld a, [W_StrDest + 1]
  ld h, a
  ld a, [W_StrTemp]
  ld b, a
  add l
  ld l, a
  jr nc, .noCarry
  inc h
.noCarry
  ld a, [W_StrCenterWidth]
  sub b
  ret z
  ret c
  ld b, a
.loop
  di
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  xor a
  ld [hli], a
  ei
  dec b
  jr nz, .loop
  ret

StrClearTileZero:
  ; Blanks tile 0 of VRAM bank 1 (in both addressing modes): cells left in bank 1 that the
  ; game later clears with tile 0 show it.
  push hl
  push bc
  ld hl, $8000
  call .clear
  ld hl, $9000
  call .clear
  pop bc
  pop hl
  ret
.clear
  ld b, 16
.loop
  di
  ld a, 1
  ldh [rVBK_], a
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  xor a
  ld [hli], a
  ldh [rVBK_], a
  ei
  dec b
  jr nz, .loop
  ret

StrClearBuffers:
  ld hl, W_StrBuf1
  ld b, 16
  xor a
.loop
  ld [hli], a
  dec b
  jr nz, .loop
  ret

StrDrawChar:
  ; a = character
  ld [W_StrChar], a
  ld l, a
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  ld de, VWFFont
  ld a, [W_StrNarrow]
  or a
  jr z, .gotFont
  ld de, VWFNarrowFont
.gotFont
  add hl, de
  ld d, h
  ld e, l
  ld a, [W_StrX]
  and 7
  ld c, a
  ld hl, W_StrBuf1
  ld b, 8
.rowLoop
  push bc
  ld a, [de]
  inc de
  ld b, a
  ld a, c
  or a
  ld c, 0
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
  ld a, [hl]
  or c
  ld [hl], a
  pop hl
  inc hl
  pop bc
  dec b
  jr nz, .rowLoop

  ld a, [W_StrChar]
  ld l, a
  ld h, 0
  ld de, VWFWidths
  ld a, [W_StrNarrow]
  or a
  jr z, .gotWidths
  ld de, VWFNarrowWidths
.gotWidths
  add hl, de
  ld a, [W_StrX]
  ld b, a
  add [hl]
  inc a
  ld [W_StrX], a
  xor b
  and $F8
  ret z
  ; Crossed into the next tile
  call StrFlushTile
  ld hl, W_StrTile
  inc [hl]
  ld hl, W_StrBuf2
  ld de, W_StrBuf1
  ld b, 8
.copyLoop
  ld a, [hl]
  ld [de], a
  xor a
  ld [hli], a
  inc de
  dec b
  jr nz, .copyLoop
  ret

StrFlushTile:
  ld a, [W_StrMode]
  or a
  jp nz, StrFlushTileRun
  ; Writes W_StrBuf1 to the tile of cell W_StrDest + W_StrTile
  ld a, [W_StrDest]
  ld l, a
  ld a, [W_StrDest + 1]
  ld h, a
  ld a, [W_StrTile]
  add l
  ld l, a
  jr nc, .noCarry
  inc h
.noCarry
  ; Does the cell already use a bank 1 tile?
  di
  ld a, 1
  ldh [rVBK_], a
.waitAttr
  ldh a, [rSTAT]
  and 2
  jr nz, .waitAttr
  ld a, [hl]
  ld b, a
  xor a
  ldh [rVBK_], a
  ei
  bit 3, b
  jr z, .allocate
  di
.waitTile
  ldh a, [rSTAT]
  and 2
  jr nz, .waitTile
  ld c, [hl]
  ei
  ld a, c
  or a
  jr nz, .gotTile ; tile 0 is never used, it stays blank

.allocate
  ld a, [W_StrNextTile]
  or a
  jr nz, .allocated
  call StrClearTileZero
  ld a, 1
.allocated
  ld c, a
  inc a
  cp STR_RING_LAST + 1
  jr c, .storeNext
  ld a, 1
.storeNext
  ld [W_StrNextTile], a
  ; Map the tile and switch the cell to bank 1
  di
.waitMap
  ldh a, [rSTAT]
  and 2
  jr nz, .waitMap
  ld [hl], c
  ld a, 1
  ldh [rVBK_], a
  ld a, b
  or $08
  ld b, a
.waitMapAttr
  ldh a, [rSTAT]
  and 2
  jr nz, .waitMapAttr
  ld [hl], b
  xor a
  ldh [rVBK_], a
  ei

.gotTile
  ; hl = tile address in bank 1
  ld l, c
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  ld a, [W_LCDCShadow]
  bit 4, a
  ld de, $8000
  jr nz, .addBase
  bit 7, c
  jr nz, .addBase
  ld de, $9000
.addBase
  add hl, de
  ld de, W_StrBuf1
  ld b, 8
.writeLoop
  ld a, [de]
  inc de
  ld c, a
  di
  ld a, 1
  ldh [rVBK_], a
.waitWrite
  ldh a, [rSTAT]
  and 2
  jr nz, .waitWrite
  ld a, c
  ld [hli], a
  ld [hli], a
  xor a
  ldh [rVBK_], a
  ei
  dec b
  jr nz, .writeLoop
  ret

SECTION "VWF Narrow Font", ROMX[$6400], BANK[$80]
VWFNarrowFont::
  INCBIN "build/gfx/VWFNarrowFont.1bpp"
VWFNarrowWidths::
  INCBIN "build/gfx/VWFNarrowFont.widths"

SECTION "VWF Tile Run Renderer", ROMX[$6D00], BANK[$80]
VWFRenderTileRun::
  ; Renders W_StrBuffer into W_TileCount tiles at W_TileDest (VRAM bank 0),
  ; aligned per W_TileAlign, and maps them at W_TileMapDest with indices from W_TileIndex.
  ld a, 1
  ld [W_StrMode], a
  ; Clear the tiles
  ld a, [W_TileDest]
  ld l, a
  ld a, [W_TileDest + 1]
  ld h, a
  ld a, [W_TileCount]
  swap a
  ld c, a
.clear
  di
.waitClear
  ldh a, [rSTAT]
  and 2
  jr nz, .waitClear
  xor a
  ld [hli], a
  ei
  dec c
  jr nz, .clear
  ; Map the tiles
  ld a, [W_TileMapDest]
  ld l, a
  ld a, [W_TileMapDest + 1]
  ld h, a
  ld a, [W_TileIndex]
  ld b, a
  ld a, [W_TileCount]
  ld c, a
.map
  di
.waitMap
  ldh a, [rSTAT]
  and 2
  jr nz, .waitMap
  ld [hl], b
  ei
  inc hl
  inc b
  dec c
  jr nz, .map
  ; Starting position
  xor a
  ld [W_StrTemp + 1], a
  call VWFMeasureStringTiles
  xor a
  ld [W_StrX], a
  ld a, [W_TileAlign]
  or a
  jr z, .start
  ld a, [W_StrTemp + 1]
  ld b, a
  ld a, [W_TileCount]
  add a
  add a
  add a
  sub b
  jr nc, .gotX
  xor a
.gotX
  ld [W_StrX], a
.start
  ld a, [W_StrX]
  srl a
  srl a
  srl a
  ld [W_StrTile], a
  xor a
  ld [W_StrNarrow], a
  call StrClearBuffers
  ld hl, W_StrBuffer
.loop
  ld a, [hli]
  cp STR_TERMINATOR
  jr z, .done
  cp STR_NARROW
  jr nz, .draw
  ld [W_StrNarrow], a
  jr .loop
.draw
  push hl
  call StrDrawChar
  pop hl
  ld a, [W_StrTile]
  ld b, a
  ld a, [W_TileCount]
  cp b
  jr z, .ended
  jr c, .ended
  jr .loop
.ended
  ret

.done
  ld a, [W_StrX]
  and 7
  ret z
  ; fall through to flush the last partial tile

StrFlushTileRun::
  ; Writes W_StrBuf1 to tile W_StrTile of the run
  ld a, [W_StrTile]
  ld b, a
  ld a, [W_TileCount]
  dec a
  cp b
  ret c
  ld l, b
  ld h, 0
  add hl, hl
  add hl, hl
  add hl, hl
  add hl, hl
  ld a, [W_TileDest]
  add l
  ld l, a
  ld a, [W_TileDest + 1]
  adc h
  ld h, a
  ld de, W_StrBuf1
  ld b, 8
.write
  ld a, [de]
  inc de
  ld c, a
  di
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, c
  ld [hli], a
  ld [hli], a
  ei
  dec b
  jr nz, .write
  ret
