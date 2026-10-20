# Medarot 2 Translation Guide

This translation follows the style of the Medabots team's Medarot 1 and Medarot 3 English
translations (https://github.com/Medabots/medarot1, https://github.com/Medabots/medarot3).
Local copies are at `/home/user/medarot1` and `/home/user/medarot3`; their translated dialog is
in `text/dialog/*.csv` (Original + Translated columns) and is the best reference for tone.

## General style

* Be faithful to the Japanese. Translate meaning and tone, keep jokes, puns (adapt them when
  a literal rendering makes no sense), character quirks, and onomatopoeia.
* Use the **original Japanese names** (the Medapedia / fan-translation names), never the US
  dub names: Ikki (not Ikki Tenryou in casual speech), Arika (not Erika), Metabee, Rokusho,
  Medarotch (not Medawatch), robattle, Medarotter (not Medafighter), RoboRobo Gang (not
  Rubberobo), Phantom Retort / Retort, Mr. Uruchi (the referee), Tinpet, Medal, Medaforce.
  `scripts/res/glossary_m2.csv` is the authority for names; when a term is missing there, check
  `/home/user/medarot3/scripts/res/glossary.csv` (EN column) and the M1/M3 translated lists.
* **No honorifics** (-kun, -chan, -san, -sama). As in Medarot 3, render さん / さま addressed to
  adults as "Mr." / "Ms." where natural (e.g. 白玉さん → Mr. Shiratama, スルメさま → Ms.
  Surume), and simply drop -kun / -chan. はかせ = "Doctor" / "Dr. X". せんせい = "Teacher" /
  "Mr./Ms. X" as context suggests.
* RoboRobo Gang members end sentences with ロボ: render as ", robo" / "robo!" like Medarot 3
  ("What's this, robo?", "I don't know, robo!").
* Use "..." (three periods) for ・・・ / … . Use "!?" for !? . Stuttering: "I-I don't know".
* Long vowels/shouts: "Aaah!", "Whoa!", "Hmph". Laughter: "Hahaha", "Ohohoho", "Gwahahaha".
* Natural, lively English suitable for kids and adults. Contractions are fine. Keep each
  character's voice consistent (Ikki: earnest boy; Arika: bossy, energetic reporter;
  Metabee: brash, rude; Rokusho: stoic samurai; etc.).
* Game terms: パーツ = parts, あたま = head, みぎうで = right arm, ひだりうで = left arm, きゃく/あし =
  legs, そうこう = armor, じゅうりょく... use the glossary. きのうていし = "shutdown" (function
  ceasing), ロボトル = robattle, リーダー = leader, メダチェンジ = Medachange, メダフォース =
  Medaforce, ティンペット = Tinpet, メダロッチ = Medarotch, メダロットしゃ = Medarot Company,
  メダロットはかせ = the Medarot Doctor (check glossary), しんがたメダロッチ = new-model Medarotch.

## File format

`text/dialog/TextSectionNN.csv`: columns `Index, Pointer, Original, Translated`. Put the
English in `Translated`. Do not modify the other columns.

* Rows whose Original is `@XXX` are duplicates of entry XXX: **leave Translated empty**.
* Rows that are garbage (mostly `<$XX>` codes, or long runs of nonsense / repeated `ア`), and
  rows with an empty Original: leave empty.
* Debug/test lines (e.g. メッセージテスト, かいはつちゅう) should still be translated.

### Control codes (keep them!)

| Code | Meaning | What to do |
|---|---|---|
| `<@XX>` | Show portrait XX for the following text (`<@FF>` = none) | Keep every one, in the same order, at the start of the same box. `scripts/res/portraits.tbl` says who each portrait is: **use it to know who is speaking**. |
| `<&XXXX>` | Inserts a name from RAM (player name, Medarot name, item...) | Keep, in a grammatical position. |
| `<*XX>` | End of text with exit mode XX (when absent, the text ends with mode 00) | Keep at the very end, unchanged. |
| `<SXX>` | Text speed | Keep in place. |
| `<CF>` | Wait for the A button, then start a new box | Keep the box structure of the original: one `<CF>` where the original has one. |
| `<CC>` | Clear the box without waiting | Keep where the original has it (usually right after `<CF>`). |
| `<CR>` | Line break inside a box | **Do not use it in translations** (replace with a space). Line breaks and extra boxes are added automatically when the text is built. |

Lines are wrapped automatically (≈ 28–34 characters per line, 2 lines per box).

All sections, including `TextSection00.csv` and `TextSection01.csv` (system, shop and battle
messages), use the variable width font: no abbreviations are needed.

### Allowed characters

`a-z A-Z 0-9`, space, and `. , ' " & ( ) ; % ~ # * = ♪ _ [ ] $ é - · ♥ / ? ! : “ ” ¥`
and `…` (prefer "..."). Do **not** use `<` or `>` except in control codes. No other Unicode
(no em dashes: use "-" or "--"; no curly apostrophes: use ').

### Validate

Run `python3 scripts/check_text.py text/dialog/TextSectionNN.csv` after editing. It must report
0 errors; warnings about differing control codes must be justified (normally fix them).

## Name lists (`text/ptrlists/*.csv`)

Fill the `*_EN` columns with the full English name (no abbreviations). Names are drawn with the
variable width font; the build stores names longer than the game's fixed-size buffers as
"name tokens" and expands them when drawn. The limit is the on-screen width of the field
(8 tiles = 64 pixels for most names, 6 tiles for medals/attributes, 5 for skills/attacks);
names that are too wide are drawn with the narrow font automatically, and the build reports
names that don't fit even then.
