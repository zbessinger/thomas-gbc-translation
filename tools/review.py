"""Write script/review.md: Japanese next to the UK/US English, wrapped exactly as the game
will show it ('/' = line break, '▼' = new text box)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from insert_text import BOXES, resolve, wrap


def layout(text, entry):
    box = BOXES[entry.get("box", "dialogue")]
    if entry.get("raw"):
        pages = [text.split("\n")]
    else:
        pages = wrap(text, entry.get("widths", box["widths"]))
    return " ▼ ".join(" / ".join(p) for p in pages)


def main():
    entries = yaml.safe_load(Path("script/dialogue.yaml").read_text())
    glossary = yaml.safe_load(Path("script/glossary.yaml").read_text())
    rows = ["# Translation review\n",
            "`/` = line break, `▼` = next text box. Edit `en` in `script/dialogue.yaml` (or a draft file).\n",
            "| Addr | Box | Japanese | English (UK) | English (US, if different) |",
            "|---|---|---|---|---|"]
    for e in entries:
        if not e["len"] or e["jp"] == "<END>":
            continue
        en = (e.get("en") or "").strip()
        uk = layout(resolve(en, "uk", glossary), e) if en else "—"
        us = layout(resolve(en, "us", glossary), e) if en else "—"
        jp = e["jp"].replace("<NL>", " / ").replace("<PAGE>", " ▼ ").replace("<END>", "")
        cell = lambda s: s.replace("|", "\\|")
        rows.append(f"| `{e['addr']}` | {e.get('box', 'dialogue')} | {cell(jp)} | {cell(uk)} | {cell(us) if us != uk else ''} |")
    Path("script/review.md").write_text("\n".join(rows) + "\n")
    print("wrote script/review.md")


if __name__ == "__main__":
    main()
