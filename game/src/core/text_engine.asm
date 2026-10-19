INCLUDE "game/src/common/hardware.asm"
INCLUDE "game/src/common/wram.asm"
INCLUDE "game/src/common/functions.asm"

; Main script engine.
;
; This is a reimplementation of the original engine at $1C69-$22E3, following the original
; logic for every control code, with the following changes:
;  * Text offsets are 16-bit (the original only allowed 256 bytes per text).
;  * Text tables hold (bank, address) entries, so text can be stored in any bank.
;  * Characters are drawn with a variable width font (see patch/vwf.asm) in both modes.
;
; Control codes:
;  C1 XX   - End of text, XX is the exit mode
;  C2      - Move to the second line
;  C3 XX   - Set text speed (FF draws instantly)
;  C4      - Wait for input, then clear the box
;  C5 XXXX - Draw a C0-terminated string from RAM
;  C6      - Clear the box without waiting
;  C7 XX   - Show portrait XX (FF hides it)

SECTION "Main Script Trampoline", ROM0[$060A]
  call MainScriptProcess

SECTION "Main Script Engine", ROM0[$1C69]
MainScriptInit::
  ; a = mode (0 = draw directly to the tilemap, 1 = draw to the tiles mapped in the window)
  ld [W_TextMode], a
  xor a
  ld [W_TextOffset], a
  ld [W_TextOffset + 1], a
  ld [W_TextSubIndex], a
  ld [W_TextFinished], a
  ld [W_TextDelay], a
  ld [W_TextEndState], a
  ld [W_TextStartState], a
  ld [W_TextSpeed], a
  call VWFReset
  ld a, $FF
  ld [W_TextPortrait], a
  ld a, $00
  ld [$C44E], a
  ld a, $04
  ld [$C44F], a
  ld a, $08
  ld [$C450], a
  ld a, $04
  ld [$C451], a
  ld a, $00
  call $1639
  ld a, [W_TextMode]
  or a
  jr nz, .renderedTiles
  ld hl, $9C41
  call MainScriptSetCursor
  ld a, $01
  call $1C2C
  jp MainScriptMapMode0Tiles

.renderedTiles
  ld a, [W_TextWindowAlt]
  or a
  jr nz, .altWindow
  ld a, $01
  call $1C2C
  ld hl, 0
  jp MainScriptSetCursor

.altWindow
  ld bc, $0006
  ld e, $01
  ld a, $00
  call $0B2A
  ld bc, $0006
  ld e, $41
  ld a, $00
  call $0C6E
  ld hl, 0
  jp MainScriptSetCursor

MainScriptProcess::
  ; a = text section, bc = text index
  call MainScriptLoadText
  ld a, [W_TextMode]
  or a
  jr z, .main
  ld a, [W_TextStartState]
  cp $02
  jr z, .main
  call MainScriptGetCurrent
  ld a, [hli]
  cp $C3
  jr nz, .notInstant
  ld a, [hl]
  cp $FF
  jr nz, .notInstant
  call MainScriptClearBox
  ld a, $02
  ld [W_TextStartState], a
  ld a, [W_TextBank]
  rst $10
  jr .main

.notInstant
  ld a, [W_TextStartState]
  or a
  jr nz, .startState1
  call MainScriptClearBox
  ld a, $01
  ld [W_TextStartState], a
  ret

.startState1
  ld a, $01
  ld [W_TextC430], a
  ld a, $02
  ld [W_TextStartState], a
  ret

.main
  ld a, [W_TextFinished]
  or a
  ret nz
  ld a, [W_TextDelay]
  or a
  jr z, MainScriptLoop
  dec a
  ld [W_TextDelay], a
  ret

MainScriptLoop::
  call MainScriptGetCurrent
  ld a, [hl]
  cp $C1
  jp z, MainScriptCCEnd
  cp $C2
  jp z, MainScriptCCNewLine
  cp $C3
  jp z, MainScriptCCSpeed
  cp $C4
  jp z, MainScriptCCWaitAndClear
  cp $C5
  jp z, MainScriptCCRAMString
  cp $C6
  jp z, MainScriptCCClear
  cp $C7
  jp z, MainScriptCCPortrait
  jp MainScriptCharacter

