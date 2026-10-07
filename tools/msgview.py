"""Show any dialogue message in the real in-stage (window) box or cutscene box and capture
every page. The game is driven to its first message of that box type (stage 1: message 3 in
the window box, message 1 in the cutscene box) and the loader ($12:428C) is made to read
our message ID instead.

usage: python tools/msgview.py ROM OUT_DIR {stage|cutscene} ID [ID ...]   (IDs or 'all')
"""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from emu import boot, run
from explore import enter

LOADER = (0x12, 0x428C)
TRIGGER = {"stage": 3, "cutscene": 1}


def tap(pb, frames=40):
    pb.button_press("a"); run(pb, 4); pb.button_release("a"); run(pb, frames)


def view(rom, out, box, msg_id, max_pages=12):
    pb = boot(rom)
    state = {"swapped": False, "done": False}

    def cb(_):
        if not state["swapped"] and pb.memory[0xC960] == TRIGGER[box]:
            pb.memory[0xC960] = msg_id
            state["swapped"] = True
    pb.hook_register(*LOADER, cb, None)
    enter(pb, "stage", 1)
    for _ in range(80):
        if state["swapped"]:
            break
        tap(pb)
    pages = []
    if state["swapped"]:
        for p in range(max_pages):
            pb.button_press("a"); run(pb, 160); pb.button_release("a"); run(pb, 20)  # fast-print
            img = pb.screen.image.convert("RGB")
            if pages and img.tobytes() == pages[-1].tobytes():
                break
            pages.append(img.copy())
            if not (pb.memory[0xC95F] & 0x80):     # message box closed
                break
            tap(pb, 20)
    pb.stop(save=False)
    paths = []
    for i, im in enumerate(pages):
        p = Path(out) / f"{box}_{msg_id:03d}_{i}.png"
        im.resize((320, 288)).save(p); paths.append(str(p))
    return paths


if __name__ == "__main__":
    rom, out, box = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    out.mkdir(parents=True, exist_ok=True)
    ids = sys.argv[4:]
    if ids == ["all"]:
        ids = sorted({e["ids"][0] for e in yaml.safe_load(Path("script/dialogue.yaml").read_text())
                      if e["len"] and e["jp"] != "<END>"})
    for i in map(int, ids):
        print(i, len(view(rom, out, box, i)), "pages")
