# Hookshot Enhanced (HOOKSHOT-ZOT)

A community fork of **[Hookshot](https://git.notrexed.dev/Hookshot/Hookshot)** by NotRexed and its contributors: the
Switch 2 *The Legend of Zelda: Ocarina of Time* statically recompiled to run natively on PC. This fork adds PC-side
tools and options on top of upstream, while staying close to it so its releases can be merged in.

> [!IMPORTANT]
> This repository does not contain the game, keys or an executable. You need your own copy at the version Hookshot
> supports. Never share game files, saves or anything built from them. Upstream's rules apply:
> [CONTRIBUTING.md](../CONTRIBUTING.md).

- **Based on:** upstream tag `v2.3.1`. Upstream's own documentation is the [main readme](../readme.md).
- **Status:** early development. Nothing here is released yet; build from source.
- **Not affiliated** with upstream. Report fork-specific problems here, not on upstream's tracker.

## What the fork adds

| Feature | State | Docs |
|---|---|---|
| Save manager: SHA-256-verified snapshots, safe restore, zip export/import | Done (branch `feature/save-manager`) | [SAVE_MANAGER.md](../docs/enhanced/SAVE_MANAGER.md) |
| DualSense lightbar and adaptive triggers, profiles | Planned | [ROADMAP.md](../docs/enhanced/ROADMAP.md) |
| Performance recording (CSV, percentiles, session report) | Planned | |
| Mod manager over the existing RomFS loader | Planned | |
| Saved graphics profiles | Planned | |
| HUD editor, photo mode | Research | |

What upstream already has, and what the fork adds, is in [FEATURE_MATRIX.md](../docs/enhanced/FEATURE_MATRIX.md).

## Build

Windows: [BUILD_WINDOWS.md](../docs/enhanced/BUILD_WINDOWS.md). The fork is built from a clone with the Hookshot
Builder's own tools; it has no launcher or updater of its own yet.

## License

GPL-3.0-or-later, as upstream ([LICENSE](../LICENSE)). Third-party code keeps its own licenses and notices.
