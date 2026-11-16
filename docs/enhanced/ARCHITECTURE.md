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
- **Option IDs** (the numbers the host asks the renderer for, `HOS_OPT_*` in `gpu/vk/vk_api.h`): the fork's start at
  1000 (pad rows 1000, audio 1010, photo mode 1020, HUD editor 1100 to 1199). Upstream's grow one at a time from the
  50s, and its main already took 59 to 71 after v2.3.1, where the fork's first IDs were: past 1000 an upstream merge
  never gives two options one ID. The IDs never leave the running game (the options file keys rows by name), so moving
  them changes no player's settings. `tests/test_enh_option_ids.py` keeps the split; upstream's `tests/test_option_ids.py`
  checks that no two IDs are equal.
- **Off switch**: every runtime feature has one, and with it off the game behaves as upstream.
- **Docs**: `docs/enhanced/`. The fork's landing page is `.github/README.md`, so upstream's `readme.md` stays as it is.

## The product layer

The Enhanced files never name the product themselves: they take its names from `host/enh_product.h` (C and C++) and
its Python twin `scripts/enhanced/enh_product.py`. Carrying the Enhanced layer to another fork of the same game (a
Longshot Enhanced: option 3 of the architecture study) then means changing those two files, not every feature.

| Name | Hookshot | Used for |
|---|---|---|
| `ENH_PRODUCT` / `PRODUCT` | `Hookshot` | The photos' folder (`Pictures\Hookshot`) and file names |
| `ENH_ENHANCED` / `ENHANCED` | `Hookshot Enhanced` | The first line of the files the layer writes (profiles, `enh_hud.ini`) |
| `ENH_OPTIONS` / `OPTIONS` | `hookshot_options.ini` | The Insert menu's options file |
| `ENH_ENV_PREFIX` | `HOOKSHOT_ENH_` | The switches: `enh_env("LIGHTBAR")` reads `HOOKSHOT_ENH_LIGHTBAR`. It must be a prefix `host/hos_main.c` takes from the env file |
| `ENH_STORE_WIN`, `ENH_STORE_POSIX`, `ENH_STORE_ENV_PREFIX` | `HookshotZOT`, `hookshot-zot`, `HOOKSHOT_ZOT_` | The tools' stores (`%LOCALAPPDATA%\HookshotZOT\snapshots`, ...) and the variables that move them |
| `VERSION_FILES`, `SAVES_SCRIPT`, `SAVES_PROGRAM` | `hookshot_version.txt`, `oot_saves.py`, `HOOKSHOT` | The save manager's game side |
| `SNAPSHOT_FORMAT` / `SNAPSHOT_FORMATS` | `hookshot-zot-snapshot` / any `<name>-zot-snapshot` | Snapshots written / read (the forks of one game keep the same save files) |

Nothing a player has changes: the switches, the stores and the photos' folder keep their names. The save manager's
`--game` is also `--hookshot`, and a snapshot's manifest now records `product` and `game_version` (older ones'
`hookshot_version` is still read). `tests/test_enh_product.py` fails when an Enhanced file names the product outside
these two files, or when they disagree.

`scripts/enhanced/port_to.py` carries the layer, these two files made from a product profile, and the hooks to another
fork ([PORTING.md](PORTING.md)).

Still per product, by design: the hooks in upstream files, the menu rows' texts (they must be literals in
`gpu/vk/vk_menu.cpp`), `readme.md`'s rows, and `scripts/enhanced/build_windows.ps1`.
