// (enhanced) Hookshot Enhanced HUD editor in the Insert menu's Gameplay tab (enh_hud.h; docs/enhanced/HUD_EDITOR.md).
// Included by gpu/vk/vk_menu.cpp beside the other enh_*.inc. HUD element chooses an element; HUD visible, HUD size,
// HUD position X and Y and HUD opacity show and change its settings (opts.enh_hud_*: the rows' own values, kept in
// step with gpu/vk/enh_hud.cpp's by enh_hud_sync, which the menu's input calls); Reset HUD puts every element back.
// Nothing here is in set_row, save or menu_init: the tests cut those out (CLAUDE.md).
// (ENH_HUD_NAMES, the elements' names, are in vk_menu.cpp itself, where menu_i18n.h's test finds them)
const char* tx_enh_hud_element(int v) { return ENH_HUD_NAMES[std::clamp(v, 0, HOS_ENH_HUD_ELEMENTS - 1)]; }
const char* tx_enh_hud_offset(int v) {
    static char b[16];
    snprintf(b, sizeof b, "%+d", v);
    return b;
}
int* enh_hud_rows[ENH_HUD_FIELDS] = {&opts.enh_hud_visible, &opts.enh_hud_size, &opts.enh_hud_x, &opts.enh_hud_y,
                                     &opts.enh_hud_alpha};
/// The rows and the element's settings in step: a new element chosen shows its settings; a row changed is the element's
void enh_hud_sync() {
    static int shown = -1;
    enh_hud_bind(ini_path().substr(0, ini_path().find_last_of("\\/") + 1));
    const int e = std::clamp(opts.enh_hud_sel, 0, HOS_ENH_HUD_ELEMENTS - 1);
    if (e != shown) {
        for (int f = 0; f < ENH_HUD_FIELDS; f++) *enh_hud_rows[f] = enh_hud_value(e * ENH_HUD_FIELDS + f);
        shown = e;
        return;
    }
    for (int f = 0; f < ENH_HUD_FIELDS; f++)
        if (*enh_hud_rows[f] != enh_hud_value(e * ENH_HUD_FIELDS + f)) enh_hud_set(e, f, *enh_hud_rows[f]);
}
bool enh_hud_reset_row(const Row& r) { return !r.value && !strcmp(r.name, "Reset HUD"); }
void enh_hud_reset_press() {
    enh_hud_reset();
    const int e = std::clamp(opts.enh_hud_sel, 0, HOS_ENH_HUD_ELEMENTS - 1);
    for (int f = 0; f < ENH_HUD_FIELDS; f++) *enh_hud_rows[f] = enh_hud_value(e * ENH_HUD_FIELDS + f);
}
