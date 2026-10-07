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

## Graphics with Japanese text (to redraw)
- Title screen logo + "ボタンをおしてね!" (press a button).
- Main menu: なにをプレイしますか? / おはなしのつづき / おはなしをはじめる /
  ミニゲームであそぶ / トーマスずかん.
- Minigame menu banner: ステージクリアでミニゲームがふえるよ.
- Encyclopedia: header plate "トーマスずかん", per-character name plates, "Nページ".
- Not yet located in ROM; several high-entropy banks (8, 16, 17, 20, 25, 28) look
  compressed.
