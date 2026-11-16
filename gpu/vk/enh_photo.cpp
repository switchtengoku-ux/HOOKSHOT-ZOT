// (enhanced) Hookshot Enhanced photo mode, the renderer's side (enh_photo.h; docs/enhanced/PHOTO_MODE.md).
// The photo mode's state lives here: the menu's Photo mode row and F8 switch it, the host reads it every present
// (HOS_OPT_ENH_PHOTO) and from it hides the HUD, holds the world still and gives the sticks to the free camera
// (host/enh_photo.c). A photo is asked by F9 or the menu's Take a photo row and taken by vk_replay.cpp at the next present,
// at the picture's own size (enh_photo_shot.inc).
#include "enh_photo.h"
#include <atomic>
#include <cstdlib>
#include <mutex>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

namespace mkwvk {
void logf(const char* fmt, ...);

namespace {
std::atomic<int> photo_on{0}, photo_asks{0};
std::mutex said_mu;
std::string said;   // (said_mu)
}   // namespace

int enh_photo_on() { return photo_on.load(std::memory_order_relaxed); }
void enh_photo_set(int on) {
    if (photo_on.exchange(on ? 1 : 0, std::memory_order_relaxed) != (on ? 1 : 0))
        logf("enhanced: photo mode %s", on ? "on" : "off");
}
void enh_photo_toggle() { enh_photo_set(!enh_photo_on()); }
void enh_photo_ask() { photo_asks.fetch_add(1, std::memory_order_relaxed); }
int enh_photo_take_ask() { return photo_asks.exchange(0, std::memory_order_relaxed); }

void enh_photo_keys() {
#ifdef _WIN32
    static bool was8, was9;
    DWORD pid = 0;
    if (const HWND fg = GetForegroundWindow()) GetWindowThreadProcessId(fg, &pid);
    const bool focused = pid == GetCurrentProcessId();
    const bool f8 = focused && (GetAsyncKeyState(VK_F8) & 0x8000) != 0, f9 = focused && (GetAsyncKeyState(VK_F9) & 0x8000) != 0;
    if (f8 && !was8) enh_photo_toggle();
    if (f9 && !was9) enh_photo_ask();
    was8 = f8, was9 = f9;
#endif
}

std::string enh_photo_folder() {
#ifdef _WIN32
    // (the user's own Pictures folder, as Windows knows it: moved to OneDrive or another drive, it is there, not
    // %USERPROFILE%\Pictures. shell32 and ole32 loaded at the first use, as vk_menu.cpp share_downloads does: hookshot_vk.dll
    // imports only kernel32, user32, gdi32, advapi32 and the UCRT)
    using KnownFolderFn = HRESULT(WINAPI*)(const GUID&, DWORD, HANDLE, wchar_t**);
    using FreeFn = void(WINAPI*)(void*);
    static const auto known = (KnownFolderFn)(void*)GetProcAddress(LoadLibraryExW(L"shell32.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32), "SHGetKnownFolderPath");
    static const auto free_mem = (FreeFn)(void*)GetProcAddress(LoadLibraryExW(L"ole32.dll", nullptr, LOAD_LIBRARY_SEARCH_SYSTEM32), "CoTaskMemFree");
    static const GUID pictures = {0x33E28130, 0x4E1E, 0x4676, {0x83, 0x5A, 0x98, 0x39, 0x5C, 0x3B, 0xC3, 0xBB}};   // (FOLDERID_Pictures)
    wchar_t* w = nullptr;
    std::string dir;
    if (known && SUCCEEDED(known(pictures, 0, nullptr, &w)) && w) {
        char b[MAX_PATH * 4];
        if (WideCharToMultiByte(CP_UTF8, 0, w, -1, b, sizeof b, nullptr, nullptr) > 0) dir = b;
    }
    if (w && free_mem) free_mem(w);
    if (!dir.empty()) return dir + "\\" ENH_PRODUCT;
    const char* home = getenv("USERPROFILE");
    return home && *home ? std::string(home) + "\\Pictures\\" ENH_PRODUCT : std::string("photos");
#else
    const char* home = getenv("HOME");
    return home && *home ? std::string(home) + "/Pictures/" ENH_PRODUCT : std::string("photos");
#endif
}

void enh_photo_written(const std::string& path, bool ok) {
    std::lock_guard lk(said_mu);
    said = ok ? "Photo saved." : "The photo could not be saved.";
    logf("enhanced: photo %s %s", ok ? "saved to" : "could not be saved to", path.c_str());
}
const char* enh_photo_said() {
    std::lock_guard lk(said_mu);
    static std::string copy;
    copy = said;
    return copy.empty() ? nullptr : copy.c_str();
}
}   // namespace mkwvk
