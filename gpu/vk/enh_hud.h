// (enhanced) Hookshot Enhanced HUD editor, the renderer's side (gpu/vk/enh_hud.cpp; docs/enhanced/HUD_EDITOR.md): each HUD
// element's settings (visible, size, X, Y, opacity), kept in hookshot_options.ini as enh_hud_<element>_<field> lines
// (gpu/vk/enh_hud_store.h), answered to the host through the option callback (HOS_OPT_ENH_HUD + element * 5 + field,
// host/enh_hud.c), which asks again only when HOS_OPT_ENH_HUD_GEN changes.
#pragma once
#include <cstdio>

namespace mkwvk {
enum { ENH_HUD_VISIBLE, ENH_HUD_SIZE, ENH_HUD_X, ENH_HUD_Y, ENH_HUD_ALPHA, ENH_HUD_FIELDS };
enum { ENH_HUD_PRESET_FULL, ENH_HUD_PRESET_MINIMAL, ENH_HUD_PRESET_HIDDEN, ENH_HUD_PRESET_CUSTOM };
int enh_hud_value(int index);                 // (element * ENH_HUD_FIELDS + field; read from the options file the first time)
int enh_hud_generation();                     // (a new number at each change: the host reads the values again)
bool enh_hud_set(int element, int field, int value);   // (true when it changed)
void enh_hud_reset();                         // (every element as the game draws it)
bool enh_hud_preset_apply(int preset);        // (the elements a preset shows; their size, place and opacity kept)
int enh_hud_preset_now();                     // (the preset the elements are, ENH_HUD_PRESET_CUSTOM when none)
void enh_hud_save_lines(FILE* f);             // (the enh_hud_ lines, the slots' too: gpu/vk/vk_menu.cpp save())
void enh_hud_slot_save(int slot, int scale, int fade);   // (slot 0 to 2: every element and the Whole HUD rows kept)
bool enh_hud_slot_load(int slot, int* scale, int* fade);  // (false for an empty slot; else every element back as saved)
int enh_hud_default(int field);
}   // namespace mkwvk