MainScriptLoadText:
  ; a = text section, bc = text index
  ; Switches to the bank of the text and stores its address
  push bc
  ld hl, MainScriptSectionTable
  ld c, a
  ld b, 0
  add hl, bc
  add hl, bc
  add hl, bc
  ld a, [hli]
  ld e, [hl]
  inc hl
  ld d, [hl]
  rst $10
  pop bc
  ld h, d
  ld l, e
  add hl, bc
  add hl, bc
  add hl, bc
  ld a, [hli]
  ld e, [hl]
  inc hl
  ld d, [hl]
  ld [W_TextBank], a
  rst $10
  ld a, e
  ld [W_TextPtr], a
  ld a, d
  ld [W_TextPtr + 1], a
  ret

MainScriptGetCurrent::
  ; hl = address of the current character
  push de
  ld a, [W_TextPtr]
  ld l, a
  ld a, [W_TextPtr + 1]
  ld h, a
  ld a, [W_TextOffset]
  ld e, a
  ld a, [W_TextOffset + 1]
  ld d, a
  add hl, de
  pop de
  ret

MainScriptAdvance1::
  ld b, 1
MainScriptAdvance::
  ; Advances the text offset by b
  ld a, [W_TextOffset]
  add b
  ld [W_TextOffset], a
  ret nc
  ld a, [W_TextOffset + 1]
  inc a
  ld [W_TextOffset + 1], a
  ret

MainScriptSetCursor:
  ld a, h
  ld [W_TextCursorHi], a
  ld a, l
  ld [W_TextCursorLo], a
  ret

MainScriptApplySpeed:
  ; Sets the delay to the text speed, if the speed is instant then continue drawing
  ld a, [W_TextSpeed]
  ld [W_TextDelay], a
  cp $FF
  ret nz
  xor a
  ld [W_TextDelay], a
  jp MainScriptLoop

; C1 - End of text
MainScriptCCEnd:
  ld a, [W_TextEndState]
  or a
  jr nz, .laterState
  call MainScriptGetCurrent
  inc hl
  ld a, [hl]
  jr .dispatch

.laterState
  add $04

.dispatch
  ld hl, .table
  call $10B6
  jp hl

.table
  dw .mode0
  dw .mode1
  dw .mode2
  dw .mode3
  dw MainScriptEndFinish
  dw MainScriptEndState1
  dw MainScriptIncrementEndState
  dw MainScriptEndState3

.mode0
  ; Wait for input and close the window
  call MainScriptCheckInput
  or a
  ret z
  ld a, $0E
  ldh [H_SoundEffect], a
  call MainScriptHideWindow
  jp MainScriptEndFinish

.mode1
  ; Close the window without waiting
  call MainScriptHideWindow
  jp MainScriptEndFinish

.mode2
  ; Wait for input and keep the window open
  call MainScriptCheckInput
  or a
  ret z
  ld a, $0E
  ldh [H_SoundEffect], a
  jp MainScriptEndFinish

.mode3
  ; Wait for input and clear the box
  call MainScriptCheckInput
  or a
  ret z
  ld a, $0E
  ldh [H_SoundEffect], a
  call MainScriptClearBox
  jp MainScriptEndFinish

MainScriptEndState1:
  call $1B9B
  ld a, $01
  ld [W_TextC430], a
  ; Fall through
MainScriptIncrementEndState:
  ld a, [W_TextEndState]
  inc a
  ld [W_TextEndState], a
  ret

MainScriptEndState3:
  call MainScriptClearPortrait
  ld a, $01
  ld [W_TextFinished], a
  ret

MainScriptEndFinish:
  ld a, [W_TextPortrait]
  cp $FF
  jr nz, .hasPortrait
  ld a, $01
  ld [W_TextFinished], a
  ret

.hasPortrait
  ld a, $01
  ld [W_TextEndState], a
  ret

