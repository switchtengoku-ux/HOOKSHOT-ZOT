/* (enhanced) Hookshot Enhanced HUD editor, the host's side (docs/enhanced/HUD_EDITOR.md): each HUD element shown or
   hidden, its size, its place and its opacity, from the Insert menu's HUD editor rows (gpu/vk/enh_menu_hud.inc).

   host/enh_photo.c hos_enh_hud_placed hands every 2D pane whose transform the game has just made to hos_enh_hud_edit
   (host/hos_wide_ui.c hos_wide_ui_placed, before that file's own moves). A pane belongs to an element when it is the
   element's own pane (ENH_HUD_ELEMENTS: a layout and a pane name, or the layout's root) or when its parent belongs to it:
   the game makes a parent's transform before its children's, so a small table of panes is enough (elem_of).
   On the element's own pane:
   - hidden: its 3x3 part set to 0, the whole element drawn from a point (as the photo mode's hidden HUD);
   - size: its 3x3 part times the size, about its own origin (an element named by its pane: its corner), or for a whole
     layout (origin at the canvas's middle) about the 16:9 canvas's corner or edge it sits on (ENH_HUD_ELEMENTS' anchor);
   - place: its translation moved by the offsets, in the HUD canvas's units (3840 x 2160, y up).
   On every pane of the element that draws (a picture, a text box, a window: not a group, whose alpha the game multiplies
   into its children, so an element nested three deep came out at an eighth): the opacity, as min(the pane's own, the
   setting) in its alpha (+0x74), so the game's fades still run. While an element is not opaque every pane remakes its
   transform each present (hos_wide_ui_force), since a pane's alpha can change with no new transform.
   The pause menu's map page is MapMenu_00 as the minimap is: it is told apart as host/hos_wide_ui.c does (its icons'
   group N_MapIcon_00 at the canvas's origin) and never edited.
   The settings come from the renderer (rx_option HOS_OPT_ENH_HUD + element * 5 + field), read once a present. */
#include "hos.h"
#include "../gpu/vk/vk_api.h"   /* (HOS_OPT_ENH_HUD) */
#include <math.h>
#include <stdlib.h>
#include <string.h>

enum { L_RES = 0xf8, R_NAME = 0x18, R_PANE_NAMES = 0x20, L_PANES = 0x100, L_COUNT = 0x13c, P_SIZE = 0xb0,
       P_LAYOUT = 0x18, P_XX = 0x28, P_X = 0x4c, P_Y = 0x50, P_W = 0x58, P_H = 0x5c, P_ALPHA = 0x74, P_FLAGS = 0xa8 };
enum { A_BOX_TL, A_BOX_TR, A_TL, A_TR, A_BL, A_BR, A_TOP, A_BOTTOM };
       /* (what an element keeps when it is resized: its own pane's top left or top right corner, or a corner or edge of the
          HUD's 16:9 canvas for a whole layout, whose root's origin is the canvas's middle) */

typedef struct { const char *layout, *pane; int anchor; } HudElement;
/* (the order is the menu's and the option ids': gpu/vk/enh_menu_hud.inc ENH_HUD_NAMES) */
static const HudElement ENH_HUD_ELEMENTS[HOS_ENH_HUD_ELEMENTS] = {
    {"PlayerStatus_00", "Pa_HeartGauge_00", A_BOX_TL},   /* hearts */
    {"PlayerStatus_00", "Pa_MpGauge_00", A_BOX_TL},      /* magic */
    {"PlayerStatus_00", "Pa_GuideCross_00", A_BOX_TL},   /* the item buttons under them */
    {"PlayerStatus_00", "N_ScaleR_00", A_BOX_TR},        /* the item and action buttons at the top right */
    {"MapMenu_00", NULL, A_BR},                      /* the minimap */
    {"Location_00", NULL, A_TOP},                    /* the place's name */
};
enum { F_VISIBLE, F_SIZE, F_X, F_Y, F_ALPHA };

static struct { int visible, size, x, y, alpha; } set[HOS_ENH_HUD_ELEMENTS];
static int any_alpha, any_edit, restoring;   /* (restoring: presents left to put back the panes an opacity lowered) */
int rx_option(int id, int otherwise);   /* host/rx_backend.c */
extern volatile uint32_t hos_wide_ui_force;

