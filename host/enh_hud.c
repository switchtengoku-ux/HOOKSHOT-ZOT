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
   - place: its translation moved by the offsets, percent of the screen's width and height (hud_screen; y up), kept on the
     screen (hud_keep), and moved by host/hos_wide_ui.c after its own moves (hos_enh_hud_shift).
   On every pane of the element that draws (a picture, a text box, a window: not a group, whose alpha the game multiplies
   into its children, so an element nested three deep came out at an eighth): the opacity, as min(the pane's own, the
   setting) in its alpha (+0x74), so the game's fades still run. While an element is not opaque every pane remakes its
   transform each present (hos_wide_ui_force), since a pane's alpha can change with no new transform.
   The pause menu's map page is MapMenu_00 as the minimap (and the dungeon minimap with its keys count) is: it is told
   apart by its own groups being drawn (map_page_shown) and never edited.
   The settings come from the renderer (rx_option HOS_OPT_ENH_HUD + element * 5 + field), read again only when
   HOS_OPT_ENH_HUD_GEN has changed; the Whole HUD rows (HOS_OPT_ENH_HUD_SCALE, _FADE) multiply each element's size and
   opacity (hud_effective). */
#include "hos.h"
#include "../gpu/vk/vk_api.h"   /* (HOS_OPT_ENH_HUD) */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { L_RES = 0xf8, R_NAME = 0x18, R_PANE_NAMES = 0x20, L_PANES = 0x100, L_COUNT = 0x13c, P_SIZE = 0xb0,
       P_LAYOUT = 0x18, P_XX = 0x28, P_X = 0x4c, P_Y = 0x50, P_W = 0x58, P_H = 0x5c, P_ALPHA = 0x74, P_FLAGS = 0xa8 };
enum { A_BOX_TL, A_BOX_TR, A_ORIGIN, A_TL, A_TR, A_BL, A_BR, A_TOP, A_BOTTOM };
       /* (what an element keeps when it is resized: its own pane's top left or top right corner, or a corner or edge of the
          HUD's 16:9 canvas for a whole layout, whose root's origin is the canvas's middle; or its own origin, for the magic
          gauge, whose box is far wider than the bar drawn from its origin: kept to the box, it went off the screen's left
          edge at 50%) */

/* (lead: A_ORIGIN's point that far left of the origin. left, right, down, up: what the element draws about its anchor at
   100%, in canvas units, kept on the screen when it is moved (hud_keep); measured on 3440x1440 and 1920x1080 shots, with a margin, 2026-11-19. The
   game's boxes are no use there: the item buttons' is far wider than what they draw, a whole layout's is the canvas) */
typedef struct { const char *layout, *pane; int anchor; float lead, left, right, down, up; } HudElement;
/* (the order is the menu's and the option ids': gpu/vk/enh_menu_hud.inc ENH_HUD_NAMES) */
static const HudElement ENH_HUD_ELEMENTS[HOS_ENH_HUD_ELEMENTS] = {
    {"PlayerStatus_00", "Pa_HeartGauge_00", A_BOX_TL, 0, 0, 800, 220, 0},   /* hearts (two rows of ten) */
    {"PlayerStatus_00", "Pa_MpGauge_00", A_ORIGIN, 230, 0, 450, 30, 30},    /* magic: its bar's left end, 230 units left of its
                                                                               origin (its box is 1256 wide about the origin;
                                                                               HOS_ENH_HUD_DIAG=1 logs and the bar lined up with
                                                                               the hearts, 2026-11-19) */
    {"PlayerStatus_00", "Pa_GuideCross_00", A_BOX_TL, 0, -780, 500, 600, 0},   /* the item buttons under them (their box's
                                                                                left is 780 left of what they draw) */
    {"PlayerStatus_00", "N_ScaleR_00", A_ORIGIN, 0, 450, 0, 500, 0},        /* the item and action buttons at the top right
                                                                               (origin: the corner) */
    {"MapMenu_00", NULL, A_BR, 0, 820, 0, 0, 900},                          /* the minimap (in a dungeon, its keys
                                                                               count above it) */
    {"Location_00", NULL, A_TOP, 0, 800, 800, 300, 0},                      /* the place's name */
};
enum { F_VISIBLE, F_SIZE, F_X, F_Y, F_ALPHA };
/* (the game's own scaling group of the left gauges, hos_wide_ui.c's RULES: N_ScaleL_00, its origin at the 16:9 canvas's
   top left corner, holds the hearts and N_ScaleL_01, the magic's and the item buttons' group (its origin at the canvas's
   middle). The Whole HUD size scales N_ScaleL_00 alone, about its origin, so everything in it shrinks or grows together
   into the corner and keeps its lining up (HOS_ENH_HUD_DIAG=1 logs showed it, 2026-11-19). Scaled each about its own
   point, the magic, whose point is in its bar's middle, came out of line; N_ScaleL_01 scaled too was scaled twice) */
