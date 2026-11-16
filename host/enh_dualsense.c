/* (enhanced) Hookshot Enhanced: PlayStation pads' lightbar, low-life pulse and the DualSense's adaptive triggers
   (host/enh_dualsense.h has the colours and the effect block, docs/enhanced/DUALSENSE.md the guide).

   The Insert menu's Controls rows choose them (HOS_OPT_ENH_*: Lightbar, Low-life pulse, Adaptive triggers), and change
   at once. A switch in hookshot_env.txt (or the environment), when set, wins over its row for the run:
     HOOKSHOT_ENH_LIGHTBAR=hearts | off
     HOOKSHOT_ENH_LOW_LIFE_RUMBLE=1 | 0
     HOOKSHOT_ENH_TRIGGERS=1 | 2 | off
   With everything off, nothing is sent to any pad (a pad this code changed is put back first).

   Two threads meet here. The game's (host/hos_main.c hos_oot_lift_player, while Link is updated, so only in play)
   hands Link's life over through one atomic word and its time; the pads' (host/pad_sdl.c pads_poll, every 4 ms) sends
   each pad what changed: the lightbar only when its colour changes, the triggers when their setting changes or the pad
   connects. When the life is older than ENH_LIFE_STALE_NS (the title, a pause, a load) the lightbar goes back to SDL's
   own first-player colour. At one heart or less each red blink also gives a short pulse on the motors (the menu's
   Rumble strength scales it, Off turns it off), never while the game's own rumble plays: pad_sdl.c's next rumble, the
   game's, replaces it, and its duration (ENH_DS_BEAT_MS) ends it otherwise.
   At exit the triggers are cleared and the lightbar put back, so the pad does not keep the game's resistance. */
#include "hos.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "hos_sdl.h"
#include "enh_dualsense.h"
#include "enh_product.h"   /* (enh_env: the switches' names) */
#include "../gpu/vk/vk_api.h"   /* (HOS_OPT_ENH_*) */

#define ENH_MAX_PADS 8
#define ENH_LIFE_STALE_NS 2000000000LL

int rx_option(int id, int otherwise);   /* host/rx_backend.c: the Insert menu's rows */

/* the environment's switches: -1 unset (the menu decides), else the value; read once */
static int env_lightbar = -2, env_beat = -2, env_triggers = -2;
static int logged = -1;   /* (the settings last logged, packed) */
static uint64_t enh_life_word;   /* (life << 16 | max, 0 none: written by the game's thread) */
static int64_t enh_life_ns;
static struct {
    void *gc;
    uint32_t serial;
    int kind;
    int rgb;              /* (the colour last sent, 0xRRGGBB, or -1: not touched) */
    int triggers;         /* (the trigger setting sent, or -1: not touched) */
    int warned;
    int64_t beat;         /* (the blink cycle pulsed last) */
} enh_pads[ENH_MAX_PADS];

typedef struct { int lightbar, beat, triggers; } EnhSettings;

static EnhSettings enh_settings(void) {
    if (env_lightbar == -2) {
        const char *l = enh_env("LIGHTBAR"), *b = enh_env("LOW_LIFE_RUMBLE"), *t = enh_env("TRIGGERS");
        env_lightbar = l ? enh_ds_parse_lightbar(l) : -1;
        env_beat = b ? !(!strcmp(b, "0") || !strcmp(b, "off")) : -1;
        env_triggers = t ? enh_ds_parse_triggers(t) : -1;
    }
    EnhSettings s;
    s.lightbar = env_lightbar >= 0 ? env_lightbar : rx_option(HOS_OPT_ENH_LIGHTBAR, 0) != 0;
    s.beat = s.lightbar && (env_beat >= 0 ? env_beat : rx_option(HOS_OPT_ENH_LOW_LIFE_RUMBLE, 1) != 0);
    const int t = env_triggers >= 0 ? env_triggers : rx_option(HOS_OPT_ENH_TRIGGERS, 0);
    s.triggers = t >= ENH_DS_TRIGGERS_OFF && t <= ENH_DS_TRIGGERS_STRONG ? t : ENH_DS_TRIGGERS_OFF;
    const int packed = s.lightbar | s.beat << 1 | s.triggers << 2;
    if (packed != logged) {
        if (logged >= 0 || packed)
            hos_log("enhanced: PlayStation pads: lightbar %s, low-life pulse %s, adaptive triggers %s%s",
                    s.lightbar ? "hearts" : "off", s.beat ? "on" : "off",
                    s.triggers == ENH_DS_TRIGGERS_STRONG ? "strong" : s.triggers ? "light" : "off",
                    env_lightbar >= 0 || env_beat >= 0 || env_triggers >= 0 ? " (" ENH_ENV_FILE " sets some)" : "");
        logged = packed;
    }
    return s;
}

