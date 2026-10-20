# Menu and screen tilemaps

Many menus and screens draw their static Japanese text (menu items, labels, window titles)
as part of a *tilemap*: a block of tile numbers copied straight into the background map.
These texts are not in `text/dialog` and need to be translated in `text/tilemaps/*.txt`.

* `scripts/dump_tilemaps.py` dumps them:
  `python3 scripts/dump_tilemaps.py baserom_kuwagata.gbc text/tilemaps [--all] [--force]`
  (existing files are kept unless `--force`; `--all` also dumps the maps listed as graphics).
* `scripts/build_tilemaps.py` re-encodes the translated ones into
  `build/tilemaps/tilemaps.asm`, which `game/src/patch/tilemaps.asm` includes. `make` runs it
  automatically when a file in `text/tilemaps/` changes.
* `scripts/common/tilemaps.py` holds the codec (decode/encode/compress, text run detection).

Untranslated tilemaps (no `EN:` filled in) are not touched at all: the ROM stays byte-identical
in the tilemap banks.

## How the game draws tilemaps

`Call_000_0b2a` (BG map $9C00) / `Call_000_0b1f` (BG map $9800), reached through the home
jump table at $0171/$0174, draw tilemap `e` of table `a` at tile position `b`=x, `c`=y.
The bank of table `a` is the byte at `$0C52 + a`; that bank starts with 256 pointers
(`$4000 + e*2`). The attribute (palette) maps work the same way through `Call_000_0c6e` /
`Call_000_0c54` with the bank table at `$0DA1` (banks $38/$39); they hold no text and are
left alone.

| Table | Bank | Entries used | Text tilemaps dumped |
|---|---|---|---|
| 0 | $34 | $00-$99 (entries $9A-$FF are unused, pointing at the end of the data) | 33 |
| 1 | $35 | $00-$E6 | 27 |

Data format (first byte = header; `$FF` = empty map):

* header & 3 == 0, **raw**: `$FF` end, `$FE` next row (back to the start column), `$FD` skip
  a tile (leave what is on screen), `$FC tt nn` tile `tt` repeated `nn` times, anything else
  is a tile. Raw maps have variable-length rows.
* header & 3 != 0, **compressed**: a linear stream of tiles, 32 per row (the VRAM row width;
  only columns 0-19 are on screen). Commands: `%00nnnnnn` + n+1 literal tiles, `%01nnnnnn tt`
  repeat tt n+2 times, `%10nnnnnn tt` tt, tt+1, ... (n+2 tiles), `%11nnnnnn tt` tt, tt-1, ...;
  `$FF` ends the map.

In menu screens tiles $00-$7F are the font (kana in the original, the English fixed-width font
in the patch: `scripts/res/charmap_en.tbl`) and $E7-$F5 are digits/symbols; $80-$E6 and $F6-$FF
are screen graphics (window borders etc.). Many other screens (title, character art, the link
cable screens, ...) load their own graphics over tiles $00-$7F, so their tilemaps "decode" to
nonsense kana: those are listed in `GRAPHICS` in `dump_tilemaps.py` and not dumped.

## File format

One file per tilemap: `text/tilemaps/<table>_<index>.txt` (index in hex). When several
indices share the same data the file is named after the first one and lists the others; the
builder repoints all of them.

```
# Tilemap 0_54: table 0 (bank $34), index $54
# Data: $34:50A4, raw (header $00), 85 bytes, 11x8 tiles
# Screen: Medarot menu: Make leader / View status / Back
#
# Layout ('＃' graphics tile, '．' blank tile $00, '　' not drawn, ゛゜ dakuten tiles):
#      ０１２３４５６７８９０
#    0|＃＃＃＃＃＃＃＃＃＃＃|
#    1|＃．．．゛．．．．．＃|
#    2|＃．リーターにする．＃|
#    ...

[0_54]

@ 2,2 max 8
JP: リーダーにする
EN:
```

* Lines starting with `#` are comments. The **layout** shows the whole map as it is drawn,
  one character per tile (full-width, so it lines up in a monospace editor with CJK fonts).
  Dakuten/handakuten are separate tiles in the row above the kana, exactly as in the ROM.
* `[0_54]` identifies the tilemap. Do not change it.
* Each **text entry** is one horizontal run of text:
  * `@ row,col max N`: the text starts at that row/column (0-based, relative to the tilemap's
    top-left corner) and there are `N` tiles available from there before the next graphics
    tile, the next piece of text, or the end of the row (the end of the screen, column 20,
    for compressed maps).
  * `JP:` the original, with the dakuten from the row above merged in (`ダ`). Do not edit it:
    the builder checks it against the ROM.
  * `EN:` the translation. **Leave it empty to keep the Japanese.**

### Translating

* Write the English after `EN: ` (one space after the colon is ignored, trailing spaces are
  dropped). One character = one tile, fixed width. `<$XX>` inserts tile/character code XX.
  No line breaks or control codes.
* The English must fit in `max` tiles (labels use the variable width font, switching to the
  narrow font automatically when needed); the builder stops with an error naming the file/line
  when it would overwrite a graphics tile or other text. Write full words, no abbreviations.
