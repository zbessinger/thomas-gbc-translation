"""Play a story stage automatically: advance dialogue, hold right, and brute-force the
track-repair puzzles from save states. Stops when a banner (>= 7 sprites in a row) appears.
usage: python tools/stagebot.py ROM STAGE OUT_DIR [max_frames]"""
import io
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from emu import boot, press, run, shot
from explore import enter

ORANGE_Y = 140                      # carousel bar row (puzzle UI)


def puzzle_active(pb):
    img = pb.screen.image.convert("RGB")
    r, g, b = img.getpixel((2, ORANGE_Y))
    return r > 200 and 80 < g < 200 and b < 80 and not (pb.memory[0xC95F] & 0x80)


def banner(pb):
    o = bytes(pb.memory[0xFE00:0xFEA0])
    rows = Counter(o[4 * k] for k in range(40) if 0 < o[4 * k] < 160)
    best = rows.most_common(1)
    return best[0] if best and best[0][1] >= 7 else None


def solve_puzzle(pb, rom):
    s0 = io.BytesIO(); pb.save_state(s0)
    for moves in (["left"], [], ["right"], ["left", "left"], ["right", "right"], ["left"] * 3,
                  ["right"] * 3, ["left"] * 4, ["right"] * 4, ["left"] * 5, ["right"] * 5):
        s0.seek(0); pb.load_state(s0)
        for m in moves:
            press(pb, m, hold=4, after=20)
        press(pb, "a", hold=4, after=150)
        if not puzzle_active(pb):
            return moves
    s0.seek(0); pb.load_state(s0)
    return None


def play(rom, stage, out, max_frames=60000):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    pb = boot(rom)
    enter(pb, "stage", stage)
    frames, log = 0, []
    dirs, d, still, last = ["right", "up", "down", "left"], 0, 0, None
    while frames < max_frames:
        if pb.memory[0xC95F] & 0x80:
            press(pb, "a", hold=4, after=26)
        elif puzzle_active(pb):
            log.append(("puzzle", frames, solve_puzzle(pb, rom)))
        else:
            pb.button_press(dirs[d]); pb.tick(29, False); pb.tick(1, True); pb.button_release(dirs[d])
            # steer: if the scenery stops moving, try the next direction
            sig = pb.screen.image.convert("L").crop((0, 0, 160, 40)).resize((16, 4)).tobytes()
            still = still + 1 if sig == last else 0
            last = sig
            if still >= 4:
                d, still = (d + 1) % len(dirs), 0
        frames += 30
        b = banner(pb)
        if b:
            run(pb, 10)
            shot(pb, str(out / "banner.png"), scale=3)
            st = io.BytesIO(); pb.save_state(st); (out / "banner.state").write_bytes(st.getvalue())
            log.append(("banner", frames, b))
            break
        if frames % 3000 == 0:
            shot(pb, str(out / f"f{frames:06d}.png"))
    pb.stop(save=False)
    return log


if __name__ == "__main__":
    a = sys.argv
    for entry in play(a[1], int(a[2]), a[3], int(a[4]) if len(a) > 4 else 60000):
        print(entry)
