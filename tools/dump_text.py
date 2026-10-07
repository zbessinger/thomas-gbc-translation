"""Dump the bank-18 dialogue script (pointer table at 0x49850) to script/dialogue.yaml."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from tbl import decode

BANK = 0x12
BANK_BASE = BANK * 0x4000
PTR_TABLE = 0x49850
PTR_COUNT = 256


def gb_to_rom(addr):
    return BANK_BASE + addr - 0x4000


def read_pointers(rom):
    return [rom[PTR_TABLE + 2 * i] | rom[PTR_TABLE + 2 * i + 1] << 8 for i in range(PTR_COUNT)]


def dump(rom):
    ptrs = read_pointers(rom)
    entries = {}
    for msg_id, addr in enumerate(ptrs):
        if addr not in entries:
            off = gb_to_rom(addr)
            text, end = decode(rom, off)
            entries[addr] = {"addr": f"0x{addr:04X}", "rom": f"0x{off:05X}", "len": end - off,
                             "ids": FlowList(), "jp": text, "en": ""}
        entries[addr]["ids"].append(msg_id)
    return sorted(entries.values(), key=lambda e: e["addr"])


class _Dumper(yaml.SafeDumper):
    pass


class FlowList(list):
    pass


_Dumper.add_representer(FlowList, lambda d, v: d.represent_sequence("tag:yaml.org,2002:seq", v, flow_style=True))

if __name__ == "__main__":
    rom = Path(sys.argv[1] if len(sys.argv) > 1 else "rom/thomas-jp.gbc").read_bytes()
    out = Path(sys.argv[2] if len(sys.argv) > 2 else "script/dialogue.yaml")
    entries = dump(rom)
    if out.exists():  # keep translations and per-message layout overrides
        old = {e["addr"]: e for e in yaml.safe_load(out.read_text()) or []}
        for e in entries:
            for key in ("en", "widths", "notes"):
                if key in old.get(e["addr"], {}):
                    e[key] = old[e["addr"]][key]
    out.write_text(yaml.dump(entries, Dumper=_Dumper, allow_unicode=True, sort_keys=False, width=1000, default_flow_style=False))
    print(f"{len(entries)} unique messages, {sum(e['len'] for e in entries)} bytes -> {out}")
