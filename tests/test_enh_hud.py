"""Hookshot Enhanced's HUD editor, the parts that need no game (docs/enhanced/HUD_EDITOR.md):

- gpu/vk/enh_hud_store.h, compiled alone: the defaults, a value clamped to its row's range, the hookshot_options.ini lines
  (enh_hud_<element>_<field>=<value>) written and read back, other keys left alone (the rows' own enh_hud_scale,
  enh_hud_element...), the old enh_hud.ini lines read, and the presets (Full, Minimal the hearts alone, Hidden, Custom
  otherwise; a preset changes visibility only);
- host/enh_hud.c hud_effective, cut out and compiled: an element's size and opacity times the Whole HUD rows', rounded,
  never fully transparent; its visibility and place untouched;
- the wiring: gpu/vk/vk_menu.cpp save() owns the enh_hud_ lines and writes them through enh_hud_save_lines
  (tests/test_menu_save_atomic.py, which compiles save(), has a stand-in); the menu saves an element's change at once, a held slider's when let go; the
  host asks the thirty values again only when HOS_OPT_ENH_HUD_GEN changes; the three new rows and their keys.

python -I -B tests/test_enh_hud.py [--cc clang] [--cxx clang++]
"""
import argparse
from pathlib import Path
import re
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cc", "clang", "--cxx", "{cxx}"]

ROOT = Path(__file__).resolve().parents[1]