MainScriptCheckInput:
  ; Returns a = 1 if A was pressed or held long enough
  ldh a, [H_JPInputChanged]
  and $01
  jr nz, .pressed
  ldh a, [H_JPInputHeldDown]
  and $01
  ret z
  ld a, [W_TextSubIndex]
  cp $10
  jr z, .pressed
  inc a
  ld [W_TextSubIndex], a
  xor a
  ret

.pressed
  ld a, $01
  ret

MainScriptHideWindow:
  ld a, [W_TextWindowAlt]
  or a
  ret nz
  xor a
  jp $1C2C

; C2 - New line
MainScriptCCNewLine:
  ld a, [W_TextMode]
  or a
  jr nz, .renderedTiles
  ld hl, $9C81
  jr .setCursor

.renderedTiles
  ld hl, $0012

.setCursor
  call MainScriptSetCursor
  call VWFNewLine
  call MainScriptAdvance1
  xor a
  ld [W_TextSubIndex], a
  jp MainScriptLoop

; C3 - Text speed
MainScriptCCSpeed:
  call MainScriptGetCurrent
  inc hl
  ld a, [hl]
  ld [W_TextDelay], a
  ld [W_TextSpeed], a
  ld b, 2
  call MainScriptAdvance
  ld a, [W_TextDelay]
  cp $FF
  ret nz
  xor a
  ld [W_TextDelay], a
  jp MainScriptLoop

; C4 - Wait for input and clear the box
MainScriptCCWaitAndClear:
  ld b, $79 ; Down arrow
  ld a, [$C3C0]
  and $04
  jr nz, .drawArrow
  ld b, $00

.drawArrow
  ld a, [W_TextMode]
  or a
  jr nz, .renderedTiles
  ld hl, $9C92
  ld a, b
  di
  call $0A9F
  ld [hl], a
  ei
  jr .checkInput

.renderedTiles
  ld hl, $8E60
  ld a, b
  call $23AE
  ld a, [W_TextBank]
  rst $10

.checkInput
  ldh a, [H_JPInputChanged]
  and $01
  jr nz, .pressed
  ldh a, [H_JPInputHeldDown]
  and $01
  ret z
  ld a, [W_TextSubIndex]
  cp $10
  jr z, .pressed
  inc a
  ld [W_TextSubIndex], a
  ret

.pressed
  ld a, $0E
  ldh [H_SoundEffect], a
  xor a
  ld [W_TextSubIndex], a
  ld a, [W_TextMode]
  or a
  jr nz, .clearRenderedTiles
  ld bc, $0000
  ld e, $00
  ld a, $00
  call $0B2A
  call MainScriptMapMode0Tiles
  ld hl, $9C41
  jr .done

.clearRenderedTiles
  call MainScriptClearBox
  ld hl, 0

.done
  call MainScriptSetCursor
  jp MainScriptAdvance1

; C5 - Draw a string from RAM
MainScriptCCRAMString:
  call MainScriptGetCurrent
  inc hl
  ld a, [hli]
  ld h, [hl]
  ld l, a
  ld a, [W_TextSubIndex]
  ld c, a
  ld b, $00
  add hl, bc
  ld a, [hl]
  cp $C0
  jr nz, .drawCharacter
  ld b, 3
  call MainScriptAdvance
  xor a
  ld [W_TextSubIndex], a
  jp MainScriptApplySpeed

.drawCharacter
  call MainScriptDrawCharacter
  ld a, [W_TextSubIndex]
  inc a
  ld [W_TextSubIndex], a
  jp MainScriptApplySpeed

; C6 - Clear the box
MainScriptCCClear:
  call MainScriptClearBox
  ld a, [W_TextMode]
  or a
  jr nz, .renderedTiles
  ld hl, $9C41
  jr .done

.renderedTiles
  ld hl, 0

.done
  call MainScriptSetCursor
  jp MainScriptAdvance1

; C7 - Portrait
MainScriptCCPortrait:
  call MainScriptGetCurrent
  inc hl
  ld a, [hl]
  cp $FF
  jr nz, .showPortrait
  ld a, [W_TextPortrait]
  cp $FF
  jp z, .skip
  ld a, [W_TextEndState]
  cp $00
  jp z, MainScriptEndState1
  cp $01
  jp z, MainScriptIncrementEndState
  call MainScriptClearPortrait
  ld a, $FF
  ld [W_TextPortrait], a
  xor a
  ld [W_TextEndState], a
  ld b, 2
  jp MainScriptAdvance

