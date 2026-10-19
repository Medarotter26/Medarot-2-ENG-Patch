# Strings inserted from RAM (`<&XXXX>`)

| Code | Contents (inferred from context) | Max length |
|---|---|---|
| `<&CB26>` | Player's name (Ikki by default; the player can rename him) | 8 |
| `<&B33D>` | Name of the acting Medarot in battle | 8 |
| `<&B346>` | Part name / part type / skill name in battle messages (e.g. "<&B346> attack!", "<&B346> part was destroyed!") | 7 |
| `<&B34F>` | Attack name or a number (damage / healing amount) in battle messages | 5 |
| `<&CD49>` | Part name (losing parts after a robattle) | 8 |
| `<&C50F>` | Part type ("Head", "Right Arm"...) or Medal name | 8 |
| `<&C560>` | Part / list name obtained | 8 |
| `<&C518>` | Medaforce name or skill name | 8 |
| `<&CC9E>` | Name (race winner, part name in link trades) | 8 |
| `<&CCA9>` | Part type | 5 |
| `<&C462>` | Item name | 8 |

Names are English nouns without articles; write sentences so they read naturally with any
value (e.g. "Got the <&C50F> part \"<&C560>\"!" or "<&B33D> used <&B346>!").
