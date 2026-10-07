"""Set English text for messages: python tools/set_en.py edits.yaml  (mapping addr -> text)."""
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from dump_text import FlowList, _Dumper

SCRIPT = Path("script/dialogue.yaml")


def save(entries, path=SCRIPT):
    for e in entries:
        e["ids"] = FlowList(e["ids"])
    path.write_text(yaml.dump(entries, Dumper=_Dumper, allow_unicode=True, sort_keys=False,
                              width=1000, default_flow_style=False))


if __name__ == "__main__":
    edits = yaml.safe_load(Path(sys.argv[1]).read_text())
    entries = yaml.safe_load(SCRIPT.read_text())
    by_addr = {e["addr"]: e for e in entries}
    for addr, text in edits.items():
        by_addr[addr]["en"] = text
    save(entries)
    print(f"updated {len(edits)} messages")
