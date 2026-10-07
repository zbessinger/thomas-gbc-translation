"""Scripted playthrough of the menus/opening for a ROM; writes a labelled contact sheet.
usage: python tools/playtest.py ROM OUT_DIR"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emu import boot, press, run, shot
from montage import montage


def tap_a(pb, hold=200):
    """Hold A (fast text), release, settle."""
    pb.button_press("a"); run(pb, hold); pb.button_release("a"); run(pb, 30)


def main(rom, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    shots = []

    def snap(pb, name):
        p = out / f"{len(shots):02d}_{name}.png"; shot(pb, p); shots.append(str(p))

    # 1. "Continue" with no save -> system message
    pb = boot(rom); run(pb, 300); snap(pb, "title")
    press(pb, "start", after=90); snap(pb, "menu")
    press(pb, "up", after=20); press(pb, "a", after=200); snap(pb, "no_save")
    pb.stop(save=False)

    # 2. Encyclopedia intro + locked entry
    pb = boot(rom); run(pb, 300); press(pb, "start", after=90)
    press(pb, "down", after=20); press(pb, "down", after=20)
    tap_a(pb, 300); snap(pb, "book_intro")
    tap_a(pb, 300); snap(pb, "book_locked")
    pb.stop(save=False)

    # 3. Opening story
    pb = boot(rom); run(pb, 300); press(pb, "start", after=90); press(pb, "a", after=90)
    for i in range(12):
        tap_a(pb); snap(pb, f"story{i}")
    pb.stop(save=False)

    montage(shots, str(out / "sheet.png"))
    print(out / "sheet.png")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
