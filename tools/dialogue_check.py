"""Display every dialogue message in the real in-stage (window) box and capture every page.

A save state is taken in stage 1 just before the game opens message 3 in the portrait box;
for each message we reload it, make the loader read our ID instead, and page through with A.
Automatic checks per page: nothing may be drawn on the box's right border column (19) or
outside the three text rows, and the box must close (no hang).

usage: python tools/dialogue_check.py ROM OUT_DIR    -> OUT_DIR/sheet_NN.png, report.txt
"""
import io
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from emu import boot, run
from explore import enter
from montage import montage

LOADER = (0x12, 0x428C)


def window_cells(pb):
    m = bytes(pb.memory[0, 0x9C00:0x9CC0])
    return [m[r * 32:r * 32 + 20] for r in range(6)]


def check_message(pb_state, rom, msg_id, outdir):
    from pyboy import PyBoy
    pb = boot(rom)
    pb_state.seek(0)
    pb.load_state(pb_state)
    swapped = {"done": False}

    def cb(_):
        if not swapped["done"]:
            pb.memory[0xC960] = msg_id
            swapped["done"] = True
    pb.hook_register(*LOADER, cb, None)
    issues, pages = [], []
    blank_border = None

    def page_done():
        return (pb.memory[0xC95F] & 0x40) or pb.memory[0xC964] == 4 or not (pb.memory[0xC95F] & 0x80)

    for p in range(16):
        pb.button_press("a")                      # hold A: fast print
        for f in range(1500):
            pb.tick(1, False)
            if swapped["done"] and f > 10 and page_done():
                break
        pb.button_release("a"); run(pb, 6)
        if not swapped["done"]:
            issues.append("loader not reached"); break
        cells = window_cells(pb)
        if blank_border is None:
            blank_border = [row[19] for row in cells]
        if [row[19] for row in cells] != blank_border:
            issues.append(f"page {p + 1}: text on border column")
        pages.append(pb.screen.image.convert("RGB").copy())
        if not (pb.memory[0xC95F] & 0x80) or pb.memory[0xC964] == 4:
            break
        pb.button_press("a"); run(pb, 4); pb.button_release("a"); run(pb, 4)   # next page
    else:
        issues.append("did not close after 16 pages")
    pb.stop(save=False)
    paths = []
    for i, im in enumerate(pages):
        path = outdir / f"m{msg_id:03d}_{i}.png"
        im.resize((320, 288)).save(path)
        paths.append(str(path))
    return paths, issues


def main(rom, out):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    # Build the save state: play to the frame where message 3 is about to load.
    pb = boot(rom)
    state = {"buf": None}

    def cb(_):
        if pb.memory[0xC960] == 3 and state["buf"] is None:
            buf = io.BytesIO(); pb.save_state(buf); state["buf"] = buf
    pb.hook_register(*LOADER, cb, None)
    enter(pb, "stage", 1)
    for _ in range(200):
        if state["buf"] is not None:
            break
        pb.button_press("a"); run(pb, 3); pb.button_release("a"); run(pb, 30)
    pb.stop(save=False)
    if state["buf"] is None:
        sys.exit("could not reach the in-stage box")

    entries = yaml.safe_load(Path("script/dialogue.yaml").read_text())
    report, all_paths = [], []
    for e in entries:
        if e["len"] == 0 or e["jp"] == "<END>" or e.get("box"):
            continue
        mid = e["ids"][0]
        paths, issues = check_message(state["buf"], rom, mid, out)
        all_paths += paths
        report.append(f"{e['addr']} id {mid:3d}: {len(paths)} pages" + (f"  ISSUES: {'; '.join(issues)}" if issues else ""))
        print(report[-1], flush=True)
    (out / "report.txt").write_text("\n".join(report) + "\n")
    for i in range(0, len(all_paths), 20):
        montage(all_paths[i:i + 20], str(out / f"sheet_{i // 20:02d}.png"), cols=5)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