static const char *const ENH_HUD_GROUPS[] = {"N_ScaleL_00"};
enum { IN_GROUP = 7 };   /* (a pane's mark in the map: a group's, or below one and in no element) */

typedef struct { int visible, size, x, y, alpha; } HudSet;
static HudSet set[HOS_ENH_HUD_ELEMENTS];   /* (what is applied: the element's own times the Whole HUD rows) */
static int own_size[HOS_ENH_HUD_ELEMENTS];   /* (its own size alone: an element in a scaled group, which has the Whole HUD's) */
static int whole_size = 100;                 /* (the Whole HUD size, percent) */
static volatile int page_on;   /* (MapMenu_00 shows the pause menu's map page: map_page_shown) */
static int diag_left;   /* (lines left to log after a change: HOS_ENH_HUD_DIAG=1, the left gauges' panes as placed) */
static int any_alpha, any_edit, restoring;   /* (restoring: presents left to put back the panes an opacity lowered) */
int rx_option(int id, int otherwise);   /* host/rx_backend.c */
extern volatile uint32_t hos_wide_ui_force;
extern volatile float hos_ui_qx, hos_ui_qy;   /* host/hos_wide_ui.c */

/* An element's settings as applied: its own size and opacity times the whole HUD's (percent, rounded to the nearest) */
static inline HudSet hud_effective(HudSet own, int scale, int fade) {
    HudSet out = own;
    out.size = (own.size * scale + 50) / 100;
    out.alpha = (own.alpha * fade + 50) / 100;
    if (out.alpha < 1) out.alpha = 1;
    return out;
}

/* The screen's width and height in the HUD canvas's units, for the offsets (percent of them, so an element can go anywhere
   on any screen shape): host/hos_wide_ui.c's hos_ui_qx and _qy are the share of the screen the 16:9 canvas takes across
   and up (0: all of it, a 16:9 screen) */
static inline void hud_screen(float qx, float qy, float *w, float *h) {
    *w = qx > 0.0f && qx < 1.0f ? 3840.0f / qx : 3840.0f;
    *h = qy > 0.0f && qy < 1.0f ? 2160.0f / qy : 2160.0f;
}

/* An element's move along one axis of the screen (half: half its size), as wanted but kept on it: lo and hi are what of
   the element must stay on (its box's sides, or its anchor alone), where it is now; bigger than the screen, its low side
   stays on */
static inline float hud_keep(float lo, float hi, float want, float half) {
    const float least = -half - lo, most = half - hi;
    if (least > most) return least;
    return want < least ? least : want > most ? most : want;
}

/* The point a resized element keeps (x, y up, in the HUD canvas's units about its middle): a corner or edge of the 16:9
   canvas (3840 x 2160), the element's own origin, or its own box's top left or top right, from the origin's place in the
   box (ox, oy: 0 left/top, 1 centre, 2 right/bottom; w, h its size) */
static inline void hud_anchor(int a, float x, float y, float w, float h, unsigned ox, unsigned oy, float lead, float *ax,
                              float *ay) {
    const float hx = 1920.0f, hy = 1080.0f;
    *ax = a == A_TL || a == A_BL ? -hx : a == A_TR || a == A_BR ? hx : 0.0f;
    *ay = a == A_TL || a == A_TR || a == A_TOP ? hy : a == A_BL || a == A_BR || a == A_BOTTOM ? -hy : 0.0f;
    if (a == A_ORIGIN) *ax = x - lead, *ay = y;
    if (a == A_BOX_TL || a == A_BOX_TR) {
        const float left = x - (ox == 1 ? w * 0.5f : ox == 2 ? w : 0.0f);
        *ax = a == A_BOX_TL ? left : left + w;
        *ay = y + (oy == 1 ? h * 0.5f : oy == 2 ? h : 0.0f);   /* (y up: the top is above the origin) */
    }
}

