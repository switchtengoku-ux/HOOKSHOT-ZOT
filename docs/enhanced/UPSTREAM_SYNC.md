# Keeping up with upstream

Upstream is a Forgejo server, not GitHub, so the fork is an independent GitHub repository with upstream's full history
and an `upstream` remote. There is no "Sync fork" button: syncing is a merge, by hand.

| Remote | URL | Use |
|---|---|---|
| `origin` | `https://github.com/switchtengoku-ux/HOOKSHOT-ZOT.git` | the fork |
| `upstream` | `https://git.notrexed.dev/Hookshot/Hookshot.git` | fetch only (`git remote set-url --push upstream no-push`) |

## Rules

- Merge **release tags** (`v2.3.2`, `v2.4.0`, ...), not upstream's `main`: it moves many times a day and is untested.
- **Merge, never rebase** `enhanced/main` onto upstream: the fork's history and its published commits stay as they are.
- One sync per branch and pull request, with no fork changes mixed in.
- Fork work in new files (see [CLAUDE.md](../../CLAUDE.md)) keeps conflicts rare; the files most likely to conflict are
  the big upstream ones a feature had to touch (`gpu/vk/vk_menu.cpp`, `host/nn_hid.c`, `host/pad_sdl.c`).

## Steps

```powershell
git fetch upstream --tags
git tag --sort=-creatordate | Select-Object -First 5        # the newest tags
git switch enhanced/main
git switch -c sync/v2.3.2
git merge --no-ff v2.3.2 -m "Merge upstream v2.3.2"
# resolve conflicts, keeping each (enhanced) block; then:
#   1. tests\run_all.py, compared with docs\enhanced\TEST_BASELINE.md (update it if upstream's own results changed)
#   2. a build with scripts\enhanced\build_windows.ps1 and a run in the game
#   3. a line in docs\enhanced\CHANGELOG.md
git push -u origin sync/v2.3.2      # then a pull request into enhanced/main
```

Pushing tags: `git push origin --tags` sends upstream's new tags to the fork. GitHub Actions is disabled on the fork;
upstream's workflows build on every tag and publish releases, so keep it disabled until the workflows are adapted.

## Before the first release

- The Windows launcher and the Builder update from upstream (`builder/HookshotBuilder/Updater.cs`,
  `builder/py/hookshot_builder/updater.py`, `builder/setup/setup.c`). A build from the clone has no launcher, so this
  does not apply yet. A fork release that ships the Builder must point these at the fork's releases or turn updating off.
- `.github/workflows/release.yml` and the build workflows assume upstream's release process.
- `.github/dependabot.yml` is removed in the fork (Dependabot opened pull requests to bump upstream's workflow
  actions, which do not run here). An upstream merge that changes that file brings it back as a conflict: keep it
  deleted.
