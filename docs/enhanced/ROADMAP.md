# Roadmap (Hookshot Enhanced)

Ordered by value for the risk, each step on its own `feature/` branch. Each one: study the code, propose, get approval,
implement, test against [TEST_BASELINE.md](TEST_BASELINE.md), document, commit.

| # | Step | State | Notes |
|---|---|---|---|
| 1 | Audit of v2.3.1, the PC's tools and the XC3 project | Done | [FEATURE_MATRIX.md](FEATURE_MATRIX.md), [XC3_TECHNICAL_REUSE.md](XC3_TECHNICAL_REUSE.md) |
| 2 | Repository: clone with history, remotes, GitHub repo, `enhanced/main` | Done | [UPSTREAM_SYNC.md](UPSTREAM_SYNC.md) |
| 3 | Unmodified v2.3.1 built and tested on this PC | Done | [BUILD_WINDOWS.md](BUILD_WINDOWS.md), [TEST_BASELINE.md](TEST_BASELINE.md) |
| 4 | Save manager | Done (`feature/save-manager`) | [SAVE_MANAGER.md](SAVE_MANAGER.md) |
| 5 | Foundations: CLAUDE.md, fork README, build script, these docs | In review (`feature/foundations`) | |
| 6 | DualSense: lightbar (hearts colour), low-life pulse, adaptive triggers, on/off | Done: menu rows on Controls ([DUALSENSE.md](DUALSENSE.md)) |
| 6b | Music volume and Effects volume (not in the original brief) | In review (`feature/audio-mix`) | [AUDIO_MIX.md](AUDIO_MIX.md) |
| 7 | Performance recording: from the menu or a key, P95/P99, session report | Planned | Ideas from XC3's `perfmon.c`; code in `gpu/vk/vk_fps.cpp` |
| 8 | Mod manager tool over the existing loader: list, enable/disable, conflicts, profiles | Planned | No second loader: `host/mods.c`'s rules |
| 9 | Named graphics profiles | Planned | A tool over `hookshot_options.ini` first |
| 10 | HUD editor | Research | `host/hos_wide_ui.c` sees every HUD pane's transform; opacity is unknown |
| 11 | Photo mode | Research | Free camera exists in the debug tools; HUD hide to find |
| 12 | Stabilization and a first release | Later | Needs the launcher/updater decision ([UPSTREAM_SYNC.md](UPSTREAM_SYNC.md)) |
