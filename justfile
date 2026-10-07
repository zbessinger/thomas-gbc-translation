# Kikansha Thomas – Sodor-tou no Nakama-tachi (GBC) English translation

rom := "rom/thomas-jp.gbc"
out := "out/thomas-en.gbc"
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

# build the English ROM and fix its checksums
build:
    uv run python tools/insert_text.py --rom {{rom}} --out {{out}}
    rgbfix -v {{out}}

# create IPS + BPS patches against the clean ROM
patch: build
    {{flips}} --create --ips {{rom}} {{out}} out/thomas-en.ips
    {{flips}} --create --bps {{rom}} {{out}} out/thomas-en.bps

# round-trip the JP script and confirm both patches reproduce the built ROM
verify: patch
    uv run python tools/verify.py
