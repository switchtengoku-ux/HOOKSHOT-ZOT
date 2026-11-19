# Roadmap (Hookshot Enhanced)

Ordered by value for the risk, each step on its own `feature/` branch. Each one: study the code, propose, get approval,
implement, test against [TEST_BASELINE.md](TEST_BASELINE.md), document, commit.

| # | Step | State | Notes |
|---|---|---|---|
| 1 | Audit of v2.3.1, the PC's tools and the XC3 project | Done | [FEATURE_MATRIX.md](FEATURE_MATRIX.md), [XC3_TECHNICAL_REUSE.md](XC3_TECHNICAL_REUSE.md) |
| 2 | Repository: clone with history, remotes, GitHub repo, `enhanced/main` | Done | [UPSTREAM_SYNC.md](UPSTREAM_SYNC.md) |
| 3 | Unmodified v2.3.1 built and tested on this PC | Done | [BUILD_WINDOWS.md](BUILD_WINDOWS.md), [TEST_BASELINE.md](TEST_BASELINE.md) (now v2.3.2's) |
| 4 | Save manager | Done (`feature/save-manager`) | [SAVE_MANAGER.md](SAVE_MANAGER.md) |
| 5 | Foundations: CLAUDE.md, fork README, build script, these docs | Done (`feature/foundations`) | |
| 6 | DualSense: lightbar (hearts colour), low-life pulse, adaptive triggers, on/off | Done: menu rows on Controls ([DUALSENSE.md](DUALSENSE.md)) |
| 6b | Music volume and Effects volume (not in the original brief) | Done | [AUDIO_MIX.md](AUDIO_MIX.md) |
| 7 | Performance recording: from the menu or a key, P95/P99, session report | Postponed (performance is fine for now) | Ideas from XC3's `perfmon.c`; code in `gpu/vk/vk_fps.cpp` |
| 8 | Mod manager tool over the existing loader: list, enable/disable, conflicts, profiles | Done: a tool ([MOD_MANAGER.md](MOD_MANAGER.md)); a Mods tab later | No second loader: `host/mods.c`'s rules |
| 9 | Named graphics profiles | Done: a tool and two Graphics rows in the menu ([GRAPHICS_PROFILES.md](GRAPHICS_PROFILES.md)) | A tool over `hookshot_options.ini` first |
| 10 | HUD editor | Done: six elements, visible, size, place, opacity, reset, presets, whole-HUD size and opacity ([HUD_EDITOR.md](HUD_EDITOR.md)); no HUD profiles of your own yet | Opacity found at pane `+0x74` |
| 11 | Photo mode | Done: phases 1 and 2 ([PHOTO_MODE.md](PHOTO_MODE.md)); no depth of field | Free camera exists in the debug tools; HUD hide to find |
| 11b | Porting the layer to another fork of the same game (not in the original brief) | Done: `port_to.py` ([PORTING.md](PORTING.md)) | For a future Longshot Enhanced |
| 12 | Stabilization and a first release | Later: no public release while the owner is the only player; built from the clone | When public: a zip on GitHub Releases with updating turned off, bug-report links pointing at the fork ([UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)) |

Upstream merges, each on its `sync/` branch ([UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)): v2.3.1 (the fork's start), v2.3.2.