/* Each present (host/enh_photo.c hos_enh_photo_tick): the settings, and the panes remade when they change. The elements'
   own are asked for again only when the renderer's number for them has changed (one call, not thirty, a present) */
void hos_enh_hud_tick(void) {
    static HudSet own[HOS_ENH_HUD_ELEMENTS];
    static int gen = -1, last_scale = -1, last_fade = -1;
    const int now_gen = rx_option(HOS_OPT_ENH_HUD_GEN, 0);
    const int scale = rx_option(HOS_OPT_ENH_HUD_SCALE, 100), fade = rx_option(HOS_OPT_ENH_HUD_FADE, 100);
    const int changed = now_gen != gen || scale != last_scale || fade != last_fade;
    if (now_gen != gen)
        for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
            const int base = HOS_OPT_ENH_HUD + e * 5;
            own[e].visible = rx_option(base + F_VISIBLE, 1);
            own[e].size = rx_option(base + F_SIZE, 100);
            own[e].x = rx_option(base + F_X, 0);
            own[e].y = rx_option(base + F_Y, 0);
            own[e].alpha = rx_option(base + F_ALPHA, 100);
        }
    gen = now_gen, last_scale = scale, last_fade = fade;
    if (changed) {
        any_alpha = any_edit = 0;
        whole_size = scale;
        for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
            set[e] = hud_effective(own[e], scale, fade);
            own_size[e] = own[e].visible ? own[e].size : 0;
            any_alpha |= set[e].visible && set[e].alpha < 100;
            any_edit |= !set[e].visible || set[e].size != 100 || set[e].x || set[e].y || set[e].alpha < 100;
        }
        any_edit |= scale != 100;
        static int diag = -1;
        if (diag < 0) { const char *d = getenv("HOS_ENH_HUD_DIAG"); diag = d && d[0] == '1'; }
        if (diag) __atomic_store_n(&diag_left, 24, __ATOMIC_RELAXED);
        restoring = 30;   /* (half a second: every pane an opacity lowered is placed again and put back) */
    } else if (restoring) restoring--;
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

/* pane -> 1 + the element it belongs to (0 none) and whether an opacity set its alpha, the game's threads writing it; a slot
   is taken over by a newer pane. One word a slot, the pane's address above its 8 low bits (a guest address is far below
   2^56), so a reader never gets one pane's address with another's element */
enum { MAP = 1 << 14 };
static uint64_t map[MAP];
static uint32_t slot(uint64_t pane) { return (uint32_t)((pane >> 4) * 0x9E3779B1u) & (MAP - 1); }
static uint64_t slot_get(uint64_t pane) {   /* (its low byte: element 0 to 7, bit 4 lowered, bit 5 cut by a scissor pane
                                                above it; 0 when another pane is there) */
    const uint64_t w = __atomic_load_n(&map[slot(pane)], __ATOMIC_ACQUIRE);
    return w >> 8 == pane ? w & 0xff : 0;
}
static int elem_get(uint64_t pane) { return (int)(slot_get(pane) & 7); }   /* (1 to 6, IN_GROUP, or 0) */
static int lowered_get(uint64_t pane) { return (int)(slot_get(pane) >> 4 & 1); }
static int clipped_get(uint64_t pane) { return (int)(slot_get(pane) >> 5 & 1); }
static void elem_put(uint64_t pane, int elem, int lowered, int clipped) {
    __atomic_store_n(&map[slot(pane)], pane << 8 | (uint64_t)(elem & 7) | (uint64_t)(lowered != 0) << 4 | (uint64_t)(clipped != 0) << 5,
                     __ATOMIC_RELEASE);
}

static float ld(Ctx *c, uint64_t a) { const uint32_t u = (uint32_t)recomp_load32(c, a); float f; memcpy(&f, &u, 4); return f; }
static void st(Ctx *c, uint64_t a, float f) { uint32_t u; memcpy(&u, &f, 4); recomp_store32(c, a, u); }

