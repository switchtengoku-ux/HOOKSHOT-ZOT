// (enhanced) Hookshot Enhanced: graphics profiles in the Insert menu's Graphics tab (docs/enhanced/GRAPHICS_PROFILES.md).
// Included by gpu/vk/vk_menu.cpp inside its namespace, after set_row and save, before the text fields' table: it uses the
// menu's own rows, ini_key, parse_output and save, so a profile is read and written exactly as the options file is.
//
// - Graphics profile (opts.enh_gfx_profile): Left and Right choose among the saved profiles; A or Enter loads the one shown
//   (enh_profile_load, from vk_menu.cpp's input).
// - Save profile as (a text field, enh_profile_field_row): Enter saves the Graphics tab's settings under the name typed.
// The profiles are scripts/enhanced/zot_graphics.py's files: <store>/<name>.ini, the Graphics tab's key=value lines, the store
// %LOCALAPPDATA%\<ENH_STORE_WIN>\graphics-profiles ($XDG_DATA_HOME/<ENH_STORE_POSIX>/graphics-profiles), or
// <ENH_STORE_ENV_PREFIX>GRAPHICS (host/enh_product.h, through enh_photo.h).
// (paths as the game's char strings, UTF-8: the exe's manifest makes that the code page, tests/test_utf8_paths.py)

enum { ENH_PROFILE_NONE, ENH_PROFILE_LOADED, ENH_PROFILE_SAVED, ENH_PROFILE_NONE_YET, ENH_PROFILE_UNREADABLE,
       ENH_PROFILE_BAD_NAME, ENH_PROFILE_NO_FOLDER, ENH_PROFILE_NO_OPTIONS, ENH_PROFILE_UNWRITABLE };   // (enh_profile_texts)

std::string enh_profiles_dir() {
    if (const char* own = enh_store_env("GRAPHICS"); own && *own) return own;
#ifdef _WIN32
    const char* base = getenv("LOCALAPPDATA");
    return base && *base ? std::string(base) + "\\" ENH_STORE_WIN "\\graphics-profiles" : std::string();
#else
    const char* data = getenv("XDG_DATA_HOME");
    std::string base = data && *data ? data : "";
    if (base.empty()) {
        const char* home = getenv("HOME");
        if (!home || !*home) return std::string();
        base = std::string(home) + "/.local/share";
    }
    return base + "/" ENH_STORE_POSIX "/graphics-profiles";
#endif
}
std::string enh_profile_file(const std::string& name) {
#ifdef _WIN32
    return enh_profiles_dir() + "\\" + name + ".ini";
#else
    return enh_profiles_dir() + "/" + name + ".ini";
#endif
}
/// A profile name as the tool takes it: 1 to 40 letters, digits, spaces, '-' or '_', a letter or digit first
bool enh_profile_name_ok(const char* s) {
    const size_t n = strlen(s);
    if (!n || n > 40 || !isalnum((unsigned char)s[0])) return false;
    for (size_t i = 0; i < n; i++)
        if (!isalnum((unsigned char)s[i]) && s[i] != ' ' && s[i] != '-' && s[i] != '_') return false;
    return true;
}
std::vector<std::string> enh_profiles;   // (the saved profiles' names, sorted ignoring case)
std::chrono::steady_clock::time_point enh_profiles_read;
const char* enh_profile_said = nullptr;   // (the help's line after a load or a save: menu_i18n.h translates it)

/// The profiles folder read again, at most once a second (the row's text asks for it every frame the menu draws)
void enh_profiles_refresh(bool now = false) {
    const auto t = std::chrono::steady_clock::now();
    if (!now && enh_profiles_read.time_since_epoch().count() && t - enh_profiles_read < std::chrono::seconds(1)) return;
    enh_profiles_read = t;
    std::vector<std::string> found;
    std::error_code ec;
    const std::string dir = enh_profiles_dir();
    if (!dir.empty())
        for (const auto& e : std::filesystem::directory_iterator(std::filesystem::path(dir), ec)) {
            const std::string n = e.path().filename().string();
            if (n.size() > 4 && n.compare(n.size() - 4, 4, ".ini") == 0 && enh_profile_name_ok(n.substr(0, n.size() - 4).c_str()))
                found.push_back(n.substr(0, n.size() - 4));
        }
    std::sort(found.begin(), found.end(), [](const std::string& a, const std::string& b) {
        return std::lexicographical_compare(a.begin(), a.end(), b.begin(), b.end(),
                                            [](char x, char y) { return tolower((unsigned char)x) < tolower((unsigned char)y); });
    });
    enh_profiles = found;
    for (Row& r : rows)
        if (r.value == &opts.enh_gfx_profile) r.hi = enh_profiles.empty() ? 0 : (int)enh_profiles.size() - 1;
    opts.enh_gfx_profile = std::clamp(opts.enh_gfx_profile, 0, enh_profiles.empty() ? 0 : (int)enh_profiles.size() - 1);
}
const char* tx_enh_profile(int v) {
    enh_profiles_refresh();
    if (enh_profiles.empty()) return enh_profile_texts[ENH_PROFILE_NONE];
    static std::string shown;
    shown = enh_profiles[std::clamp(v, 0, (int)enh_profiles.size() - 1)];
    return shown.c_str();
}
bool enh_profile_row(const Row& r) { return r.value == &opts.enh_gfx_profile; }
/// The Graphics tab's rows a profile holds: every one with a value, but the profile row itself
bool enh_profile_holds(const Row& r) { return r.tab == TAB_GRAPHICS && r.value && r.value != &opts.enh_gfx_profile; }

