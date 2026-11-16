"""The player's settings file, hookshot_options.ini, in the user folder the game is given (host/options_path.c), not beside the
game: every build the launcher starts reads the same one, so an update into a new folder keeps the settings. Built as the game
builds it (Windows with its own headers, Linux with the POSIX shim) and run from a made-up game folder. No game: authored
placeholder files only.

- HOS_OPTIONS_FILE names the file (relative: to the working folder);
- --user <folder>: in that folder; relative, to the game folder when the game is started with nothing (it goes there), else to
  the working folder; --romfs and --compile-shaders take their values, and an image named first is not the user folder;
- no --user (RecompLauncher, a shortcut, the tools): beside the game, as before, whatever the working folder;
- chosen once;
- the copy: the game folder's file (a build's from before) into the user folder when that has none, and the log says where the
  file is. Not a file with only make_game.py's compile_shaders=, not over a file there, not with HOS_OPTIONS_FILE, not when the
  file is the game folder's; a user folder that cannot be written keeps the game folder's for the run.

python -I -B tests/test_options_path.py [--cc gcc]
"""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

RUN_ALL_ARGS = ["--cc", "gcc"]
ROOT = Path(__file__).resolve().parents[1]
WINDOWS = sys.platform == "win32"
EXE = "hookshot.exe" if WINDOWS else "hookshot"

MAIN = r'''
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include "options_path.h"
void hos_log(const char *fmt, ...) { va_list ap; va_start(ap, fmt); printf("log: "); vprintf(fmt, ap); printf("\n"); va_end(ap); }
int main(int argc, char **argv) {
    hos_options_choose(argc, argv);
    hos_options_choose(1, argv);   /* (once a process: the second call changes nothing) */
    if (getenv("T_CARRY")) hos_options_carry(), hos_options_carry();
    printf("file: %s\n", hos_options_file());
    return 0;
}
'''


