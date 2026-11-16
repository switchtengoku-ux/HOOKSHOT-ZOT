# HUD editor (Hookshot Enhanced)

Insert menu → **Gameplay**, below the photo mode's rows. Each HUD element can be shown or hidden, resized, moved and
made see-through; **Reset HUD** puts every element back as the game draws it. Every row is in English and French.

| Row | Values | What it does |
|---|---|---|
| HUD element | Hearts, Magic, Item buttons, Top-right buttons, Minimap, Place name | The element the rows below set; each element keeps its own settings |
| HUD visible | Off, On | Shows or hides the element |
| HUD size | 25% to 200%, steps of 5 | Its size. It keeps its own top-left corner (top-right for Top-right buttons), or for Minimap and Place name the canvas's bottom-right corner and top edge |
| HUD position X | -800 to +800, steps of 20 | Left (lower) or right (higher), in the HUD canvas's units (3840 wide) |
| HUD position Y | -800 to +800, steps of 20 | Down (lower) or up (higher), in the canvas's units (2160 high) |
| HUD opacity | 10% to 100%, steps of 10 | How solid it is drawn |
| Reset HUD | | Every element back to visible, 100%, +0, +0, 100% |

The settings are kept in `enh_hud.ini`, beside `hookshot_options.ini` (one `<element>.<field>=<value>` line each:
element 0 to 5 in the order above, field 0 visible, 1 size, 2 X, 3 Y, 4 opacity). Deleting the file is the same as
Reset HUD. Nothing is changed while every element is at its default: the feature is then off.

On a wider screen than 16:9 the elements still go to the screen's edges as upstream's ultrawide HUD places them: the
editor's size and offsets apply first, on the 16:9 canvas.

## How it works

| File | Role |
|---|---|
| `host/enh_hud.c` (new) | Edits each HUD pane when the game makes its transform: hidden (3x3 part set to 0), size (3x3 part scaled about the element's corner), place (translation moved), opacity (alpha at pane `+0x74` set to min(the game's, the setting), so the game's fades still run) |
| `gpu/vk/enh_hud.cpp` / `.h` (new) | The settings, `enh_hud.ini`, the option ids the host reads (`HOS_OPT_ENH_HUD` 70 + element × 5 + field) |
| `gpu/vk/enh_menu_hud.inc` (new) | The rows' cells, the chosen element's settings shown in the rows and written back (`enh_hud_sync`), Reset HUD |
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

## Checked (2026-11-15, driven runs at 1720x720, saves snapshotted before and restored after)

- Magic hidden; item buttons moved; top-right buttons at 50% opacity; minimap at 60% size in its corner.
- Hearts at 150% grow from their top-left corner; top-right buttons at 150% grow from their top-right corner.
- Top-right buttons at 150% and 50% opacity together, hearts and minimap at 50%: frame and icons all drawn, see-through.
- Full test suite: 547 passed, the 24 known failures, no new one.

Not yet checked: Place name (it was not on screen in the runs), menus and cutscenes with edited elements, play on the
owner's 3440x1440 screen.

## Limits

- Six elements. Rupees, the keys count, the text box and the pointer are not elements yet.
- No HUD profiles yet (one set of settings).
