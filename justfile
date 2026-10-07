# Kikansha Thomas – Sodor-tou no Nakama-tachi (GBC) English translation

rom := "rom/thomas-jp.gbc"
dubs := "uk us"
flips := "vendor/flips/flips"

# list recipes
default:
    @just --list

# one-time: fetch + build Flips (patcher) and mgbdis (disassembler) into vendor/
setup:
    test -d vendor/flips || git clone --depth 1 https://github.com/Alcaro/Flips vendor/flips
    test -x {{flips}} || (cd vendor/flips && make TARGET=cli)
    test -d vendor/mgbdis || git clone --depth 1 https://github.com/mattcurrie/mgbdis vendor/mgbdis
    uv sync

# re-dump the Japanese script (keeps existing en/widths/notes fields)
dump:
    uv run python tools/dump_text.py {{rom}} script/dialogue.yaml

# validate the English script without writing a ROM
check:
    uv run python tools/insert_text.py --check

# regenerate edited screen art (gfx/screens/*/make.py -> screen.png, items.png)
gfx:
    for f in gfx/screens/*/make.py; do uv run python $f; done

# build out/thomas-en-uk.gbc and out/thomas-en-us.gbc and fix their checksums
build:
    uv run python tools/insert_text.py --rom {{rom}} --out "out/thomas-en-{dub}.gbc"
    for d in {{dubs}}; do rgbfix -v -Wno-overwrite out/thomas-en-$d.gbc; done

# create IPS + BPS patches (one pair per dub) against the clean ROM
patch: build
    for d in {{dubs}}; do {{flips}} --create --ips {{rom}} out/thomas-en-$d.gbc out/thomas-en-$d.ips; {{flips}} --create --bps {{rom}} out/thomas-en-$d.gbc out/thomas-en-$d.bps; done

# round-trip the JP script and confirm every patch reproduces its built ROM
verify: patch
    uv run python tools/verify.py {{dubs}}

# side-by-side JP / UK / US review sheet (script/review.md)
review:
    uv run python tools/review.py