/* Each present (host/enh_photo.c hos_enh_photo_tick): the settings, and the panes remade when they change */
void hos_enh_hud_tick(void) {
    static int last[HOS_ENH_HUD_ELEMENTS * 5], first = 1;
    int now[HOS_ENH_HUD_ELEMENTS * 5], changed = first;
    first = 0;
    any_alpha = any_edit = 0;
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
        const int base = HOS_OPT_ENH_HUD + e * 5;
        set[e].visible = rx_option(base + F_VISIBLE, 1);
        set[e].size = rx_option(base + F_SIZE, 100);
        set[e].x = rx_option(base + F_X, 0);
        set[e].y = rx_option(base + F_Y, 0);
        set[e].alpha = rx_option(base + F_ALPHA, 100);
        any_alpha |= set[e].visible && set[e].alpha < 100;
        any_edit |= !set[e].visible || set[e].size != 100 || set[e].x || set[e].y || set[e].alpha < 100;
        const int v[5] = {set[e].visible, set[e].size, set[e].x, set[e].y, set[e].alpha};
        memcpy(now + e * 5, v, sizeof v);
    }
    changed |= memcmp(now, last, sizeof now) != 0;
    memcpy(last, now, sizeof last);
    if (changed) restoring = 30;   /* (half a second: every pane an opacity lowered is placed again and put back) */
    else if (restoring) restoring--;
    if (changed || any_alpha || restoring) hos_wide_ui_force = 2;   /* (remade now; with an opacity, every present) */
}

static int name_is(Ctx *c, uint64_t g, const char *want) {
    if (!g) return 0;
    for (size_t i = 0; i < 64; i++) {
        const char ch = (char)recomp_load8(c, g + i);
        if (ch != want[i]) return 0;
        if (!ch) return 1;
    }
    return 0;
}

/* pane -> 1 + the element it belongs to (0 none), the game's threads writing it; a slot is taken over by a newer pane */
enum { MAP = 1 << 14 };
static struct { uint64_t pane; uint8_t elem, lowered; } map[MAP];   /* (lowered: its alpha was set by an opacity) */
static uint32_t slot(uint64_t pane) { return (uint32_t)((pane >> 4) * 0x9E3779B1u) & (MAP - 1); }
static int elem_get(uint64_t pane) {
    const uint32_t i = slot(pane);
    return __atomic_load_n(&map[i].pane, __ATOMIC_ACQUIRE) == pane ? map[i].elem : 0;
}
static int lowered_get(uint64_t pane) {
    const uint32_t i = slot(pane);
    return __atomic_load_n(&map[i].pane, __ATOMIC_ACQUIRE) == pane && map[i].lowered;
}
static void elem_put(uint64_t pane, int elem, int lowered) {
    const uint32_t i = slot(pane);
    map[i].elem = (uint8_t)elem, map[i].lowered = (uint8_t)lowered;
    __atomic_store_n(&map[i].pane, pane, __ATOMIC_RELEASE);
}

static float ld(Ctx *c, uint64_t a) { const uint32_t u = (uint32_t)recomp_load32(c, a); float f; memcpy(&f, &u, 4); return f; }
static void st(Ctx *c, uint64_t a, float f) { uint32_t u; memcpy(&u, &f, 4); recomp_store32(c, a, u); }

/* Whether MapMenu_00's layout shows the pause menu's map page: its icons' group at the canvas's origin (hos_wide_ui.c) */
static int map_page(Ctx *c, uint64_t layout, uint64_t res) {
    const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
    const uint32_t count = (uint32_t)recomp_load32(c, layout + L_COUNT) & 0xffff;
    for (uint32_t k = 0; names && k < count && k < 512; k++)
        if (name_is(c, recomp_load64(c, names + (uint64_t)k * 8), "N_MapIcon_00")) {
            const uint64_t p = base + (uint64_t)k * P_SIZE;
            return fabsf(ld(c, p + P_X)) < 1.0f && fabsf(ld(c, p + P_Y)) < 1.0f;
        }
    return 0;
}

