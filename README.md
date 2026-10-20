# Medarot 2 English Translation

An English translation patch for **Medarot 2 (Kuwagata Version)** for the Game Boy Color, made in
the style of the Medabots team's [Medarot 1](https://github.com/Medabots/medarot1) and
[Medarot 3](https://github.com/Medabots/medarot3) translations: original Japanese names
(Metabee, Rokusho, Arika, RoboRobo Gang, Medarotch, robattle...) and terminology from the
[Medapedia](https://medarot.meowcorp.us/wiki/Main_Page).

## Applying the patch

1. Get the original ROM: *Medarot 2 - Kuwagata Version (Japan) (SGB Enhanced) (GB Compatible)*,
   SHA-1 `48fc8c6e84c63ee47f5a2c5e99dc1666d6e9f496`.
2. Apply `medarot2_kuwagata.ips` with any IPS patcher (e.g. [Rom Patcher JS](https://www.marcrobledo.com/RomPatcher.js/)).
   The patched ROM is 4MB.

## Building

Dependencies: Make, Python 3 with Pillow, [rgbds](https://github.com/gbdev/rgbds) 1.0+.

1. Put the original ROM in the project root as `baserom_kuwagata.gbc`.
2. Run `make` (builds `medarot2_kuwagata.gbc`) or `make ips` (also builds the IPS patch).

## Layout

| Path | Contents |
|---|---|
| `text/dialog/TextSectionNN.csv` | All script text (Original / Translated). See `doc/TRANSLATION_GUIDE.md`. |
| `text/ptrlists/*.csv` | Name lists: Medarots, parts, medals, attacks, items... |
| `text/tilemaps/` | Menu text stored in tilemaps |
| `gfx/tilesets/` | Replacement graphics (Japanese text drawn in tiles) |
| `game/src/core/text_engine.asm` | Rewritten script engine (16-bit offsets, banked text tables) |
| `game/src/patch/vwf.asm` | Variable width font renderer for dialog |
| `game/src/patch/fonts.asm` | English fixed width font for menus |
| `scripts/` | Dumpers and builders |
| `doc/` | Reverse engineering notes, glossary notes, portraits |

## How it works

The patch is built as an rgbds overlay on top of the original ROM, padded to 4MB:

* The main script engine (`$1C69`-`$22E3`) is reimplemented: text offsets are 16-bit and text
  tables hold bank+address entries, so the English script lives in banks `$81`+.
* Dialog is drawn with a variable width font (the Medarot 3 translation's font), wrapped
  automatically at build time. Menu strings and labels use the same font, rendered into private
  tiles in VRAM bank 1, so names are never abbreviated on the Game Boy Color.
* On the original Game Boy there is no VRAM bank 1. Menu strings are drawn into font tiles
  that aren't on screen instead (all text uses the variable width font, so the letter tiles are
  free), found by scanning the tilemaps. Screens that need the real font tiles (the name entry
  keyboards) and the staff roll use the fixed width font, with the short names and labels from
  the `Name_DMG` columns in `text/ptrlists` and the `DMG:` lines in `text/tilemaps`.
* The English encoding puts all printable characters in `$00-$7F`, the part of the font every
  menu screen loads, keeping the original digits (`$E7-$F0`) and symbols.

## Testing

`debug menu`: the game contains a developer debug menu (message checker, shop, encounters...),
reachable by setting `wC3E0` to `$31` while in the overworld (e.g. with an emulator's memory editor).

## Credits

* Fonts: Medarot 3 translation by the Medabots team
* Terminology: Medapedia, Medarot 1 and Medarot 3 translations
