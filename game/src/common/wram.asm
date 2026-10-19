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
