// (enhanced) Hookshot Enhanced photo mode, the renderer's side (gpu/vk/enh_photo.cpp; docs/enhanced/PHOTO_MODE.md):
// whether the photo mode is on (the host reads it: HOS_OPT_ENH_PHOTO, host/enh_photo.c), the photos asked for, and what the
// last one did. Shared by vk_menu.cpp (its Gameplay rows), vk_replay.cpp (the capture, enh_photo_shot.inc) and vk_replay's
// option callback.
#pragma once
#include <cstdint>
#include <string>
#include "../../host/enh_product.h"   // (the product's names: ENH_PRODUCT, ENH_STORE_*)

namespace mkwvk {
int enh_photo_on();                 // (1 while the photo mode is on)
void enh_photo_set(int on);
void enh_photo_toggle();
void enh_photo_ask();               // (a photo of the next present)
int enh_photo_take_ask();           // (the asks since the last call: the capture's side)
void enh_photo_keys();              // (each present: F8 the photo mode, F9 a photo, while the game's window has the focus)
std::string enh_photo_folder();     // (where photos go: Pictures\<ENH_PRODUCT>, or $HOME/Pictures/<ENH_PRODUCT>)
void enh_photo_written(const std::string& path, bool ok);
const char* enh_photo_said();       // (the menu's line about the last photo: "Photo saved." or why not; nullptr none)
}   // namespace mkwvk
