# Mod manager (Hookshot Enhanced)

`scripts/enhanced/zot_mods.py` manages the `mods` folder Hookshot already loads: it lists the mods in load order,
shows which files two mods both supply and which one wins, turns mods on and off, and keeps named sets of mods. It is
not a second loader: it only reads folders and renames them, by the rules of upstream's loader (`host/mods.c`,
[mods.md](../mods.md)). No engine code is changed.

Python 3 (standard library only). The game indexes its mods when it starts: a change takes effect at the next start.

```powershell
python -I scripts\enhanced\zot_mods.py list --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_mods.py conflicts --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_mods.py disable "02-hd-textures" --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_mods.py enable "02-hd-textures" --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_mods.py profile save "sans mods" --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_mods.py profile apply "complet" --game G:\EMU\NS2\ZOT
```

| Command | What it does |
|---|---|
| `list` | Every mod, numbered in load order when on, `off` otherwise, with its RomFS file count; notes an `exefs` folder (not applied) and a mod kept off by a folder above it |
| `conflicts` | The files more than one mod that is on supplies, grouped by mods, with the winner (the one that loads last); `--all` lists every file. Warns when several mods carry the resource size table, since only the winner's is used |
| `disable MOD` / `enable MOD` | Renames the mod's own folder with a `_` in front, or takes it away. Never overwrites a folder; `--dry-run` shows the rename |
| `profile save NAME` | The mods on now, kept as NAME (`--replace` to overwrite) |
| `profile apply NAME` | The profile's mods on and every other mod off; names a mod the profile has that the folder no longer has. `--dry-run` shows the renames |
| `profile list` / `show NAME` / `delete NAME` | The profiles, one, or none |

`MOD` is the mod's path below the mods folder (`contents/0400486024DEC000/my-mod`) or its folder's name, with or
without its `_`. `--mods DIR` names the mods folder itself instead of the game folder (as `HOS_MODS`). Profiles are
kept in `%LOCALAPPDATA%\HookshotZOT\mod-profiles` (`--store` or `HOOKSHOT_ZOT_MODS` for another folder).

## The loader's rules it follows

- The mods folder is `mods` in the game folder (beside `image.bin`), or `HOS_MODS`.
- A folder holding `romfs` or `exefs`, one to four levels down, is a mod; nothing below a mod is looked at.
- A folder starting with `.` is skipped; with `-` or `_` it is off, and so is every mod below it.
- Mods load in the order of their whole path below the mods folder, case ignored: for a file two mods supply, the one
  that sorts last wins. Number them (`01-...`, `02-...`) to choose the order.
- An `exefs` folder is not applied (the game's code is compiled ahead of time). A link to a folder inside a `romfs` is
  not followed; links to files are.

`tests/test_enh_mods.py` checks these against made-up mods, and that `host/mods.c` still sorts, limits the depth and
reads the off prefixes as the tool assumes.

## Not yet

A Mods tab in the Insert menu, a catalog with versions and dependencies (upstream's mods.md says the loader has no
manifest, so there is nothing to read them from), and changing the load order other than by renaming.