STORE_FIXTURE = r'''#include <cstdio>
#include <cstring>
#include "enh_hud_store.h"
using namespace enh_hud_store;
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); return 1; } } while (0)
static bool same(const Store& a, const Store& b) { return !memcmp(a.v, b.v, sizeof a.v); }
int main() {
    Store s;
    s.reset();
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++)
        CHECK(s.v[e][VISIBLE] == 1 && s.v[e][SIZE] == 100 && s.v[e][X] == 0 && s.v[e][Y] == 0 && s.v[e][ALPHA] == 100);
    CHECK(preset_of(s) == PRESET_FULL);
    CHECK(s.set(0, SIZE, 150) && s.v[0][SIZE] == 150);
    CHECK(!s.set(0, SIZE, 150));                              /* the same value: no change */
    CHECK(s.set(1, SIZE, 999) && s.v[1][SIZE] == 200);        /* clamped to the row's range */
    CHECK(s.set(2, X, -5000) && s.v[2][X] == -100);           /* x, y: percent of the screen, edge to edge */
    CHECK(s.set(2, Y, 100) && s.v[2][Y] == 100);
    CHECK(s.set(5, ALPHA, 0) && s.v[5][ALPHA] == 10);
    CHECK(!s.set(HOS_ENH_HUD_ELEMENTS, SIZE, 50) && !s.set(0, FIELDS, 1) && !s.set(-1, SIZE, 50));
    puts("ok: defaults and clamping");

    Store r;
    r.reset();
    CHECK(read_key(r, "enh_hud_hearts_size", "150") && r.v[0][SIZE] == 150);
    CHECK(read_key(r, "enh_hud_place_opacity", "5\n") && r.v[5][ALPHA] == 10);
    CHECK(read_key(r, "enh_hud_minimap_y", "-12") && r.v[4][Y] == -12);
    CHECK(read_key(r, "enh_hud_items_x", "-640") && r.v[2][X] == -100);   /* past the edge: clamped */
    CHECK(read_key(r, "enh_hud_buttons_visible", "0") && r.v[3][VISIBLE] == 0);
    const char* others[] = {"enh_hud_scale", "enh_hud_fade", "enh_hud_preset", "enh_hud_element", "enh_hud_size",
                            "enh_hud_hearts", "enh_hud_hearts_", "enh_hud_heartsx_size", "enh_hud_hearts_sizes",
                            "hud_hearts_size", "volume"};
    for (const char* k : others) CHECK(!read_key(r, k, "1"));
    puts("ok: options file keys read, other keys left alone");

    FILE* f = tmpfile();
    CHECK(f);
    write_lines(s, f);
    rewind(f);
    Store back;
    back.reset();
    back.v[0][VISIBLE] = 0;   /* (every line read back over a different start) */
    char line[128];
    int lines = 0;
    while (fgets(line, sizeof line, f)) {
        char* eq = strchr(line, '=');
        CHECK(eq);
        *eq = 0;
        CHECK(read_key(back, line, eq + 1));
        lines++;
    }
    fclose(f);
    CHECK(lines == HOS_ENH_HUD_ELEMENTS * FIELDS && same(s, back));
    puts("ok: every element's line written and read back");

    Store old;
    old.reset();
    CHECK(read_legacy_line(old, "0.1=150\n") && old.v[0][SIZE] == 150);
    CHECK(read_legacy_line(old, "4.4=60") && old.v[4][ALPHA] == 60);
    CHECK(read_legacy_line(old, "1.0=0") && old.v[1][VISIBLE] == 0);
    CHECK(read_legacy_line(old, "2.2=384") && old.v[2][X] == 10);    /* canvas units then: 384 of 3840 is 10% */
    CHECK(read_legacy_line(old, "2.3=-540") && old.v[2][Y] == -25);  /* -540 of 2160 */
    CHECK(read_legacy_line(old, "3.2=-20") && old.v[3][X] == -1);    /* rounded to the nearest */
    CHECK(!read_legacy_line(old, "# Hookshot Enhanced HUD editor") && !read_legacy_line(old, "7.0=1") &&
          !read_legacy_line(old, "0.5=1") && !read_legacy_line(old, "enh_hud_hearts_size=1"));
    puts("ok: the old enh_hud.ini lines");

    Store p;
    p.reset();
    p.v[3][SIZE] = 150, p.v[4][ALPHA] = 40;
    CHECK(preset_apply(p, PRESET_MINIMAL) && preset_of(p) == PRESET_MINIMAL);
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) CHECK(p.v[e][VISIBLE] == (e == HEARTS));
    CHECK(p.v[3][SIZE] == 150 && p.v[4][ALPHA] == 40);       /* size and opacity kept */
    CHECK(!preset_apply(p, PRESET_MINIMAL));                  /* already so */
    CHECK(preset_apply(p, PRESET_HIDDEN) && preset_of(p) == PRESET_HIDDEN);
    CHECK(preset_apply(p, PRESET_FULL) && preset_of(p) == PRESET_FULL);
    p.v[1][VISIBLE] = 0;
    CHECK(preset_of(p) == PRESET_CUSTOM);                     /* the magic hidden alone */
    CHECK(!preset_apply(p, PRESET_CUSTOM) && !preset_apply(p, 9) && p.v[1][VISIBLE] == 0);
    p.reset();
    p.v[0][VISIBLE] = 0, p.v[2][VISIBLE] = 0, p.v[3][VISIBLE] = 0, p.v[4][VISIBLE] = 0, p.v[5][VISIBLE] = 0;
    CHECK(preset_of(p) == PRESET_CUSTOM);                     /* one element shown, not the hearts */
    puts("ok: presets");

    /* the HUD slots: written and read back, other keys left alone, an unused slot not written */
    Slot slots[SLOTS], back_slots[SLOTS];
    Store mine;
    mine.reset();
    mine.v[0][X] = -40, mine.v[4][ALPHA] = 30, mine.v[1][VISIBLE] = 0;
    slots[1].s = mine, slots[1].scale = 80, slots[1].fade = 60, slots[1].used = true;
    FILE* sf = tmpfile();
    CHECK(sf);
    write_slot_lines(slots, sf);
    rewind(sf);
    int slot_lines = 0;
    while (fgets(line, sizeof line, sf)) {
        char* eq = strchr(line, '=');
        CHECK(eq);
        *eq = 0;
        CHECK(strncmp(line, "enh_hud_slot2_", 14) == 0);   /* (slots 1 and 3 unused: no line) */
        CHECK(read_slot_key(back_slots, line, eq + 1));
        slot_lines++;
    }
    fclose(sf);
    CHECK(slot_lines == 2 + HOS_ENH_HUD_ELEMENTS * FIELDS);
    CHECK(back_slots[1].used && !back_slots[0].used && !back_slots[2].used);
    CHECK(same(back_slots[1].s, mine) && back_slots[1].scale == 80 && back_slots[1].fade == 60);
    CHECK(!read_slot_key(back_slots, "enh_hud_slot", "1") && !read_slot_key(back_slots, "enh_hud_slot4_scale", "1") &&
          !read_slot_key(back_slots, "enh_hud_slot1_hearts_bogus", "1") && !read_slot_key(back_slots, "enh_hud_hearts_x", "1"));
    CHECK(read_slot_key(back_slots, "enh_hud_slot3_scale", "999") && back_slots[2].scale == 150 && back_slots[2].used);
    Store r2;
    r2.reset();
    CHECK(!read_key(r2, "enh_hud_slot1_hearts_x", "5"));   /* (a slot's line is not the HUD's own) */
    puts("ok: HUD slots");

    /* the dungeon minimap, an element of its own: a file or slot from before takes the minimap's settings */
    CHECK(!strcmp(ELEMENT_KEYS[DUNGEON_MAP], "dungeon_map") && !strcmp(ELEMENT_KEYS[MINIMAP], "minimap"));
    Store d;
    d.reset();
    d.v[MINIMAP][X] = -60, d.v[MINIMAP][ALPHA] = 50;
    inherit_dungeon_map(d);
    CHECK(d.v[DUNGEON_MAP][X] == -60 && d.v[DUNGEON_MAP][ALPHA] == 50 && d.v[DUNGEON_MAP][VISIBLE] == 1);
    CHECK(read_key(d, "enh_hud_dungeon_map_y", "30") && d.v[DUNGEON_MAP][Y] == 30 && d.v[MINIMAP][Y] == 0);
    Slot ds[SLOTS];
    CHECK(read_slot_key(ds, "enh_hud_slot1_minimap_x", "-5") && !ds[0].dungeon_seen);
    CHECK(read_slot_key(ds, "enh_hud_slot1_dungeon_map_x", "7") && ds[0].dungeon_seen && ds[0].s.v[DUNGEON_MAP][X] == 7);
    puts("ok: the dungeon minimap");
    return 0;
}
'''

