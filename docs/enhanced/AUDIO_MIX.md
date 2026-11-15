# Music volume and Effects volume (Hookshot Enhanced)

Two rows on the Insert menu's **Audio** tab, under Volume: **Music volume** and **Effects volume**, 0 to 150% in steps
of 5, 100% by default. They change at once and are saved as `enh_music_volume` and `enh_effects_volume` in
`hookshot_options.ini`. They follow the Volume row's curve (50% is a quarter, -12 dB; 150% is 2.25 times, +7 dB), and
Volume still applies on top. At 100% both, the sound is exactly upstream's. The game's own settings have no such rows.

For one run, `HOOKSHOT_ENH_MUSIC_VOLUME=<0..150>` and `HOOKSHOT_ENH_EFFECTS_VOLUME=<0..150>` in `hookshot_env.txt`
win over the rows. `HOOKSHOT_ENH_AUDIO_LOG=1` logs each voice slot's group when it changes
(`enhanced: voice 26 is music (ADPCM or other, 4 queued, pitch 1.00, 1 destinations)`); `=2` also lists every playing
voice every 2 s.

## Which sound is the music

The game names nothing in its sound graph, so the rule comes from recorded runs (2026-11-15, v2.3.1: the title screen,
Hyrule Field standing and swinging the sword, the pause menu; `HOS_AUDIO_TRACE=1`, `HOS_AUDIO_STATS=1`, and
`HOOKSHOT_ENH_AUDIO_LOG=2`, which logs every playing voice every 2 s):

- The graph: the final mix (0) is fed by one bus (sub mix 5), which is fed by the effect sub mixes (1, and 10 with its
  own children 3, 4, 6, 7, 8, 9: reverb and other sends). Voices reach them through splitters, which the game reroutes
  as it plays.
- The title screen's music: the game's PCM16 stream player, six voices (a 5.1 stream as mono voices), straight to the
  bus.
- **The music in play is ADPCM**, like the effects, and goes through sub mix 1 with them. What sets it apart: it
  streams (three or four buffers kept queued, hundreds appended, never a loop), at a pitch of exactly 1.00, dry (one
  destination, no reverb send). In Hyrule Field: four such voices in lockstep, and a stereo pair to the bus.
- The ambiences stream too, but with reverb sends (sub mixes 3 and 6) or a pitch that bends; the effects are short
  sounds of one or two buffers, mostly with reverb sends and varied pitch.

Two first rules failed in play and were replaced: "sent straight to the bus" (the title screen only) and "PCM16" (the
title screen only).

So a voice is **music** when it is PCM16, or when it streams dry at pitch 1; everything else is **effects**. A voice
keeps the music group until it stops, so a queue that runs low for a moment does not move it. A check run with Music
volume at 0% took the title screen's bus energy from 0.617 to 0, and in play logged the field's streams as music.
## How it works

- `host/enh_audio.h` (new): the rule and the curve, compiled by `tests/test_enh_audio.py`.
- `host/enh_audio.c` (new): the percents (the rows, or the environment), read every 50 ms, and each voice's gain this
  frame and its last.
- `host/nn_audio.c` (marked `(enhanced)`): `render_frame` renders each voice through `enh_render_voice`, which asks
  `hos_enh_audio_gain` for the voice's gains (by its format, queue, loop, pitch and destinations) and scales
  the voice's own volume ramp by those gains for the frame and puts the volume back after, so the change ramps over
  a frame like the game's own volume changes. It sits outside the part of `nn_audio.c` that
  `tests/test_audio_biquad.py` compiles alone.
- `gpu/vk/vk_api.h` (`HOS_OPT_ENH_MUSIC_VOLUME` 64, `HOS_OPT_ENH_EFFECTS_VOLUME` 65), `gpu/vk/vk_replay.cpp`,
  `gpu/vk/vk_menu.h`/`.cpp` (the rows, sliders that stop at their ends, their `enh_` keys), `readme.md` (their lines).

## Limits

- Voiced dialogue was not in the recorded runs. If the game streams it through the same PCM16 player, it counts as
  music; then a third row (Voice volume) needs another rule.
- Above 100%, loud music can clip; the game's own limiter still runs after the mix.
- The rows are not translated yet.
