// (enhanced) Hookshot Enhanced HUD editor, the renderer's side (enh_hud.h; docs/enhanced/HUD_EDITOR.md).
// The settings of the HUD's elements (HOS_ENH_HUD_ELEMENTS, gpu/vk/vk_api.h) live here, apart from the menu's own options:
// the menu's HUD rows show the element chosen (gpu/vk/enh_menu_hud.inc), the host reads them through the option callback.
// They are kept in hookshot_options.ini (enh_hud_store.h's lines), which gpu/vk/vk_menu.cpp save() writes whole and moves
// over the old file: read from it the first time a value is asked for. An options file with none of those lines yet
// takes them from the enh_hud.ini of before (beside the options file, or beside the game), until the next save.
#include "enh_hud.h"
#include "enh_hud_store.h"
#include "vk_api.h"
#include "vk_paths.h"   // (options_path, game_module_path)
#include <atomic>
#include <cstdio>
#include <mutex>
#include <string>

namespace mkwvk {
void logf(const char* fmt, ...);

namespace {
std::mutex mu;
enh_hud_store::Store store;
enh_hud_store::Slot slots[enh_hud_store::SLOTS];   // (the saved HUDs: the HUD slot rows)
bool loaded = false;
std::atomic<int> generation{1};

/// The old enh_hud.ini in a folder: true when it had at least one setting
bool read_legacy(const std::string& folder) {
    const std::string path = folder + "enh_hud.ini";
    FILE* f = fopen(path.c_str(), "r");
    if (!f) return false;
    bool any = false;
    char line[64];
    while (fgets(line, sizeof line, f)) any |= enh_hud_store::read_legacy_line(store, line);
    fclose(f);
    if (any) logf("enhanced: HUD editor: settings read from %s; the options file keeps them from the next save", path.c_str());
    return any;
}

void load_locked() {
    if (loaded) return;
    const std::string path = options_path();
    if (path.empty()) {   // (no options file this run, or not known yet: the defaults, asked again next time)
        store.reset();
        return;
    }
    loaded = true;
    store.reset();
    bool found = false, dungeon = false;
    if (FILE* f = fopen(path.c_str(), "r")) {
        char line[256];
        while (fgets(line, sizeof line, f)) {
            char* eq = strchr(line, '=');
            if (!eq) continue;
            *eq = 0;
            if (enh_hud_store::read_slot_key(slots, line, eq + 1)) continue;
            const bool mine = enh_hud_store::read_key(store, line, eq + 1);
            found |= mine, dungeon |= mine && !strncmp(line, "enh_hud_dungeon_map_", 20);
        }
        fclose(f);
    }
    if (!found && !read_legacy(path.substr(0, path.find_last_of("\\/") + 1))) {
        char exe[MAX_PATH];
        const std::string game(exe, game_module_path(exe, MAX_PATH));
        read_legacy(game.substr(0, game.find_last_of("\\/") + 1));
    }
    // (a file from before the dungeon minimap was an element of its own: it is where the minimap is, as it was)
    if (!dungeon) enh_hud_store::inherit_dungeon_map(store);
    for (auto& s : slots)
        if (s.used && !s.dungeon_seen) enh_hud_store::inherit_dungeon_map(s.s);
}
}   // namespace

int enh_hud_default(int field) { return enh_hud_store::default_of(field); }

int enh_hud_value(int index) {
    std::lock_guard lk(mu);
    load_locked();
    if (index < 0 || index >= HOS_ENH_HUD_ELEMENTS * ENH_HUD_FIELDS) return 0;
    return store.v[index / ENH_HUD_FIELDS][index % ENH_HUD_FIELDS];
}

int enh_hud_generation() { return generation.load(std::memory_order_acquire); }

bool enh_hud_set(int element, int field, int value) {
    std::lock_guard lk(mu);
    load_locked();
    if (!store.set(element, field, value)) return false;
    generation.fetch_add(1, std::memory_order_release);
    return true;
}

void enh_hud_reset() {
    {
        std::lock_guard lk(mu);
        load_locked();
        store.reset();
        generation.fetch_add(1, std::memory_order_release);
    }
    logf("enhanced: HUD editor: every element as the game draws it");
}

bool enh_hud_preset_apply(int preset) {
    std::lock_guard lk(mu);
    load_locked();
    if (!enh_hud_store::preset_apply(store, preset)) return false;
    generation.fetch_add(1, std::memory_order_release);
    return true;
}

int enh_hud_preset_now() {
    std::lock_guard lk(mu);
    load_locked();
    return enh_hud_store::preset_of(store);
}

void enh_hud_save_lines(FILE* f) {
    std::lock_guard lk(mu);
    load_locked();
    enh_hud_store::write_lines(store, f);
    enh_hud_store::write_slot_lines(slots, f);
}

void enh_hud_slot_save(int slot, int scale, int fade) {
    if (slot < 0 || slot >= enh_hud_store::SLOTS) return;
    {
        std::lock_guard lk(mu);
        load_locked();
        slots[slot].s = store, slots[slot].scale = scale, slots[slot].fade = fade, slots[slot].used = true;
    }
    logf("enhanced: HUD editor: the HUD saved to slot %d", slot + 1);
}

bool enh_hud_slot_load(int slot, int* scale, int* fade) {
    if (slot < 0 || slot >= enh_hud_store::SLOTS) return false;
    {
        std::lock_guard lk(mu);
        load_locked();
        if (!slots[slot].used) return false;
        store = slots[slot].s, *scale = slots[slot].scale, *fade = slots[slot].fade;
        generation.fetch_add(1, std::memory_order_release);
    }
    logf("enhanced: HUD editor: the HUD of slot %d", slot + 1);
    return true;
}
}   // namespace mkwvk
