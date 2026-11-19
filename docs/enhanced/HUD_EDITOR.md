# HUD editor (Hookshot Enhanced)

Insert menu → **Gameplay**, below the photo mode's rows. A preset chooses which elements show, two rows size and fade the
whole HUD, and each HUD element can be shown or hidden, resized, moved and made see-through; **Reset HUD** puts everything
back as the game draws it. Every row is in English and French.

| Row | Values | What it does |
|---|---|---|
| HUD preset | Full, Minimal, Hidden (Custom) | Which elements show: all, the hearts alone, or none. It leaves their size, place and opacity alone. It reads Custom when the elements were shown or hidden one by one |
| Whole HUD size | 50% to 150%, steps of 5 | Every element's size times this |
| Whole HUD opacity | 10% to 100%, steps of 10 | Every element's opacity times this |
| HUD element | Hearts, Magic, Item buttons, Top-right buttons, Minimap, Place name | The element the rows below set; each element keeps its own settings |
| HUD visible | Off, On | Shows or hides the element |
| HUD size | 25% to 200%, steps of 5 | Its size. It keeps its own top-left corner (top-right for Top-right buttons), or for Minimap and Place name the canvas's bottom-right corner and top edge |
| HUD position X | -800 to +800, steps of 20 | Left (lower) or right (higher), in the HUD canvas's units (3840 wide) |
| HUD position Y | -800 to +800, steps of 20 | Down (lower) or up (higher), in the canvas's units (2160 high) |
| HUD opacity | 10% to 100%, steps of 10 | How solid it is drawn |
| Reset HUD | | Every element back to visible, 100%, +0, +0, 100%, and the whole HUD to 100% |

The settings are kept in `hookshot_options.ini`: the rows above as `enh_hud_preset`, `enh_hud_scale`, `enh_hud_fade` and
the chosen element's `enh_hud_element`..., and each element's own as `enh_hud_<element>_<field>=<value>` (elements
`hearts`, `magic`, `items`, `buttons`, `minimap`, `place`; fields `visible`, `size`, `x`, `y`, `opacity`), written with the
rest of the file, whole, then moved over it. Before 2026-11-19 they were in `enh_hud.ini`: a file with no `enh_hud_<element>`
line yet takes them from there (beside the options file, or beside the game) and keeps them from its next save; the old file
can then be deleted. Nothing is changed while every element is at its default and the whole HUD at 100%: the feature is
then off.

On a wider screen than 16:9 the elements still go to the screen's edges as upstream's ultrawide HUD places them: the
editor's size and offsets apply first, on the 16:9 canvas.

## How it works

| File | Role |
|---|---|
| `host/enh_hud.c` (new) | Edits each HUD pane when the game makes its transform: hidden (3x3 part set to 0), size (3x3 part scaled about the element's corner), place (translation moved), opacity (alpha at pane `+0x74` set to min(the game's, the setting), so the game's fades still run) |
| `gpu/vk/enh_hud_store.h` (new) | The settings as kept, pure: their `hookshot_options.ini` lines, the old `enh_hud.ini` lines, the presets (`tests/test_enh_hud.py`) |
| `gpu/vk/enh_hud.cpp` / `.h` (new) | The settings read from the options file once, the lines `save()` writes, the option ids the host reads (`HOS_OPT_ENH_HUD` 1100 + element × 5 + field; `HOS_OPT_ENH_HUD_SCALE` 1130, `_FADE` 1131, and `_GEN` 1132, a number that changes at each change, so the host reads the thirty values again only then) |
| `gpu/vk/enh_menu_hud.inc` (new) | The rows' cells, the chosen element's settings shown in the rows and written back (`enh_hud_sync`, which saves a change, or a slider's when it is let go), the preset, Reset HUD |
| `gpu/vk/vk_menu.cpp`, `vk_menu.h`, `vk_api.h`, `vk_replay.cpp`, `menu_i18n.h`, `host/enh_photo.c`, `readme.md` | Small hooks marked `(enhanced)`, the rows' texts and their French |

The panes come from `host/hos_wide_ui.c` `hos_wide_ui_placed` (upstream), through the photo mode's weak hook
`hos_enh_hud_placed`. A pane belongs to an element when it is the element's own pane (a layout and a pane name, or a
whole layout's root) or when its parent does; the game makes a parent's transform before its children's.

What the study found in the game's panes (0xb0 bytes each, a layout's panes at `layout+0x100`, their count at
`+0x13c`, names at the resource's `+0x20`): width `+0x58`, height `+0x5c`, translation `+0x6c/+0x70` (the made
transform's `+0x4c/+0x50`), alpha `+0x74` (a float), flags `+0xa8` (the origin's place in the box: `(flags >> 11 &
0x7f) % 3` and `/ 3 % 3`; the pane's kind: `flags >> 22 & 0xf`, 1 picture, 2 text box, 3 window).

Details that matter:
- The opacity is set on the panes that draw only (picture, text box, window). A group's alpha is multiplied into its
  children by the game, so setting it on groups too made an element nested three deep come out at an eighth.
- While an element is not opaque, every pane remakes its transform each present (`hos_wide_ui_force`), since the game
  can change an alpha without a new transform; for half a second after a change too, so the panes come back to 1.0.
- The pause menu's map page uses `MapMenu_00` as the minimap does: it is told apart as `hos_wide_ui.c` does (its
  `N_MapIcon_00` group at the canvas's origin) and never edited.
- The made transforms are the canvas's (3840x2160, centred, y up): an edit to a parent carries to its children.
- Each element grows from its own anchor: hearts and item buttons from their box's top-left, the top-right buttons from
  their group's origin (the canvas's top-right corner), the minimap from its bottom-right, the place name from its top,
  and magic from its bar's left end (its origin less 230 units times its size), so it stays in line with the hearts.
- Whole HUD size scales the elements on their own, except the left group: `N_ScaleL_00` (hearts, and within it
  `N_ScaleL_01` with magic and the item buttons) is scaled once about the canvas's top-left, so the three keep their
  places to one another; their own sizes then apply inside it.
- A whole layout's root is a pane with no parent named `RootPane`: the place name's text panes come with no parent too.
- `HOS_ENH_HUD_DIAG=1` logs the edited panes (name, parent, element, place before and after) for 24 lines.

## Checked (2026-11-15, driven runs at 1720x720, saves snapshotted before and restored after)

- Magic hidden; item buttons moved; top-right buttons at 50% opacity; minimap at 60% size in its corner.
- Hearts at 150% grow from their top-left corner; top-right buttons at 150% grow from their top-right corner.
- Top-right buttons at 150% and 50% opacity together, hearts and minimap at 50%: frame and icons all drawn, see-through.
- Full test suite: 547 passed, the 24 known failures, no new one.

Second pass (2026-11-19, the owner in game): presets, Whole HUD size at 50% and 150% (hearts, magic and item buttons
in line), Whole HUD opacity, magic alone at 50% (left end in line with the hearts), the HUD changing live behind the
open menu, Reset HUD, the settings kept in `hookshot_options.ini` after a restart. Full test suite: the known failures
only.

Not yet checked: menus and cutscenes with edited elements.

## Limits

- Six elements. Rupees, the keys count, the text box and the pointer are not elements yet.
- Three presets, fixed; no saved HUD profiles of your own yet.
- Not measured yet: what an opacity below 100% costs (every pane remakes its transform each present while one is).
