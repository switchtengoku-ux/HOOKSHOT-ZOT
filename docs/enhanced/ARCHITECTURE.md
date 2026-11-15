# Architecture notes for the fork

Upstream's own design is in [design.md](../design.md) and its layout in [development.md](../development.md#layout).
This page is what the fork needs from it.

## Upstream in one table

| Part | What | Fork's use |
|---|---|---|
| `nx2/` | Python pipeline: unpacks the dump, lifts the game's AArch64 code to C, builds; `make_game.py` is what the Builder runs. Game hooks are inserted into the lifted code by `oot_patches.py`, `oot_wide.py`, `oot_fov.py` | Only if a feature needs a new hook in the game's code |
| `host/` | The Horizon OS reimplementation in C: services (`nn_*.c`), input (`nn_hid.c`, `pad_sdl.c`, `hos_sdl.c`), files and mods (`nn_fs.c`, `mods.c`), HUD layout (`hos_wide_ui.c`), game-specific code (`oot_*.c`); entry `hos_main.c` | Controllers, HUD, game state |
| `gpu/vk/` | The Vulkan renderer (`hookshot_vk.dll`, C++): replay, textures, upscalers, frame generation, the Insert menu (`vk_menu.cpp`, ImGui), FPS counter (`vk_fps.cpp`), options. Its interface `vk_api.h` is versioned: a change to `MkwVkHost`/`MkwVkRenderer` bumps `MKWVK_API_VERSION` | Menu rows, performance recording, graphics |
| `builder/` | Hookshot Builder (.NET 8 WPF), its setup and launcher, the Linux builder | Not changed until a fork release |
| `scripts/` | Save copier, benchmarks, profilers, release tooling | `scripts/enhanced/` beside it |
| `tests/` | Game-free checks run by `run_all.py`; many read the source text | `tests/test_enh_*.py` |

Settings: `hookshot_options.ini` (the menu's rows, written whole by `vk_menu.cpp` at each change) and
`hookshot_env.txt` (`RX_`, `HOS_`, `HOOKSHOT_`, ... switches, read by `host/hos_main.c`).

## Where fork code goes

- **Tools that work on files** (saves, mods, profiles, reports): Python in `scripts/enhanced/`, standard library only,
  importing upstream scripts unchanged where they already do part of the job (as `zot_saves.py` imports `oot_saves.py`).
- **Runtime features**: new files `host/enh_*.c` or `gpu/vk/enh_*.cpp`, called from upstream code through small marked
  `(enhanced)` edits. How the build picks up a new source file is still to be checked in `nx2/` before the first one.
- **Options**: `enh_*` keys in `hookshot_options.ini`; switches `HOOKSHOT_ENH_*` in `hookshot_env.txt`.
- **Off switch**: every runtime feature has one, and with it off the game behaves as upstream.
- **Docs**: `docs/enhanced/`. The fork's landing page is `.github/README.md`, so upstream's `readme.md` stays as it is.
