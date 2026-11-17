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
| `list` | The profiles, with their output size, upscaler, frame rate cap and HDR |
| `show NAME` | A profile's settings, by row name and as the menu shows them |
| `diff NAME --game GAME` | What applying it would change, row by row (`Game frame rate cap  90 -> 120`) |
| `apply NAME --game GAME` | Its settings put into the game's options file: the Graphics lines only, every other line kept in its order. The file before is copied to `<store>\backups` first. `--dry-run` shows the changes and writes nothing |
| `delete NAME` | The profile removed |

Profiles are kept in `%LOCALAPPDATA%\HookshotZOT\graphics-profiles` (`--store` or `HOOKSHOT_ZOT_GRAPHICS` for
another folder), one small `.ini` each, so a profile works for every game folder. A name is 1 to 40 letters, digits,
spaces, `-` or `_`.

## What a profile holds

The 29 keys the menu saves its Graphics rows under, in the menu's order (`GRAPHICS_KEYS`): Quality preset, Aspect
ratio, Output resolution, Profile, Upscaler, DLSS model, Render resolution, Sharpness, Frame generation (and by),
Frame pacing, Game frame rate cap, Reflex, Anti-Lag 2, Fullscreen, V-Sync, Window scaling filter, CRT filter, CRT
lines, Ultrawide menus, the HDR rows, Texture detail, Anisotropic filtering, GPU device and Threaded rendering.
Upstream v2.3.2 removed VRAM budget: a profile saved before it keeps its `vram_budget` line, which loading skips.
`tests/test_enh_graphics.py` checks that list, the row names and the choices it shows (`ROWS`) against
`gpu/vk/vk_menu.cpp`, so a row or a choice upstream adds or renames shows up as a failing test.

Rows marked "after a restart" in the menu take effect at the next start, as when they are changed there. A row the
PC cannot use (Reflex without an NVIDIA card) is saved and put back as it is; the game ignores it there as usual.

## In the game's menu

The Insert menu's **Graphics** tab has the same profiles, under Quality preset:

| Row | What it does |
|---|---|
| **Graphics profile** | Left and Right choose among the saved profiles; **A or Enter loads** the one shown. The settings change at once; the rows that apply after a restart are asked about when the menu closes, as when they are changed by hand |
| **Save profile as** | A text field: type a name (letters, digits, spaces, `-`, `_`) and press Enter to save the Graphics settings as they are now. A name already saved is replaced |

The menu and the tool use the same files, so a profile saved in one shows in the other. Deleting a profile is the tool's
`delete` for now. The rows and their messages are in French too (`gpu/vk/menu_i18n.h`).

How it is built: `gpu/vk/enh_graphics_profiles.inc` (included by `gpu/vk/vk_menu.cpp` after `struct FieldRow`) loads a
profile through the menu's own rows, `ini_key` and `parse_output`, as `menu_init` reads the options file, then saves;
it saves one by letting `save()` write the options file and keeping its Graphics lines. `vk_menu.cpp` has the two rows
(after Quality preset, outside the sections `tests/test_menu_sections.py` fixes), their texts (`enh_profile_texts`, so
`menu_i18n.h` can translate them), the load on A or Enter, and the field in `field_row` (upstream's `field_rows` table
keeps its one entry, which `tests/test_menu_text_field.py` checks).