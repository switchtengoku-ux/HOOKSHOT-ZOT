# PlayStation pads: lightbar and adaptive triggers (Hookshot Enhanced)

Optional features for PlayStation controllers, off unless switched on, in the Insert menu's **Controls** tab
(**Lightbar**, **Low-life pulse**, **Adaptive triggers**; saved as `enh_lightbar`, `enh_low_life_rumble` and
`enh_triggers` in `hookshot_options.ini`). They change at once. With them off, nothing is sent to any pad and the game
behaves as upstream.

| Row | Choices | Default |
|---|---|---|
| Lightbar | Off, Hearts | Off |
| Low-life pulse | Off, On (with the Lightbar on Hearts) | On |
| Adaptive triggers | Off, Light, Strong | Off |

The switches below, in `hookshot_env.txt` or the environment, win over their row for the run when they are set
(remove the line to choose in the menu again):

| Switch | Values | What it does | Pads |
|---|---|---|---|
| `HOOKSHOT_ENH_LIGHTBAR` | `hearts` (or `1`), `off` | The lightbar shows Link's life: green when full, yellow at half, red near empty; it blinks at one heart or less. Outside play (title, pause, loading) it goes back to SDL's own blue after 2 s | DualSense, DualShock 4 |
| `HOOKSHOT_ENH_LOW_LIFE_RUMBLE` | on by default with the lightbar; `0` or `off` | At one heart or less, a short pulse (90 ms) on the motors at each red blink, like a heartbeat. Scaled by the menu's Rumble strength (Off: none); skipped while the game's own rumble plays | DualSense, DualShock 4 |
| `HOOKSHOT_ENH_TRIGGERS` | `1` (light), `2` (strong), `off` | A constant resistance on L2 and R2 for the whole pull | DualSense |

For example, in `hookshot_env.txt` beside `hookshot.exe`:

```
HOOKSHOT_ENH_LIGHTBAR=hearts
HOOKSHOT_ENH_TRIGGERS=1
```

At exit the triggers are cleared and the lightbar put back. `hookshot_log.txt` says what was switched on
(`enhanced: PlayStation pads: ...`), which pad was recognised (`enhanced: "DualSense Wireless Controller" is a DualSense`)
and, once per pad, if SDL refused a colour or an effect.

## How it works

- `host/enh_dualsense.c` (new): the switches, Link's life handed from the game's thread to the pads' thread through
  one atomic word, and what each pad is sent. The lightbar is sent only when its colour changes; the trigger effect once
  per connection.
- `host/enh_dualsense.h` (new): the pure part, compiled by `tests/test_enh_dualsense.py`: pad kinds from
  `SDL_GetGamepadType`, the switches, the hearts colour, the DualSense effect block.
- Upstream files, small edits marked `(enhanced)`:
  - `gpu/vk/vk_api.h`: `HOS_OPT_ENH_LIGHTBAR` (61), `HOS_OPT_ENH_LOW_LIFE_RUMBLE`, `HOS_OPT_ENH_TRIGGERS`, past
    upstream's reserved 60. `gpu/vk/vk_replay.cpp` answers them; `gpu/vk/vk_menu.h`/`.cpp` have the rows and their
    `enh_` keys. `readme.md`: their lines in the option table.
  - `host/hos_sdl.c` / `.h`: `SDL_SetGamepadLED` (`SDL_GameControllerSetLED` on SDL2) loaded, optional, and
    `hos_sdl_pad_led`.
  - `host/pad_sdl.c`: `hos_enh_pad` called for each pad at each poll (with whether the game's rumble plays and the
    Rumble strength), `hos_enh_pad_gone` when one disconnects.
  - `host/oot_state_tap.c`: `hos_oot_life`, Link's `PlayerStatus.Life` and `MaxLife` (quarter hearts).
  - `host/hos_main.c`: in `hos_oot_lift_player`, during Link's update, the life read and handed over, only with the
    lightbar on.
- The triggers use SDL's raw DualSense effect (`SDL_SendGamepadEffect`): only the trigger bits of the block are set,
  so SDL's rumble, lightbar and player lights are not changed by it.

## Limits and checks to do on a real pad

- Started from Steam, the game may see Steam Input's stand-in pad instead of the DualSense (`host/steam_pads.h`): the
  colour or the resistance may then not reach the pad. A game started from its own `hookshot.exe` opens the pad
  directly.
- To check by hand: USB and Bluetooth; losing and gaining hearts; the title, a pause and a load (blue after 2 s);
  rumble still working with the triggers on; unplugging and plugging the pad back in.
- The menu rows are not translated yet: they show in English in every menu language.
- The rows needed a line each in upstream's `readme.md` option table (`tests/test_readme_menu_rows.py`), the one
  edit of `readme.md` the fork makes.
