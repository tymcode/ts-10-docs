---
name: effect-algorithm-columns
description: >-
  Repair and check Pg, Sl, Mi, and Off in TS-10 effect algorithm sheets.
  Use when editing midi-specification/06-effects.html algorithm tables,
  fixing OCR in the first columns, or applying the effect-parameter
  page/slot/multi-index rules.
---

# Effect algorithm column rules

Apply these rules to each `table.sysex.sheets` inside `div#algorithm-NN` in `midi-specification/06-effects.html`. Columns, in order: **Pg**, **Sl**, **Mi**, **Off**, Type, Label, Internal, Size, Displayed.

Algorithms **00–05** are the reference. **04** and **05** already satisfied the rules before the repair pass. Do not invent a different layout when a reference algorithm shows the same label sequence.

## Ruleset

The first column is always two digits and increases from row to row within each algorithm table
The second column is always two digits and ranges from 00 to 05. it is always increments until the value in the first column increments.
The second column repeats itself when there are values in the third column
The third column, if it has numbers, is always either 00 or 01. Those numbers appear in sequential row pairs and start at 00.
The fourth column is always sorted ascending within the algorithm table. Though I have found those to be reliable from the OCR. (I don't understand why those were so reliable when the first two column were so terrible out of the OCR.)
The first six algorithms have been corrected and can be used for reference.

## How to apply them

Write **Pg** and **Sl** as two digits (`36`, `02`). **Mi** is `--`, `00`, or `01`.

- **Pg** stays the same or increases. It never goes backwards. Legal pages are 36–45. Several rows may share a page. Pages may be skipped.
- **Sl** is 00–05. On one page it strictly increases, except when **Mi** is a pair: those two rows share one slot.
- A new page restarts the slot sequence. The new page does not have to start at 00. Slots may be skipped when the source value is a legal two-digit slot.
- **Mi** numbers occur only as a consecutive pair `00` then `01` on the same Pg and Sl. Anything else in that column is `--`.
- Treat dotted or spaced label pairs as one slot: `DIFFUSION .1` / `.2`, `ENVELOPE LEVEL .1` / `.2`, then `.3` / `.4`, and so on. Pair from the odd number. A leftover such as `.9` is `--` on the next slot. Do not pair hyphenated names such as `DELAY-1` or `DIFFUSION-1` unless they already form a `00`/`01` pair.
- Keep a Pg or Sl that is already a legal two-digit value and does not break the sequence. If it collides or is garbage, move it to the nearest legal value. Use the reference patterns below only to fill a missing value or to break a tie.
- Do not edit **Off**, and do not reorder rows to force Off into ascending order. In algorithms 04 and 05, Off is not monotonic (page 38 is `001`, `003`, `002`, `004`) because the sheet is in page/slot order. Trust the offset digits; repair Pg, Sl, and Mi around them.

## Reference patterns

From algorithms 04 and 05, when the same labels appear in the same order:

| Labels | Pg | Sl | Mi |
| --- | --- | --- | --- |
| EFFECT | 36 | 02 | `--` |
| VAR | 36 | 05 | `--` |
| SENDS A--B, B--REVRB, A--REVRB, FX2--REVRB, DRY | 38 | 01, 02, 03, 04, 05 | `--` |
| DEFINITION, then DIFFUSION .1 / .2 | 44 | 04, then 05 | `--`, then `00`/`01` |
| MOD SRC, DEST, MIN, MAX | 45 | 00, 02, 03, 05 | `--` |

`MOD-1 SRC` and `MOD-2 SRC` use that same slot pattern when the slot cell is missing. A legal slot that is not one of those values stays. Adjacent `FX-1 …` / `FX-2 …` rows are slots 02 and 05 on the same page when the slot cell is missing.

## Check

After an edit, every data row in the algorithm (skip `td.row-note`) must satisfy:

- Pg matches `36`–`45`, Sl matches `00`–`05`, Mi is `--`, `00`, or `01`
- Pg is non-decreasing
- On the same page, Sl increases, unless this row is Mi `01` and the previous row is Mi `00` with the same Sl
- Mi `00` is immediately followed by Mi `01` on that same slot; Mi `01` does not appear alone
