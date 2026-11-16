# Save manager (Hookshot Enhanced)

`scripts/enhanced/zot_saves.py` keeps verified snapshots of Hookshot's saves outside the game folder, restores them
safely, and moves them between PCs as zip files. It complements `scripts/oot_saves.py` (copies between Hookshot and the
emulators, [saves.md](../saves.md)), which it imports unchanged for finding the save folder, the running-game check, the
link check and the atomic swap. No engine code is changed: nothing runs unless you run the script.

Python 3 (standard library only). Close the game before `snapshot` and `restore`.

## Commands

On Windows, `--game` (or `--hookshot`, the same option) is the game folder (the one with `user\`); on Linux it defaults to `~/.local/share/hookshot`.

```powershell
python -I scripts\enhanced\zot_saves.py snapshot --hookshot "G:\Games\Hookshot" --label before-water-temple
python -I scripts\enhanced\zot_saves.py list
python -I scripts\enhanced\zot_saves.py verify
python -I scripts\enhanced\zot_saves.py restore 20261115-161740-before-water-temple --hookshot "G:\Games\Hookshot"
python -I scripts\enhanced\zot_saves.py export 20261115-161740-before-water-temple --zip my-save.zip
python -I scripts\enhanced\zot_saves.py import my-save.zip --label from-laptop
python -I scripts\enhanced\zot_saves.py prune --keep 10
```

| Command | What it does |
|---|---|
| `snapshot` | Copies the profile's save folder (`account.sav`, `option.sav`, `slot_*`) into a new snapshot with a `manifest.json` (each file's size and SHA-256). Written into a hidden folder, checked against the manifest, then renamed into place |
| `list` | The snapshots, with profile, slot count, size and the Hookshot version they came from |
| `verify` | Checks every snapshot (or the ones named) against its manifest: missing, extra or changed files |
| `restore` | Checks the snapshot, refuses while a game runs, snapshots the current save as `<time>-pre-restore` and checks it, copies the snapshot beside the save, swaps it in with renames, then checks the result. The save folder ends up with exactly the snapshot's files |
| `export` | A checked snapshot as a zip (the source path is left out of its manifest). It holds your saves: keep it private |
| `import` | Adds a zip made by `export` to the store as a snapshot. It never writes into a game folder: use `restore` after |
| `prune` | Deletes all but the newest `N` snapshots of each profile. Damaged snapshots are never deleted by `prune` |

| Option | |
|---|---|
| `--store DIR` | The snapshot store. Default `%LOCALAPPDATA%\HookshotZOT\snapshots` (Windows), `$XDG_DATA_HOME/hookshot-zot/snapshots` (Linux), or `$HOOKSHOT_ZOT_SNAPSHOTS` |
| `--profile ID` | When the game folder has more than one profile |
| `--label NAME` | 1 to 40 letters, digits, `-` or `_` |
| `--dry-run` | Says what would happen, changes nothing (`snapshot`, `restore`, `import`, `prune`) |
| `--force` | Skips the running-game check. Only when you are sure no game is running |

## Safety rules

- The store is outside the game folder, so a launcher update or a rebuild never touches it.
- A snapshot that does not match its manifest is never restored or exported.
- `restore` always keeps the current save as a checked snapshot first; to undo a restore, restore that `pre-restore`
  snapshot.
- `import` checks the zip before extracting: only `manifest.json`, `account.sav`, `option.sav` and `slot_NN/<file>`;
  no absolute paths, `..`, drive letters or links; size caps; every file's SHA-256 against the manifest.
- Snapshots and exported zips contain your saves. They are never committed (`.gitignore` covers `*.sav`) and must not
  be shared as game files.

## Tests

`tests/test_enh_saves.py` (run by `tests/run_all.py`) uses made-up save files in temp folders and replaces the
running-game check; it covers snapshot, verify, restore with its pre-restore snapshot, dry runs, the running-game
guard, export/import round trip, unsafe zips and prune.
