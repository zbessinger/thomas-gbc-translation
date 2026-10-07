# Thomas the Tank Engine: Friends of Sodor — English translation

Fan translation of *Kikansha Thomas – Sodor-tou no Nakama-tachi* (Tamasoft, 2001, Game Boy Color).

## Requirements
- Clean ROM: `Kikansha Thomas - Sodor-tou no Nakama-tachi (Japan).gbc`
  (SHA-1 `8abd4406ec19bfecd6d675285fa73ef2d5ea622e`, CRC32 `223bb19c`), copied to `rom/thomas-jp.gbc`.
- `uv`, `just`, `rgbds` (`brew install rgbds`), a C++ compiler (for Flips).

## Usage
```sh
just setup     # fetch/build Flips + mgbdis, install Python deps
just check     # validate the English script (line widths, glyph limits, space budget)
just build     # out/thomas-en.gbc
just patch     # out/thomas-en.ips + out/thomas-en.bps
just verify    # JP round-trip + patches reproduce the built ROM
```

## Layout
- `script/dialogue.yaml` — every message: Japanese (`jp`) and English (`en`). English is plain
  prose; the build word-wraps it. `\n` forces a line break, `<PAGE>` a new text box.
- `gfx/font_en.txt` — editable 8×8 English font.
- `tools/` — table, dumper, inserter, emulator helpers. `notes/re-notes.md` — ROM internals.

Distribute the patch files only, never the ROM.