int hos_enh_lightbar_on(void) { return enh_settings().lightbar; }

void hos_enh_set_life(int life, int max) {
    if (life < 0 || max <= 0 || life > 0xffff || max > 0xffff) return;
    __atomic_store_n(&enh_life_ns, hos_now_ns(), __ATOMIC_RELAXED);
    __atomic_store_n(&enh_life_word, (uint64_t)life << 16 | (uint64_t)max, __ATOMIC_RELEASE);
}

static void enh_send_triggers(int slot, void *gc, int level) {
    uint8_t e[ENH_DS_EFFECT_SIZE];
    enh_ds_trigger_effect(level, e);
    if (!hos_sdl_pad_effect(gc, e, sizeof e) && !(enh_pads[slot].warned & 2)) {
        enh_pads[slot].warned |= 2;
        hos_log("enhanced: \"%s\": SDL did not take the trigger effect (%s)", hos_sdl_pad_name(gc), hos_sdl_error());
    }
    enh_pads[slot].triggers = level;
}

static void enh_send_led(int slot, void *gc, const uint8_t rgb[3]) {
    if (!hos_sdl_pad_led(gc, rgb[0], rgb[1], rgb[2]) && !(enh_pads[slot].warned & 1)) {
        enh_pads[slot].warned |= 1;
        hos_log("enhanced: \"%s\": SDL did not set the lightbar (%s)", hos_sdl_pad_name(gc), hos_sdl_error());
    }
}

static void enh_restore_all(void) {   /* (at exit: the pads as SDL had them) */
    static const uint8_t blue[3] = {ENH_DS_DEFAULT_R, ENH_DS_DEFAULT_G, ENH_DS_DEFAULT_B};
    for (int i = 0; i < ENH_MAX_PADS; i++) {
        void *gc = enh_pads[i].gc;
        if (!gc) continue;
        if (enh_pads[i].triggers > 0) enh_send_triggers(i, gc, ENH_DS_TRIGGERS_OFF);
        if (enh_pads[i].rgb >= 0) enh_send_led(i, gc, blue);
    }
}

void hos_enh_pad_gone(int slot) {
    if (slot >= 0 && slot < ENH_MAX_PADS) enh_pads[slot].gc = NULL;
}

void hos_enh_pad(int slot, void *gc, uint32_t serial, int64_t now, int game_rumbling, int strength) {
    if (slot < 0 || slot >= ENH_MAX_PADS || !gc) return;
    const EnhSettings s = enh_settings();
    const int fresh_pad = enh_pads[slot].gc != gc || enh_pads[slot].serial != serial;
    /* (all off: nothing to do, unless this pad still shows what an earlier setting sent) */
    if (!s.lightbar && !s.triggers && (fresh_pad || (enh_pads[slot].rgb < 0 && enh_pads[slot].triggers <= 0))) return;
    static int exit_hook;
    if (!exit_hook) {
        exit_hook = 1;
        atexit(enh_restore_all);
    }
    if (fresh_pad) {   /* (a pad newly opened in this slot) */
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
    uint8_t rgb[3] = {ENH_DS_DEFAULT_R, ENH_DS_DEFAULT_G, ENH_DS_DEFAULT_B};
    if (s.lightbar) {
        const uint64_t word = __atomic_load_n(&enh_life_word, __ATOMIC_ACQUIRE);
        const int64_t at = __atomic_load_n(&enh_life_ns, __ATOMIC_RELAXED);
        const int fresh = word && now - at < ENH_LIFE_STALE_NS;
        if (fresh) enh_ds_hearts_color((int)(word >> 16), (int)(word & 0xffff), now / 1000000, rgb);
        if (fresh && s.beat) {
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
            enh_send_led(slot, gc, rgb);
            enh_pads[slot].rgb = packed;
        }
    } else if (enh_pads[slot].rgb >= 0) {   /* (turned off: SDL's colour back, then left alone) */
        enh_send_led(slot, gc, rgb);
        enh_pads[slot].rgb = -1;
    }
    if (kind == ENH_DS_PS5 && enh_pads[slot].triggers != s.triggers && (s.triggers || enh_pads[slot].triggers > 0))
        enh_send_triggers(slot, gc, s.triggers);
}