* `DMG: text` (after `EN:`) is the fallback for original Game Boy screens that must use the fixed
  width font (one character per tile, e.g. the name entry screen). It is needed when `EN:` has
  more characters than the entry's tiles (the builder warns); without it `EN:` is used.
* When an entry is translated, the original Japanese tiles of that run are blanked first
  (tile $00), as are the ゛/゜ tiles above them, so shorter English leaves no leftovers.
  Some boxes draw the dakuten inside the border tile above the kana (e.g. メダル in
  `0_38`, パスワード in `1_D6`); the entry then has a comment like
  `# (dakuten drawn in graphics tile above column 3 ($C3, becomes $BB when translated))`, and
  that tile is replaced by the plain border tile automatically.
* You may change `row,col` of an entry to move the text (e.g. one column left into the blank
  margin to gain a tile, or onto the now empty dakuten row to get a second line). The
  target tiles must be blank/text tiles in the original.
* To put text where the original had none, add an entry without a `JP:` line:
  ```
  @ 1,2
  EN: Second line
  ```
* `@! row,col` (with `!`) skips all safety checks and writes anywhere, including over
  graphics tiles (use `<$XX>` to draw a specific graphics tile, e.g. to patch a border).
* Tiles that the original leaves **undrawn** (`　` in the layout; `$FD` in raw maps) are
  usually filled in by the game at run time (numbers, names, prices). Writing over them prints
  a warning: make sure nothing else is drawn there.
* Blank areas inside windows may also be filled at run time (cursor `▶` positions, numbers),
  so check the screen in an emulator when you use space beyond the original text.

### Things to know

* The name-entry keyboards (`1_53`, `1_54`) are tilemaps too, but the character picked at
  each cursor position comes from a separate table in the code: changing the keyboard picture
  alone does not change what gets typed.
* Several maps contain stats/number layouts (`/`, `:`, `×`, `00円` …) that the game fills in;
  keep those tiles in place (they are not part of the text entries unless adjacent to kana).
* `1_15` (きたむら ルアー はつばい!), `1_41` (キャラクター/せいし/アニメ), `1_6F` and `1_E1`
  could not be tied to a screen; they may be debug or unused.

## Placement (build_tilemaps.py)

For each tilemap with a translation, per table bank:

1. if the re-encoded map is not larger than the original, it is written over the original
   data (`SECTION "Tilemap T_II", ROMX[addr], BANK[$34/$35]`);
2. otherwise it goes in the free space at the end of the same bank (bank $34: $6720-$7FFF,
   bank $35: $65F0-$7FFF, ~6KB each, more than all the text maps together) and every pointer
   that used the old address is rewritten (`SECTION "Tilemap T Pointer II"`);
3. if that space ever runs out the build fails with an error. (Moving a table to another bank
   would mean moving the whole table, since the bank is one byte per table at $0C52, and the
   original data of a table already fills ~10KB.)

Raw maps are re-encoded with `$FC` runs for 4+ identical tiles; compressed maps are
re-compressed greedily. Both encoders round-trip every original map (checked on all 284).

## Tilemap list

R = raw, C = compressed. Numbers in parentheses are the `max` tiles available for each entry.

