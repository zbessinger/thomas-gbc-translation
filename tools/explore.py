"""Drive the game into a stage or minigame and capture a contact sheet of what appears.
usage: python tools/explore.py ROM {stage|mini} N OUT_DIR [frames] [buttons]
Everything is unlocked by setting WRAM $CBF3-$CC3F after the title."""
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emu import boot, press, run, shot
from montage import montage

GRID = {1: [], 2: ["right"], 3: ["down"], 4: ["down", "right"]}


def enter(pb, kind, n):
    run(pb, 300)
    press(pb, "start", after=90)
    for a in range(0xCBF3, 0xCC40):
        pb.memory[a] = 0xFF
    if kind == "mini":
        press(pb, "down", after=20)
    press(pb, "a", after=200)                 # stage select / minigame menu
    if kind == "stage" and n == 5:
        press(pb, "right", after=60); press(pb, "right", after=90)
    else:
        for k in GRID[n]:
            press(pb, k, after=40)
    press(pb, "a", after=60)


def explore(rom, kind, n, out, frames=6000, every=150, buttons="a"):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    pb = boot(rom)
    enter(pb, kind, n)
    rnd = random.Random(n)
    shots, last = [], None
    for f in range(0, frames, 30):
        b = rnd.choice(buttons.split(","))
        press(pb, b, hold=4, after=26)
        if f % every == 0:
            img = pb.screen.image.convert("RGB")
            sig = img.resize((20, 18)).tobytes()
            if sig != last:                       # skip near-identical consecutive frames
                p = out / f"{len(shots):03d}.png"; img.resize((320, 288)).save(p); shots.append(str(p)); last = sig
    pb.stop(save=False)
    for i in range(0, len(shots), 16):
        montage(shots[i:i + 16], str(out / f"sheet{i // 16}.png"))
    print(f"{len(shots)} shots -> {out}/sheet*.png")


if __name__ == "__main__":
    a = sys.argv
    explore(a[1], a[2], int(a[3]), a[4], int(a[5]) if len(a) > 5 else 6000, buttons=a[6] if len(a) > 6 else "a")
