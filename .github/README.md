# Hookshot Enhanced (HOOKSHOT-ZOT)

A community fork of **[Hookshot](https://git.notrexed.dev/Hookshot/Hookshot)** by NotRexed and its contributors: the
Switch 2 *The Legend of Zelda: Ocarina of Time* statically recompiled to run natively on PC. This fork adds PC-side
tools and options on top of upstream, while staying close to it so its releases can be merged in.

> [!IMPORTANT]
> This repository does not contain the game, keys or an executable. You need your own copy at the version Hookshot
> supports. Never share game files, saves or anything built from them. Upstream's rules apply:
> [CONTRIBUTING.md](../CONTRIBUTING.md).

- **Based on:** upstream tag `v2.3.2`. Upstream's own documentation is the [main readme](../readme.md).
- **Status:** early development. Nothing here is released yet; build from source.
- **Not affiliated** with upstream. Report fork-specific problems here, not on upstream's tracker.

## What the fork adds

| Feature | State | Docs |
|---|---|---|
| Save manager: SHA-256-verified snapshots, safe restore, zip export/import | Done (branch `feature/save-manager`) | [SAVE_MANAGER.md](../docs/enhanced/SAVE_MANAGER.md) |
| DualSense lightbar, low-life pulse and adaptive triggers | Done | [DUALSENSE.md](../docs/enhanced/DUALSENSE.md) |
| Music and effects volume | Done | [AUDIO_MIX.md](../docs/enhanced/AUDIO_MIX.md) |
| Saved graphics profiles, in the menu and as a tool | Done | [GRAPHICS_PROFILES.md](../docs/enhanced/GRAPHICS_PROFILES.md) |
| Mod manager tool over the existing RomFS loader | Done (a tool; no menu page yet) | [MOD_MANAGER.md](../docs/enhanced/MOD_MANAGER.md) |
| Photo mode | Done | [PHOTO_MODE.md](../docs/enhanced/PHOTO_MODE.md) |
| HUD editor | Done | [HUD_EDITOR.md](../docs/enhanced/HUD_EDITOR.md) |
| Performance recording (CSV, percentiles, session report) | Postponed | [ROADMAP.md](../docs/enhanced/ROADMAP.md) |

What upstream already has, and what the fork adds, is in [FEATURE_MATRIX.md](../docs/enhanced/FEATURE_MATRIX.md).

## Build

Windows: [BUILD_WINDOWS.md](../docs/enhanced/BUILD_WINDOWS.md). The fork is built from a clone with the Hookshot
Builder's own tools; it has no launcher or updater of its own yet.

## License

GPL-3.0-or-later, as upstream ([LICENSE](../LICENSE)). Third-party code keeps its own licenses and notices.
