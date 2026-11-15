# Graphics profiles (Hookshot Enhanced)

`scripts/enhanced/zot_graphics.py` saves the Insert menu's **Graphics** tab under a name and puts it back in one go:
a "4K quality" and a "120 FPS" set, say, switched without going through 28 rows. It works on `hookshot_options.ini`
in the game folder and changes nothing else: no engine code, no other line of the file.

Python 3 (standard library only). **Close the game before `apply`**: the game rewrites the whole options file at every
change in its menu, and reads it at the start.

```powershell
python -I scripts\enhanced\zot_graphics.py save "4K qualite" --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_graphics.py list
python -I scripts\enhanced\zot_graphics.py diff "120 FPS" --game G:\EMU\NS2\ZOT
python -I scripts\enhanced\zot_graphics.py apply "120 FPS" --game G:\EMU\NS2\ZOT
```

| Command | What it does |
|---|---|
| `save NAME --game GAME` | The game's Graphics settings saved as profile NAME (`--replace` to overwrite one) |
| `list` | The profiles, with their output size, upscaler, frame rate cap and HDR (as the file numbers them) |
| `show NAME` | A profile's lines |
| `diff NAME --game GAME` | What applying it would change, line by line |
| `apply NAME --game GAME` | Its settings put into the game's options file: the Graphics lines only, every other line kept in its order. The file before is copied to `<store>\backups` first. `--dry-run` shows the changes and writes nothing |
| `delete NAME` | The profile removed |

Profiles are kept in `%LOCALAPPDATA%\HookshotZOT\graphics-profiles` (`--store` or `HOOKSHOT_ZOT_GRAPHICS` for
another folder), one small `.ini` each, so a profile works for every game folder. A name is 1 to 40 letters, digits,
spaces, `-` or `_`.

## What a profile holds

The 28 keys the menu saves its Graphics rows under, in the menu's order (`GRAPHICS_KEYS`): Quality preset, Aspect
ratio, Output resolution, Profile, Upscaler, DLSS model, Render resolution, Sharpness, Frame generation (and by),
Frame pacing, Game frame rate cap, Reflex, Anti-Lag 2, Fullscreen, V-Sync, Window scaling filter, Ultrawide menus, the
HDR rows, Texture detail, Anisotropic filtering, GPU device, Threaded rendering and VRAM budget.
`tests/test_enh_graphics.py` checks that list against `gpu/vk/vk_menu.cpp`'s rows, so a row upstream adds or renames
shows up as a failing test.

Rows marked "after a restart" in the menu take effect at the next start, as when they are changed there. A row the
PC cannot use (Reflex without an NVIDIA card) is saved and put back as it is; the game ignores it there as usual.

## Not yet

A row in the Insert menu to switch profiles while playing. The tool comes first; the row needs the menu to read and
write profile files, which is a larger change to `gpu/vk/vk_menu.cpp`.
