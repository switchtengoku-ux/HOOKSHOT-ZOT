"""Hookshot Enhanced's option IDs stay apart from upstream's, game-free (gpu/vk/vk_api.h).

Upstream adds option IDs one at a time from the 50s (its main took 59 to 71 after v2.3.1); the fork's start at 1000, so an
upstream merge never gives two options one ID. tests/test_option_ids.py (upstream's) checks that no two IDs are equal;
this one checks the split that keeps it so:
- every HOS_OPT_ENH_* ID is at least 1000, every other HOS_OPT_* ID and every numeric id the option callback answers is
  below it;
- the HUD editor's range (HOS_OPT_ENH_HUD + elements * fields) fits before 1200 and no other Enhanced ID falls in it;
- the option callback answers every Enhanced ID.

python -I -B tests/test_enh_option_ids.py
"""
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parent.parent
BASE = 1000


def enum_values(text):
    """name -> value of every HOS_OPT_ enum constant (literal starts and implicit increments)."""
    text = re.sub(r"/\*.*?\*/|//[^\n]*", "", text, flags=re.S)
    values = {}
    for body in re.findall(r"enum\s*\{([^}]*)\}\s*;", text):
        if "HOS_OPT_" not in body:
            continue
        nxt = 0
        for item in (s.strip() for s in body.split(",")):
            if not item:
                continue
            m = re.fullmatch(r"(\w+)\s*(?:=\s*(\d+))?", item)
            assert m, "vk_api.h: an option enum entry this test cannot read: %r" % item
            nxt = int(m.group(2)) if m.group(2) else nxt
            values[m.group(1)] = nxt
            nxt += 1
    return values


def main():
    api = (ROOT / "gpu" / "vk" / "vk_api.h").read_text(encoding="utf-8")
    values = enum_values(api)
    enh = {n: v for n, v in values.items() if n.startswith("HOS_OPT_ENH_")}
    upstream = {n: v for n, v in values.items() if not n.startswith("HOS_OPT_ENH_")}
    assert len(enh) >= 7 and len(upstream) >= 30, "the option enums were not found"
    low = sorted(n for n, v in enh.items() if v < BASE)
    assert not low, "Enhanced option IDs below %d, where upstream's grow: %s" % (BASE, ", ".join(low))
    high = sorted(n for n, v in upstream.items() if v >= BASE)
    assert not high, "option IDs at or past %d, the Enhanced range: %s" % (BASE, ", ".join(high))
    replay = (ROOT / "gpu" / "vk" / "vk_replay.cpp").read_text(encoding="utf-8")
    callback = replay.split("t.option =", 1)[1].split("};", 1)[0]
    numeric = sorted({int(x) for x in re.findall(r"\bid\s*==\s*(\d+)\b", callback)})
    assert numeric and max(numeric) < BASE, "the option callback answers a numeric id in the Enhanced range"
    # the HUD editor's range
    elements = int(re.search(r"#define HOS_ENH_HUD_ELEMENTS (\d+)", api).group(1))
    hud_h = (ROOT / "gpu" / "vk" / "enh_hud.h").read_text(encoding="utf-8")
    fields = re.search(r"enum \{([^}]*)\bENH_HUD_FIELDS\b", hud_h).group(1).count(",")
    start = enh["HOS_OPT_ENH_HUD"]
    end = start + elements * fields
    assert end <= BASE + 200, "the HUD editor's IDs (%d to %d) run past %d" % (start, end - 1, BASE + 199)
    inside = sorted(n for n, v in enh.items() if start < v < end)
    assert not inside, "Enhanced IDs inside the HUD editor's range: %s" % ", ".join(inside)
    # the callback answers each Enhanced ID
    for name in enh:
        if name == "HOS_OPT_ENH_HUD":
            assert "id >= HOS_OPT_ENH_HUD && id < HOS_OPT_ENH_HUD + HOS_ENH_HUD_ELEMENTS * ENH_HUD_FIELDS" in callback, \
                "the option callback does not answer the HUD editor's range"
        else:
            assert re.search(r"\bid == %s\b" % name, callback), "the option callback does not answer %s" % name
    print("PASS: %d Enhanced option IDs from %d (HUD %d to %d), %d upstream ones and %d numeric ids below it"
          % (len(enh), BASE, start, end - 1, len(upstream), len(numeric)))


if __name__ == "__main__":
    main()
