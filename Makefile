export LC_CTYPE=C
export PYTHONIOENCODING=utf-8

VERSIONS := kuwagata
OUTPUT_PREFIX := medarot2_
ORIGINAL_PREFIX := baserom_

PYTHON := python3
CC := rgbasm
CC_ARGS := -Weverything -Wno-unmapped-char
LD := rgblink
LD_ARGS :=
FIX := rgbfix
FIX_ARGS := -v -p 0xFF

BUILD := build
SRC := game/src
SCRIPT := scripts
RES := $(SCRIPT)/res

# Text is placed in the expanded ROM space
TEXT_FIRST_BANK := 0x81
TEXT_LAST_BANK := 0xBF

MODULES := core patch text
SOURCES := $(foreach MODULE,$(MODULES),$(wildcard $(SRC)/$(MODULE)/*.asm))
OBJECTS := $(patsubst $(SRC)/%.asm,$(BUILD)/%.o,$(SOURCES))
COMMON := $(wildcard $(SRC)/common/*.asm)

FONT := $(BUILD)/gfx/VWFFont.1bpp
FONT_WIDTHS := $(BUILD)/gfx/VWFFont.widths
FIXED_FONT := $(BUILD)/gfx/FixedFont.2bpp
NARROW_FONT := $(BUILD)/gfx/VWFNarrowFont.1bpp $(BUILD)/gfx/VWFNarrowFont.widths
DIALOG := $(wildcard text/dialog/*.csv)
TEXT_OUT := $(BUILD)/text/text_data.asm
TILEMAPS := $(wildcard text/tilemaps/*.txt)
TILEMAP_OUT := $(BUILD)/tilemaps/tilemaps.asm
PTRLISTS := $(wildcard text/ptrlists/*.csv)
PTRLISTS_OUT := $(BUILD)/text/ptrlists.asm
LIST_RELOCATION_BANK := 0xC8
TILESETS := $(wildcard gfx/tilesets/*.png gfx/tilesets/*.count)
TILESETS_OUT := $(BUILD)/gfx/tilesets.asm
TILESET_FIRST_BANK := 0xD0
TILESET_LAST_BANK := 0xDF

.PHONY: all clean $(VERSIONS) ips
all: $(VERSIONS)
kuwagata: $(OUTPUT_PREFIX)kuwagata.gbc

$(OUTPUT_PREFIX)%.gbc: $(OBJECTS) $(BUILD)/$(ORIGINAL_PREFIX)%_expanded.gbc
	$(LD) $(LD_ARGS) -n $(OUTPUT_PREFIX)$*.sym -m $(OUTPUT_PREFIX)$*.map -O $(BUILD)/$(ORIGINAL_PREFIX)$*_expanded.gbc -o $@ $(OBJECTS)
	$(FIX) $(FIX_ARGS) $@

ips: $(foreach VERSION,$(VERSIONS),$(OUTPUT_PREFIX)$(VERSION).ips)
$(OUTPUT_PREFIX)%.ips: $(OUTPUT_PREFIX)%.gbc $(ORIGINAL_PREFIX)%.gbc
	$(PYTHON) $(SCRIPT)/make_ips.py $(ORIGINAL_PREFIX)$*.gbc $< $@

# Pad the original ROM to 4MB to make room for the translation
$(BUILD)/$(ORIGINAL_PREFIX)%_expanded.gbc: $(ORIGINAL_PREFIX)%.gbc | $(BUILD)
	$(PYTHON) $(SCRIPT)/expand_rom.py $< $@

$(BUILD)/%.o: $(SRC)/%.asm $(COMMON) | $(BUILD)
	@mkdir -p $(dir $@)
	$(CC) $(CC_ARGS) -o $@ $<

$(BUILD)/core/text_engine.o: $(TEXT_OUT)
$(BUILD)/text/text_data.o: $(TEXT_OUT)
$(BUILD)/text/ptrlists.o: $(PTRLISTS_OUT)
$(BUILD)/patch/vwf.o: $(FONT) $(FONT_WIDTHS)
$(BUILD)/patch/vwf_strings.o: $(NARROW_FONT)
$(BUILD)/patch/fonts.o: $(FIXED_FONT)
$(BUILD)/patch/tilemaps.o: $(TILEMAP_OUT)
$(BUILD)/patch/tilesets.o: $(TILESETS_OUT)

$(FONT) $(FONT_WIDTHS) $(FIXED_FONT) $(NARROW_FONT): gfx/patch/M3Font.1bpp.png gfx/patch/M1FixedFont.png gfx/patch/M3NarrowFont.1bpp.png $(SCRIPT)/build_font.py $(RES)/charmap_en.tbl | $(BUILD)
	$(PYTHON) $(SCRIPT)/build_font.py $< $(ORIGINAL_PREFIX)kuwagata.gbc $(RES)/charmap_en.tbl $(FONT) $(FONT_WIDTHS) $(FIXED_FONT)

$(TEXT_OUT): $(DIALOG) $(FONT_WIDTHS) $(SCRIPT)/build_text.py $(SCRIPT)/textcodec.py $(RES)/charmap_en.tbl
	$(PYTHON) $(SCRIPT)/build_text.py $(ORIGINAL_PREFIX)kuwagata.gbc text/dialog $(FONT_WIDTHS) $(BUILD)/text $(TEXT_FIRST_BANK) $(TEXT_LAST_BANK)

$(PTRLISTS_OUT): $(FONT_WIDTHS) $(PTRLISTS) $(SCRIPT)/build_ptrlists.py $(SCRIPT)/dump_ptrlists.py $(SCRIPT)/textcodec.py $(RES)/charmap_en.tbl
	@mkdir -p $(dir $@)
	$(PYTHON) $(SCRIPT)/build_ptrlists.py $(ORIGINAL_PREFIX)kuwagata.gbc text/ptrlists $@ $(LIST_RELOCATION_BANK)

$(TILESETS_OUT): $(TILESETS) $(SCRIPT)/build_tilesets.py
	@mkdir -p $(dir $@)
	$(PYTHON) $(SCRIPT)/build_tilesets.py gfx/tilesets $@ $(TILESET_FIRST_BANK) $(TILESET_LAST_BANK)

# Menu/screen tilemaps (text/tilemaps/*.txt); untranslated tilemaps are left untouched
$(TILEMAP_OUT): $(FONT_WIDTHS) $(TILEMAPS) $(SCRIPT)/build_tilemaps.py $(SCRIPT)/dump_tilemaps.py $(SCRIPT)/common/tilemaps.py $(SCRIPT)/textcodec.py $(RES)/charmap_en.tbl $(RES)/charmap_jp.tbl
	$(PYTHON) $(SCRIPT)/build_tilemaps.py $(ORIGINAL_PREFIX)kuwagata.gbc text/tilemaps $@ $(FONT_WIDTHS)

$(BUILD):
	mkdir -p $@

clean:
	rm -rf $(BUILD) $(OUTPUT_PREFIX)*.gbc $(OUTPUT_PREFIX)*.sym $(OUTPUT_PREFIX)*.map $(OUTPUT_PREFIX)*.ips
.SECONDARY:
