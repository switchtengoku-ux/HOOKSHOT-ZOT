/* (enhanced) Hookshot Enhanced: Music volume and Effects volume (host/enh_audio.h has the rule and the curve,
   docs/enhanced/AUDIO_MIX.md the guide).

   host/nn_audio.c render_frame asks hos_enh_audio_gain, on the mixer thread, for each playing voice's gain this frame
   (its group's) and the one its last frame had, and scales the voice's own volume ramp by them for the frame. The Insert
   menu's Audio rows set the percents (HOS_OPT_ENH_MUSIC_VOLUME, HOS_OPT_ENH_EFFECTS_VOLUME), read again every 50 ms;
   HOOKSHOT_ENH_MUSIC_VOLUME / HOOKSHOT_ENH_EFFECTS_VOLUME (0 to 150) in hookshot_env.txt win over them for the run.
   At 100% both, nothing is changed. HOOKSHOT_ENH_AUDIO_LOG=1 logs each voice slot's group when it changes. */
#include "hos.h"
#include <stdio.h>
#include <stdlib.h>
#include "enh_audio.h"
#include "enh_product.h"   /* (enh_env: the switches' names) */
#include "../gpu/vk/vk_api.h"   /* (HOS_OPT_ENH_*) */

#define ENH_AUDIO_VOICES 512   /* (nn_audio.c MAX_VOICES) */
#define ENH_AUDIO_REFRESH_NS 50000000LL

int rx_option(int id, int otherwise);   /* host/rx_backend.c: the Insert menu's rows */

static int env_music = -2, env_effects = -2, audio_log = -1;
static float gains[2] = {1.0f, 1.0f};   /* [ENH_AUDIO_EFFECTS], [ENH_AUDIO_MUSIC] */
static int64_t gains_ns;
static int logged_percents = -1;
static float last_gain[ENH_AUDIO_VOICES];
static signed char last_class[ENH_AUDIO_VOICES];
static int ready;

static int env_percent(const char *name) {
    const char *v = enh_env(name);
    if (!v || !*v) return -1;
    const int p = atoi(v);
    return p < 0 ? 0 : p > ENH_AUDIO_MAX_PERCENT ? ENH_AUDIO_MAX_PERCENT : p;
}

static void refresh(int64_t now) {
    if (env_music == -2) {
        env_music = env_percent("MUSIC_VOLUME");
        env_effects = env_percent("EFFECTS_VOLUME");
        audio_log = enh_env("AUDIO_LOG") && atoi(enh_env("AUDIO_LOG")) != 0;
    }
    if (gains_ns && now - gains_ns < ENH_AUDIO_REFRESH_NS) return;
    gains_ns = now;
    const int music = env_music >= 0 ? env_music : rx_option(HOS_OPT_ENH_MUSIC_VOLUME, 100);
    const int effects = env_effects >= 0 ? env_effects : rx_option(HOS_OPT_ENH_EFFECTS_VOLUME, 100);
    gains[ENH_AUDIO_MUSIC] = enh_audio_gain(music);
    gains[ENH_AUDIO_EFFECTS] = enh_audio_gain(effects);
    if ((music << 8 | effects) != logged_percents) {
        if (logged_percents >= 0 || music != 100 || effects != 100)
            hos_log("enhanced: music volume %d%%, effects volume %d%%%s", music, effects,
                    env_music >= 0 || env_effects >= 0 ? " (" ENH_ENV_FILE " sets some)" : "");
        logged_percents = music << 8 | effects;
    }
}

static int64_t last_played[ENH_AUDIO_VOICES];

/* the voice stopped (or was never started): its next sound is judged afresh */
void hos_enh_audio_forget(int index) {
    if (index >= 0 && index < ENH_AUDIO_VOICES && ready) last_class[index] = -1, last_played[index] = 0;
}

void hos_enh_audio_gain(int index, int is_pcm16, int queued, int loops, float pitch, int destinations, int64_t played,
                        float *from, float *to) {
    if (index < 0 || index >= ENH_AUDIO_VOICES) return;
    if (!ready) {
        for (int i = 0; i < ENH_AUDIO_VOICES; i++) last_gain[i] = 1.0f, last_class[i] = -1;
        ready = 1;
    }
    refresh(hos_now_ns());
    if (played < last_played[index]) last_class[index] = -1;   /* (a new sound in this voice) */
    last_played[index] = played;
    int group = enh_audio_class(is_pcm16, queued, loops, pitch, destinations);
    if (last_class[index] == ENH_AUDIO_MUSIC) group = ENH_AUDIO_MUSIC;   /* (music until it stops) */
    if (audio_log && last_class[index] != group)
        hos_log("enhanced: voice %d is %s (%s, %d queued%s, pitch %.2f, %d destinations)", index,
                group == ENH_AUDIO_MUSIC ? "music" : "effects", is_pcm16 ? "PCM16" : "ADPCM or other", queued,
                loops ? ", looping" : "", pitch, destinations);
    last_class[index] = (signed char)group;
    *from = last_gain[index];
    *to = gains[group];
    last_gain[index] = *to;
}