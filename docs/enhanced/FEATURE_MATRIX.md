# Feature matrix: upstream v2.3.1 and the fork

From reading v2.3.1's source and readme (2026-11-15). "Upstream" is what v2.3.1 already does; the fork does not
rebuild it.

| Area | Upstream v2.3.1 | Missing / fork's target | Where it would go |
|---|---|---|---|
| Controllers | SDL3/SDL2 at run time; DualSense and DualShock 4 detected; prompts for Switch, Xbox, PS4, PS5, Steam Deck, keyboard; touchpad click opens the menu or is bindable; gyro (motion page); rumble strength; HD rumble to motors; layout presets; remapping; per-button toggle; dead zone | DualSense **lightbar**, **adaptive triggers**, haptics beyond rumble, touchpad as a surface, per-controller profiles | `host/pad_sdl.c`, `host/hos_sdl.c`, game state from `host/oot_state_tap.c` |
| HUD | Ultrawide HUD planner moves edge panes to the screen's edges (`host/hos_wide_ui.c`); ultrawide menus (full width, blurred sides, black bars); menu size | Per-element move / scale / opacity / hide (done, [HUD_EDITOR.md](HUD_EDITOR.md)); HUD profiles | `host/hos_wide_ui.c` hooks |
| Graphics | DLSS, DLAA, FSR 3.1, FSR 4; sharpness; Catmull-Rom/Lanczos; anisotropic; HDR (Expanded, Native, paper white, peak, contrast, PsychoV35); quality presets incl. Auto; frame generation; Reflex; Anti-Lag 2; texture detail; VRAM budget; FOV | **Named, saved graphics profiles**; before/after comparison | `hookshot_options.ini` keys (a tool first), later `gpu/vk/vk_menu.cpp` |
| Performance | FPS counter (FPS, frame time with 1 % low, graph, breakdown); `RX_VK_FRAME_TRACE` per-frame CSV; `RX_VK_PASS_TIMING`; VRAM lines in the log; `scripts/hookshot_bench.py`; bug report | Recording started from a key or the menu; P95/P99; session report; A/B comparison | `gpu/vk/vk_fps.cpp`, `scripts/enhanced/` |
| Saves | `scripts/oot_saves.py` list/import/export between Hookshot and emulators, with backup, running-game check, dry run; Builder import | **Done in the fork:** snapshots, SHA-256 manifests, safe restore, zip export/import, prune | `scripts/enhanced/zot_saves.py` |
| Mods | RomFS file mods in `mods/`, ordered by path, disabled with a `_`/`.`/`-` prefix, size-table selection, prompt merge (`docs/mods.md`) | Catalog, enable/disable tool, conflict report, profiles, a Mods tab (upstream's doc says none exist) | `scripts/enhanced/` over `host/mods.c`'s rules |
| Photo | Free camera (debug tools), FOV, picture without the menu (bug report), control-bridge screenshots | HUD hide, photo UI, high-resolution capture, depth of field, pause | research |
| Settings | Insert menu (Graphics, Audio, Gameplay, Controls, Debug), `hookshot_options.ini`, 14 menu languages, restart prompts | An Enhanced section: module switches, version, diagnostics | `gpu/vk/vk_menu.cpp` (small, marked edits) |
| Build | `nx2/make_game.py`, llvm-mingw, Builder (.NET 8 WPF) | Fork build script | `scripts/enhanced/build_windows.ps1` (done) |
| Tests | `tests/run_all.py`, about 650 game-free checks | Fork tests `tests/test_enh_*.py`; a baseline | `docs/enhanced/TEST_BASELINE.md` (done) |
