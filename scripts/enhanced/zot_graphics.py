"""Hookshot Enhanced graphics profiles: the Insert menu's Graphics tab saved under a name and put back in one go.

    python -I scripts/enhanced/zot_graphics.py save NAME --game GAME [--force]   the game's Graphics settings, as NAME
    python -I scripts/enhanced/zot_graphics.py list                               the profiles
    python -I scripts/enhanced/zot_graphics.py show NAME                          a profile's settings
    python -I scripts/enhanced/zot_graphics.py diff NAME --game GAME              what applying it would change
    python -I scripts/enhanced/zot_graphics.py apply NAME --game GAME [--dry-run] [--force]
    python -I scripts/enhanced/zot_graphics.py delete NAME
    --store DIR (any command): where profiles are kept; default %LOCALAPPDATA%\\HookshotZOT\\graphics-profiles on
    Windows, $XDG_DATA_HOME/hookshot-zot/graphics-profiles on Linux, or $HOOKSHOT_ZOT_GRAPHICS when set.

GAME is the game folder, the one with hookshot_options.ini (gpu/vk/vk_menu.cpp writes it beside the game). A profile is
a small text file of the Graphics tab's lines (GRAPHICS_KEYS, the keys the menu saves its Graphics rows under), so the
same profile works for every game folder. apply changes those lines only: the Audio, Gameplay and Controls lines, the
controls and every other line stay as they are, in their order. The file as it was is copied to <store>/backups first,
and the new one is written beside it and renamed into place.

The game rewrites the whole file at every change in the menu, and reads it at the start: close the game before apply
(it refuses while Hookshot runs; --force skips that check). Rows marked "after a restart" in the menu take effect at the
next start anyway. Standard library only; the guide is docs/enhanced/GRAPHICS_PROFILES.md.
"""
import argparse
import datetime
import importlib.util
import os
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("oot_saves", os.path.join(os.path.dirname(HERE), "oot_saves.py"))
oot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oot)

Fail = oot.Fail
OPTIONS = "hookshot_options.ini"
SUFFIX = ".ini"
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_ -]{0,39}$")
HEADER = "# Hookshot Enhanced graphics profile: the Graphics tab of hookshot_options.ini (scripts/enhanced/zot_graphics.py)"
# The Graphics tab's rows as hookshot_options.ini keys them, in the menu's order (gpu/vk/vk_menu.cpp rows and ini_key;
# tests/test_enh_graphics.py checks this list against them)
GRAPHICS_KEYS = (
    "quality_preset", "ultrawide", "output_res", "handheld_profile", "dlss", "dlss_model", "resolution", "sharpness",
    "frame_generation", "frame_generation_by", "frame_pacing", "frame_rate_cap", "nvidia_reflex", "amd_anti-lag_2",
    "fullscreen", "vsync", "upscaling", "ultrawide_menus", "hdr", "hdr_paper_white", "hdr_peak_brightness",
    "hdr_contrast", "hdr_tone_mapper", "texture_detail", "anisotropic_filtering", "gpu_device", "threaded_rendering",
    "vram_budget",
)
VALUE = re.compile(r"[A-Za-z0-9x._ -]{0,64}$")
# Each key's row name and its choices as the menu shows them (gpu/vk/vk_menu.cpp: the rows' names and their tx_
# functions' tables; tests/test_enh_graphics.py checks the tables against the source). A key not here, or a number past
# its list, is shown as it is in the file; units are added for the rows that are numbers.
ROWS = {
    "quality_preset": ("Quality preset", ["Custom", "Minimum (4GB)", "Low (6GB)", "Balanced (8GB)", "High (12GB)",
                                          "Ultra (16GB+)", "Auto (this PC)"]),
    "ultrawide": ("Aspect ratio", ["Output resolution's own shape", "Monitor's shape"]),
    "output_res": ("Output resolution", None),
    "handheld_profile": ("Profile", ["Docked", "Handheld"]),
    "dlss": ("Upscaler", ["Game's own", "NVIDIA DLSS", "NVIDIA DLAA", "AMD FSR 3.1", "AMD FSR 4", "AMD FSR 4 Native AA",
                          "Off (no upscaling)"]),
    "dlss_model": ("DLSS model", ["Transformer (K)", "Transformer 2 (M)", "Transformer 2 (L)", "NVIDIA default"]),
    "resolution": ("Render resolution", ["Auto", "100%", "75%", "67%", "50%", "58%", "33%", "42%", "83%", "92%"]),
    "sharpness": ("Sharpness", "%"),
    "frame_generation": ("Frame generation", ["Off", "Auto", "2x", "3x", "4x", "5x", "6x", "7x", "8x"]),
    "frame_generation_by": ("Frame generation by", ["Auto", "Built-in FG"]),
    "frame_pacing": ("Frame pacing", ["Off", "On"]),
    "frame_rate_cap": ("Game frame rate cap", ["60 (the console's)", "90", "120", "144", "165", "240", "Uncapped", "30"]),
    "nvidia_reflex": ("NVIDIA Reflex", ["Off", "On", "On + Boost"]),
    "amd_anti-lag_2": ("AMD Anti-Lag 2", ["Off", "On"]),
    "fullscreen": ("Fullscreen", ["Off", "On"]),
    "vsync": ("V-Sync", ["Auto", "On", "Off"]),
    "upscaling": ("Window scaling filter", ["Off", "Catmull-Rom", "Lanczos"]),
    "ultrawide_menus": ("Ultrawide menus", ["Full width", "Centred, blurred sides", "Centred, black bars"]),
    "hdr": ("HDR", ["Off", "Expanded", "Native (the game's)"]),
    "hdr_paper_white": ("HDR paper white", " nits"),
    "hdr_peak_brightness": ("HDR peak brightness", " nits"),
    "hdr_contrast": ("HDR contrast", "%"),
    "hdr_tone_mapper": ("HDR tone mapper", ["Vanilla", "PsychoV35"]),
    "texture_detail": ("Texture detail", ["Auto", "Full", "Medium", "Low"]),
    "anisotropic_filtering": ("Anisotropic filtering", ["Game's", "2x", "4x", "8x", "16x"]),
    "gpu_device": ("GPU device", None),
    "threaded_rendering": ("Threaded rendering", ["Auto", "On", "Off"]),
    "vram_budget": ("VRAM budget", ["Auto", "2.2 GB (4GB preset)", "3.6 GB", "4.8 GB", "6 GB", "7.5 GB", "9 GB", "11 GB"]),
}