/* Whether MapMenu_00's layout shows the pause menu's map page and not the minimap: the page's own groups (N_LocalMap_00,
   the area's; N_WorldMap_00, the world's) were drawn in the last presents, which the minimap's never are (a hidden group's
   transform is not made). Its icons' group at the canvas's origin, hos_wide_ui.c's sign, is no use here: the dungeon
   minimap has it there too, and the page has it 20 units down while it opens, so the page was moved with the minimap and
   then never told apart again (a diagnostic of its panes, 2026-11-19). A menu's panes are made again only when they change,
   so it is a state: on when the page's groups are drawn, off when anything in N_MiniMap_00 is (the minimap's own: the
   page draws none of it) */
static int map_page_shown(void) { return page_on; }

/* The element whose own pane this is (1 + its index), IN_GROUP for a scaling group's own pane, else 0 */
static void pane_name(Ctx *c, uint64_t pane, char *out, size_t n);   /* (below: the diagnostic's) */
static int own_element(Ctx *c, uint64_t pane, uint64_t parent) {
    const uint64_t layout = recomp_load64(c, pane + P_LAYOUT);
    const uint64_t res = layout ? recomp_load64(c, layout + L_RES) : 0;
    const uint64_t lname = res ? recomp_load64(c, res + R_NAME) : 0;
    if (!lname) return 0;
    if (parent && name_is(c, lname, "MapMenu_00")) {   /* (the map page's groups drawn: map_page_shown) */
        const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
        const uint64_t name = names && pane >= base ? recomp_load64(c, names + (pane - base) / P_SIZE * 8) : 0;
        const uint64_t playout = recomp_load64(c, parent + P_LAYOUT), pres = playout ? recomp_load64(c, playout + L_RES) : 0;
        const uint64_t pbase = playout ? recomp_load64(c, playout + L_PANES) : 0, pnames = pres ? recomp_load64(c, pres + R_PANE_NAMES) : 0;
        const uint64_t pname = pnames && parent >= pbase ? recomp_load64(c, pnames + (parent - pbase) / P_SIZE * 8) : 0;
        const int page = name_is(c, name, "N_LocalMap_00") || name_is(c, name, "N_WorldMap_00") ? 1
                       : name_is(c, pname, "N_MiniMap_00") ? 0 : -1;
        if (page >= 0 && page != page_on) {
            page_on = page;
            hos_wide_ui_force = 3;   /* (the root was placed for the other this present: every pane made again) */
        }
        return 0;
    }
    if (whole_size != 100 && parent && name_is(c, lname, "PlayerStatus_00")) {
        const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
        const uint64_t name = names && pane >= base ? recomp_load64(c, names + (pane - base) / P_SIZE * 8) : 0;
        for (size_t g = 0; name && g < sizeof ENH_HUD_GROUPS / sizeof ENH_HUD_GROUPS[0]; g++)
            if (name_is(c, name, ENH_HUD_GROUPS[g])) return IN_GROUP;
    }
    for (int e = 0; e < HOS_ENH_HUD_ELEMENTS; e++) {
        const HudElement *el = &ENH_HUD_ELEMENTS[e];
        if (!name_is(c, lname, el->layout)) continue;
        if (!el->pane) {
            /* (the layout's root: no parent, and named RootPane. The place name's text and frame are made with no parent too,
               and were taken for the whole layout and resized a second time) */
            if (parent) continue;
            const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
            if (diag_left > 0) {   /* (HOS_ENH_HUD_DIAG=1: a whole layout's panes made with no parent, and whether taken) */
                char name[40];
                pane_name(c, pane, name, sizeof name);
                hos_log("enhanced: HUD diag: %s no-parent pane %s, map page %d", el->layout, name,
                        !strcmp(el->layout, "MapMenu_00") ? map_page_shown() : -1);
            }
            if (!names || pane < base || !name_is(c, recomp_load64(c, names + (pane - base) / P_SIZE * 8), "RootPane")) continue;
            if (!strcmp(el->layout, "MapMenu_00") && map_page_shown()) return 0;
            return e + 1;
        }
        const uint64_t base = recomp_load64(c, layout + L_PANES), names = recomp_load64(c, res + R_PANE_NAMES);
        if (!names || pane < base) continue;
        if (name_is(c, recomp_load64(c, names + (pane - base) / P_SIZE * 8), el->pane)) return e + 1;
    }
    return 0;
}

