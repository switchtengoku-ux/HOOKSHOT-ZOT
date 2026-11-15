"""Hookshot Enhanced's Music volume and Effects volume, the pure part (host/enh_audio.h, used by host/enh_audio.c),
compiled and checked with no game and no sound device:

- a voice is music when it is PCM16 (the title screen's stream player), or when it streams (three or more buffers
  queued, not looping) dry (one destination) at a pitch of exactly 1, as the music in play does; a streamed ambience
  with reverb sends, a pitch-bent stream, a looping sound and short one- or two-buffer effects are effects;
- the percent curve is the Volume row's (50% a quarter), 0 silences, 100 is 1, 150 is the top and anything above
  is held there;
Also checks the wiring: host/nn_audio.c render_frame renders each voice through enh_render_voice, which asks
hos_enh_audio_gain for the voice's gains and puts its volume back after (marked (enhanced)), outside the part of
nn_audio.c that tests/test_audio_biquad.py compiles; and
the Insert menu has its two Audio rows with enh_ keys, as sliders that stop at their ends, answered by the renderer's
option callback under IDs 64 and 65.

python -I -B tests/test_enh_audio.py [--cc clang]
"""
import argparse
from pathlib import Path
import subprocess
import tempfile

RUN_ALL_ARGS = ["--cc", "clang"]

ROOT = Path(__file__).resolve().parents[1]

FIXTURE = r'''#include <math.h>
#include <stdio.h>
#include "enh_audio.h"
#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL:%d %s\n", __LINE__, #x); return 1; } } while (0)
#define NEAR(a, b) (fabsf((a) - (b)) < 1e-5f)
int main(void) {
    CHECK(enh_audio_class(1, 4, 0, 1.0f, 1) == ENH_AUDIO_MUSIC);    /* the title screen's PCM16 stream */
    CHECK(enh_audio_class(1, 1, 1, 0.9f, 3) == ENH_AUDIO_MUSIC);    /* PCM16 whatever else */
    CHECK(enh_audio_class(0, 4, 0, 1.0f, 1) == ENH_AUDIO_MUSIC);    /* in play: a dry ADPCM stream at pitch 1 */
    CHECK(enh_audio_class(0, 3, 0, 1.0f, 1) == ENH_AUDIO_MUSIC);
    CHECK(enh_audio_class(0, 4, 0, 1.0f, 3) == ENH_AUDIO_EFFECTS);  /* an ambience with reverb sends */
    CHECK(enh_audio_class(0, 4, 0, 0.94f, 1) == ENH_AUDIO_EFFECTS); /* a pitch-bent stream */
    CHECK(enh_audio_class(0, 2, 0, 1.0f, 1) == ENH_AUDIO_EFFECTS);  /* a short sound */
    CHECK(enh_audio_class(0, 4, 1, 1.0f, 1) == ENH_AUDIO_EFFECTS);  /* a loop */
    CHECK(enh_audio_class(0, 4, 0, 1.0f, 0) == ENH_AUDIO_EFFECTS);  /* sent nowhere */
    CHECK(enh_audio_gain(0) == 0.0f && enh_audio_gain(-5) == 0.0f);
    CHECK(NEAR(enh_audio_gain(100), 1.0f) && NEAR(enh_audio_gain(50), 0.25f) && NEAR(enh_audio_gain(150), 2.25f));
    CHECK(NEAR(enh_audio_gain(400), 2.25f));
    puts("ok: music rule and volume curve");
    return 0;
}
'''


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cc", default="clang")
    args = p.parse_args()
    audio = (ROOT / "host" / "nn_audio.c").read_text(encoding="utf-8")
    hook = audio[audio.index("static void enh_render_voice("):]
    hook = hook[:hook.index("\n}\n")]
    assert "hos_enh_audio_gain((int)(v - voices), v->format == FMT_PCM16, v->nwb," in hook, \
        "host/nn_audio.c enh_render_voice no longer asks hos_enh_audio_gain"
    assert "hos_enh_audio_forget((int)(v - voices));" in hook, "host/nn_audio.c no longer resets a stopped voice's group"
    assert "v->volume = volume;" in hook, "host/nn_audio.c enh_render_voice no longer puts the voice's volume back"
    assert "enh_render_voice(&voices[i]);   /* (enhanced)" in audio, "host/nn_audio.c render_frame bypasses the volumes"
    tested = audio[audio.index("#define FRAME"):audio.index("static int mix_depth(")]
    assert "enh_" not in tested, "the fork's code moved into the part tests/test_audio_biquad.py compiles alone"
    menu = (ROOT / "gpu" / "vk" / "vk_menu.cpp").read_text(encoding="utf-8")
    replay = (ROOT / "gpu" / "vk" / "vk_replay.cpp").read_text(encoding="utf-8")
    api = (ROOT / "gpu" / "vk" / "vk_api.h").read_text(encoding="utf-8")
    for row, field, opt in (("Music volume", "enh_music_volume", "HOS_OPT_ENH_MUSIC_VOLUME"),
                            ("Effects volume", "enh_effects_volume", "HOS_OPT_ENH_EFFECTS_VOLUME")):
        assert '{TAB_AUDIO, "%s", &opts.%s, 0, 150, 5,' % (row, field) in menu, "vk_menu.cpp: no %s row" % row
        assert '!strcmp(r.name, "%s")) return "%s";' % (row, field) in menu, "vk_menu.cpp: %s has no enh_ key" % row
        assert "if (id == %s) return opts.%s;" % (opt, field) in replay, "vk_replay.cpp does not answer %s" % opt
    for fn in ("bool is_slider(", "bool stops_at_ends("):
        body = menu[menu.index(fn):]
        body = body[:body.index("}")]
        assert '"Music volume"' in body and '"Effects volume"' in body, "vk_menu.cpp %s leaves the rows out" % fn
    assert "HOS_OPT_ENH_MUSIC_VOLUME = 64" in api, "the Audio rows' option IDs moved"
    with tempfile.TemporaryDirectory() as tmp:
        src, exe = Path(tmp) / "fixture.c", Path(tmp) / "fixture.exe"
        src.write_text(FIXTURE, encoding="utf-8")
        subprocess.run([args.cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "host"), str(src), "-lm",
                        "-o", str(exe)], check=True)
        out = subprocess.run([str(exe)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stderr or "the fixture failed")
        print(out.stdout.strip())


if __name__ == "__main__":
    main()
