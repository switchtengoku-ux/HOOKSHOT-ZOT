// (enhanced) Hookshot Enhanced HUD editor in the Insert menu's Gameplay tab (enh_hud.h; docs/enhanced/HUD_EDITOR.md).
// Included by gpu/vk/vk_menu.cpp beside the other enh_*.inc. HUD preset shows which elements are visible (Full, Minimal,
// Hidden, or Custom when they are none of those) and, changed, shows those; Whole HUD size and Whole HUD opacity are plain
// rows the host reads (HOS_OPT_ENH_HUD_SCALE and _FADE). HUD element chooses an element; HUD visible, HUD size, HUD
// position X and Y and HUD opacity show and change its settings (opts.enh_hud_*: the rows' own values, kept in step with
// gpu/vk/enh_hud.cpp's by enh_hud_sync, which the menu's input calls); Reset HUD puts every element back.
// Nothing here is in set_row or menu_init: the tests cut those out (CLAUDE.md). save() writes the elements' lines through
// enh_hud_save_lines (tests/test_menu_save_atomic.py has its stand-in).
// (ENH_HUD_NAMES and ENH_HUD_PRESET_NAMES are in vk_menu.cpp itself, where menu_i18n.h's test finds them)
const char* tx_enh_hud_element(int v) { return ENH_HUD_NAMES[std::clamp(v, 0, HOS_ENH_HUD_ELEMENTS - 1)]; }
const char* tx_enh_hud_preset(int v) { return ENH_HUD_PRESET_NAMES[std::clamp(v, 0, (int)ENH_HUD_PRESET_CUSTOM)]; }
const char* tx_enh_hud_offset(int v) {
    static char b[16];
    snprintf(b, sizeof b, "%+d", v);
    return b;
}
int* enh_hud_rows[ENH_HUD_FIELDS] = {&opts.enh_hud_visible, &opts.enh_hud_size, &opts.enh_hud_x, &opts.enh_hud_y,
                                     &opts.enh_hud_alpha};
void enh_hud_show(int e) {   // (the rows show element e's settings)
    for (int f = 0; f < ENH_HUD_FIELDS; f++) *enh_hud_rows[f] = enh_hud_value(e * ENH_HUD_FIELDS + f);
}
/// The rows and the elements' settings in step: a new element chosen shows its settings; a row changed is the element's; a
/// preset chosen shows its elements. A change is saved at once (save() writes the elements' lines), or, while a slider is
/// held, when it is let go (drag_row)
void enh_hud_sync() {
    static int shown = -1, preset_shown = -1;
    const int e = std::clamp(opts.enh_hud_sel, 0, HOS_ENH_HUD_ELEMENTS - 1);
    bool changed = false;
    if (e != shown) {
        enh_hud_show(e);
        shown = e;
    } else {
        for (int f = 0; f < ENH_HUD_FIELDS; f++)
            if (*enh_hud_rows[f] != enh_hud_value(e * ENH_HUD_FIELDS + f)) changed |= enh_hud_set(e, f, *enh_hud_rows[f]);
    }
    if (preset_shown >= 0 && opts.enh_hud_preset != preset_shown && opts.enh_hud_preset != ENH_HUD_PRESET_CUSTOM &&
        enh_hud_preset_apply(opts.enh_hud_preset))
        enh_hud_show(e), changed = true;
    opts.enh_hud_preset = preset_shown = enh_hud_preset_now();   // (Custom when the elements are no preset)
    if (changed && drag_row < 0) save();
}
bool enh_hud_reset_row(const Row& r) { return !r.value && !strcmp(r.name, "Reset HUD"); }
void enh_hud_reset_press() {
    enh_hud_reset();
    opts.enh_hud_scale = opts.enh_hud_fade = 100;
    enh_hud_show(std::clamp(opts.enh_hud_sel, 0, HOS_ENH_HUD_ELEMENTS - 1));
    opts.enh_hud_preset = enh_hud_preset_now();
    save();
}