def row_name(key):
    return ROWS.get(key, (key, None))[0]


def label(key, value):
    """value (as the file has it) as the menu shows it"""
    if value is None:
        return "(none)"
    choices = ROWS.get(key, (key, None))[1]
    if key == "gpu_device":
        return "Auto" if value == "0" else "card %s" % value
    if isinstance(choices, str):
        return value + choices
    if isinstance(choices, list) and value.isdigit() and int(value) < len(choices):
        return choices[int(value)]
    return value


def default_store():
    env = os.environ.get("HOOKSHOT_ZOT_GRAPHICS")
    if env:
        return env
    if oot.WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "HookshotZOT", "graphics-profiles")
    return os.path.join(oot.data_home(), "hookshot-zot", "graphics-profiles")


def check_name(name):
    if not NAME.match(name or ""):
        raise Fail("a profile name is 1 to 40 letters, digits, spaces, '-' or '_', starting with a letter or digit: %r is not"
                   % name)
    return name


def profile_path(store, name):
    return os.path.join(store, check_name(name) + SUFFIX)


def options_path(game):
    if not game:
        raise Fail("name the game folder with --game (the folder with %s)" % OPTIONS)
    path = os.path.join(game, OPTIONS)
    if not os.path.isfile(path):
        raise Fail("no %s in %s: start the game there once, or name its folder" % (OPTIONS, game))
    return path


def read_lines(path):
    with open(path, encoding="utf-8", errors="surrogateescape", newline="") as f:
        return f.read().splitlines()


def key_of(line):
    k, eq, _ = line.partition("=")
    return k.strip() if eq and not line.lstrip().startswith(("#", ";")) else None


def graphics_of(lines):
    """{key: value} of the Graphics lines in an options file's lines (the last one wins, as the game reads it)"""
    out = {}
    for line in lines:
        k = key_of(line)
        if k in GRAPHICS_KEYS:
            out[k] = line.partition("=")[2].strip()
    return out


def read_profile(store, name):
    path = profile_path(store, name)
    if not os.path.isfile(path):
        raise Fail("no profile %s in %s (list shows them)" % (name, store))
    values = graphics_of(read_lines(path))
    for k, v in values.items():
        if not VALUE.match(v):
            raise Fail("profile %s: %s=%r is not a value the menu writes" % (name, k, v))
    if not values:
        raise Fail("profile %s has no Graphics settings" % name)
    return values


def refuse_running(args):
    if getattr(args, "dry_run", False) or args.force:
        return
    busy = oot.running_games()
    if busy:
        raise Fail("close %s first (or pass --force): the game rewrites %s at every change in its menu"
                   % (" and ".join(busy), OPTIONS))


def write_atomic(path, lines):
    folder = os.path.dirname(os.path.abspath(path))
    fd, tmp = tempfile.mkstemp(prefix="." + os.path.basename(path) + "-", dir=folder)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", errors="surrogateescape", newline="\n") as f:
            f.write("\n".join(lines) + "\n")
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def apply_lines(lines, values):
    """lines with each Graphics key set to values' (in place where the line is; missing ones appended)"""
    out, done = [], set()
    for line in lines:
        k = key_of(line)
        if k in values:
            if k in done:
                continue   # (a repeated key: one line, the profile's)
            out.append("%s=%s" % (k, values[k]))
            done.add(k)
        else:
            out.append(line)
    out += ["%s=%s" % (k, values[k]) for k in GRAPHICS_KEYS if k in values and k not in done]
    return out


