// (enhanced) Hookshot Enhanced HUD editor: its settings as they are kept (gpu/vk/enh_hud.cpp; docs/enhanced/HUD_EDITOR.md).
// Pure, no file and no lock: tests/test_enh_hud.py compiles it alone.
// Each element's five fields are lines of hookshot_options.ini, "enh_hud_<element>_<field>=<value>" (enh_hud_hearts_size=150);
// the file from before, enh_hud.ini, had "<element>.<field>=<value>" lines (read_legacy_line). The presets (the HUD preset
// row) set which elements are visible and leave their size, place and opacity alone.
#pragma once
#include "vk_api.h"   // (HOS_ENH_HUD_ELEMENTS)
#include <algorithm>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace enh_hud_store {
enum { VISIBLE, SIZE, X, Y, ALPHA, FIELDS };
enum { PRESET_FULL, PRESET_MINIMAL, PRESET_HIDDEN, PRESET_CUSTOM };
// (the order is the menu's and the option ids': ENH_HUD_NAMES in gpu/vk/vk_menu.cpp, ENH_HUD_ELEMENTS in host/enh_hud.c)
inline const char* const ELEMENT_KEYS[HOS_ENH_HUD_ELEMENTS] = {"hearts", "magic", "items", "buttons", "minimap", "place"};
inline const char* const FIELD_KEYS[FIELDS] = {"visible", "size", "x", "y", "opacity"};
inline constexpr int LO[FIELDS] = {0, 25, -800, -800, 10}, HI[FIELDS] = {1, 200, 800, 800, 100};
inline constexpr int HEARTS = 0;   // (the one element the Minimal preset keeps)

inline int default_of(int field) { return field == VISIBLE ? 1 : field == SIZE || field == ALPHA ? 100 : 0; }

struct Store {
    int v[HOS_ENH_HUD_ELEMENTS][FIELDS];
    void reset() {
        for (auto& e : v)
            for (int f = 0; f < FIELDS; f++) e[f] = default_of(f);
    }
    bool set(int element, int field, int value) {   // (true when it changed)
        if (element < 0 || element >= HOS_ENH_HUD_ELEMENTS || field < 0 || field >= FIELDS) return false;
        value = std::clamp(value, LO[field], HI[field]);
        if (v[element][field] == value) return false;
        v[element][field] = value;
        return true;
    }
};

/// An options file's line "enh_hud_<element>_<field>" = value: true, and the field set (clamped); false for any other key
inline bool read_key(Store& s, const char* key, const char* value) {
    if (strncmp(key, "enh_hud_", 8) != 0) return false;
    key += 8;
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
        const size_t n = strlen(ELEMENT_KEYS[e]);
        if (strncmp(key, ELEMENT_KEYS[e], n) != 0 || key[n] != '_') continue;
        for (int f = 0; f < FIELDS; f++)
            if (!strcmp(key + n + 1, FIELD_KEYS[f])) {
                s.v[e][f] = std::clamp(atoi(value), LO[f], HI[f]);
                return true;
            }
    }
    return false;
}

/// Every element's every field, one line each (hookshot_options.ini: written by gpu/vk/vk_menu.cpp save())
inline void write_lines(const Store& s, FILE* f) {
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++)
        for (int k = 0; k < FIELDS; k++) fprintf(f, "enh_hud_%s_%s=%d\n", ELEMENT_KEYS[e], FIELD_KEYS[k], s.v[e][k]);
}

/// A line of the enh_hud.ini from before: "<element>.<field>=<value>" (true when it was one)
inline bool read_legacy_line(Store& s, const char* line) {
    int e, k, v;
    if (line[0] == '#' || sscanf(line, "%d.%d=%d", &e, &k, &v) != 3 || e < 0 || e >= HOS_ENH_HUD_ELEMENTS || k < 0 || k >= FIELDS)
        return false;
    s.v[e][k] = std::clamp(v, LO[k], HI[k]);
    return true;
}

/// The preset the elements' visibility is: Full (all), Minimal (the hearts alone), Hidden (none), else Custom
inline int preset_of(const Store& s) {
    int shown = 0;
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) shown += s.v[e][VISIBLE] != 0;
    if (shown == HOS_ENH_HUD_ELEMENTS) return PRESET_FULL;
    if (shown == 0) return PRESET_HIDDEN;
    if (shown == 1 && s.v[HEARTS][VISIBLE]) return PRESET_MINIMAL;
    return PRESET_CUSTOM;
}

/// A preset's visibility on every element (true when one changed); Custom changes nothing
inline bool preset_apply(Store& s, int preset) {
    if (preset < PRESET_FULL || preset > PRESET_HIDDEN) return false;
    bool changed = false;
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++)
        changed |= s.set(e, VISIBLE, preset == PRESET_FULL || (preset == PRESET_MINIMAL && e == HEARTS));
    return changed;
}
}   // namespace enh_hud_store
