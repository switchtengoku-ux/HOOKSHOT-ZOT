# Hookshot Enhanced changelog

Changes of the fork only. Upstream's are in [CHANGELOG.md](../../CHANGELOG.md).

## Unreleased (based on upstream v2.3.1)

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
