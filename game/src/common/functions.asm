; Shared constants for the patch

; VWF drawing areas
DEF VWF_LINE_TILES          EQU 18
DEF VWF_MODE1_TILE_ADDRESS  EQU $8C30
DEF VWF_MODE1_FIRST_TILE     EQU $C3
DEF STR_RING_LAST           EQU $BF ; tiles $C0-$FF of VRAM bank 1 are reserved for mode 0 text

; Name tokens: names that don't fit the game's fixed-size buffers are stored as
; NAME_TOKEN, list id, index (then the usual $C0 terminator) and expanded when drawn.
DEF NAME_TOKEN              EQU $C8
DEF STR_TERMINATOR          EQU $C0
DEF STR_MAX_TILES           EQU 18
DEF STR_NARROW              EQU $C9 ; Switches the rest of a string to the narrow font

DEF DMG_STR_LAST EQU $6C ; original Game Boy: string tiles are font tiles $01-$6C (all but the symbols)
DEF DMG_FONT_GLYPHS EQU $48 ; last font tile with a glyph the fixed width text needs
