/* (enhanced) Hookshot Enhanced, photo mode (docs/enhanced/PHOTO_MODE.md), the host's side: the HUD hidden, the world held
   still and the free camera, each from a switch or a key, and all three while the photo mode is on.

   The photo mode (F8, or the Insert menu's Gameplay row Photo mode) lives in the renderer (gpu/vk/enh_photo.cpp); its
   state is read here every present (HOS_OPT_ENH_PHOTO). While it is on, the HUD is hidden, the world held still and the
   debug tools' free camera moves the view (host/hos_main.c hos_oot_free_view and host/nn_hid.c ask hos_enh_photo_camera),
   whether the debug tools are on or not; the game gets no buttons. F9, or the row Take a photo, saves a PNG of the
   picture at its own size (gpu/vk/enh_photo_shot.inc).

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
   half second: "hud=1" and "freeze=1" in it switch those on (anything else off); "photo=1" or "photo=0" sets the photo
   mode; "shot=<n>", a number other than the last one read, asks a photo (rx_option_set: gpu/vk/vk_menu.cpp
   menu_option_set). */
#include <stdio.h>
#include "hos.h"
#include "../gpu/vk/vk_api.h"   /* (HOS_OPT_ENH_PHOTO) */
#include "enh_product.h"   /* (enh_env: the switches' names) */
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

static volatile int hud_hidden, frozen, read_switches;   /* (the switches and keys F6, F7 alone) */
static volatile int photo_on;                            /* (the photo mode: all three) */
int rx_option(int id, int otherwise);   /* host/rx_backend.c */

/* the free camera's view and sticks while the photo mode is on (weak in host/hos_main.c and host/nn_hid.c) */
int hos_enh_photo_camera(void) { return photo_on; }

static int env_set(const char *name) {   /* (an Enhanced switch: enh_env) */
    const char *v = enh_env(name);
    return v && *v && atoi(v) != 0;
}

static void switches(void) {
    if (read_switches) return;
    read_switches = 1;
    hud_hidden = env_set("HUD_HIDE");
    frozen = env_set("FREEZE");
    if (hud_hidden || frozen)
        hos_log("enhanced: photo: HUD %s, world %s (F6 and F7 switch them)", hud_hidden ? "hidden" : "shown",
                frozen ? "held still" : "moving");
}

int hos_enh_hud_hidden(void) {
    switches();
    return hud_hidden || photo_on;
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
    {   /* (enhanced) the HUD editor's settings (host/enh_hud.c) */
        void hos_enh_hud_tick(void);
        hos_enh_hud_tick();
    }
    {   /* (the photo mode, the renderer's: its change remakes the panes, as the HUD switch does) */
        const int on = rx_option(HOS_OPT_ENH_PHOTO, 0) != 0;
        if (on != photo_on) {
            photo_on = on;
            extern volatile uint32_t hos_wide_ui_force;
            hos_wide_ui_force = 3;
            hos_log("enhanced: photo mode %s: HUD, world and camera %s", on ? "on" : "off", on ? "taken" : "given back");
        }
    }
    static const char *file;
    static int looked;
    static int64_t next;
    if (!looked) looked = 1, file = enh_env("PHOTO_FILE");
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
            void rx_option_set(int id, int value);   /* host/rx_backend.c */
            static int last_photo = -1, last_shot = -1;
            const int want = strstr(text, "photo=1") ? 1 : strstr(text, "photo=0") ? 0 : -1;
            if (want >= 0 && want != last_photo) rx_option_set(HOS_OPT_ENH_PHOTO, want), last_photo = want;
            const char *shot = strstr(text, "shot=");
            const int shot_n = shot ? atoi(shot + 5) : -1;
            if (shot_n >= 0 && shot_n != last_shot) {
                if (last_shot >= 0) rx_option_set(HOS_OPT_ENH_PHOTO, 2);   /* (the first number read is the start) */
                last_shot = shot_n;
            }
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
    {   /* (enhanced) the HUD editor's moves, sizes and opacities (host/enh_hud.c) */
        void hos_enh_hud_edit(Ctx *c, uint64_t pane, uint64_t parent);
        hos_enh_hud_edit(c, pane, parent);
    }
    if (!(hud_hidden || photo_on) || parent || !pane) return;
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
    if (!frozen && !photo_on) return bits;
    const float f = ENH_FREEZE_SECONDS;
    uint32_t b;
    memcpy(&b, &f, 4);
    return b;
}