EFFECTIVE_FIXTURE = r'''#include <stdio.h>
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); return 1; } } while (0)
/* ACTUAL */
int main(void) {
    const HudSet own = {1, 150, -40, 60, 50};
    HudSet e = hud_effective(own, 100, 100);
    CHECK(e.visible == 1 && e.size == 150 && e.x == -40 && e.y == 60 && e.alpha == 50);
    e = hud_effective(own, 50, 50);
    CHECK(e.size == 75 && e.alpha == 25 && e.x == -40 && e.y == 60 && e.visible == 1);
    const HudSet faint = {0, 25, 0, 0, 10};
    e = hud_effective(faint, 150, 10);
    CHECK(e.visible == 0 && e.size == 38 && e.alpha == 1);   /* 37.5 rounded; never 0 */
    puts("ok: the Whole HUD rows times each element's own");

    /* the point a resized element keeps: a box 864 wide, its origin in the middle, at x = -1500 */
    float ax, ay;
    hud_anchor(A_BOX_TL, -1500.0f, 900.0f, 864.0f, 40.0f, 1, 1, 0.0f, &ax, &ay);
    CHECK(ax == -1932.0f && ay == 920.0f);                    /* the box's top left, 432 left of the origin */
    hud_anchor(A_ORIGIN, -1500.0f, 900.0f, 864.0f, 40.0f, 1, 1, 0.0f, &ax, &ay);
    CHECK(ax == -1500.0f && ay == 900.0f);                    /* the origin itself */
    hud_anchor(A_ORIGIN, -1560.0f, 830.0f, 1256.0f, 155.0f, 1, 1, 230.0f * 0.5f, &ax, &ay);
    CHECK(ax == -1675.0f && ay == 830.0f);                    /* a lead, scaled as the pane: the magic bar's left end */
    hud_anchor(A_BOX_TR, 1700.0f, 900.0f, 200.0f, 100.0f, 2, 0, 0.0f, &ax, &ay);
    CHECK(ax == 1700.0f && ay == 900.0f);                     /* origin at the box's top right */
    hud_anchor(A_BR, 0.0f, 0.0f, 0.0f, 0.0f, 0, 0, 0.0f, &ax, &ay);
    CHECK(ax == 1920.0f && ay == -1080.0f);                   /* the canvas's bottom right */
    hud_anchor(A_TOP, 0.0f, 0.0f, 0.0f, 0.0f, 0, 0, 0.0f, &ax, &ay);
    CHECK(ax == 0.0f && ay == 1080.0f);
    puts("ok: anchors");

    /* the screen in canvas units, which the offsets are percent of */
    float w, h;
    hud_screen(0.0f, 0.0f, &w, &h);
    CHECK(w == 3840.0f && h == 2160.0f);                      /* 16:9: the canvas itself */
    hud_screen(0.5f, 1.0f, &w, &h);
    CHECK(w == 7680.0f && h == 2160.0f);                      /* 32:9: twice as wide */
    hud_screen(1.0f, 0.75f, &w, &h);
    CHECK(w == 3840.0f && h == 2880.0f);                      /* 4:3: taller */
    puts("ok: the screen's size for the offsets");

    /* an element moved across the screen stays on it: a box from -2400 to -1600 on a screen 5160 wide (half 2580) */
    CHECK(hud_keep(-2400.0f, -1600.0f, 1000.0f, 2580.0f) == 1000.0f);   /* within: as wanted */
    CHECK(hud_keep(-2400.0f, -1600.0f, 5000.0f, 2580.0f) == 4180.0f);   /* its right side at the right edge */
    CHECK(hud_keep(-2400.0f, -1600.0f, -900.0f, 2580.0f) == -180.0f);   /* its left side at the left edge */
    CHECK(hud_keep(2580.0f, 2580.0f, -5160.0f, 2580.0f) == -5160.0f);   /* an anchor in the right corner: to the left one */
    CHECK(hud_keep(2580.0f, 2580.0f, 300.0f, 2580.0f) == 0.0f);         /* and no further out */
    CHECK(hud_keep(-3000.0f, 3000.0f, 500.0f, 2580.0f) == -(2580.0f - 3000.0f));   /* wider than the screen: its low side on */
    puts("ok: kept on the screen");
    return 0;
}
'''


