"""Write a battery save (.srm, 8 KiB) with every stage, minigame and encyclopedia entry
unlocked, for quick testing in any emulator (RetroArch, mGBA, SameBoy...).

Save format (from $00:213E / $00:227C): WRAM $CBEB-$CC11 (8-byte signature copied from ROM
0x2119, then progress flags from $CBF3) + 16-bit checksum at $CC12 = ~(sum of the 39 bytes).
The 41-byte block is stored twice in SRAM, at $A020 and $A120.

usage: python tools/make_save.py ROM OUT.srm"""
import sys
from pathlib import Path


def make_save(rom):
    block = bytearray(rom[0x2119:0x2121]) + bytearray([0xFF] * (0x27 - 8))   # $CBEB-$CC11
    s = sum(block) & 0xFFFF
    chk = (~s) & 0xFFFF
    block += bytes([chk & 0xFF, chk >> 8])
    sram = bytearray(0x2000)
    sram[0x20:0x20 + len(block)] = block
    sram[0x120:0x120 + len(block)] = block
    return bytes(sram)


if __name__ == "__main__":
    Path(sys.argv[2]).write_bytes(make_save(Path(sys.argv[1]).read_bytes()))
    print("wrote", sys.argv[2])