/* The element whose own pane this is (1 + its index), else 0 */
static int own_element(Ctx *c, uint64_t pane, uint64_t parent) {
    const uint64_t layout = recomp_load64(c, pane + P_LAYOUT);
    const uint64_t res = layout ? recomp_load64(c, layout + L_RES) : 0;
    const uint64_t lname = res ? recomp_load64(c, res + R_NAME) : 0;
    if (!lname) return 0;
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
        const HudElement *el = &ENH_HUD_ELEMENTS[e];
        if (!name_is(c, lname, el->layout)) continue;
        if (!el->pane) {
            if (parent) continue;   /* (the layout's root) */
            if (!strcmp(el->layout, "MapMenu_00") && map_page(c, layout, res)) return 0;
            return e + 1;
        }
        const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
        if (!names || pane < base) continue;
        if (name_is(c, recomp_load64(c, names + (pane - base) / P_SIZE * 8), el->pane)) return e + 1;
    }
    return 0;
}

void hos_enh_hud_edit(Ctx *c, uint64_t pane, uint64_t parent) {
    if (!pane) return;
    const int was_lowered = lowered_get(pane);
    if (!any_edit && !restoring && !was_lowered) return;
    const int own = any_edit ? own_element(c, pane, parent) : 0;
    const int elem = !any_edit ? 0 : own ? own : parent ? elem_get(parent) : 0;
    const int e = elem - 1;
    const uint32_t type = ((uint32_t)recomp_load32(c, pane + P_FLAGS) >> 22) & 0xf;   /* (1 picture, 2 text box, 3 window) */
    const int lower = elem && set[e].visible && set[e].alpha < 100 && type >= 1 && type <= 3;
    if (was_lowered && !lower) st(c, pane + P_ALPHA, 1.0f);   /* (the opacity back to 100%: the pane as the game drew it) */
    elem_put(pane, elem, lower);
    if (!elem) return;
    if (own) {
        float m[9];
        for (int k = 0; k < 9; k++) m[k] = ld(c, pane + P_XX + 4 * (uint64_t)k);
        float x = ld(c, pane + P_X), y = ld(c, pane + P_Y);
        float s = set[e].visible ? (float)set[e].size / 100.0f : 0.0f;
        if (s != 1.0f) {
            /* (the corner that stays: the HUD's 16:9 canvas's, 3840 x 2160 about its middle. This runs before
               host/hos_wide_ui.c's own moves, which then take the element to a wider screen's edge as usual) */
            const float hx = 1920.0f, hy = 1080.0f;
            const int a = ENH_HUD_ELEMENTS[e].anchor;
            float ax = a == A_TL || a == A_BL ? -hx : a == A_TR || a == A_BR ? hx : 0.0f;
            float ay = a == A_TL || a == A_TR || a == A_TOP ? hy : a == A_BL || a == A_BR || a == A_BOTTOM ? -hy : 0.0f;
            if (a == A_BOX_TL || a == A_BOX_TR) {   /* (the pane's own box, from its origin's place in it: f_8154a820, as hos_wide_ui.c) */
                const uint32_t flags = (uint32_t)recomp_load32(c, pane + P_FLAGS);
                const uint32_t ox = ((flags >> 11) & 0x7f) % 3, oy = ((flags >> 11) & 0x7f) / 3 % 3;   /* (0 left/top, 1 centre, 2 right/bottom) */
                const float w = ld(c, pane + P_W) * fabsf(m[0]), h = ld(c, pane + P_H) * fabsf(m[4]);
                const float left = x - (ox == 1 ? w * 0.5f : ox == 2 ? w : 0.0f);
                ax = a == A_BOX_TL ? left : left + w;
                ay = y + (oy == 1 ? h * 0.5f : oy == 2 ? h : 0.0f);   /* (y up: the top is above the origin) */
            }
            for (int k = 0; k < 9; k++) m[k] *= s;
            x = ax + (x - ax) * s, y = ay + (y - ay) * s;
            for (int k = 0; k < 9; k++) st(c, pane + P_XX + 4 * (uint64_t)k, m[k]);
        }
        x += (float)set[e].x, y += (float)set[e].y;
        st(c, pane + P_X, x), st(c, pane + P_Y, y);
    }
    if (lower) {
        const float want = (float)set[e].alpha / 100.0f, a = ld(c, pane + P_ALPHA);
        if (a > want) st(c, pane + P_ALPHA, want);
    }
}
