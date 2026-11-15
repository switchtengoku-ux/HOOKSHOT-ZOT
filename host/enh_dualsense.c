/* (enhanced) Hookshot Enhanced: PlayStation pads' lightbar and the DualSense's adaptive triggers (host/enh_dualsense.h
   has the colours and the effect block, docs/enhanced/DUALSENSE.md the guide).

   Off unless hookshot_env.txt (or the environment) asks for it, and then nothing at all is sent to any pad:
     HOOKSHOT_ENH_LIGHTBAR=hearts   the lightbar shows Link's life (DualSense and DualShock 4)
     HOOKSHOT_ENH_TRIGGERS=1 | 2    a light or strong constant resistance on L2 and R2 (DualSense)
     HOOKSHOT_ENH_LOW_LIFE_RUMBLE=0 no heartbeat pulse at one heart or less (on by default with the lightbar)

   Two threads meet here. The game's (host/hos_main.c hos_oot_lift_player, while Link is updated, so only in play)
   hands Link's life over through one atomic word and its time; the pads' (host/pad_sdl.c pads_poll, every 4 ms) sends
   each pad what changed: the lightbar only when its colour changes, the triggers once per connection. When the life is
   older than ENH_LIFE_STALE_NS (the title, a pause, a load) the lightbar goes back to SDL's own first-player colour.
   At one heart or less, with the lightbar on, each red blink also gives a short pulse on the motors (the menu's Rumble
   strength scales it, Off turns it off), never while the game's own rumble plays: pad_sdl.c's next rumble, the
   game's, replaces it, and its duration (ENH_DS_BEAT_MS) ends it otherwise.
   At exit the triggers are cleared and the lightbar put back, so the pad does not keep the game's resistance. */
#include "hos.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hos_sdl.h"
#include "enh_dualsense.h"

#define ENH_MAX_PADS 8
#define ENH_LIFE_STALE_NS 2000000000LL

static int enh_lightbar = -1, enh_triggers = -1, enh_beat = -1;   /* (-1: the switches not read yet) */
static uint64_t enh_life_word;   /* (life << 16 | max, 0 none: written by the game's thread) */
static int64_t enh_life_ns;
static struct {
    void *gc;
    uint32_t serial;
    int kind;
    int rgb;              /* (the colour last sent, 0xRRGGBB, or -1) */
    int triggers;         /* (the trigger setting sent, or -1) */
    int warned;
    int64_t beat;         /* (the blink cycle pulsed last) */
} enh_pads[ENH_MAX_PADS];

static void enh_read_switches(void) {
    if (enh_lightbar >= 0) return;
    enh_lightbar = enh_ds_parse_lightbar(getenv("HOOKSHOT_ENH_LIGHTBAR"));
    enh_triggers = enh_ds_parse_triggers(getenv("HOOKSHOT_ENH_TRIGGERS"));
    {
        const char *b = getenv("HOOKSHOT_ENH_LOW_LIFE_RUMBLE");
        enh_beat = enh_lightbar && !(b && (!strcmp(b, "0") || !strcmp(b, "off")));
    }
    if (enh_lightbar || enh_triggers)
        hos_log("enhanced: PlayStation pads: lightbar %s, low-life pulse %s, adaptive triggers %s",
                enh_lightbar ? "hearts" : "off", enh_beat ? "on" : "off",
                enh_triggers == ENH_DS_TRIGGERS_STRONG ? "strong" : enh_triggers ? "light" : "off");
}

int hos_enh_lightbar_on(void) {
    enh_read_switches();
    return enh_lightbar != ENH_DS_LIGHTBAR_OFF;
}

void hos_enh_set_life(int life, int max) {
    if (life < 0 || max <= 0 || life > 0xffff || max > 0xffff) return;
    __atomic_store_n(&enh_life_ns, hos_now_ns(), __ATOMIC_RELAXED);
    __atomic_store_n(&enh_life_word, (uint64_t)life << 16 | (uint64_t)max, __ATOMIC_RELEASE);
}

