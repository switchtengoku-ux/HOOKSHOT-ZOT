"""Hookshot Enhanced's lightbar and adaptive triggers, the pure part (host/enh_dualsense.h, used by
host/enh_dualsense.c). The header is compiled and checked, with no pad and no game:

- which SDL pad types are a DualShock 4 or a DualSense, in SDL3's and SDL2's numbers, and nothing else;
- the switches: only "hearts"/1 turn the lightbar on, only 1/light and 2/strong the triggers;
- the hearts colour: green when full, yellow at half, red near empty, the blink at one heart or less, and numbers that
  are not a life left alone;
- the low-life heartbeat: due once per blink at one heart or less, only in the blink's on half, never above one
  heart; its motor levels follow Rumble strength (Off: none);
- the trigger effect block: 47 bytes, only the trigger bits enabled (rumble and lights untouched), the clear effect
  for Off, a constant resistance for Light and Strong, the same on both triggers.

Also checks that host/pad_sdl.c and host/hos_main.c call into it at the places the feature needs, marked (enhanced).

python -I -B tests/test_enh_dualsense.py [--cc clang]
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cc", "clang"]

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r'''#include <stdio.h>
#include "enh_dualsense.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); return 1; } } while (0)
int main(void) {
    /* pad kinds */
    CHECK(enh_ds_kind(3, 5) == ENH_DS_PS4 && enh_ds_kind(3, 6) == ENH_DS_PS5);
    CHECK(enh_ds_kind(2, 4) == ENH_DS_PS4 && enh_ds_kind(2, 7) == ENH_DS_PS5);
    CHECK(enh_ds_kind(3, 7) == ENH_DS_NONE && enh_ds_kind(3, 3) == ENH_DS_NONE);   /* Switch Pro, Xbox One */
    CHECK(enh_ds_kind(2, 6) == ENH_DS_NONE && enh_ds_kind(2, 5) == ENH_DS_NONE);   /* virtual, Switch Pro */
    CHECK(enh_ds_kind(0, 6) == ENH_DS_NONE);
    /* switches */
    CHECK(enh_ds_parse_lightbar(NULL) == ENH_DS_LIGHTBAR_OFF && enh_ds_parse_lightbar("off") == ENH_DS_LIGHTBAR_OFF);
    CHECK(enh_ds_parse_lightbar("0") == ENH_DS_LIGHTBAR_OFF && enh_ds_parse_lightbar("") == ENH_DS_LIGHTBAR_OFF);
    CHECK(enh_ds_parse_lightbar("hearts") == ENH_DS_LIGHTBAR_HEARTS && enh_ds_parse_lightbar("1") == ENH_DS_LIGHTBAR_HEARTS);
    CHECK(enh_ds_parse_triggers(NULL) == ENH_DS_TRIGGERS_OFF && enh_ds_parse_triggers("3") == ENH_DS_TRIGGERS_OFF);
    CHECK(enh_ds_parse_triggers("1") == ENH_DS_TRIGGERS_LIGHT && enh_ds_parse_triggers("light") == ENH_DS_TRIGGERS_LIGHT);
    CHECK(enh_ds_parse_triggers("2") == ENH_DS_TRIGGERS_STRONG && enh_ds_parse_triggers("strong") == ENH_DS_TRIGGERS_STRONG);
    /* hearts: full green, half yellow, empty red (at a time in the blink's on half) */
    uint8_t c[3] = {1, 2, 3};
    CHECK(enh_ds_hearts_color(48, 48, 0, c) && c[0] == 0 && c[1] == 255 && c[2] == 0);
    CHECK(enh_ds_hearts_color(24, 48, 0, c) && c[0] == 255 && c[1] == 255 && c[2] == 0);
    CHECK(enh_ds_hearts_color(12, 48, 0, c) && c[0] == 255 && c[1] == 127 && c[2] == 0);
    CHECK(enh_ds_hearts_color(36, 48, 0, c) && c[0] == 127 && c[1] == 255);
    CHECK(enh_ds_hearts_color(0, 48, 0, c) && c[0] == 255 && c[1] == 0);
    /* one heart or less: on for 400 ms, off for 400 ms; more than one heart never blinks */
    CHECK(enh_ds_hearts_color(4, 48, 100, c) && c[0] == 255);
    CHECK(enh_ds_hearts_color(4, 48, 500, c) && c[0] == 0 && c[1] == 0 && c[2] == 0);
    CHECK(enh_ds_hearts_color(5, 48, 500, c) && c[0] == 255);
    /* not a life: rgb left as it was */
    c[0] = 9, c[1] = 9, c[2] = 9;
    CHECK(!enh_ds_hearts_color(10, 0, 0, c) && !enh_ds_hearts_color(-1, 48, 0, c));
    CHECK(!enh_ds_hearts_color(49, 48, 0, c) && !enh_ds_hearts_color(10, 81, 0, c));
    CHECK(c[0] == 9 && c[1] == 9 && c[2] == 9);
    /* heartbeat: once per blink cycle, in its on half, at one heart or less */
    CHECK(enh_ds_heartbeat_due(4, 48, 100, 0) == 1);
    CHECK(enh_ds_heartbeat_due(4, 48, 300, 1) == 0);           /* the same cycle: pulsed already */
    CHECK(enh_ds_heartbeat_due(4, 48, 500, 1) == 0);           /* the off half */
    CHECK(enh_ds_heartbeat_due(4, 48, 850, 1) == 2);           /* the next cycle */
    CHECK(enh_ds_heartbeat_due(1, 48, 100, 0) == 1 && enh_ds_heartbeat_due(0, 48, 100, 0) == 1);
    CHECK(enh_ds_heartbeat_due(5, 48, 100, 0) == 0);           /* more than one heart */
    CHECK(enh_ds_heartbeat_due(4, 0, 100, 0) == 0 && enh_ds_heartbeat_due(-1, 48, 100, 0) == 0);
    CHECK(enh_ds_beat_level(ENH_DS_BEAT_LOW, 100) == ENH_DS_BEAT_LOW && enh_ds_beat_level(ENH_DS_BEAT_LOW, 0) == 0);
    CHECK(enh_ds_beat_level(ENH_DS_BEAT_LOW, 50) == ENH_DS_BEAT_LOW / 2 && enh_ds_beat_level(60000, 150) == 65535);
    /* trigger effects */
    uint8_t e[ENH_DS_EFFECT_SIZE];
    CHECK(sizeof e == 47);
    enh_ds_trigger_effect(ENH_DS_TRIGGERS_OFF, e);
    CHECK(e[0] == 0x0c && e[1] == 0);                         /* only the triggers: no rumble, lightbar or lights */
    CHECK(e[ENH_DS_RIGHT_TRIGGER] == 0x05 && e[ENH_DS_LEFT_TRIGGER] == 0x05);
    for (int i = 2; i < ENH_DS_EFFECT_SIZE; i++)
        if (i != ENH_DS_RIGHT_TRIGGER && i != ENH_DS_LEFT_TRIGGER) CHECK(e[i] == 0);
    enh_ds_trigger_effect(ENH_DS_TRIGGERS_LIGHT, e);
    CHECK(e[0] == 0x0c && e[10] == 0x01 && e[11] == 0 && e[12] == 60 && e[21] == 0x01 && e[23] == 60);
    enh_ds_trigger_effect(ENH_DS_TRIGGERS_STRONG, e);
    CHECK(e[12] == 160 && e[23] == 160 && e[38] == 0 && e[44] == 0 && e[45] == 0 && e[46] == 0);
    puts("ok: lightbar colours, heartbeat, pad kinds, switches and trigger effects");
    return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cc", default="clang")
    args = p.parse_args()
    # the hooks are where the feature needs them, and marked
    pad = (ROOT / "host" / "pad_sdl.c").read_text(encoding="utf-8")
    assert "hos_enh_pad(i, gc, pads[i].serial, now, lo || hi, strength);" in pad, "host/pad_sdl.c no longer calls hos_enh_pad"
    assert "hos_enh_pad_gone(i);" in pad, "host/pad_sdl.c no longer tells host/enh_dualsense.c a pad went away"
    main_c = (ROOT / "host" / "hos_main.c").read_text(encoding="utf-8")
    assert "hos_enh_set_life(life, max_life)" in main_c, "host/hos_main.c no longer hands Link's life over"
    for text, name in ((pad, "pad_sdl.c"), (main_c, "hos_main.c")):
        assert "(enhanced)" in text, "host/%s: the fork's edits are not marked (enhanced)" % name
    with tempfile.TemporaryDirectory() as tmp:
        src, exe = Path(tmp) / "fixture.c", Path(tmp) / "fixture.exe"
        src.write_text(FIXTURE, encoding="utf-8")
        subprocess.run([args.cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "host"), str(src), "-o", str(exe)],
                       check=True)
        out = subprocess.run([str(exe)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stderr or "the fixture failed")
        print(out.stdout.strip())


if __name__ == "__main__":
    main()
