"""Headless PyBoy helpers for driving the game and capturing screens/VRAM."""
from pyboy import PyBoy

ROM = "rom/thomas-jp.gbc"

def boot(rom=ROM):
    return PyBoy(rom, window="null", cgb=True, sound_emulated=False)

def run(pb, frames):
    for _ in range(frames):
        pb.tick(1, False)
    pb.tick(1, True)

def press(pb, button, hold=4, after=20):
    pb.button_press(button)
    run(pb, hold)
    pb.button_release(button)
    run(pb, after)

def shot(pb, path, scale=2):
    img = pb.screen.image.convert("RGB")
    img.resize((img.width * scale, img.height * scale)).save(path)
