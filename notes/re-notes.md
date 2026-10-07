# Reverse-engineering notes

ROM: `Kikansha Thomas - Sodor-tou no Nakama-tachi (Japan).gbc`, 1 MiB, SHA-1
`8abd4406ec19bfecd6d675285fa73ef2d5ea622e`, MBC5+RAM+battery, CGB-only (`$0143=$C0`).
Free banks (all `$FF`): 9–13, 21, 32–63.

## Text encoding (`tools/tbl.py`)
| Code | Meaning |
|---|---|
| `00` | space |
| `01–0A` | 0–9 |
| `0B–38` | hiragana あ…ん (plain gojūon order, no voiced forms) |
| `39–41` | ぁぃぅぇぉゃゅょっ |
| `42–6F` | katakana ア…ン |
| `70–78` | ァィゥェォャュョッ |
| `79` / `7A` | ゜ / ゛ — stored **before** the kana; drawn one row above, cursor not advanced |
| `7B–83` | 、。!「」ー♪?・ |
| `84+` | box-border graphics (not used by text) |
| `FF 00` | newline (cursor = line start, +2 tile rows) |
| `FF 01` | wait for button + clear box (page) |
| `FF 02` | end of message |

## Dialogue script (bank `$12`)
- Pointer table `$12:5850` (ROM `0x49850`), 256 × LE16 → message IDs 0–255. 153 unique
  targets; IDs 253–255 point at empty fill. Only reference: `ld de,$5850` at `$12:429C`.
- Text block ROM `0x49A50–0x4B371` (6434 B); bank is free from `0x4B372` to `0x4BFFF`.
  Repack budget = 9648 B.
- Message ID is read from `$C960`; current text pointer kept in `$C966/7`.

## Per-message font loader (`$12:428C`)
1. Clear 256 "used" flags at `$C96D`.
2. Scan the message to `FF 02`, flagging every byte value (FF args skipped).
3. For each used code (ascending), copy its 2bpp glyph from `$18:5F20 + code*16`
   (ROM `0x61F20`) into WRAM2 `$D000+`, then DMA to VRAM `$8A70` (tile `$A7`…).
4. Rewrite flags into a code→tile map (`$A7`, `$A8`, …). **More than 89 distinct codes
   in one message hangs the game** (`jr @` at `$12:4315`).
=> Any glyph set works as long as each message uses ≤ 89 distinct codes. No code change
   is needed for a fixed-width English font.

## Printer (`$12:4425…`)
- One char every 10 frames (2 if A held). Writes mapped tile to the shadow tilemap
  (`$C968/9` = cursor), attribute plane at +`$400`. No width check / no auto-wrap.
- Main dialogue box: text starts at screen column 2; 3 lines at rows 1/3/5.
  The ▼ "next" sprite covers columns 17–18 of the last row → widths 17/17/15.
- A second copy of the printer exists in bank `$12` (~line 5276 of the mgbdis output),
  probably for the encyclopedia box.

## Compressed graphics (`tools/lz.py`, `tools/screen.py`)
- LZSS decoder at `$00:18A4`. Stream = `u16 decoded_size, u16 n` + n bytes. Flag bytes LSB
  first: 1 = literal, 0 = 2-byte ref `lo, hi`: length `(hi&0F)+3`, distance
  `((hi>>4)<<8|lo)+1`. Decodes straight to VRAM/WRAM. 166 streams in the ROM
  (`notes/lz_streams.tsv`); our greedy encoder matches the original sizes (100%).
- Screen asset lists live in bank 0 around `0x1340–0x1420`: 6-byte entries
  `ptr16, rom_bank, vram_dest16, vram_bank`, `FF FF FF`-terminated. Repointing an asset is
  just rewriting its entry; new streams go into free banks 9–13 (`tools/build_gfx.py`).
  - Title list `0x1360` (bank `$13`): tiles→`$9000` vb0/vb1, attrs, map.
  - Main menu list `0x13F3` (bank `$1C`); minigame menu `0x139F` (bank `$1E`);
    encyclopedia `0x1384` (bank `$04`).
- Screens are LCDC `$E7` (signed tile addressing). Retiler keeps unchanged cells' map
  entries exactly (palettes repeat colours, so indices can't be re-derived from RGB) and
  only allocates tiles freed by edited cells. Each 8×8 cell must fit one BG palette.
- Main-menu highlight: menu code (bank 2) rewrites item cells from tables at `$02:4431`
  (positions), `$4439`/`$44A9` (normal tiles/attrs), `$4521`/`$4591` (selected),
  4 items × 2 rows × 14 cells; handled by `tools/menu_items.py`.

## Code-drawn graphics (bank 2 / 4 / 5 tables)
- Minigame menu (`0x139F`): "clear stages" banner = 20 OBJ sprites (8x16, 10x2), tiles
  `$02–$29` of the `$1E:4000` sprite stream, OBJ palette 1 (`tools/minigame_banner.py`).
  Card titles: `$02:513B` positions, `$5143` tiles, `$51A3` attrs (4 × 8×3, both VRAM banks).
- Stage select (`0x13C0`): labels `$02:4D25`/`$4D2D`/`$4D8D`; labels 2–4 shown when
  WRAM `$CBF3` ≠ 0. Page 2 (Stage 5) is the `$9C00` tilemap of the same list.
- Encyclopedia (`0x1384`): intro header = tiles `$41–$5D` of the bank-1 stream, layout
  `0x10509`, attrs `0x104E5`. Name plates: bank 5 pointer table (27) → raw tiles, loader
  copies `$200` bytes to tile `$41`+; layouts `0x128F7`, attrs `0x12C21` (27 × 30).
  "ページ" = tiles `$2C–$33` (bank 1). 26 real entries + "???".
- Test unlocks: after the title, set WRAM `$CBF3–$CC3F` to `$FF` (all stages, minigames
  and encyclopedia entries).

## Graphics status
- Done: title, main menu, minigame menu (banner + titles), stage select (both pages),
  encyclopedia (header, 26 plates, page bar).
- To do: inside the minigames and story stages (signs, HUD text, results screens).