/* A pane's name, for the diagnostic ("?" when it has none) */
static void pane_name(Ctx *c, uint64_t pane, char *out, size_t n) {
    const uint64_t layout = pane ? recomp_load64(c, pane + P_LAYOUT) : 0, res = layout ? recomp_load64(c, layout + L_RES) : 0;
    const uint64_t base = layout ? recomp_load64(c, layout + L_PANES) : 0, names = res ? recomp_load64(c, res + R_PANE_NAMES) : 0;
    const uint64_t g = names && pane >= base ? recomp_load64(c, names + (pane - base) / P_SIZE * 8) : 0;
    out[0] = '?', out[1] = 0;
    for (size_t i = 0; g && i + 1 < n; i++) if (!(out[i] = (char)recomp_load8(c, g + i))) break;
    out[n - 1] = 0;
}

/* The move hos_enh_hud_edit worked out for an element's own pane, handed to host/hos_wide_ui.c on the same thread, which
   makes it after its own moves (hos_enh_hud_shift) */
static _Thread_local struct {
    uint64_t pane;
    int e, move, whole;            /* (lo to top: about the pane's origin, or for a whole layout on the screen) */
    float lo, hi, bottom, top, want_x, want_y, half_w, half_h;
} shift;

/* What each element draws, about its own pane's place: measured on the panes that draw as host/hos_wide_ui.c places them
   (hos_enh_hud_shift), gathered while the element is made (cur) and kept from the last time it was (last). The table's
   extents (ENH_HUD_ELEMENTS) are for the first presents only: measured, an element goes right to the screen's edge
   whatever it holds (two rows of hearts or one, the dungeon minimap's keys count) */
typedef struct { float lo, hi, bottom, top; int n; } HudExtent;
static HudExtent ext_cur[HOS_ENH_HUD_ELEMENTS], ext_last[HOS_ENH_HUD_ELEMENTS];
static float own_fx[HOS_ENH_HUD_ELEMENTS], own_fy[HOS_ENH_HUD_ELEMENTS];   /* (its own pane's place, as drawn) */

/* A pane of element e drawn at x, y (its origin, as placed): its box added to what the element draws. Only the panes that
   draw (picture, text box, window) and a scissor pane (4: what is under it is drawn cut to it, the map's icons beyond the
   minimap's window are not seen), seen, and not as big as the screen */
static void hud_measure(Ctx *c, uint64_t pane, int e, float x, float y) {
    const uint32_t flags = (uint32_t)recomp_load32(c, pane + P_FLAGS), type = (flags >> 22) & 0xf;
    if ((type < 1 || type > 4) || clipped_get(pane) || ld(c, pane + P_ALPHA) < 0.02f) return;
    const float w = ld(c, pane + P_W) * fabsf(ld(c, pane + P_XX)), h = ld(c, pane + P_H) * fabsf(ld(c, pane + P_XX + 16));
    if (!(w > 1.0f && h > 1.0f && w < 1500.0f && h < 1500.0f)) return;
    const unsigned ox = ((flags >> 11) & 0x7f) % 3, oy = ((flags >> 11) & 0x7f) / 3 % 3;
    const float left = x - (ox == 1 ? w * 0.5f : ox == 2 ? w : 0.0f) - own_fx[e];
    const float top = y + (oy == 1 ? h * 0.5f : oy == 2 ? h : 0.0f) - own_fy[e];
    HudExtent *m = &ext_cur[e];
    if (!m->n) m->lo = left, m->hi = left + w, m->bottom = top - h, m->top = top;
    else m->lo = fminf(m->lo, left), m->hi = fmaxf(m->hi, left + w), m->bottom = fminf(m->bottom, top - h), m->top = fmaxf(m->top, top);
    m->n++;
}

/* Each pane just placed by host/hos_wide_ui.c at x, y (the screen's middle 0, in canvas units): an element's own pane gets
   its move, kept on the screen (1 and the move; 0 for any other pane); a pane in an element is measured */
