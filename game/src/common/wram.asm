; Original game variables used by the text engine
DEF W_CurrentBank            EQU $C425
DEF W_TextOffsetOrig         EQU $C426 ; (unused by the patched engine)
DEF W_TextDelay              EQU $C427
DEF W_TextCursorHi           EQU $C428 ; Mode 0: tilemap address hi, Mode 1: 0
DEF W_TextCursorLo           EQU $C429 ; Mode 0: tilemap address lo, Mode 1: tile index
DEF W_TextSpeed              EQU $C42A
DEF W_TextSubIndex           EQU $C42B ; A-hold counter / RAM string index
DEF W_TextMode               EQU $C42C ; 0 = direct tilemap, 1 = rendered tiles
DEF W_TextPortrait           EQU $C42D
DEF W_TextBank               EQU $C42E
DEF W_TextFinished           EQU $C42F
DEF W_TextC430               EQU $C430
DEF W_TextEndState           EQU $C435
DEF W_TextStartState         EQU $C436
DEF W_TextChar               EQU $C44E
DEF W_TextDakuten            EQU $C44F
DEF W_TextWindowAlt          EQU $C4FB

; Patch variables (verified unused by the original game)
DEF W_TextPtr                EQU $DD71 ; 2 bytes, little endian, start of the current text
DEF W_TextOffset             EQU $DD73 ; 2 bytes, little endian
DEF W_VWFX                   EQU $DD75 ; pixel x on the current line
DEF W_VWFLine                EQU $DD76 ; current line (0 or 1)
DEF W_VWFTileBuffer          EQU $DD77 ; 8 bytes, 1bpp, current tile
DEF W_VWFTileBuffer2         EQU $DD7F ; 8 bytes, 1bpp, overflow tile
DEF W_VWFChar                EQU $DD87
DEF W_VWFSavedBank           EQU $DD88
DEF W_VWFScratch             EQU $DD89 ; 2 bytes

; VWF strings (menus)
DEF W_StrDest                EQU $DD8B ; 2 bytes, little endian, tilemap address
DEF W_StrX                   EQU $DD8D
DEF W_StrTile                EQU $DD8E
DEF W_StrBuf1                EQU $DD8F ; 8 bytes
DEF W_StrBuf2                EQU $DD97 ; 8 bytes
DEF W_StrNextTile            EQU $DD9F ; next VRAM bank 1 tile to allocate
DEF W_StrSavedBank           EQU $DDA0
DEF W_StrTemp                EQU $DDA1 ; 2 bytes
DEF W_StrChar                EQU $DDA3
DEF W_StrCenterWidth         EQU $DDA4
DEF W_StrNarrow              EQU $DDA5
DEF W_StrBuffer              EQU $DDAC ; 24 bytes, string with name tokens expanded
DEF W_StrBufferEnd           EQU $DDC4
DEF W_TextRAMBuffer          EQU $DDC4 ; 24 bytes, RAM string being drawn by the main script
DEF W_TextRAMBufferEnd       EQU $DDDC

DEF W_HardwareType           EQU $C3E6 ; $11 on CGB
DEF W_LCDCShadow             EQU $C3C9

; VWF strings drawn into a dedicated run of tiles
DEF W_StrMode                EQU $CBD0 ; 0 = bank 1 tiles per cell, 1 = dedicated tile run
DEF W_TileDest               EQU $CBD1 ; 2 bytes, VRAM address of the first tile
DEF W_TileMapDest            EQU $CBD3 ; 2 bytes, tilemap address of the first cell
DEF W_TileIndex              EQU $CBD5 ; index of the first tile
DEF W_TileCount              EQU $CBD6
DEF W_TileAlign              EQU $CBD7 ; 0 = left, 1 = right