/// A or Enter on Graphics profile: the profile shown loaded into the Graphics rows, as the options file's lines are at the
/// start (menu_init), then saved; rows that take a restart are asked about at the next close, as when changed by hand
void enh_profile_load() {
    enh_profiles_refresh(true);
    if (enh_profiles.empty()) {
        enh_profile_said = enh_profile_texts[ENH_PROFILE_NONE_YET];
        return;
    }
    const std::string name = enh_profiles[std::clamp(opts.enh_gfx_profile, 0, (int)enh_profiles.size() - 1)];
    FILE* f = fopen(enh_profile_file(name).c_str(), "r");
    if (!f) {
        enh_profile_said = enh_profile_texts[ENH_PROFILE_UNREADABLE];
        return;
    }
    char line[128];
    int follow = -1, loaded = 0;
    while (fgets(line, sizeof line, f)) {
        line[strcspn(line, "\r\n")] = 0;
        char* eq = strchr(line, '=');
        if (!eq || line[0] == '#') continue;
        *eq = 0;
        for (Row& r : rows) {
            if (!enh_profile_holds(r) || strcmp(line, ini_key(r))) continue;
            if (r.value == &opts.ultrawide) follow = atoi(eq + 1) == 1;   // (1: the monitor's shape; set with the size, below)
            else *r.value = r.value == &opts.output_res ? parse_output(eq + 1) : std::min(std::max(atoi(eq + 1), r.lo), r.hi);
            env_release(r.value);
            loaded++;
        }
    }
    fclose(f);
    // (the Aspect ratio as the file keeps it: the monitor's shape, or the Output resolution's own)
    opts.ultrawide = aspect_of_choice(opts.output_res, follow == 1);
    for (Row& r : rows) {
        if (r.value == &opts.output_res) r.hi = last_choice();
        if (r.value == &opts.ultrawide) r.hi = aspect_last();
    }
    // (the mip trimming of the preset loaded, as the options file's load gives it to a file without memory_budget;
    // the VRAM budgets themselves are the card's since v2.3.2, texture_budget.h and mirror_budget.h)
    opts.budget = opts.preset > 0 && opts.preset != kAutoPreset ? opts.preset : 0;
    samplers_changed();
    temporal_reset_failure();
    menu_refresh = true;
    {
        int now[mr::kMax];
        restart_values(now);
        restart_state.note(now);
    }
    save();
    enh_profile_said = enh_profile_texts[ENH_PROFILE_LOADED];
    logf("menu: graphics profile %s loaded (%d settings)", name.c_str(), loaded);
}

bool enh_profile_char(char c) { return isalnum((unsigned char)c) || c == ' ' || c == '-' || c == '_'; }
TextField enh_profile_field{{}, 0, 0, 40, enh_profile_char, nullptr};
/// Enter in Save profile as: the Graphics tab's lines of the options file (save() writes them first, in its own form), kept as
/// the profile of that name. nullptr when saved, else why not
const char* enh_profile_save_apply() {
    char name[sizeof enh_profile_field.text];
    snprintf(name, sizeof name, "%s", enh_profile_field.text);
    for (int n = (int)strlen(name); n > 0 && name[n - 1] == ' '; n--) name[n - 1] = 0;
    if (!enh_profile_name_ok(name)) return enh_profile_texts[ENH_PROFILE_BAD_NAME];
    const std::string dir = enh_profiles_dir();
    if (dir.empty()) return enh_profile_texts[ENH_PROFILE_NO_FOLDER];
    std::error_code ec;
    std::filesystem::create_directories(std::filesystem::path(dir), ec);
    save();
    FILE* in = fopen(ini_path().c_str(), "r");
    if (!in) return enh_profile_texts[ENH_PROFILE_NO_OPTIONS];
    std::string body = "# " ENH_ENHANCED " graphics profile: the Graphics tab of " ENH_OPTIONS " (saved in the menu)\n";
    char line[128];
    while (fgets(line, sizeof line, in)) {
        const char* eq = strchr(line, '=');
        if (!eq) continue;
        const std::string key(line, (size_t)(eq - line));
        for (const Row& r : rows)
            if (enh_profile_holds(r) && key == ini_key(r)) {
                body += line;
                if (body.back() != '\n') body += '\n';
                break;
            }
    }
    fclose(in);
    const std::string path = enh_profile_file(name), part = path + ".new";
    FILE* out = fopen(part.c_str(), "w");
    if (!out) return enh_profile_texts[ENH_PROFILE_UNWRITABLE];
    const bool ok = fwrite(body.data(), 1, body.size(), out) == body.size();
    if (fclose(out) != 0 || !ok) {
        remove(part.c_str());
        return enh_profile_texts[ENH_PROFILE_UNWRITABLE];
    }
    std::filesystem::rename(std::filesystem::path(part), std::filesystem::path(path), ec);
    if (ec) {
        remove(part.c_str());
        return enh_profile_texts[ENH_PROFILE_UNWRITABLE];
    }
    enh_profiles_refresh(true);
    for (int i = 0; i < (int)enh_profiles.size(); i++)
        if (enh_profiles[i] == name) opts.enh_gfx_profile = i;
    enh_profile_said = enh_profile_texts[ENH_PROFILE_SAVED];
    logf("menu: graphics profile %s saved", name);
    return nullptr;
}
// (the Save profile as row's field, as vk_menu.cpp field_row finds it: beside field_rows, which keeps upstream's one entry)
const FieldRow enh_profile_field_row{"Save profile as", &enh_profile_field, enh_profile_save_apply};