int hos_enh_hud_shift(Ctx *c, uint64_t pane, float x, float y, float *dx, float *dy) {
    if (!pane) return 0;
    if (shift.pane != pane) {
        const int el = any_edit ? elem_get(pane) : 0;
        if (el >= 1 && el <= HOS_ENH_HUD_ELEMENTS) hud_measure(c, pane, el - 1, x, y);
        return 0;
    }
    const int e = shift.e, move = shift.move;
    shift.pane = 0;
    if (ext_cur[e].n) ext_last[e] = ext_cur[e];
    ext_cur[e].n = 0;
    *dx = *dy = 0.0f;
    if (move) {
        const HudExtent *m = &ext_last[e];
        const float ox = shift.whole ? 0.0f : x, oy = shift.whole ? 0.0f : y;
        const float lo = m->n ? x + m->lo : ox + shift.lo, hi = m->n ? x + m->hi : ox + shift.hi;
        const float bottom = m->n ? y + m->bottom : oy + shift.bottom, top = m->n ? y + m->top : oy + shift.top;
        *dx = hud_keep(lo, hi, shift.want_x, shift.half_w);
        *dy = hud_keep(bottom, top, shift.want_y, shift.half_h);
    }
    own_fx[e] = x + *dx, own_fy[e] = y + *dy;
    return move;
}