def same(a, b):
    return os.path.normcase(os.path.normpath(str(a))) == os.path.normcase(os.path.normpath(str(b)))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cc", default="gcc")
    a = p.parse_args()
    cc = shutil.which(a.cc) or shutil.which("clang") or a.cc
    with tempfile.TemporaryDirectory(prefix="hookshot-options-path-") as tmp:
        tmp = Path(tmp)
        (tmp / "main.c").write_text(MAIN)
        built = tmp / EXE
        if WINDOWS:
            subprocess.run([cc, "-std=gnu11", "-I", str(ROOT / "host"), "-Wall", "-Wextra", "-Werror",
                            str(ROOT / "host" / "options_path.c"), str(tmp / "main.c"), "-o", str(built)], check=True)
        else:
            inc = ["-std=gnu11", "-I", str(ROOT / "host" / "posix"), "-I", str(ROOT / "host")]
            obj = tmp / "options_path.o"   # (no warning in it; the shim is built as the game builds it)
            subprocess.run([cc, *inc, "-Wall", "-Wextra", "-Werror", "-c", str(ROOT / "host" / "options_path.c"), "-o", str(obj)],
                           check=True)
            subprocess.run([cc, *inc, str(obj), str(ROOT / "host" / "posix" / "win32_posix.c"), str(tmp / "main.c"), "-o", str(built),
                            "-lpthread", "-ldl"], check=True)

        def game_folder(name, beside_image=True):
            game = tmp / name / "game"
            game.mkdir(parents=True)
            if beside_image:
                (game / "image.bin").write_text("image")
            shutil.copy2(built, game / EXE)
            return game

        cwd = tmp / "cwd"
        cwd.mkdir()

        def run(game, *args, carry=False, **env):
            e = {k: v for k, v in os.environ.items() if k not in ("HOS_OPTIONS_FILE", "T_CARRY")}
            if carry:
                e["T_CARRY"] = "1"
            e.update(env)
            out = subprocess.run([str(game / EXE), *args], cwd=cwd, env=e, check=True, capture_output=True, text=True,
                                 timeout=60).stdout
            return out.split("file: ", 1)[1].strip(), out

        def want(got, path, what):
            assert same(got, path), "%s: %s, not %s" % (what, got, path)

        g = game_folder("a")
        beside = g / "hookshot_options.ini"
        want(run(g)[0], beside, "started with nothing")
        want(run(g, "image.bin")[0], beside, "an image named, no --user")
        want(run(game_folder("b", beside_image=False))[0], tmp / "b" / "game" / "hookshot_options.ini", "no image.bin beside")
        want(run(g, "--romfs", "--user", "--user", str(tmp / "u"))[0], tmp / "u" / "hookshot_options.ini",
             "--romfs takes its value, even one named --user")
        want(run(g, "--compile-shaders", "all", "--user", str(tmp / "u"))[0], tmp / "u" / "hookshot_options.ini", "--user")
        want(run(g, "--user", "rel")[0], g / "rel" / "hookshot_options.ini", "--user relative, started with nothing")
        want(run(g, "image.bin", "--user", "rel")[0], cwd / "rel" / "hookshot_options.ini", "--user relative with an image")
        want(run(g, "--user", str(tmp / "u"), HOS_OPTIONS_FILE=str(tmp / "own.ini"))[0], tmp / "own.ini", "HOS_OPTIONS_FILE")
        want(run(g, HOS_OPTIONS_FILE="own.ini")[0], cwd / "own.ini", "HOS_OPTIONS_FILE relative")

        # the copy: a build's from before into the user folder, once; the log says where the file is
        g = game_folder("d")
        (g / "hookshot_options.ini").write_text("dlss=1\nframe_generation=2\ncompile_shaders=1\n")
        user = tmp / "d" / "user-folder"
        got, out = run(g, "--user", str(user), carry=True)
        want(got, user / "hookshot_options.ini", "after the copy")
        assert (user / "hookshot_options.ini").read_text() == "dlss=1\nframe_generation=2\ncompile_shaders=1\n", out
        assert out.count("options: the settings file is ") == 1 and str(user) in out, out
        assert out.count("were copied to") == 1, out
        (user / "hookshot_options.ini").write_text("dlss=4\n")   # (the player's since: never written over)
        got, out = run(g, "--user", str(user), carry=True)
        assert (user / "hookshot_options.ini").read_text() == "dlss=4\n" and "copied" not in out, out
        got, out = run(g, carry=True)   # (no --user: the game folder's, as before, nothing copied)
        want(got, g / "hookshot_options.ini", "no --user, after a copy")
        assert "copied" not in out and str(g / "hookshot_options.ini") in out, out

        g = game_folder("e")
        (g / "hookshot_options.ini").write_text("compile_shaders=1\n")   # (make_game.py's, a new folder: not the player's)
        user = tmp / "e" / "user-folder"
        got, out = run(g, "--user", str(user), carry=True)
        assert not (user / "hookshot_options.ini").exists() and "copied" not in out, out

        g = game_folder("f")
        (g / "hookshot_options.ini").write_text("dlss=1\n")
        got, out = run(g, "--user", str(tmp / "f" / "u"), carry=True, HOS_OPTIONS_FILE=str(tmp / "f" / "own.ini"))
        assert not (tmp / "f" / "own.ini").exists() and not (tmp / "f" / "u").exists() and "copied" not in out, out
        got, out = run(g, "--user", str(g), carry=True)   # (the user folder is the game folder: the file is already there)
        want(got, g / "hookshot_options.ini", "--user the game folder")
        assert "copied" not in out and (g / "hookshot_options.ini").read_text() == "dlss=1\n", out
        blocked = tmp / "f" / "blocked"
        blocked.write_text("a file where the user folder would be")
        got, out = run(g, "--user", str(blocked), carry=True)
        want(got, g / "hookshot_options.ini", "a user folder that cannot be written")
        assert "could not be copied" in out, out
    print("PASS: hookshot_options.ini in the user folder (HOS_OPTIONS_FILE, --user; without it beside the game, as before), "
          "chosen once; a build's from before copied there once (not compile_shaders= alone, not over a file, not with "
          "HOS_OPTIONS_FILE), the log saying where it is")


if __name__ == "__main__":
    main()