static void enh_restore_all(void) {   /* (at exit: the pads as SDL had them) */
    for (int i = 0; i < ENH_MAX_PADS; i++) {
        void *gc = enh_pads[i].gc;
        if (!gc) continue;
        if (enh_pads[i].triggers > 0) {
            uint8_t e[ENH_DS_EFFECT_SIZE];
            enh_ds_trigger_effect(ENH_DS_TRIGGERS_OFF, e);
            hos_sdl_pad_effect(gc, e, sizeof e);
        }
        if (enh_pads[i].rgb >= 0) hos_sdl_pad_led(gc, ENH_DS_DEFAULT_R, ENH_DS_DEFAULT_G, ENH_DS_DEFAULT_B);
    }
}

void hos_enh_pad_gone(int slot) {
    if (slot >= 0 && slot < ENH_MAX_PADS) enh_pads[slot].gc = NULL;
}

void hos_enh_pad(int slot, void *gc, uint32_t serial, int64_t now, int game_rumbling, int strength) {
    enh_read_switches();
    if ((!enh_lightbar && !enh_triggers) || slot < 0 || slot >= ENH_MAX_PADS || !gc) return;
    static int exit_hook;
    if (!exit_hook) {
        exit_hook = 1;
        atexit(enh_restore_all);
    }
    if (enh_pads[slot].gc != gc || enh_pads[slot].serial != serial) {   /* (a pad newly opened in this slot) */
        enh_pads[slot].gc = gc;
        enh_pads[slot].serial = serial;
        enh_pads[slot].kind = enh_ds_kind(hos_sdl_load(), hos_sdl_pad_type(gc));
        enh_pads[slot].rgb = -1;
        enh_pads[slot].triggers = -1;
        enh_pads[slot].warned = 0;
        enh_pads[slot].beat = 0;
        if (enh_pads[slot].kind)
            hos_log("enhanced: \"%s\" is a %s", hos_sdl_pad_name(gc), enh_pads[slot].kind == ENH_DS_PS5 ? "DualSense" : "DualShock 4");
    }
    const int kind = enh_pads[slot].kind;
    if (kind == ENH_DS_NONE) return;
    if (enh_lightbar) {
        uint8_t rgb[3] = {ENH_DS_DEFAULT_R, ENH_DS_DEFAULT_G, ENH_DS_DEFAULT_B};
        const uint64_t word = __atomic_load_n(&enh_life_word, __ATOMIC_ACQUIRE);
        const int64_t at = __atomic_load_n(&enh_life_ns, __ATOMIC_RELAXED);
        const int fresh = word && now - at < ENH_LIFE_STALE_NS;
        if (fresh) enh_ds_hearts_color((int)(word >> 16), (int)(word & 0xffff), now / 1000000, rgb);
        if (fresh && enh_beat) {
            const int64_t cycle = enh_ds_heartbeat_due((int)(word >> 16), (int)(word & 0xffff), now / 1000000,
                                                       enh_pads[slot].beat);
            if (cycle) {
                enh_pads[slot].beat = cycle;   /* (a cycle the game's rumble had is skipped, not put off) */
                const uint16_t lo = enh_ds_beat_level(ENH_DS_BEAT_LOW, strength), hi = enh_ds_beat_level(ENH_DS_BEAT_HIGH, strength);
                if (!game_rumbling && (lo || hi)) hos_sdl_pad_rumble(gc, lo, hi, ENH_DS_BEAT_MS);
            }
        }
        const int packed = rgb[0] << 16 | rgb[1] << 8 | rgb[2];
        if (packed != enh_pads[slot].rgb) {
            if (!hos_sdl_pad_led(gc, rgb[0], rgb[1], rgb[2]) && !(enh_pads[slot].warned & 1)) {
                enh_pads[slot].warned |= 1;
                hos_log("enhanced: \"%s\": SDL did not set the lightbar (%s)", hos_sdl_pad_name(gc), hos_sdl_error());
            }
            enh_pads[slot].rgb = packed;
        }
    }
    if (kind == ENH_DS_PS5 && enh_triggers && enh_pads[slot].triggers != enh_triggers) {
        uint8_t e[ENH_DS_EFFECT_SIZE];
        enh_ds_trigger_effect(enh_triggers, e);
        if (!hos_sdl_pad_effect(gc, e, sizeof e) && !(enh_pads[slot].warned & 2)) {
            enh_pads[slot].warned |= 2;
            hos_log("enhanced: \"%s\": SDL did not take the trigger effect (%s)", hos_sdl_pad_name(gc), hos_sdl_error());
        }
        enh_pads[slot].triggers = enh_triggers;
    }
}
