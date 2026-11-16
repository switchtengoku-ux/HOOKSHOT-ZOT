# Porting the Enhanced layer to another fork (`scripts/enhanced/port_to.py`)

Hookshot Enhanced is the one place the Enhanced features are written. `port_to.py` carries them to another fork of the
same game, such as a future Longshot Enhanced: option 3 of the architecture study, where the layer is copied, never
linked, and each fork keeps its own upstream.

```
python -I scripts/enhanced/port_to.py TARGET --product longshot                # a dry run: TARGET is not changed
python -I scripts/enhanced/port_to.py TARGET --product longshot --apply        # the port, left in TARGET for review
```

`TARGET` is a clean git checkout of the other fork, on its Enhanced branch. `--ref` is the commit of this repository to
port (default `enhanced/main`; a commit, never the working tree), `--base` where this fork left upstream (default
`v2.3.1`, used for the first port only).

## What a port does

| Part | Files | How |
|---|---|---|
| The layer | `host/enh_*`, `gpu/vk/enh_*`, `scripts/enhanced/*.py`, `scripts/enhanced/products/*.json`, `tests/test_enh_*.py` | Copied whole from `--ref`. A layer file the last port brought and `--ref` no longer has is removed |
| The product files | `host/enh_product.h`, `scripts/enhanced/enh_product.py` | Made from `--ref`'s with the profile's names (`scripts/enhanced/products/<name>.json`) |
| The hooks | The `(enhanced)` edits to upstream files | The diff of those files from `--base` (or from the last port's commit) to `--ref`, applied with `git apply --3way`. A hunk that does not apply is left as a conflict; a file the target does not have is skipped |
| The manifest | `scripts/enhanced/ported_from.json` | The commit ported, the profile and the layer's files: the next port starts from there |

Never ported, each fork keeps its own: `CLAUDE.md`, `.github/`, `docs/enhanced/`, `scripts/enhanced/build_windows.ps1`.

The report ends with the added hook lines that name this product (`Hookshot`): menu texts (they must stay literals in
`gpu/vk/vk_menu.cpp` for the translations), comments, anything that may need the target's name.

Safety: a dry run makes the port in a throwaway worktree of the target and removes it. `--apply` refuses a target with
changes to tracked files and commits nothing. Both fetch this repository's commits into the target's object store (no
branch, no tag), which `git apply --3way` needs. Exit status: 0 done, 1 conflicts to resolve, 2 refused.

## Profiles

| Key | Hookshot | Longshot |
|---|---|---|
| `product` | Hookshot | Longshot |
| `options` | `hookshot_options.ini` | `longshot_options.ini` |
| `env_prefix`, `env_file` | `HOOKSHOT_ENH_`, `hookshot_env.txt` | `LONGSHOT_ENH_`, `longshot_env.txt` |
| `store_win`, `store_posix`, `store_env_prefix` | `HookshotZOT`, `hookshot-zot`, `HOOKSHOT_ZOT_` | `LongshotZOT`, `longshot-zot`, `LONGSHOT_ZOT_` |
| `version_file`, `saves_script`, `saves_program` | `hookshot_version.txt`, `oot_saves.py`, `HOOKSHOT` | `longshot_version.txt`, `longshot_saves.py`, `LONGSHOT` |
| `snapshot_format` | `hookshot-zot-snapshot` | `longshot-zot-snapshot` |

The Longshot names were read from Longshot `v3.0.0-rc.4` (`host/hos_main.c` takes `LONGSHOT_` switches from
`longshot_env.txt`; `scripts/longshot_saves.py` has `LONGSHOT`; `nx2/make_game.py` writes `longshot_version.txt`).
`tests/test_enh_port.py` checks that `hookshot.json` gives back this repository's own product files unchanged.

## A dry run against Longshot v3.0.0-rc.4 (2026-11-16, `enhanced/main` 454f694f)

24 layer files new, the 2 product files made, hooks applied cleanly in 10 files (`vk_api.h`, `hos_main.c`,
`hos_sdl.c/.h`, `hos_wide_ui.c`, `nn_audio.c`, `nn_hid.c`, `nn_vi.c`, `oot_state_tap.c`, `pad_sdl.c`), in conflict in 4
(`menu_i18n.h`, `vk_menu.cpp`, `vk_menu.h`, `vk_replay.cpp`: the menu's rows, its French and the option callback, where
Longshot's own changes sit next to the hooks), `readme.md` skipped (Longshot has `README.md`). Not built: the first real
port is the time to build and test Longshot Enhanced.
