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

## Next

- Phase 2, photo mode: one switch (key or menu row) for the HUD hidden, the free camera, the world held, the field of
  view, and a capture key writing PNGs to `Pictures\Hookshot`; English and French.
- Phase 3, HUD editor: a menu page with each HUD element (hearts and magic, rupees, buttons, minimap, place name)
  shown or hidden, its size and its offset, and back to the game's own.