KEYS_FIXTURE = r'''#include <stdio.h>
#include <string.h>
struct Row { const char* name; };
static const char* hud_key(const Row& r) {
/* LINES */
    return nullptr;
}
int main() {
    const char* names[] = {/* NAMES */};
    const char* keys[sizeof names / sizeof names[0]];
    int n = (int)(sizeof names / sizeof names[0]);
    for (int i = 0; i < n; i++) {
        keys[i] = hud_key(Row{names[i]});
        if (!keys[i]) { fprintf(stderr, "FAIL: %s has no key\n", names[i]); return 1; }
        printf("%s=%s\n", names[i], keys[i]);
        for (int j = 0; j < i; j++)
            if (!strcmp(keys[i], keys[j])) { fprintf(stderr, "FAIL: %s and %s share %s\n", names[j], names[i], keys[i]); return 1; }
    }
    return 0;
}
'''
EXPECTED_KEYS = {"HUD preset": "enh_hud_preset", "Whole HUD size": "enh_hud_scale", "Whole HUD opacity": "enh_hud_fade",
                 "HUD element": "enh_hud_element", "HUD visible": "enh_hud_visible", "HUD size": "enh_hud_size",
                 "HUD position X": "enh_hud_x", "HUD position Y": "enh_hud_y", "HUD opacity": "enh_hud_opacity",
                 "HUD slot": "enh_hud_slot"}


def cut(source, start, end="\n}\n"):
    i = source.index(start)
    return source[i:source.index(end, i) + len(end)]


