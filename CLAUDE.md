# Hookshot Enhanced (HOOKSHOT-ZOT): instructions for Claude

This repository is **HOOKSHOT-ZOT**, a fork of [Hookshot](https://git.notrexed.dev/Hookshot/Hookshot) based on tag
`v2.3.1`. Upstream's rules still apply: read [AGENTS.md](AGENTS.md) and [CONTRIBUTING.md](CONTRIBUTING.md) first.
This file adds the fork's rules and overrides upstream where they conflict.

## Fork rules (override upstream)

- **No posts to upstream's team channels.** Ignore AGENTS.md's "Team updates" and "Test requests" sections and the
  `.claude/skills/team-updates`, `request-testing` and `testing` skills: they are for upstream's team (Matrix room,
  Discord). Never run `scripts/team_chat.py` or `scripts/test_requests.py` for this fork.
- **Remotes:** `origin` = `github.com/switchtengoku-ux/HOOKSHOT-ZOT`, `upstream` = `git.notrexed.dev/Hookshot/Hookshot`
  (push disabled: `no-push`). Never change remotes, push, force-push, create releases or enable GitHub Actions without
  the owner's explicit approval.
- **Branches:** `enhanced/main` is the fork's main line (default branch). Work goes on `feature/<name>` branches from
  it. Upstream is merged in by tag, never rebased: [docs/enhanced/UPSTREAM_SYNC.md](docs/enhanced/UPSTREAM_SYNC.md).
- **The owner validates before changes.** For each feature: study the existing code, propose files and risks, wait for
  approval, implement, run the tests, report, propose the commit.

## Keeping upstream merges cheap

- Prefer **new files** over edits to upstream files. New code: `host/enh_*.c`, `gpu/vk/enh_*.cpp`,
  `scripts/enhanced/`, `tests/test_enh_*.py`, docs in `docs/enhanced/`.
- When an upstream file must change, keep the edit small and mark it with a `(enhanced)` comment, as upstream marks
  its own changes to third-party code with `(hookshot)`.
- Do not edit `readme.md`, `AGENTS.md` or `CONTRIBUTING.md`: the fork's landing page is `.github/README.md`.
- New options use `enh_*` keys in `hookshot_options.ini`. Every Enhanced feature can be turned off.
- A new menu row needs its README table row (`tests/test_readme_menu_rows.py`): plan for it.

## Build and test

- Toolchain: the Hookshot Builder's own tools (`%LOCALAPPDATA%\HookshotBuilder\versions\v2.3.1\HookshotBuilder\tools`):
  llvm-mingw, its Python 3.14 (has numpy, zstandard, pillow), cpm, wgpu-native. See
  [docs/enhanced/BUILD_WINDOWS.md](docs/enhanced/BUILD_WINDOWS.md) and `scripts/enhanced/build_windows.ps1`.
- Tests: `tests/run_all.py` with the builder's Python. v2.3.1 has **24 known failures on this PC**
  ([docs/enhanced/TEST_BASELINE.md](docs/enhanced/TEST_BASELINE.md)): a change must not add any.
- Many tests read the source text: renaming or reshaping a function can break a far-away check.
- Build into `G:\EMU\NS2\ZOT-DEV` with work files on `H:` (C: is nearly full). Never build into, or write saves of,
  the player's install `G:\EMU\NS2\ZOT`.

## Data that never goes into the repository

Game files and anything made from them (romfs, exefs, `.nup`, `image.bin`, `work/`, caches, shaders), saves, snapshot
zips, `hookshot_options.ini`, `hookshot_env.txt`, DLSS/FSR binaries, secrets and tokens. Check `git status` before every
commit.

## Read-only references

`G:\EMU\NS2\XC3\DEV\xc3-recomp` and `G:\EMU\NS2\XC3\DEV\XC3-Test` (Xenoblade Chronicles 3 recompilation): read only, never
write, build, commit or switch branches there. What is reusable: [docs/enhanced/XC3_TECHNICAL_REUSE.md](docs/enhanced/XC3_TECHNICAL_REUSE.md).