def changes(current, values):
    return [(k, current.get(k), values[k]) for k in GRAPHICS_KEYS if k in values and current.get(k) != values[k]]


# ---- the commands ----

def cmd_save(args, store):
    refuse_running(args)
    values = graphics_of(read_lines(options_path(args.game)))
    if not values:
        raise Fail("%s has no Graphics settings yet: change one in the menu first" % OPTIONS)
    path = profile_path(store, args.name)
    if os.path.exists(path) and not args.replace:
        raise Fail("profile %s exists: pass --replace to overwrite it" % args.name)
    os.makedirs(store, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    write_atomic(path, [HEADER, "# saved %s from %s" % (stamp, os.path.abspath(args.game))] +
                 ["%s=%s" % (k, values[k]) for k in GRAPHICS_KEYS if k in values])
    print("Saved profile %s (%d settings) in %s" % (args.name, len(values), path))


def cmd_list(args, store):
    names = sorted(n[:-len(SUFFIX)] for n in (os.listdir(store) if os.path.isdir(store) else [])
                   if n.endswith(SUFFIX) and NAME.match(n[:-len(SUFFIX)]))
    print("Graphics profiles in %s:" % store)
    for n in names:
        try:
            v = read_profile(store, n)
            print("  %-24s %s, %s, %s FPS, HDR %s" % (n, v.get("output_res", "?"), label("dlss", v.get("dlss")),
                                                     label("frame_rate_cap", v.get("frame_rate_cap")), label("hdr", v.get("hdr"))))
        except Fail as e:
            print("  %-24s (unreadable: %s)" % (n, e))
    if not names:
        print("  (none)")


def cmd_show(args, store):
    for k, v in read_profile(store, args.name).items():
        print("  %-24s %s" % (row_name(k), label(k, v)))


def cmd_diff(args, store):
    values = read_profile(store, args.name)
    diff = changes(graphics_of(read_lines(options_path(args.game))), values)
    if not diff:
        print("The game already has profile %s's settings" % args.name)
    for k, old, new in diff:
        print("  %-24s %s -> %s" % (row_name(k), label(k, old), label(k, new)))


def cmd_apply(args, store):
    values = read_profile(store, args.name)
    path = options_path(args.game)
    lines = read_lines(path)
    diff = changes(graphics_of(lines), values)
    if not diff:
        print("The game already has profile %s's settings: nothing to do" % args.name)
        return
    for k, old, new in diff:
        print("  %-24s %s -> %s" % (row_name(k), label(k, old), label(k, new)))
    if args.dry_run:
        print("Dry run: nothing was changed")
        return
    refuse_running(args)
    backups = os.path.join(store, "backups")
    os.makedirs(backups, exist_ok=True)
    backup = os.path.join(backups, "%s-%s" % (datetime.datetime.now().strftime("%Y%m%d-%H%M%S"), OPTIONS))
    shutil.copy2(path, backup)
    write_atomic(path, apply_lines(lines, values))
    if graphics_of(read_lines(path)) != {**graphics_of(lines), **values}:
        shutil.copy2(backup, path)
        raise Fail("the written file did not read back as expected: the old one is back")
    print("Applied profile %s (%d changes). The file before is %s" % (args.name, len(diff), backup))


def cmd_delete(args, store):
    path = profile_path(store, args.name)
    if not os.path.isfile(path):
        raise Fail("no profile %s in %s" % (args.name, store))
    os.remove(path)
    print("Deleted profile %s" % args.name)


COMMANDS = {"save": cmd_save, "list": cmd_list, "show": cmd_show, "diff": cmd_diff, "apply": cmd_apply,
            "delete": cmd_delete}


def parser():
    p = argparse.ArgumentParser(prog="zot_graphics.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--store", metavar="DIR", help="where profiles are kept (default: %s)" % default_store())
    sub = p.add_subparsers(dest="command", required=True)
    q = sub.add_parser("save", help="the game's Graphics settings saved as a profile")
    q.add_argument("name")
    q.add_argument("--game", required=True, metavar="GAME")
    q.add_argument("--replace", action="store_true", help="overwrite a profile of that name")
    q.add_argument("--force", action="store_true", help="even if a game seems to be running")
    sub.add_parser("list", help="the profiles")
    q = sub.add_parser("show", help="a profile's settings")
    q.add_argument("name")
    q = sub.add_parser("diff", help="what applying a profile would change")
    q.add_argument("name")
    q.add_argument("--game", required=True, metavar="GAME")
    q = sub.add_parser("apply", help="a profile's settings put into the game's options (close the game first)")
    q.add_argument("name")
    q.add_argument("--game", required=True, metavar="GAME")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--force", action="store_true", help="even if a game seems to be running")
    q = sub.add_parser("delete", help="a profile removed")
    q.add_argument("name")
    return p


def main(argv=None):
    args = parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    store = os.path.abspath(args.store or default_store())
    try:
        COMMANDS[args.command](args, store)
    except (Fail, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
