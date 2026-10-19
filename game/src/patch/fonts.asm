; Fixed width font used by menus and tilemap-mode text (one tile per character code)

; Glyphs drawn one at a time by the game (e.g. the 'next' arrow in text boxes)
SECTION "Fixed Font Glyphs", ROMX[$5CFB], BANK[$3B]
  INCBIN "build/gfx/FixedFont.2bpp"

; Tileset 0 is the font loaded to $9000 by menus. It is replaced with an uncompressed copy.
SECTION "Fixed Font Tileset", ROMX[$7000], BANK[$80]
FixedFontTileset::
  db 0 ; Uncompressed
  dw 128 * 16
  INCBIN "build/gfx/FixedFont.2bpp"

SECTION "Tileset 0 Source", ROM0[$3A20]
  dw FixedFontTileset

SECTION "Tileset 0 Bank", ROMX[$682B], BANK[$3B]
  db BANK(FixedFontTileset)
