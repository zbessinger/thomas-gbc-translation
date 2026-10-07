"""Sanity checks: (1) the JP script round-trips byte-exactly through the table/encoder,
(2) the IPS and BPS patches applied to the clean ROM reproduce the built ROM exactly."""
import hashlib
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from tbl import encode

FLIPS = "vendor/flips/flips"


def sha1(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def roundtrip(rom_path, script_path):
    rom = Path(rom_path).read_bytes()
    bad = [e["addr"] for e in yaml.safe_load(Path(script_path).read_text())
           if encode(e["jp"]) != rom[int(e["rom"], 16):int(e["rom"], 16) + e["len"]]]
    print(f"round-trip: {'OK' if not bad else 'FAIL ' + ', '.join(bad)}")
    return not bad


def patches(clean, built, ips, bps):
    ok = True
    want = sha1(built)
    with tempfile.TemporaryDirectory() as td:
        for patch in (ips, bps):
            out = Path(td) / "applied.gbc"
            subprocess.run([FLIPS, "--apply", patch, clean, str(out)], check=True, capture_output=True)
            got = sha1(out)
            print(f"{Path(patch).name}: {'OK' if got == want else 'FAIL'} ({got})")
            ok &= got == want
    return ok


if __name__ == "__main__":
    ok = roundtrip("rom/thomas-jp.gbc", "script/dialogue.yaml")
    for dub in sys.argv[1:] or ["uk", "us"]:
        base = f"out/thomas-en-{dub}"
        ok &= patches("rom/thomas-jp.gbc", f"{base}.gbc", f"{base}.ips", f"{base}.bps")
    sys.exit(0 if ok else 1)
