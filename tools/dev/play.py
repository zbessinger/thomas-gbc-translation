"""DEV ONLY - quick-test launcher. Not part of the translation build or the patches.
Safe to delete: remove tools/dev/ and the "DEV ONLY" section at the end of the justfile.

Opens the freshly built ROM in a PyBoy window and drives it, at full speed, to a scene
that is slow to reach by hand, then hands control to you. Scenes are replayed from boot
every time (no stored save states), so they always show the current build.

usage: python tools/dev/play.py SCENE [uk|us]      (or: just play SCENE [dub])
       python tools/dev/play.py --list

Keys (PyBoy window): arrows = d-pad, A = a, S = b, Enter = start, Backspace = select,
Space = fast-forward (hold), Esc = quit.
"""
import io
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
from pyboy import PyBoy  # noqa: E402

from make_save import make_save  # noqa: E402


def tap(pb, button, hold=4, after=30):
    pb.button_press(button)
    pb.tick(hold, True)
    pb.button_release(button)
    pb.tick(after, True)


# ---------------------------------------------------------------- scenes

def stage_clear(pb):
    """Story stage 1 (Farm) right before the STAGE CLEAR! banner.
    The game's own stage-clear routine ($00:1FBE) is triggered once the stage is running:
    the per-frame stage-end check ($00:1FF2) is redirected to it for a single frame."""
    pb.tick(300, True)
    tap(pb, "start", after=90)          # title -> menu (cursor starts on Continue with a save)
    tap(pb, "a", after=200)             # Continue -> stage select
    tap(pb, "a", after=60)              # Stage 1
    state = {"armed": False, "fired": False, "quiet": 0}

    def trigger(_):
        # count stage frames with no text box open
        state["quiet"] = 0 if pb.memory[0xC95F] & 0x80 else state["quiet"] + 1
        if state["armed"] and not state["fired"] and state["quiet"] > 60:
            state["fired"] = True
            pb.register_file.PC = 0x1FBE
    pb.hook_register(0, 0x1FF2, trigger, None)
    for _ in range(300):                # skip the opening dialogue until the stage is running
        if state["quiet"] >= 30:
            break
        tap(pb, "a", after=30)
    return lambda: state.update(armed=True, quiet=0)    # fire ~1 s after you take over


SCENES = {
    "stage-clear": stage_clear,
}


def main():
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help", "--list"):
        print(__doc__)
        print("scenes:", ", ".join(SCENES))
        return
    scene, dub = args[0], (args[1] if len(args) > 1 else "us")
    if scene not in SCENES:
        sys.exit(f"unknown scene {scene!r}; choose from: {', '.join(SCENES)}")
    rom = ROOT / f"out/thomas-en-{dub}.gbc"
    if not rom.exists():
        sys.exit(f"{rom} not found - run `just build` first")
    save = io.BytesIO(make_save(rom.read_bytes()))      # all-unlocked, in memory only
    pb = PyBoy(str(rom), window="SDL2", scale=4, cgb=True, ram_file=save)
    pb.set_emulation_speed(0)                           # race to the scene
    start = SCENES[scene](pb)
    pb.set_emulation_speed(1)                           # then normal speed for you
    if start:
        start()
    while pb.tick():
        pass
    pb.stop(save=False)


if __name__ == "__main__":
    main()
