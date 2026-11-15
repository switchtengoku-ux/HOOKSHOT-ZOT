// (enhanced) Hookshot Enhanced HUD editor, the renderer's side (gpu/vk/enh_hud.cpp; docs/enhanced/HUD_EDITOR.md): each HUD
// element's settings (visible, size, X, Y, opacity), kept in enh_hud.ini beside hookshot_options.ini, answered to the host
// through the option callback (HOS_OPT_ENH_HUD + element * 5 + field, host/enh_hud.c).
#pragma once
#include <string>

namespace mkwvk {
enum { ENH_HUD_VISIBLE, ENH_HUD_SIZE, ENH_HUD_X, ENH_HUD_Y, ENH_HUD_ALPHA, ENH_HUD_FIELDS };
int enh_hud_value(int index);                 // (element * ENH_HUD_FIELDS + field; its default before the file is read)
void enh_hud_set(int element, int field, int value);
void enh_hud_reset();                         // (every element as the game draws it)
void enh_hud_bind(const std::string& folder); // (where enh_hud.ini is: the options file's folder; read the first time)
int enh_hud_default(int field);
}   // namespace mkwvk