.showPortrait
  ld b, a
  ld a, [W_TextEndState]
  cp $00
  jr z, .state0
  cp $01
  jr z, .state1
  jr .state2

.skip
  ld b, 2
  jp MainScriptAdvance

.state0
  ld a, b
  ld [W_TextPortrait], a
  ld a, [W_TextEndState]
  inc a
  ld [W_TextEndState], a
  ld a, $01
  ld [$C482], a
  ld b, $40
  ld c, $60
  ld d, $00
  ld e, $18
  jp $1B01

.state1
  ld a, $01
  ld [W_TextC430], a
  ld a, [W_TextEndState]
  inc a
  ld [W_TextEndState], a
  ret

.state2
  ld a, [W_TextPortrait]
  swap a
  srl a
  srl a
  and $03
  add $40
  rst $10
  ld hl, $4000
  ld a, [W_TextPortrait]
  and $3F
  ld b, $00
  ld c, a
  ld a, $08
  call $184E
  ld de, $8800
  ld bc, $0100
  call $0931
  ld bc, $0008
  ld e, $10
  ld a, $00
  call $1AC3
  ld a, $01
  ld [$DD26], a
  ld bc, $0008
  ld e, $0C
  ld a, $00
  call $1ACC
  ld a, $43
  rst $10
  ld hl, $4600
  ld b, $00
  ld a, [W_TextPortrait]
  ld c, a
  add hl, bc
  ld a, [hl]
  ld hl, $0200
  ld b, $00
  ld c, a
  add hl, bc
  ld b, h
  ld c, l
  ld a, $06
  call $130E
  ld a, $01
  ld [$DD00], a
  ld a, [W_TextBank]
  rst $10
  xor a
  ld [W_TextEndState], a
  ld b, 2
  jp MainScriptAdvance

; Normal character
MainScriptCharacter:
  push af
  call MainScriptAdvance1
  xor a
  ld [W_TextSubIndex], a
  pop af
  call MainScriptDrawCharacter
  jp MainScriptApplySpeed

MainScriptDrawCharacter:
  ; a = character
  ld [W_TextChar], a
  call VWFDrawCharacter
  ld a, [W_TextBank]
  rst $10
  ret

MainScriptClearPortrait:
  ld a, [W_TextPortrait]
  cp $FF
  ret z
  ld a, $00
  ld [$C44E], a
  ld a, $04
  ld [$C44F], a
  ld a, $08
  ld [$C450], a
  ld a, $04
  ld [$C451], a
  ld a, $00
  jp $1720

MainScriptClearBox::
  call VWFReset
  ld a, [W_TextWindowAlt]
  or a
  jr nz, .altWindow
  ld bc, $0000
  ld e, $00
  ld a, $00
  call $0B2A
  ld a, [W_TextMode]
  or a
  jp z, MainScriptMapMode0Tiles
  call VWFClearTiles
  ld bc, $0102
  ld e, $11
  ld a, $00
  jp $0B2A

.altWindow
  ld bc, $0006
  ld e, $01
  ld a, $00
  call $0B2A
  call VWFClearTiles
  ld bc, $0108
  ld e, $11
  ld a, $00
  jp $0B2A

MainScriptMapMode0Tiles:
  ; In mode 0, the box is drawn by mapping the VWF tiles into the window directly
  call VWFClearTiles
  ld hl, $9C41
  ld a, VWF_MODE0_TILE
  call .mapLine
  ld hl, $9C81
  ld a, VWF_MODE0_TILE + VWF_LINE_TILES
.mapLine
  ld b, VWF_LINE_TILES
.loop
  call $0AA8
  inc a
  dec b
  jr nz, .loop
  ret

MainScriptSectionTable::
  INCLUDE "build/text/section_table.asm"

MainScriptEngineEnd::
  ASSERT MainScriptEngineEnd <= $22E4, "Main script engine overflows into $22E4"