void hos_enh_hud_edit(Ctx *c, uint64_t pane, uint64_t parent) {
    shift.pane = 0;
    if (!pane) return;
    const int was_lowered = lowered_get(pane);
    if (!any_edit && !restoring && !was_lowered) return;
    const int own = any_edit ? own_element(c, pane, parent) : 0;
    const int above = any_edit && parent ? elem_get(parent) : 0;
    const int elem = !any_edit ? 0 : own ? own : above;
    const int e = elem - 1;   /* (an element's index; not for IN_GROUP) */
    const int is_elem = elem >= 1 && elem <= HOS_ENH_HUD_ELEMENTS;
    const uint32_t type = ((uint32_t)recomp_load32(c, pane + P_FLAGS) >> 22) & 0xf;   /* (1 picture, 2 text box, 3 window) */
    const int lower = is_elem && set[e].visible && set[e].alpha < 100 && type >= 1 && type <= 3;
    if (was_lowered && !lower) st(c, pane + P_ALPHA, 1.0f);   /* (the opacity back to 100%: the pane as the game drew it) */
    /* (under a scissor pane (4): drawn cut to it, so not measured, the scissor pane is: hud_measure) */
    const int clipped = elem && parent && (clipped_get(parent) || ((((uint32_t)recomp_load32(c, parent + P_FLAGS) >> 22) & 0xf) == 4));
    elem_put(pane, elem, lower, clipped);
    if (!elem) return;
    const int diag = own && diag_left > 0 && __atomic_fetch_sub(&diag_left, 1, __ATOMIC_RELAXED) > 0;
    char diag_text[200] = "";
    if (diag) {   /* (HOS_ENH_HUD_DIAG=1: an element's or a group's own pane, its parent, as the game made it) */
        char name[40], pname[40];
        pane_name(c, pane, name, sizeof name), pane_name(c, parent, pname, sizeof pname);
        const uint32_t fl = (uint32_t)recomp_load32(c, pane + P_FLAGS);
        snprintf(diag_text, sizeof diag_text, "%s (in %s, elem %d above %d) x=%.1f y=%.1f w=%.1f h=%.1f sx=%.3f origin=%u,%u",
                 name, pname, elem, above, ld(c, pane + P_X), ld(c, pane + P_Y), ld(c, pane + P_W), ld(c, pane + P_H),
                 ld(c, pane + P_XX), ((fl >> 11) & 0x7f) % 3, ((fl >> 11) & 0x7f) / 3 % 3);
    }
    if (own == IN_GROUP) {   /* (a scaling group: the Whole HUD size about the canvas's top left corner) */
        const float g = (float)whole_size / 100.0f;
        float ax, ay;
        hud_anchor(A_TL, 0, 0, 0, 0, 0, 0, 0, &ax, &ay);
        for (int k = 0; k < 9; k++) st(c, pane + P_XX + 4 * (uint64_t)k, ld(c, pane + P_XX + 4 * (uint64_t)k) * g);
        st(c, pane + P_X, ax + (ld(c, pane + P_X) - ax) * g), st(c, pane + P_Y, ay + (ld(c, pane + P_Y) - ay) * g);
        if (diag) hos_log("enhanced: HUD diag: %s -> x=%.1f y=%.1f sx=%.3f", diag_text, ld(c, pane + P_X), ld(c, pane + P_Y), ld(c, pane + P_XX));
        return;
    }
    if (own) {
        float m[9];
        for (int k = 0; k < 9; k++) m[k] = ld(c, pane + P_XX + 4 * (uint64_t)k);
        float x = ld(c, pane + P_X), y = ld(c, pane + P_Y);
        /* (in a scaled group its own size alone, the group has the Whole HUD's; else both) */
        float s = (float)(above == IN_GROUP ? own_size[e] : set[e].visible ? set[e].size : 0) / 100.0f;
        if (s != 1.0f) {
            /* (the point that stays: hud_anchor. This runs before host/hos_wide_ui.c's own moves, which then take the
               element to a wider screen's edge as usual. The origin's place in the pane's box: f_8154a820, as there) */
            const uint32_t flags = (uint32_t)recomp_load32(c, pane + P_FLAGS);
            const unsigned ox = ((flags >> 11) & 0x7f) % 3, oy = ((flags >> 11) & 0x7f) / 3 % 3;
            float ax, ay;
            hud_anchor(ENH_HUD_ELEMENTS[e].anchor, x, y, ld(c, pane + P_W) * fabsf(m[0]), ld(c, pane + P_H) * fabsf(m[4]), ox, oy,
                       ENH_HUD_ELEMENTS[e].lead * fabsf(m[0]), &ax, &ay);
            for (int k = 0; k < 9; k++) m[k] *= s;
            x = ax + (x - ax) * s, y = ay + (y - ay) * s;
            for (int k = 0; k < 9; k++) st(c, pane + P_XX + 4 * (uint64_t)k, m[k]);
        }
        st(c, pane + P_X, x), st(c, pane + P_Y, y);
        shift.pane = pane, shift.e = e, shift.move = set[e].x || set[e].y;   /* (measured from its place: hos_enh_hud_shift) */
        if (shift.move) {
            /* (the place: percent of the screen, kept on it (hud_keep), moved by host/hos_wide_ui.c after its own moves
               (hos_enh_hud_shift): moved here, a wider screen's side moves took the element for one on the other side and
               pushed it off the screen) */
            float sw, sh, ax, ay;
            hud_screen(hos_ui_qx, hos_ui_qy, &sw, &sh);
            const uint32_t flags = (uint32_t)recomp_load32(c, pane + P_FLAGS);
            const unsigned ox = ((flags >> 11) & 0x7f) % 3, oy = ((flags >> 11) & 0x7f) / 3 % 3;
            const float w = ld(c, pane + P_W) * fabsf(m[0]), h = ld(c, pane + P_H) * fabsf(m[4]);
            const HudElement *el = &ENH_HUD_ELEMENTS[e];
            hud_anchor(el->anchor, x, y, w, h, ox, oy, el->lead * fabsf(m[0]), &ax, &ay);
            /* (the element on the screen, in the canvas's units across it: the 16:9 canvas's place times the screen's share,
               its corners at the screen's; what it draws about its anchor at its size, the whole HUD's too in a group) */
            const float k = s * (above == IN_GROUP ? (float)whole_size / 100.0f : 1.0f);
            /* (an element named by its pane: about its origin, wherever host/hos_wide_ui.c then puts it (its parents' moves
               are in its place already, its own are not yet); a whole layout's root stays at the canvas's middle while its
               panes move out to the screen's sides: its corner is the screen's, the 16:9 canvas's times its share) */
            const int whole = !el->pane;
            const float bx = whole ? ax * sw / 3840.0f : ax - x, by = whole ? ay * sh / 2160.0f : ay - y;
            shift.whole = whole;
            shift.lo = bx - el->left * k, shift.hi = bx + el->right * k;
            shift.bottom = by - el->down * k, shift.top = by + el->up * k;
            shift.want_x = (float)set[e].x * sw / 100.0f, shift.want_y = (float)set[e].y * sh / 100.0f;
            shift.half_w = sw * 0.5f, shift.half_h = sh * 0.5f;
        }
        if (diag) hos_log("enhanced: HUD diag: %s -> x=%.1f y=%.1f sx=%.3f move %.1f %.1f", diag_text, x, y, ld(c, pane + P_XX),
                          shift.move ? shift.want_x : 0.0f, shift.move ? shift.want_y : 0.0f);
    }
    if (lower) {
        const float want = (float)set[e].alpha / 100.0f, a = ld(c, pane + P_ALPHA);
        if (a > want) st(c, pane + P_ALPHA, want);
    }
}
