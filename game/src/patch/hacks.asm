INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Small patches to code outside the text engine that touched its variables directly.

; The shop restarts its message by clearing the old 8-bit text offset ($C426).
SECTION "Shop Text Restart", ROMX[$7B5B], BANK[$04]
  call ClearTextOffset

SECTION "Hack Helpers", ROM0[$2220]
ClearTextOffset::
  ; a = 0
  ld [W_TextOffset], a
  ld [W_TextOffset + 1], a
  ret

NameTilesFromB335::
  ; a = first tile index, bc = VRAM address of the first tile, hl = tilemap address
  ; Draws the 8 byte name at $B335 into 8 tiles, left aligned.
  push de
  ld [W_TileIndex], a
  ld a, c
  ld [W_TileDest], a
  ld a, b
  ld [W_TileDest + 1], a
  ld a, l
  ld [W_TileMapDest], a
  ld a, h
  ld [W_TileMapDest + 1], a
  ld hl, $B335
  ld de, W_StrBuffer
  ld b, 8
  call StrCopyResolveN
  xor a
  ld [W_TileAlign], a
  ld a, 8
  ld [W_TileCount], a
  ld a, BANK(VWFRenderTileRun)
  ld hl, VWFRenderTileRun
  call StrFarCall
  pop de
  ret

ClearBank1Attr::
  ; Called by the tilemap loaders for every tile written (replacing ld a, [$DD26]).
  ; Screens with separate attribute maps ($DD26 != 0) don't rewrite attributes, so clear the
  ; VRAM bank 1 bit a variable width string may have left on the cell.
  ld a, [$DD26]
  or a
  ret z
  ld a, h
  cp $98
  jr c, .done
  di
  ld a, 1
  ldh [rVBK], a
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, [hl]
  and $F7
  ld b, a
.wait2
  ldh a, [rSTAT]
  and 2
  jr nz, .wait2
  ld [hl], b
  xor a
  ldh [rVBK], a
  ei
.done
  ld a, [$DD26]
  ret

ShopRestartClear::
  ; The shop clears its box itself; the text cells then need mapping to the VWF tiles again
  call $0267
  jp VWFMapMode0Box

AttrWriteKeepBank1::
  ; Replaces the attribute write of the box palette fill at $31D4: keeps the VRAM bank 1 bit
  ; of cells that show variable width text. a = attribute, hl = cell (VRAM bank 1 selected).
  push bc
  ld b, a
  di
.wait
  ldh a, [rSTAT]
  and 2
  jr nz, .wait
  ld a, [hl]
  and $08
  or b
  ld c, a
.wait2
  ldh a, [rSTAT]
  and 2
  jr nz, .wait2
  ld [hl], c
  ei
  inc hl
  ld a, b
  pop bc
  ret

HackHelpersEnd::
  ASSERT HackHelpersEnd <= $22E4, "Hack helpers overflow into $22E4"

; Battle: Medarot names, drawn per character into 8 tiles each
SECTION "Battle Names 0D Right", ROMX[$5505], BANK[$0D]
  ld hl, 2
  add hl, de
  ld a, 1
  call BattleNameTiles
  jp $5594

SECTION "Battle Names 0D Left", ROMX[$5605], BANK[$0D]
  ld hl, 2
  add hl, de
  xor a
  call BattleNameTiles
  jp $5694

SECTION "Battle Names 12 Right", ROMX[$5937], BANK[$12]
  ld hl, 2
  add hl, de
  ld a, 1
  call BattleNameTiles
  jp $59C6

SECTION "Battle Names 12 Left", ROMX[$5A37], BANK[$12]
  ld hl, 2
  add hl, de
  xor a
  call BattleNameTiles
  jp $5AC6

SECTION "Battle B335 Name 0D", ROMX[$639C], BANK[$0D]
  jp NameTilesFromB335

SECTION "Battle B335 Name 12", ROMX[$6803], BANK[$12]
  jp NameTilesFromB335

; Shop parts list: names were printed per character in 8 tiles, padded with spaces
SECTION "Shop List Names", ROMX[$7853], BANK[$04]
  ld e, 8
  jp PutStringPadded

; Debug menu entries (11 tiles)
SECTION "Debug Menu Names", ROMX[$510C], BANK[$1A]
  ld e, 11
  jp PutStringPadded

SECTION "Tilemap Tile Attribute Hook", ROM0[$13AE]
  call ClearBank1Attr

