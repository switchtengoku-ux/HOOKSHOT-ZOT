/* (enhanced) Hookshot Enhanced, photo mode prototype (docs/enhanced/PHOTO_MODE.md): the HUD hidden, and the world held
   still, each from a switch at the start or a key in play.

   HUD hidden (HOOKSHOT_ENH_HUD_HIDE=1, or F6): host/hos_wide_ui.c hos_wide_ui_placed hands every 2D pane whose transform
   the game has just made to hos_enh_hud_placed. A root pane (no parent) of one of the HUD's layouts (ENH_HUD_LAYOUTS, the
   same names as hos_wide_ui.c's HUD_LAYOUTS) gets its 3x3 part set to 0: the panes made from it, the whole group, are made
   from a point and draw nothing. hos_wide_ui_force makes every pane remake its transform when the switch changes, so the
   game's own transforms come back when it is turned off. Unlike hos_wide_ui.c's own moves, this works at 16:9 too: it
   reads the layout's name itself and does not need that file's plan.

   World held still (HOOKSHOT_ENH_FREEZE=1, or F7): host/nn_vi.c gives the game its frame step through hos_frame_seconds_bits
   (nx2/oot_patches.py patch_frame_seconds: the engine's step is its base times that many seconds). hos_enh_step_bits puts
   ENH_FREEZE_SECONDS there instead, so the game clock and what moves by it barely advance while the picture is still drawn
   and presented. The debug tools' free camera keeps its own clock (host/hos_main.c oot_build_free_view).

   The keys count only while the game's window has the focus, on Windows.
   HOOKSHOT_ENH_PHOTO_FILE=<path> (for driven test runs, which cannot press keys): while that file exists, it is read every
   half second and sets both, "hud=1" and "freeze=1" in it on (anything else off). */
#include <stdio.h>
#include "hos.h"
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#define WIN32_LEAN_AND_MEAN
#include <windows.h>
#endif

#define ENH_FREEZE_SECONDS 1e-6f
enum { ENH_LAYOUT_RES = 0xf8, ENH_RES_NAME = 0x18, ENH_PANE_LAYOUT = 0x18, ENH_PANE_XX = 0x28 };   /* (hos_wide_ui.c's) */

static const char *const ENH_HUD_LAYOUTS[] = {"PlayerStatus_00", "Location_00", "MapMenu_00", "Talk_00", "MessageLog_01",
                                              "PlayerStatus3D_00", "Pointer_00", "BalloonMessage_00"};

static volatile int hud_hidden, frozen, read_switches;

static int env_set(const char *name) {
    const char *v = getenv(name);
    return v && *v && atoi(v) != 0;
}

static void switches(void) {
    if (read_switches) return;
    read_switches = 1;
    hud_hidden = env_set("HOOKSHOT_ENH_HUD_HIDE");
    frozen = env_set("HOOKSHOT_ENH_FREEZE");
    if (hud_hidden || frozen)
        hos_log("enhanced: photo: HUD %s, world %s (F6 and F7 switch them)", hud_hidden ? "hidden" : "shown",
                frozen ? "held still" : "moving");
}

int hos_enh_hud_hidden(void) {
    switches();
    return hud_hidden;
}

static void set_hud(int on) {
    if (on == hud_hidden) return;
    hud_hidden = on;
    extern volatile uint32_t hos_wide_ui_force;
    hos_wide_ui_force = 3;   /* (every pane remakes its transform: hidden now, or the game's own again) */
    hos_log("enhanced: photo: HUD %s", on ? "hidden" : "shown");
}
static void set_frozen(int on) {
    if (on == frozen) return;
    frozen = on;
    hos_log("enhanced: photo: world %s", on ? "held still" : "moving");
}

/* Each present (hos_wide_ui_tick): F6 and F7, pressed while the game has the focus; the test file */
void hos_enh_photo_tick(void) {
    switches();
    static const char *file;
    static int looked;
    static int64_t next;
    if (!looked) looked = 1, file = getenv("HOOKSHOT_ENH_PHOTO_FILE");
    if (file && *file && hos_now_ns() >= next) {
        next = hos_now_ns() + 500000000LL;
        FILE *f = fopen(file, "r");
        if (f) {
            char text[64] = "";
            const size_t n = fread(text, 1, sizeof text - 1, f);
            fclose(f);
            text[n] = 0;
            set_hud(strstr(text, "hud=1") != NULL);
            set_frozen(strstr(text, "freeze=1") != NULL);
        }
    }
#ifdef _WIN32
    static int was6, was7;
    DWORD pid = 0;
    const HWND fg = GetForegroundWindow();
    if (fg) GetWindowThreadProcessId(fg, &pid);
    const int focused = pid == GetCurrentProcessId();
    const int f6 = focused && (GetAsyncKeyState(VK_F6) & 0x8000) != 0, f7 = focused && (GetAsyncKeyState(VK_F7) & 0x8000) != 0;
    if (f6 && !was6) set_hud(!hud_hidden);
    if (f7 && !was7) set_frozen(!frozen);
    was6 = f6, was7 = f7;
#endif
}

static int guest_name_is(uint64_t g, const char *want) {
    for (size_t i = 0;; i++) {
        const char ch = (char)recomp_load8(NULL, g + i);
        if (ch != want[i]) return 0;
        if (!ch) return 1;
    }
}

/* A pane's transform just made (host/hos_wide_ui.c hos_wide_ui_placed, before its own moves): a HUD layout's root made a
   point while the HUD is hidden */
void hos_enh_hud_placed(Ctx *c, uint64_t pane, uint64_t parent) {
    if (!hud_hidden || parent || !pane) return;
    const uint64_t layout = recomp_load64(c, pane + ENH_PANE_LAYOUT);
    const uint64_t res = layout ? recomp_load64(c, layout + ENH_LAYOUT_RES) : 0;
    const uint64_t name = res ? recomp_load64(c, res + ENH_RES_NAME) : 0;
    int hud = 0;   /* (the name read each time: a layout let go leaves its address to another, a menu's maybe) */
    for (size_t i = 0; name && i < sizeof ENH_HUD_LAYOUTS / sizeof ENH_HUD_LAYOUTS[0] && !hud; i++)
        hud = guest_name_is(name, ENH_HUD_LAYOUTS[i]);
    if (!hud) return;
    for (int k = 0; k < 9; k++) recomp_store32(c, pane + ENH_PANE_XX + 4 * (uint64_t)k, 0);
}

/* host/nn_vi.c: the frame step handed to the game, as a float's bits (0: the game's own) */
uint32_t hos_enh_step_bits(uint32_t bits) {
    if (!frozen) return bits;
    const float f = ENH_FREEZE_SECONDS;
    uint32_t b;
    memcpy(&b, &f, 4);
    return b;
}
