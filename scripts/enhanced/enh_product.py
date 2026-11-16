"""Hookshot Enhanced: the product the Enhanced tools work with (docs/enhanced/ARCHITECTURE.md).

The Python twin of host/enh_product.h: every scripts/enhanced tool takes the product's names from here, never as
literals, so the same tools can be carried to another fork of the same game (a Longshot Enhanced) by changing this file
alone. tests/test_enh_product.py checks that no other Enhanced file names the product. Keep both files in step.

The tools load it by path (they run with python -I, which leaves the script's folder off sys.path): see load() below,
and each tool's own few lines that call it.
"""
import importlib.util
import os
import re

PRODUCT = "Hookshot"                       # the game's name as players see it
ENHANCED = PRODUCT + " Enhanced"           # the fork's name, in the files the tools write
OPTIONS = "hookshot_options.ini"           # the Insert menu's options, beside the game (gpu/vk/vk_menu.cpp)
VERSION_FILES = ("hookshot_version.txt", os.path.join("bin", "hookshot_version.txt"))   # (nx2/make_game.py writes it)
SAVES_SCRIPT = "oot_saves.py"              # scripts/<this>: finds the game's saves and the running games
SAVES_PROGRAM = "HOOKSHOT"                 # that script's Program for this game
STORE_WIN = "HookshotZOT"                  # %LOCALAPPDATA%\<this>\<store>
STORE_POSIX = "hookshot-zot"               # $XDG_DATA_HOME/<this>/<store>
STORE_ENV_PREFIX = "HOOKSHOT_ZOT_"         # <this><NAME> moves one store
SNAPSHOT_FORMAT = "hookshot-zot-snapshot"  # the snapshots this product writes
# The snapshots it reads: its own and those of the other Enhanced forks of the same game, whose save files are the same
SNAPSHOT_FORMATS = re.compile(r"[a-z]+-zot-snapshot$")
# The Insert menu's Graphics rows as the options file keys them, in the menu's order (each product's menu has its own:
# scripts/enhanced/zot_graphics.py, checked against gpu/vk/vk_menu.cpp by tests/test_enh_graphics.py)
GRAPHICS_KEYS = (
    "quality_preset", "ultrawide", "output_res", "handheld_profile", "dlss", "dlss_model", "resolution", "sharpness",
    "frame_generation", "frame_generation_by", "frame_pacing", "frame_rate_cap", "nvidia_reflex", "amd_anti-lag_2",
    "fullscreen", "vsync", "upscaling", "ultrawide_menus", "hdr", "hdr_paper_white", "hdr_peak_brightness",
    "hdr_contrast", "hdr_tone_mapper", "texture_detail", "anisotropic_filtering", "gpu_device", "threaded_rendering",
    "vram_budget",
)

SCRIPTS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path, name):
    """A module loaded from its file (the tools' way to import, under python -I)."""
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def saves_module():
    """scripts/oot_saves.py (or this product's own), as a module."""
    return load(os.path.join(SCRIPTS, SAVES_SCRIPT), "oot_saves")


def program(oot):
    """The saves script's Program for this game."""
    return getattr(oot, SAVES_PROGRAM)


def store(oot, folder, env_name):
    """A tool's store: $<STORE_ENV_PREFIX><env_name> when set, else %LOCALAPPDATA%\\<STORE_WIN>\\<folder> on Windows,
    $XDG_DATA_HOME/<STORE_POSIX>/<folder> elsewhere."""
    env = os.environ.get(STORE_ENV_PREFIX + env_name)
    if env:
        return env
    if oot.WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, STORE_WIN, folder)
    return os.path.join(oot.data_home(), STORE_POSIX, folder)