| File | Fmt | Screen | Entries (max tiles) |
|---|---|---|---|
| `0_12` | R | Saving message | セーブちゅう! (7) |
| `0_24` | C | Records: Medals/Parts obtained, play time, wins/battles | てにいれたメダル (14); てにいれたパーツ (14); プレイじかん (11); かち/しあいすう (12) |
| `0_26` | R | Medarot order: "SELECT button: swap order" | セレクトボタンで (8); じゅんばんを いれかえます (13) |
| `0_29` | R | Item menu: Use / View | つかう (3); みる (3) |
| `0_2A` | R | Status headers: Medarot / Medal / Parts | メダロット (6); メダル (4); パーツ (4) |
| `0_2C` | R | Head parts | あたまパーツ (8) |
| `0_2D` | R | Right arm parts | みぎうでパーツ (8) |
| `0_2E` | R | Left arm parts | ひだりうでパーツ (8) |
| `0_2F` | R | Leg parts | きゃくぶパーツ (8) |
| `0_30` | R | "SELECT button: switch parts" | セレクトボタンで (10); パーツきりかえ (7) |
| `0_36` | R | Parts stats: armor / uses / success / power | そうこう (5); かいすう (5); せいこう (5); いりょく (5) |
| `0_37` | R | Parts stats: armor / charge / heat / success / power | そうこう (5); じゅうてん (5); ねつりょう (5); せいこう (5); いりょく (5) |
| `0_38` | C | Medal selection / Level | メダルせんたく (9); レベル (6) |
| `0_40` | C | Medal status: ability / remaining / compatibility / experience | のうりょくち (8); のこり (10); あいしょう (5); けいけん (9) |
| `0_41` | C | Medal skills: proficiency | じゅくれんど (18) |
| `0_42` | C | Medaforce: name / consumption / success / power | メダフォース (7); しょうひ (4); /せいこうち (6); いりょく (8) |
| `0_43` | C | Medarot status frame | メダロット (7) |
| `0_44` | C | Parts detail: Type | タイプ/ (7) |
| `0_52` | R | "Please choose a Medarot" | メダロットを えらんでください (15) |
| `0_53` | R | "Choose Medarots, or start the robattle" | メダロットを えらぶか (11); ロボトルを かいし してください (16) |
| `0_54` | R | Medarot menu | リーダーにする (8); ステータスをみる (8); もどる (8) |
| `0_55` | R | Medarot menu | チームにいれる (8); ステータスをみる (8); ロボトルかいし (8); もどる (8) |
| `0_56` | R | Medarot menu | チームからはずす (8); ステータスをみる (8); ロボトルかいし (8); もどる (8) |
| `0_75` | R | "(button): details screen" | ボタンで (9); しょうさいがめん (10) |
| `0_76` | C | Medal frame: Level | レベル (6) |
| `0_81` | R | Link menu | あそびでロボトル (8); しんけんロボトル (8); パーツのトレード (8); メダルのトレード (8); つうしんをきる (8) |
| `0_83` | R | "Transferring data! Please wait!" | データてんそうちゅう! (12); しばらくおまちください! (12) |
| `0_87` | R | "Choose the parts to trade" | トレードするパーツを (10); えらんでください (10) |
| `0_88` | R | View / Yes / No | みる (3); はい (3); いいえ (3) |
| `0_89` | R | "Is this part OK?" | このパーツで (10); よろしいですか? (10) |
| `0_94` | C | Link battle: Level x2 | レベル (6); レベル (6) |
| `0_98` | R | Yes / No | はい (3); いいえ (3) |
| `0_99` | R | Link: Explanation / Connect / Quit | せつめい (5); せつぞく (5); やめる (5) |
| `1_12` | R | Debug: Message checker | メッセージチェッカー (10) |
| `1_15` | R | ? "Kitamura Lure, on sale!" | きたむら ルアー (8); はつばい! (5) |
| `1_41` | R | ? Character / Still / Anime | キャラクター (6); せいし (3); アニメ (3) |
| `1_45` | R | Yes / No | はい (3); いいえ (3) |
| `1_48` | R | Title menu: Continue | つづきから (6) |
| `1_49` | R | Title menu: Transfer | てんそう (5) |
| `1_50` | C | Battle time setting: long / short | せんとうじかん せってい (15); ながい (7); みじかい (4) |
| `1_51` | R | Name entry: "Your name?" | キミの (6); なまえは? (5) |
| `1_52` | R | Name entry: "Medarot's name?" | メダロットの (6); なまえは? (5) |
| `1_53` | R | Name entry: katakana keyboard | 4 rows (17 each) |
| `1_54` | R | Name entry: hiragana keyboard | 4 rows (17 each) |
| `1_59` | R | Shop: Buy / Sell / Smile / Quit | かう (5); うる (5); スマイル (5); やめる (5) |
| `1_5A` | R | Shop: Buy / Sell / Smile / Password / Quit | かう (5); うる (5); スマイル (5); パスワード (5); やめる (5) |
| `1_5B` | R | Shop: money window | おかね (9) |
| `1_62` | R | Parts type: Head / R. arm / L. arm / Legs / Quit | あたま (5); みぎうで (5); ひだりうで (5); きゃくぶ (5); やめる (5) |
| `1_63` | R | Shop screen: money | おかね (6) |
| `1_68` | R | Shop: "How many to buy? ×" / "Owned ×" | いくつ かう?× (11); もっているかず× (12) |
| `1_69` | R | Shop: "Is this OK?" | これで よろしいですか? (12) |
| `1_6F` | R | ? Get / Loose / Back / ... | ゲット (4); ルーズ (4); もどる (4); ぜんげっと (5) |
| `1_7B` | R | Shop: "How many to sell? ×" / "Owned ×" | いくつ うる?× (11); もっているかず× (12) |
| `1_D6` | C | Password output | パスワード しゅつりょく (13) |
| `1_D7` | C | Password input | パスワード にゅうりょく (13) |
| `1_D8` | R | Repair / Quit | なおす (3); やめる (3) |
| `1_D9` | R | Increase / Give | ふやす (3); わたす (3) |
| `1_DA` | R | Title menu: New game | はじめから (5) |
| `1_DB` | R | Title menu: Settings | せってい (5) |
| `1_E1` | R | ? | しょう (4) |

(The JP charmap has no separate り, so the dumps show リ for both.)

## Variable width labels

Translated entries are no longer written into the tilemap as fixed width tiles. The builder
blanks their cells and stores each entry (row, column, string) in a label list per tilemap
(bank $CC); after the game loads a tilemap, the labels are drawn with the variable width font
(see `game/src/patch/tilemap_labels.asm`). So the limit of an entry is its pixel width:
`max` tiles × 8 pixels. When a label is too wide, the builder switches it to the narrow font
automatically if that fits. Exceptions: the name entry keyboards (`1_53`, `1_54`) stay fixed
width because the typed character is read back from the tilemap.

Symbols that line up with numbers the game prints (like `×` in the shop quantity box) should be
separate entries at their original column.