def run(cmd):
    subprocess.run(cmd, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cc", default="clang")
    p.add_argument("--cxx", default="clang++")
    args = p.parse_args()

    host = (ROOT / "host" / "enh_hud.c").read_text(encoding="utf-8")
    effective = "typedef struct { int visible, size, x, y, alpha; } HudSet;\n"
    assert effective in host, "host/enh_hud.c HudSet changed: update this test's cut"
    effective += cut(host, "static inline HudSet hud_effective(")
    anchors = "enum { A_BOX_TL, A_BOX_TR, A_ORIGIN, A_TL, A_TR, A_BL, A_BR, A_TOP, A_BOTTOM };\n"
    assert anchors in host, "host/enh_hud.c's anchors changed: update this test's cut"
    effective += anchors + cut(host, "static inline void hud_anchor(") + cut(host, "static inline void hud_screen(") + \
        cut(host, "static inline float hud_keep(")
    assert "*dx = hud_keep(lo, hi, shift.want_x, shift.half_w);" in host and "hud_measure(c, pane, el - 1, x, y);" in host and \
        "hud_screen(hos_ui_qx, hos_ui_qy, &sw, &sh);" in host, \
        "the offsets are no longer percent of the screen kept on it: an element cannot reach every part of it"
    wide = (ROOT / "host" / "hos_wide_ui.c").read_text(encoding="utf-8")
    placed = cut(wide, "void hos_wide_ui_placed(Ctx *c, uint64_t pane) {")
    assert placed.index("\n    placed(c, pane, parent);") < placed.index("hos_enh_hud_shift(c, pane, x, y, &dx, &dy)") < \
        placed.index("store_f(c, pane + PANE_X, x + dx)") and "n->moved += dx" in placed, \
        "host/hos_wide_ui.c no longer makes the HUD editor's place after its own moves: a wider screen's side moves " \
        "push an element moved across the screen off it"
    assert 'ENH_HUD_GROUPS[] = {"N_ScaleL_00"};' in host and \
        "above == IN_GROUP ? own_size[e]" in host, \
        "the Whole HUD size no longer scales the left gauges' group alone as one (N_ScaleL_01 is inside N_ScaleL_00)"
    assert '"RootPane")) continue;' in host, "a whole-layout element is resized at a pane that is not its root again"
    own = cut(host, "static int own_element(Ctx *c, uint64_t pane, uint64_t parent) {")
    assert '"N_LocalMap_00")' in own and '"N_WorldMap_00")' in own and '"N_MiniMap_00")' in own and \
        'if (map_page_shown()) return 0;' in own and '"N_Dungeon_01")' in own and '"N_Field_01")' in own and "(dungeon_on ? E_DUNGEON_MAP : E_MINIMAP) + 1" in own and "hos_wide_ui_force = 3;" in own and \
        '"N_MapIcon_00")' not in host, \
        "MapMenu_00's map page is told apart by its icons' group again: the dungeon minimap and its keys count are never " \
        "moved, and the pause menu's map page, caught opening, is moved with the minimap"
    assert '{"PlayerStatus_00", "Pa_MpGauge_00", A_ORIGIN, 230,' in host, \
        "the magic gauge is resized about its box again: its box is far wider than its bar, it goes off the screen"
    tick = cut(host, "void hos_enh_hud_tick(void) {")
    assert "rx_option(HOS_OPT_ENH_HUD_GEN, 0)" in tick and "if (now_gen != gen)" in tick, \
        "host/enh_hud.c no longer asks the elements' values only when HOS_OPT_ENH_HUD_GEN changes"
    assert "hud_effective(own[e], scale, fade)" in tick, "host/enh_hud.c no longer applies the Whole HUD rows"

    menu = (ROOT / "gpu" / "vk" / "vk_menu.cpp").read_text(encoding="utf-8")
    save = cut(menu, "void save() {")
    assert 'mine |= !key.compare(0, 8, "enh_hud_");' in save, "save() keeps old enh_hud_ lines after the new ones"
    assert "enh_hud_save_lines(f);" in save, "save() does not write the HUD elements' lines"
    for name, key in (("HUD preset", "enh_hud_preset"), ("Whole HUD size", "enh_hud_scale"),
                      ("Whole HUD opacity", "enh_hud_fade")):
        assert '{TAB_GAMEPLAY, "%s"' % name in menu, "the %s row is gone" % name
        assert '"%s"' % key in cut(menu, "const char* ini_key(const Row& r) {"), "ini_key has no %s" % key
    inc = (ROOT / "gpu" / "vk" / "enh_menu_hud.inc").read_text(encoding="utf-8")
    assert "if (changed && drag_row < 0) save();" in cut(inc, "void enh_hud_sync() {"), \
        "the HUD editor no longer saves an element's change"
    assert "save();" in cut(inc, "void enh_hud_reset_press() {"), "Reset HUD is no longer saved"
    slot = cut(inc, "void enh_hud_slot_press(const Row& r) {")
    assert "enh_hud_slot_save(slot, opts.enh_hud_scale, opts.enh_hud_fade)" in slot and \
        "enh_hud_slot_load(slot, &opts.enh_hud_scale, &opts.enh_hud_fade)" in slot and "save();" in slot, \
        "Save HUD to slot / Load HUD from slot no longer keep or put back the HUD, or no longer save it"
    assert "enh_hud_store::write_slot_lines(slots, f);" in (ROOT / "gpu" / "vk" / "enh_hud.cpp").read_text(encoding="utf-8"), \
        "the HUD slots are no longer written to the options file"
    for name in ("HUD position X", "HUD position Y"):
        assert '"%s", &opts.enh_hud_%s, -100, 100, 1,' % (name, name[-1].lower()) in menu, \
            "the %s row's range is not the store's (enh_hud_store.h LO and HI)" % name
    bridge = cut(menu, "int menu_setting_set(")
    assert bridge.count("enh_hud_sync();") == 2, \
        "the control bridge's option_set changes a HUD editor row the elements never get while the menu is closed"

    with tempfile.TemporaryDirectory(prefix="enh-hud-") as tmp:
        t = Path(tmp)
        (t / "store.cpp").write_text(STORE_FIXTURE, encoding="utf-8")
        run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "gpu" / "vk"), str(t / "store.cpp"),
             "-o", str(t / "store.exe")])
        run([str(t / "store.exe")])
        (t / "effective.c").write_text(EFFECTIVE_FIXTURE.replace("/* ACTUAL */", effective), encoding="utf-8")
        run([args.cc, "-std=c11", "-Wall", "-Wextra", "-Werror", str(t / "effective.c"), "-o", str(t / "effective.exe")])
        run([str(t / "effective.exe")])
        # (each HUD row's options-file key, from ini_key's own lines: "HUD position" once matched "HUD preset"'s 'p',
        # so both positions were saved as enh_hud_preset and the control bridge's option_set reached the preset row)
        ini = cut(menu, "const char* ini_key(const Row& r) {")
        lines = [l for l in ini.splitlines() if 'strncmp(r.name, "HUD ", 4)' in l or 'strncmp(r.name, "Whole HUD", 9)' in l]
        assert len(lines) == 2, "ini_key's HUD editor lines changed: update this test's cut"
        names = re.findall(r'\{TAB_GAMEPLAY, "((?:HUD|Whole HUD) [^"]+)", &', menu)
        assert set(names) == set(EXPECTED_KEYS), "the HUD editor's rows changed: %s" % names
        fixture = KEYS_FIXTURE.replace("/* LINES */", "\n".join(lines)).replace(
            "/* NAMES */", ", ".join('"%s"' % n for n in names))
        (t / "keys.cpp").write_text(fixture, encoding="utf-8")
        run([args.cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror", str(t / "keys.cpp"), "-o", str(t / "keys.exe")])
        got = dict(l.split("=", 1) for l in subprocess.run([str(t / "keys.exe")], check=True, stdout=subprocess.PIPE,
                                                            text=True).stdout.splitlines())
        assert got == EXPECTED_KEYS, "the HUD rows' keys: %s" % got
        slider = cut(menu, "bool is_slider(const Row& r) {") if "bool is_slider(const Row& r) {" in menu else ""
        assert 'strncmp(r.name + 4, "pr", 2) && strncmp(r.name + 4, "sl", 2))' in menu, \
            "HUD position X and Y are no longer sliders (dragged with the mouse)"
    print("PASS: HUD editor settings, presets, Whole HUD rows and wiring")


if __name__ == "__main__":
    main()
