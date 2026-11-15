// (enhanced) Hookshot Enhanced photo mode in the Insert menu's Gameplay tab (enh_photo.h; docs/enhanced/PHOTO_MODE.md).
// Included by gpu/vk/vk_menu.cpp beside enh_graphics_profiles.inc. Two rows that act, as Bug report does:
// - Photo mode: A or Enter switches it; switched on, the menu closes, so the picture is the game's (F8 does the same in play).
// - Take a photo: A or Enter asks a photo of the next present, the game's picture without this menu (F9 in play).
bool enh_photo_row(const Row& r) { return !r.value && (!strcmp(r.name, "Photo mode") || !strcmp(r.name, "Take a photo")); }
bool enh_photo_take_row(const Row& r) { return !r.value && !strcmp(r.name, "Take a photo"); }
/// The row's value cell: the photo mode's state, or what Take a photo does
const char* enh_photo_cell(const Row& r) { return enh_photo_take_row(r) ? "Take" : enh_photo_on() ? "On" : "Off"; }
void enh_photo_press(const Row& r) {
    if (enh_photo_take_row(r)) {
        enh_photo_ask();
        return;
    }
    enh_photo_toggle();
    if (enh_photo_on()) open_now = false;   // (the menu out of the way: the picture is the game's)
}
