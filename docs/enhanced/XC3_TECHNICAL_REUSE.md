# What the XC3 project offers this fork

From a read-only look (2026-11-15) at `G:\EMU\NS2\XC3\DEV\xc3-recomp` (branch `feature/ps5-controller-ui`, upstream
jmars125/xc3-recomp) and `G:\EMU\NS2\XC3\DEV\XC3-Test` (a run folder). The owner's own work there is one commit,
`3da9f95` "feat: add performance profiling and experimental PS5 UI overrides". The runtimes differ: nothing is copied
as is.

| XC3 element | Files | How it works | Reusable here? | Adaptation |
|---|---|---|---|---|
| CSV performance recording | `runtime/perfmon.c`, `perfmon.h`, `ui/menu.cpp` | F9 starts/stops a CSV (25 columns: present interval, waits, GPU stats, CPU time of fence/acquire/submit/present/Reflex/Streamline); lock-free sums between rows; nothing done while off; "REC CSV" shown on the overlay | **Yes, the design** | Hookshot has a per-frame CSV only from start-up (`RX_VK_FRAME_TRACE`). Recording on demand, from the menu or a key, belongs in `gpu/vk/vk_fps.cpp` |
| Frame-time percentiles | `perfmon.c` `frames_summary` | P95/P99 over the last second, sorted copy of the ring | **Yes** | Hookshot shows a 1 % low; add P95/P99 beside it |
| Present-path timing | `gfx_present.c`, `vk_sl.cpp` | Scoped wall-clock timers around Vulkan and Streamline calls, only while recording | Partly | Hookshot's Breakdown level already splits Game / Renderer / GPU wait / Pacing |
| PS5 prompts by texture replacement | `runtime/vk_texture.c` | Matches a texture by the FNV-1a hash of its decoded bytes (Joy-Con atlas 360x488 RGBA8; BC7 glyph atlases 576x288 and 352x88) and swaps in mip files from `mods/ui/...`; off unless `XC3_UI_OVERRIDE` / `XC3_PS5_GLYPHS` | **Low** | Hookshot already draws PS4/PS5 prompts (`host/prompts.c`, `nx2/prompt_*.py`). The technique only matters for a texture the prompts do not cover |
| UI texture inventory | `XC3-Test\ui-global-report\coverage_by_signature.csv`, `textures_by_screen.csv` | Textures per captured screen and candidate shared resources by size/format/mips, with sha256 prefixes | The method | A debug capture by content fingerprint in `gpu/vk/vk_texture.cpp` if a HUD or icon study needs it. The tool that made the CSVs was not found in the repository |
| Content boundary | `tools/check_content.py`, `.githooks/pre-commit`, `pre-push` | Refuses commits with game-derived files | **Yes, the idea** | A fork pre-commit check against game files and saves |
| Build | `tools/build_xc3.ps1`, MSYS2 UCRT64 clang + Ninja, two venvs | XC3's own pipeline | No | Hookshot has `nx2/make_game.py` and the Builder's tools |

XC3's `XC3-Test` folder holds game files (romfs, exefs, dumps): never copy anything from it.
