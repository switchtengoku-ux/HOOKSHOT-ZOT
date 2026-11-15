/* (enhanced) Hookshot Enhanced: PlayStation pads' lightbar and the DualSense's adaptive triggers, the pure part
   (no state, no SDL): host/enh_dualsense.c uses it, tests/test_enh_dualsense.py compiles it.

   - Which pads: from SDL_GetGamepadType (SDL3: PS4 5, PS5 6) or SDL_GameControllerGetType (SDL2: PS4 4, PS5 7).
   - Lightbar "hearts": Link's life over his hearts' total as green (full), through yellow (half), to red (empty); at one
     heart or less it blinks (on 400 ms, off 400 ms).
   - Triggers: the DualSense output report's effect block as SDL_SendGamepadEffect takes it (SDL's DS5EffectsState_t, 47
     bytes): only the right and left trigger effects are enabled (bits 0x04 and 0x08 of the first byte), so SDL's
     rumble, lightbar and player lights are left alone. Effect 0x05 clears a trigger; 0x01 is a constant resistance from
     the start of the pull (start position, force). */
#pragma once
#include <stdint.h>
#include <string.h>

enum { ENH_DS_NONE, ENH_DS_PS4, ENH_DS_PS5 };
enum { ENH_DS_LIGHTBAR_OFF, ENH_DS_LIGHTBAR_HEARTS };
enum { ENH_DS_TRIGGERS_OFF, ENH_DS_TRIGGERS_LIGHT, ENH_DS_TRIGGERS_STRONG };

#define ENH_DS_EFFECT_SIZE 47
#define ENH_DS_RIGHT_TRIGGER 10   /* (offsets in the effect block) */
#define ENH_DS_LEFT_TRIGGER 21
#define ENH_DS_BLINK_MS 400
/* SDL's own lightbar colour for the first player on a DualSense (put back when the game no longer drives it) */
#define ENH_DS_DEFAULT_R 0x00
#define ENH_DS_DEFAULT_G 0x00
#define ENH_DS_DEFAULT_B 0x40

static inline int enh_ds_kind(int sdl_version, int type) {
    if (sdl_version == 3) return type == 5 ? ENH_DS_PS4 : type == 6 ? ENH_DS_PS5 : ENH_DS_NONE;
    if (sdl_version == 2) return type == 4 ? ENH_DS_PS4 : type == 7 ? ENH_DS_PS5 : ENH_DS_NONE;
    return ENH_DS_NONE;
}

/* HOOKSHOT_ENH_LIGHTBAR: "hearts" (or 1) on, anything else (unset, "off", 0) off */
static inline int enh_ds_parse_lightbar(const char *v) {
    if (!v) return ENH_DS_LIGHTBAR_OFF;
    return !strcmp(v, "hearts") || !strcmp(v, "1") ? ENH_DS_LIGHTBAR_HEARTS : ENH_DS_LIGHTBAR_OFF;
}
/* HOOKSHOT_ENH_TRIGGERS: 1 or "light", 2 or "strong"; anything else off */
static inline int enh_ds_parse_triggers(const char *v) {
    if (!v) return ENH_DS_TRIGGERS_OFF;
    if (!strcmp(v, "1") || !strcmp(v, "light")) return ENH_DS_TRIGGERS_LIGHT;
    if (!strcmp(v, "2") || !strcmp(v, "strong")) return ENH_DS_TRIGGERS_STRONG;
    return ENH_DS_TRIGGERS_OFF;
}

/* The lightbar for life of max (quarter hearts, as the game keeps them) at now_ms. 0 and rgb untouched when the numbers
   are not a life (max not positive, life negative or above max, or past the game's 20 hearts) */
static inline int enh_ds_hearts_color(int life, int max, int64_t now_ms, uint8_t rgb[3]) {
    if (max <= 0 || max > 20 * 4 || life < 0 || life > max) return 0;
    if (life <= 4 && (now_ms / ENH_DS_BLINK_MS) % 2) {   /* (one heart or less: the off half of the blink) */
        rgb[0] = rgb[1] = rgb[2] = 0;
        return 1;
    }
    /* green to yellow over the upper half, yellow to red over the lower one (x: life * 2, from 0 to 2 * max) */
    const int x = life * 2;
    if (x >= max) {
        rgb[0] = (uint8_t)(255 * (2 * max - x) / max);
        rgb[1] = 255;
    } else {
        rgb[0] = 255;
        rgb[1] = (uint8_t)(255 * x / max);
    }
    rgb[2] = 0;
    return 1;
}

/* Low-life heartbeat: a short pulse at the start of each blink (one heart or less), on the pad's motors. Returns the
   blink cycle to pulse for (1 or more) when one is due and was not pulsed yet (last: the cycle pulsed last), else 0 */
#define ENH_DS_BEAT_MS 90
#define ENH_DS_BEAT_LOW 14000    /* (the heavy motor, 0..65535, at Rumble strength 100) */
#define ENH_DS_BEAT_HIGH 9000    /* (the light one) */
static inline int64_t enh_ds_heartbeat_due(int life, int max, int64_t now_ms, int64_t last) {
    if (max <= 0 || max > 20 * 4 || life < 0 || life > 4 || life > max || now_ms < 0) return 0;
    if ((now_ms / ENH_DS_BLINK_MS) % 2) return 0;   /* (only in the on half, where the red shows) */
    const int64_t cycle = now_ms / (2 * ENH_DS_BLINK_MS) + 1;
    return cycle != last ? cycle : 0;
}
/* A motor value at the menu's Rumble strength (percent, 0 Off), kept to the motor's range */
static inline uint16_t enh_ds_beat_level(int base, int strength) {
    if (strength <= 0) return 0;
    const long v = (long)base * strength / 100;
    return (uint16_t)(v > 65535 ? 65535 : v);
}

/* The effect block for a trigger setting: both triggers the same */
static inline void enh_ds_trigger_effect(int level, uint8_t out[ENH_DS_EFFECT_SIZE]) {
    memset(out, 0, ENH_DS_EFFECT_SIZE);
    out[0] = 0x04 | 0x08;   /* (modify the right and the left trigger's effect, nothing else) */
    uint8_t t[11] = {0x05};   /* (clear) */
    if (level == ENH_DS_TRIGGERS_LIGHT) t[0] = 0x01, t[1] = 0, t[2] = 60;
    else if (level == ENH_DS_TRIGGERS_STRONG) t[0] = 0x01, t[1] = 0, t[2] = 160;
    memcpy(out + ENH_DS_RIGHT_TRIGGER, t, sizeof t);
    memcpy(out + ENH_DS_LEFT_TRIGGER, t, sizeof t);
}
