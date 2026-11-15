/* (enhanced) Hookshot Enhanced: Music volume and Effects volume, the pure part (no state): host/enh_audio.c uses it,
   tests/test_enh_audio.py compiles it.

   Which voices are the music, from runs of the game's sound graph with every voice logged (docs/enhanced/AUDIO_MIX.md):
   - the title screen's music is the game's PCM16 stream player (six voices, a 5.1 stream);
   - in play the music is ADPCM like everything else, but streamed (buffers kept queued, three or four, never a loop),
     at a pitch of exactly 1 and dry: one destination, no send to the reverb sub mixes. The ambiences are streamed too,
     but sent to the reverb (several destinations) or bent in pitch; the effects are short sounds of one or two
     buffers, mostly with reverb sends and varied pitch.
   Where a voice goes is otherwise no sign: in play the music shares the effects' sub mix.
   So a voice is music when it is PCM16, or when it streams dry at pitch 1. A voice keeps the group it was first seen
   in as music until it stops (host/enh_audio.c), so a queue that runs low for a moment does not move it back.
   A row's percent becomes a gain on the same curve as the Insert menu's Volume (gpu/vk/vk_menu.cpp: 50% is a quarter,
   -12 dB): (percent / 100) squared, so 150% is 2.25 (+7 dB). */
#pragma once
#include <stdint.h>

enum { ENH_AUDIO_EFFECTS, ENH_AUDIO_MUSIC };
#define ENH_AUDIO_MAX_PERCENT 150

/* is_pcm16: the voice's format; queued: wave buffers queued now; loops: the current one loops; pitch: the voice's;
   destinations: how many mixes it is sent to (a splitter's count, 1 for a mix, 0 for none) */
static inline int enh_audio_class(int is_pcm16, int queued, int loops, float pitch, int destinations) {
    if (is_pcm16) return ENH_AUDIO_MUSIC;
    const int streamed = queued >= 3 && !loops, dry = destinations == 1, plain = pitch > 0.9999f && pitch < 1.0001f;
    return streamed && dry && plain ? ENH_AUDIO_MUSIC : ENH_AUDIO_EFFECTS;
}

static inline float enh_audio_gain(int percent) {
    if (percent <= 0) return 0.0f;
    if (percent > ENH_AUDIO_MAX_PERCENT) percent = ENH_AUDIO_MAX_PERCENT;
    const float p = (float)percent / 100.0f;
    return p * p;
}
