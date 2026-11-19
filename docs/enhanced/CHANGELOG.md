# Hookshot Enhanced changelog

Changes of the fork only. Upstream's are in [CHANGELOG.md](../../CHANGELOG.md).

## Unreleased (based on upstream v2.3.2)

- Save manager: `scripts/enhanced/zot_saves.py`, verified snapshots, safe restore, zip export/import, prune
  ([SAVE_MANAGER.md](SAVE_MANAGER.md)). Branch `feature/save-manager`.
- Foundations: `CLAUDE.md`, the fork's landing page `.github/README.md`, `scripts/enhanced/build_windows.ps1`, and the
  fork's docs in `docs/enhanced/` (build, test baseline, upstream sync, feature matrix, roadmap, architecture, XC3
  reuse). Branch `feature/foundations`.
- PlayStation pads: lightbar showing Link's life and DualSense adaptive triggers, switched on in `hookshot_env.txt`
  (`HOOKSHOT_ENH_LIGHTBAR`, `HOOKSHOT_ENH_TRIGGERS`) ([DUALSENSE.md](DUALSENSE.md)). Branch `feature/dualsense`.
- PlayStation pads in the Insert menu (Controls: Lightbar, Low-life pulse, Adaptive triggers). Branch `feature/dualsense-menu`.
- Music volume and Effects volume rows on the Audio tab ([AUDIO_MIX.md](AUDIO_MIX.md)). Branch `feature/audio-mix`.
- Graphics profiles: `scripts/enhanced/zot_graphics.py` saves and applies the Graphics tab's settings by name
  ([GRAPHICS_PROFILES.md](GRAPHICS_PROFILES.md)). Branch `feature/graphics-profiles`.
- Mod manager: `scripts/enhanced/zot_mods.py` lists the mods folder in load order, reports conflicts, turns mods on
  and off, and keeps mod profiles ([MOD_MANAGER.md](MOD_MANAGER.md)). Branch `feature/mod-manager`.
- Graphics profiles in the Insert menu (Graphics tab: Graphics profile, Save profile as), in English and French.
  Branch `feature/graphics-profiles-menu`.
- Photo mode: F8 or Gameplay → Photo mode hides the HUD, holds the world still and gives the controls to the free
  camera; F9 or Take a photo saves a PNG at the picture's own size in the Pictures folder ([PHOTO_MODE.md](PHOTO_MODE.md)).
  F6 and F7 hide the HUD or hold the world alone. English and French. Branch `feature/photo-hud-proto`.
- HUD editor: Gameplay → HUD element and its rows show or hide, resize, move and fade hearts, magic, item buttons,
  top-right buttons, minimap and place name; Reset HUD puts them back ([HUD_EDITOR.md](HUD_EDITOR.md)). English and
  French. Branch `feature/hud-editor`.
- HUD editor, second pass: HUD preset (Full, Minimal, Hidden), Whole HUD size and Whole HUD opacity rows; the settings
  move from `enh_hud.ini` into `hookshot_options.ini` (`enh_hud_<element>_<field>`, saved with the rest of the file, whole;
  the old file is read once); the host reads the thirty values only when they change. HUD position X and Y are percent
  of the screen (-100% to +100%), so an element can go anywhere on any screen shape; the control bridge's `option_set`
  on a HUD editor row now applies with the menu closed. The minimap element now takes the dungeon minimap and its keys
  count, and the pause menu's map page is no longer moved with it. Elements are kept on the screen by what they draw,
  measured. Three HUD slots keep a whole HUD layout (HUD slot, Save HUD to slot, Load HUD from slot). Branch
  `feature/hud-polish`.
- Product layer: the Enhanced files take the product's names from `host/enh_product.h` and
  `scripts/enhanced/enh_product.py`, so they can be carried to another fork of the game; the save manager takes
  `--game` (`--hookshot` still works) and reads other Enhanced forks' snapshots ([ARCHITECTURE.md](ARCHITECTURE.md)).
  Nothing changes for players. Branch `feature/product-neutral`.
- Option IDs: the fork's move to 1000 and up, away from upstream's (its main already uses 59 to 71, where the
  fork's were); `tests/test_enh_option_ids.py` keeps them apart ([ARCHITECTURE.md](ARCHITECTURE.md)). Nothing changes for
  players. Branch `feature/option-ids`.
- Porting tool: `scripts/enhanced/port_to.py` carries the Enhanced layer to another fork of the game (a dry run by
  default; product profiles for Hookshot and Longshot), `tests/test_enh_port.py` ([PORTING.md](PORTING.md)). The audio
  diagnostics' switch in `host/nn_audio.c` now goes through `enh_env`. Branch `feature/port-to`.
- Port fixes from the first port to Longshot: the Graphics rows a graphics profile holds are the product's own
  (`GRAPHICS_KEYS` in `enh_product.py`, `graphics_keys` in the product profiles; Longshot has no Texture detail),
  and the Enhanced tests no longer name Hookshot's files. Branch `feature/port-fixes`.
- Upstream v2.3.2 merged in. Graphics profiles follow its Graphics tab: CRT filter and CRT lines are held, VRAM budget
  is gone (an older profile's line is skipped; loading a profile gives the preset's mip trimming, as upstream does), and
  the Upscaler lists Intel XeSS. Test baseline: 25 known failures on v2.3.2 ([TEST_BASELINE.md](TEST_BASELINE.md)).
  Branch `sync/v2.3.2`.
