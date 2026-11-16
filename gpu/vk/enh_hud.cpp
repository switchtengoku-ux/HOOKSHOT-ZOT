// (enhanced) Hookshot Enhanced HUD editor, the renderer's side (enh_hud.h; docs/enhanced/HUD_EDITOR.md).
// The settings of the HUD's elements (HOS_ENH_HUD_ELEMENTS, gpu/vk/vk_api.h) live here, apart from the menu's own options:
// the menu's HUD rows show the element chosen (gpu/vk/enh_menu_hud.inc), the host reads them through the option callback.
// enh_hud.ini, beside the options file: one "<element>.<field>=<value>" line each, written whole at each change.
#include "enh_hud.h"
#include "../../host/enh_product.h"   // (ENH_ENHANCED: the file's first line)
#include "vk_api.h"
#include "vk_paths.h"   // (game_module_path: the options file's folder)
#include <algorithm>
#include <atomic>
#include <cstdio>
#include <cstdlib>
#include <mutex>

namespace mkwvk {
void logf(const char* fmt, ...);

namespace {
std::mutex mu;
int values[HOS_ENH_HUD_ELEMENTS][ENH_HUD_FIELDS];
bool ready = false;
std::string file;   // (mu: empty until bound)
const int lo[ENH_HUD_FIELDS] = {0, 25, -800, -800, 10}, hi[ENH_HUD_FIELDS] = {1, 200, 800, 800, 100};

void bind_locked(const std::string& folder);
/// The options file's folder, found the first time a setting is asked for (the host asks before the menu ever opens)
void ready_locked() {
    if (!file.empty()) return;
    char exe[MAX_PATH];
    const DWORD n = game_module_path(exe, MAX_PATH);
    const std::string path(exe, n);
    bind_locked(path.substr(0, path.find_last_of("\\/") + 1));
}
void defaults_locked() {
    for (auto& e : values)
        for (int f = 0; f < ENH_HUD_FIELDS; f++) e[f] = enh_hud_default(f);
    ready = true;
}
void write_locked() {
    if (file.empty()) return;
    const std::string part = file + ".new";
    FILE* f = fopen(part.c_str(), "w");
    if (!f) return;
    fprintf(f, "# " ENH_ENHANCED " HUD editor (the Insert menu's HUD rows): element.field=value\n");
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++)
        for (int k = 0; k < ENH_HUD_FIELDS; k++) fprintf(f, "%d.%d=%d\n", e, k, values[e][k]);
    const bool ok = fclose(f) == 0;
    std::remove(file.c_str());
    if (!ok || std::rename(part.c_str(), file.c_str()) != 0) std::remove(part.c_str());
}
}   // namespace

int enh_hud_default(int field) { return field == ENH_HUD_VISIBLE ? 1 : field == ENH_HUD_SIZE || field == ENH_HUD_ALPHA ? 100 : 0; }

int enh_hud_value(int index) {
    std::lock_guard lk(mu);
    ready_locked();
    if (index < 0 || index >= HOS_ENH_HUD_ELEMENTS * ENH_HUD_FIELDS) return 0;
    return values[index / ENH_HUD_FIELDS][index % ENH_HUD_FIELDS];
}

void enh_hud_set(int element, int field, int value) {
    if (element < 0 || element >= HOS_ENH_HUD_ELEMENTS || field < 0 || field >= ENH_HUD_FIELDS) return;
    std::lock_guard lk(mu);
    ready_locked();
    value = std::clamp(value, lo[field], hi[field]);
    if (values[element][field] == value) return;
    values[element][field] = value;
    write_locked();
}

void enh_hud_reset() {
    std::lock_guard lk(mu);
    ready_locked();
    defaults_locked();
    write_locked();
    logf("enhanced: HUD editor: every element as the game draws it");
}

void enh_hud_bind(const std::string& folder) {
    std::lock_guard lk(mu);
    bind_locked(folder);
}
namespace {
void bind_locked(const std::string& folder) {
    if (!file.empty()) return;
    file = folder + "enh_hud.ini";
    if (!ready) defaults_locked();
    if (FILE* f = fopen(file.c_str(), "r")) {
        char line[64];
        while (fgets(line, sizeof line, f)) {
            int e, k, v;
            if (line[0] != '#' && sscanf(line, "%d.%d=%d", &e, &k, &v) == 3 && e >= 0 && e < HOS_ENH_HUD_ELEMENTS && k >= 0 &&
                k < ENH_HUD_FIELDS)
                values[e][k] = std::clamp(v, lo[k], hi[k]);
        }
        fclose(f);
    }
}
}   // namespace
}   // namespace mkwvk
