# Photo mode and HUD editor (Hookshot Enhanced): study and phase 1 prototype

## What upstream v2.3.1 already has

| Piece | Where | Use |
|---|---|---|
| Every 2D pane's transform, as the game makes it | `host/hos_wide_ui.c` `hos_wide_ui_placed` (called from the game's `f_8154cab0`, `nx2/oot_wide.py`) | Hide, move or scale a HUD group or a named pane; a pane made from a parent follows it |
| The HUD's layouts by name | `hos_wide_ui.c` `HUD_LAYOUTS` | `PlayerStatus_00` (hearts, magic, rupees, buttons), `Location_00` (place name), `MapMenu_00` (minimap; also the pause menu's map page), `Talk_00`, `MessageLog_01` (text box), `PlayerStatus3D_00`, `Pointer_00`, `BalloonMessage_00` (placed from the world) |
| A free camera with its own clock | `host/hos_main.c` `oot_build_free_view` (Debug tab, Free camera) | The photo mode's camera |
| Field of view | Gameplay tab | Live |
| A PNG of the game's picture without the Insert menu | `rx_control_shot` (control bridge `shot`, the bug report) | The capture |
| The game's frame step, handed over by the host | `host/nn_vi.c` `hos_frame_seconds_bits`, read at the engine's two step divides (`nx2/oot_patches.py patch_frame_seconds`) | Holding the world still |

`hos_wide_ui.c` moves panes only while the picture is not 16:9 (`ui_on`); the fork's HUD code reads the layout names
itself, so it works at 16:9 too.

## Phase 1 prototype (`host/enh_photo.c`)

| Switch | Key | What it does |
|---|---|---|
| `HOOKSHOT_ENH_HUD_HIDE=1` | **F6** | Hides the whole HUD: the root pane of each HUD layout gets its 3x3 part set to 0 when the game makes its transform, so its group is drawn from a point; `hos_wide_ui_force` makes every pane remake its transform when the switch changes, so the game's own come back |
| `HOOKSHOT_ENH_FREEZE=1` | **F7** | Holds the world still: the frame step handed to the game becomes 1e-6 s, so its clock and what moves by it barely advance while the picture is still drawn |
| `HOOKSHOT_ENH_PHOTO_FILE=<path>` | | For driven test runs (which cannot press keys): while the file exists it is read every half second, `hud=1` and `freeze=1` in it switch each on |

The keys work while the game's window has the focus (Windows). Freezing from the start of the game would also hold the
title and the loading: switch it on in play.

Hooks in upstream files, marked `(enhanced)` and **weak** (`__attribute__((weak))`), so the upstream tests that compile
these files alone (`test_wide_ui`, `test_hud_layout`, `test_frame_rate_cap_step`, `test_present_trace`) call nothing:
`host/hos_wide_ui.c` (`hos_wide_ui_placed`, `hos_wide_ui_tick`) and `host/nn_vi.c` (`realtime_step`'s two stores).

### Checked (2026-11-15, driven run in Hyrule Field, 1920x1080 screenshots)

- HUD hidden: hearts, magic, buttons and minimap gone; shown again when switched off.
- World held still: from one screenshot to the next 3 s later, 1.2% of the pixels changed (4.9% while moving). Link,
  Navi and the enemies stand still; what still changes is the grass's wind and the anti-aliasing's fine noise.
- No new test failure against the v2.3.1 baseline.

### Not yet known

- Whether the free camera moves while the world is held (it has its own clock: it should).
- How cutscenes, menus and the text box behave with the HUD hidden or the world held.
- A pane's opacity (for the HUD editor): where the game keeps it.

## Phase 2: the photo mode

| How | What |
|---|---|
| **F8**, or Insert menu → Gameplay → **Photo mode** (A or Enter) | The photo mode on or off. On: the HUD hidden, the world held still, the free camera on the usual controls (sticks or movement keys; R and L, or Page Up and Page Down, its height; Ctrl faster), and the game gets no buttons. Switched on from the menu, the menu closes |
| **F9**, or Gameplay → **Take a photo** | A PNG of the game's picture, without the Insert menu, at its own size (3440x1440 at a 21:9 output), in the user's Pictures folder as Windows knows it (`SHGetKnownFolderPath`: moved to OneDrive, it is there), under `Hookshot`, as `Hookshot_<date>_<time>.png`. The row's help then says "Photo saved." |
| Gameplay → Field of view | The view's width, live, as before |

The free camera is the debug tools' (`host/hos_main.c` `oot_build_free_view`), turned on by the photo mode without the
debug tools. It moves while the game's window has the focus.

How it is built:
- `gpu/vk/enh_photo.cpp` / `.h` (new): the photo mode's state, the photos asked for, F8 and F9.
- `gpu/vk/enh_photo_shot.inc` (new, in `vk_replay.cpp` after `shot_ask_take`): the photo at the presented crop's size,
  its image and buffer made for it and let go after, read back without a wait, written on a thread of its own.
- `gpu/vk/enh_menu_photo.inc` (new, in `vk_menu.cpp`): the two rows' cells and presses; their texts are in
  `vk_menu.cpp` and in French in `menu_i18n.h`.
- `host/enh_photo.c`: reads the photo mode every present (`HOS_OPT_ENH_PHOTO` 66) and from it hides the HUD, holds the
  world and answers `hos_enh_photo_camera` (weak in `host/hos_main.c` and `host/nn_hid.c`).
- `vk_replay.cpp`, `vk_menu.cpp`, `vk_api.h`, `readme.md`: small hooks marked `(enhanced)`.
- `HOOKSHOT_ENH_PHOTO_FILE` also takes `photo=1|0` and `shot=<n>` for driven test runs.

Checked in a driven run (2026-11-15): photo mode on hides the HUD and holds Link and the world; a photo came out at
3440x1440 without the HUD; off gives the HUD back. The free camera switched on but could not be moved there (a run
without a window has no focus): to check in play.

Limits: an HDR picture is written as its 8-bit values, not tone mapped; the photo is the output size (a larger one needs
a larger Output resolution); no depth of field.

## Next

- Phase 3, the HUD editor: done, [HUD_EDITOR.md](HUD_EDITOR.md).