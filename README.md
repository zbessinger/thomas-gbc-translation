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
just build     # out/thomas-en-uk.gbc + out/thomas-en-us.gbc
just patch     # out/thomas-en-{uk,us}.{ips,bps}
just verify    # JP round-trip + every patch reproduces its built ROM
just review    # script/review.md: JP / UK / US side by side, wrapped as in-game
```

## Layout
- `script/dialogue.yaml` — every message: Japanese (`jp`) and English (`en`). English is plain
  prose; the build word-wraps it. `\n` forces a line break, `<PAGE>` a new text box.
- `script/glossary.yaml` — UK/US dub wording (`{fc}` → the Fat Controller / Sir Topham Hatt,
  `{trucks}` → trucks / freight cars …). Inline `{uk|us}` handles one-offs.
- `gfx/font_en.txt` — editable 8×8 English font.
- `gfx/screens/*/make.py`, `gfx/streams/make.py` — generate the English artwork (`just gfx`).
- `tools/dialogue_check.py ROM DIR` — shows every message in the real in-stage box and flags
  overflow; `tools/explore.py` drives stages/minigames and saves contact sheets.
- `tools/` — table, dumper, inserter, emulator helpers. `notes/re-notes.md` — ROM internals.

Distribute the patch files only, never the ROM.