SECTION "Shop Text Restart Clear", ROMX[$7B7D], BANK[$04]
  call ShopRestartClear

; Default player name: "Ikki" (same size as the original イッキ code)
SECTION "Default Player Name", ROMX[$4E40], BANK[$04]
  ld a, $09 ; I
  ld [hli], a
  ld a, $25 ; k
  ld [hli], a
  ld [hli], a
  ld a, $23 ; i
  ld [hli], a
  xor a
  ld [hli], a
  ld [hli], a
  ld [hli], a
  ld [hli], a
  ld [hli], a
DefaultPlayerNameEnd:
  ASSERT DefaultPlayerNameEnd == $4E50, "Default player name code changed size"

SECTION "Box Palette Fill Attribute Write", ROM0[$31ED]
  call AttrWriteKeepBank1

; The dakuten splitter is not needed in English (codes $80-$B1 are never used), which frees its
; table for more code. Callers only need [$C44F] (the dakuten tile) to be 0.
SECTION "Dakuten Split Stub", ROM0[$22E4]
  xor a
  ld [$C44F], a
  ret

SECTION "Hack Helpers 2", ROM0[$22E9]
BattleNameTiles::
  ; hl = name (RAM), a = alignment (0 left, 1 right)
  ; Draws the name into the 8 tiles at [$C440] (VRAM), mapped at [$C442] with indices from
  ; [$C448], then advances those like the original per-character loop did.
  ld [W_TileAlign], a
  ld de, W_StrBuffer
  call StrCopyResolveTo
  ld a, [$C441]
  ld [W_TileDest], a
  ld a, [$C440]
  ld [W_TileDest + 1], a
  ld a, [$C443]
  ld [W_TileMapDest], a
  ld a, [$C442]
  ld [W_TileMapDest + 1], a
  ld a, [$C448]
  ld [W_TileIndex], a
  ld a, 8
  ld [W_TileCount], a
  ld a, BANK(VWFRenderTileRun)
  ld hl, VWFRenderTileRun
  call StrFarCall
  ld a, [$C441]
  add $80
  ld [$C441], a
  jr nc, .noCarry
  ld hl, $C440
  inc [hl]
.noCarry
  ld a, [$C443]
  add 8
  ld [$C443], a
  jr nc, .noCarry2
  ld hl, $C442
  inc [hl]
.noCarry2
  ld hl, $C448
  ld a, [hl]
  add 8
  ld [hl], a
  ret

HackHelpers2End::
  ASSERT HackHelpers2End <= $2371, "Hack helpers 2 overflow into $2371"

; Default name "イマジニア" written to $C462: "Imagineer", copied from a string
SECTION "Default Imagineer Name", ROMX[$4A66], BANK[$04]
DefaultImagineerName:
  push de
  ld de, ImagineerName
  ld b, ImagineerNameEnd - ImagineerName
.loop
  ld a, [de]
  inc de
  ld [hli], a
  dec b
  jr nz, .loop
  pop de
  REPT 7
    nop
  ENDR
DefaultImagineerNameEnd:
  ASSERT DefaultImagineerNameEnd == $4A7A, "Default Imagineer name code changed size"

SECTION "Imagineer Name", ROMX[$7E00], BANK[$04]
ImagineerName:
  db $09, $27, $1B, $21, $23, $28, $1F, $1F, $2C ; Imagineer
ImagineerNameEnd:

; Staff roll: the lines were placed for the Japanese text, center them on the row instead
SECTION "Staff Roll Print", ROMX[$52C0], BANK[$04]
  call CreditsPutCentered

SECTION "Staff Roll Centering", ROMX[$7E10], BANK[$04]
CreditsPutCentered:
  ; hl = string, bc = tilemap address
  ; On the original Game Boy the roll uses the fixed width font: the scrolling tilemap holds
  ; more lines than the variable width font has tiles for.
  ld a, 1
  ld [W_StrForceFixed], a
  ld a, c
  and $E0
  ld c, a
  ld a, 20
  call GetCenteringOffset
  add c
  ld c, a
  call PutString
  xor a
  ld [W_StrForceFixed], a
  ret

; Staff roll: clear whole rows (20 tiles from column 0) for the wider English lines
SECTION "Staff Roll Clear Start", ROMX[$527D], BANK[$04]
  db $00 ; ld hl, $9800
SECTION "Staff Roll Clear Width 1", ROMX[$5282], BANK[$04]
  db 20
SECTION "Staff Roll Clear Width 2", ROMX[$5296], BANK[$04]
  db 20
