# Medapedia notes for the Medarot 2 glossary

Glossary file: `scripts/res/glossary_m2.csv` (columns `JP,EN,Category,Source,Notes`).
Wiki: https://medarot.meowcorp.us (data pulled via `/w/api.php`, `prop=wikitext`).

## Useful wiki pages

- [Medarot 2](https://medarot.meowcorp.us/wiki/Medarot_2): overview. There are 151 Medarots: 91 new ones plus the 60 from Medarot 1.
- [Medarots in Medarot 2](https://medarot.meowcorp.us/wiki/Medarots_in_Medarot_2): the main table. It has the number, model (BAT-1…), original-style name, kana, US/2 Core name, leg type and gender, in the same order as the in-game parts list.
- Individual Medarot pages (all 151 exist). `{{Infobox Medarot}}` gives the head/right/left/leg part names plus the kana. Only 18 pages have a `{{Stats-M2}}` block, which adds part codes such as BAT-11. The 60 Medarot 1 Medarots have `{{Stats-M1}}`.
- [Medals in Medarot 2](https://medarot.meowcorp.us/wiki/Medals_in_Medarot_2): all 32 medals with kana and attribute.
- Individual medal pages (e.g. [Kuwagata Medal](https://medarot.meowcorp.us/wiki/Kuwagata_Medal)): about 14 of them list the M2 Medaforce names. The format varies from page to page.
- [Actions in Medarot 2 / R](https://medarot.meowcorp.us/wiki/Actions_in_Medarot_2_/_R): 68 actions with kana. The wiki uses the later-series names and gives the literal original name in brackets.
- [Characters in Medarot 2](https://medarot.meowcorp.us/wiki/Characters_in_Medarot_2), [Characters in Medarot 2 Core](https://medarot.meowcorp.us/wiki/Characters_in_Medarot_2_Core), [Locations in Medarot 2 Core](https://medarot.meowcorp.us/wiki/Locations_in_Medarot_2_Core).
- [Medaforce](https://medarot.meowcorp.us/wiki/Medaforce) (general) and [Medarot 2 Parts Collection](https://medarot.meowcorp.us/wiki/Medarot_2_Parts_Collection) (the source of the Justice/Evil/Bottlero medals and the Fuyun Stone).
- [Hirano Kana's Medarot 2 Production Notes](https://medarot.meowcorp.us/wiki/Hirano_Kana%27s_Medarot_2_Production_Notes): a translated developer interview. It covers the scrapped "phantom script" and the beer/spirits naming theme for the cast. It is background reading, not script text.

## Translation / script pages

- The wiki has **no Medarot 2 translation project and no Medarot 2 script pages.** Searching for "Medarot 2 translation" and "Medarot 2 script" returns nothing.
- The Medapedia namespace only has translation projects for other games: [Medarot 1](https://medarot.meowcorp.us/wiki/Medapedia:Medarot_1_Translation_Project) (text, part names, lists), [Medarot 3](https://medarot.meowcorp.us/wiki/Medapedia:Medarot_3_Translation_Project) and [Medarot Navi](https://medarot.meowcorp.us/wiki/Medapedia:Medarot_Navi_Translation_Project) (script pages). Main namespace also has Medarot S translations.
- Pages that do not exist:
  - "Locations in Medarot 2" (only the 2 Core version exists), "Items in Medarot 2" and "Medaforces in Medarot 2".
  - Most minor character pages: Banchou, Awamori, Tokkuri, Prince Kir, Shandy, Spumoni, Tequila, Ryo, Margarita, Jyozo, Ginjyo, Sasuke/Goemon/Hanzo, Kannie, Yanagi, Natsuko, Kahlua, Harvey, Demon King.
  - Almost all location pages. Only Omikuji Town, Medarot Laboratory, Medarotters and Medarot Company exist.

## How the JP column was obtained

The JP strings come from the ROM (`/home/user/baserom_kuwagata.gbc`, using `scripts/res/charmap_jp.tbl`), so they match the in-game kana exactly:

| Data | ROM location | Format |
|---|---|---|
| Medarot names | 22:4200 | 151 strings separated by C0 |
| Head parts | 22:4898 | 17-byte records: `code C0 name C0 pad… flag`; flag = 1 for a female part |
| Right-arm parts | 22:54C1 | same record format |
| Left-arm parts | 22:60EB | same record format |
| Leg parts | 22:6D14 | same record format |
| Items | 22:77A3 | 10-byte records |
| Medals | 22:7A56 | |
| Terrain | 22:7B90 | |
| Short action labels | 22:7C69 | |
| Medal attributes, skills, leg types, natures | 21:6600–6D9A | |
| Medaforce names | 21:6E6C | 5 data bytes + name; 3 per medal, in medal order |
| Opponent/NPC name table | 20:4800 | |

The game font uses one glyph for リ/り, ヘ/へ, ペ/ぺ and ベ/べ, so the decoded text always shows the katakana form. In the CSV, hiragana words are written with the real hiragana (e.g. からたけわり, てんとう). Every JP entry was checked against the decoded ROM text.

The wiki kana matched the ROM for every part except these:
- パテリィバルカン (the wiki has パテリバルカン).
- コックピット (M1 spelled it コクピット).
- The Teepee head/arms became アシッド… (Acid…) in M2 (they were メルト… in M1).
- The hiragana copies of M1 Rokusho/Metabee and their parts (see below).

## Naming conventions observed

- **Medarot names** are the wiki's literal/original-style romanizations: Gaufbullet, DeathPhoenix, Wonder Angel, Kanehachi Mk2, Sakura-Chan. The table's "English name" column is the US/2 Core localization (Noctobat, Drakonfly…). Those are listed in Notes as "do not use".
- **Medarot 1 Medarots** use the medarot1 list names (Crow Tengu, CoffinBat, Head Scissors, Metal Beetle…).
- **Rokusho and Metabee:** the M2 parts list calls Ikki's KWG/KBT types ヘッドシザース and メタルビートル (Head Scissors / Metal Beetle). Rokusho and Metabee (ロクショウ/メタビー) are the character names. The transferred M1 copies are in **hiragana**: ろくしょう, めたびー, あんてな, ちゃんばらそーど…
- **Part names** are mostly English loanwords transliterated with hyphens or spaces (Psycho-Missile, Hard-Weighter, Cherub Body). Japanese puns are kept romanized (Ochitsuker, Tatacker, Mettakiller, Kaminari Ochiru).
- **Part codes:** Medarot model "XXX-1" or "XXX-0" (new M2 types use -0). Its parts are XXX-11..14 (or XXX-01..04). M1 Medarots keep their M1 codes (CRW-01…). The hiragana Rokusho copy uses the code **KGW**-01..04 (sic). The two BAY-03 "ーーーー" entries are dummies.
- **Gendered parts:** each part record has a female flag, and 33 Medarots have female parts (LadyBooster, Wonder Angel, Wind Cecil, Sunwitchy, Sailor-Multi…). Female-only parts are marked "female part" in Notes.
- **Core terms** (all match medarot3's glossary.csv):

  | Kana | EN | Notes |
  |---|---|---|
  | メダロッチ | Medarotch | not Medawatch |
  | ティンペット | Tinpet | |
  | メダル | Medal | |
  | ロボトル | robattle | |
  | メダロッター | Medarotter | not Medafighter |
  | ロボロボだん | RoboRobo Gang | not Rubberobo |
  | かいとうレトルト | Phantom Retort | |
  | レトルトレディ | Lady Retort | |
  | メダフォース | Medaforce | the wiki also mentions メダスキル "Medaskill" from later games |
  | セレクトたい | Select Corps | medarot1 uses "Select Officer" / "Select Headquarters" |
  | メダロッとう | Medarot Island | a pun |

- **Medal names:** 27 come from M1. ネズミ (Mouse) replaces M1's Wolf (おおかみ), although an unused hiragana medal table still has おおかみ. The M2-only medals are ? / せいぎ Justice / あく Evil / ぼとるろ Bottlero / ! . Skills are なぐる Strike, がむしゃら Berserk, うつ Shoot, ねらいうち Snipe, おうえん Support, まもる Protect, なおす Heal, そのほか Other (same as medarot1).

## Where the wiki and medarot1/medarot3 disagree

The medarot1/medarot3 name was used each time; the CSV Notes record the difference.

- **Characters:** コウジ = Koji (wiki "Kouji"), サラミ = Sarami (wiki "Salami"), カワムラー = Kawamuller (wiki "Kawamura"), ギンジョウ = Ginjo (wiki "Ginjyo").
- **M1 part names**, for example:

  | Kana | medarot1 | wiki |
  |---|---|---|
  | かくれみの | Mist Net | Stealth Cloak |
  | ファランクス | Pharynx | Phalanx |
  | タイクーミサイル | AA Missile | Anti-Air Missile |
  | チョーキョリホー | Ranged Cannon | Super Long Cannon |
  | ジュウザー | Gunzer | Gun Mount |
  | タイウォーター | VS Water | Thai Water |
  | クルックル | Spin-Spin | Twirl |

- **medarot1 vs medarot3** (kept medarot1, noted): チャンバラソード Chanbara Sword (M3: Samurai Sword) and オチツカー Ochitsuker (M3: Ochitsuka).
- **Medal attributes 1–20:** use medarot1's Attributes list (かくとう Melee, かやく Gunpowder); the wiki has Fight / Explosive.
- **Medaforce:**
  - たていっせん / よこいっせん / いっせいしゃげき use medarot3's Vertical Slash / Horizontal Slash / Volley Fire (wiki: Vertical Line / Horizontal Line).
  - The wiki gives about 40 of the 96 Medaforce names (Weight Bomb, Hold On Me, Justice Man…).
  - The other ~56 are my own transliterations and are marked as such. The tentative ones are puns: ミンナーウィルス, フッカーツ, ジ・バク, イエーン/サバクン/カイチュン, オシボール.

## Caveats

- **Short action labels:** the ROM list at 22:7C69 (オペレート, ボイド, インポス, リアボイド…) has my own translations. A few of the mappings to the wiki's long action names are guesses and are marked "?".
- **Items and generic opponent labels** are my own translations, apart from those that also exist in M1/M3 (Wings of Wind, Mini-Handle, Periscope, RoboRobo Medal, Name Tag, Transceiver, Town Map).
