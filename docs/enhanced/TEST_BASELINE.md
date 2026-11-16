# Test baseline (Windows, this PC)

`tests/run_all.py` on **upstream v2.3.1 unmodified**, 2026-11-15, with the Hookshot Builder's Python 3.14 and
llvm-mingw clang 23.1.5 on `PATH`: **543 passed, 24 failed, 80 skipped** (with `tests/test_enh_saves.py`). A fork change
must not add a failure to this list. Upstream's CI runs on `windows-2022` with Python 3.12, numpy, .NET 8 and that
image's compilers, which explains most of the differences.

| Likely cause | Tests |
|---|---|
| clang 23 (llvm-mingw) is stricter or lacks what a fixture expects: `-Werror` on new warnings, no `<algorithm>` in a C build, no `DWORD` | `test_fpx_sticky`, `test_fastfp_fma`, `test_spawn_emit`, `test_controls_key_slots`, `test_crash_dialog`, `test_upscaler_round_trip` |
| Temp files still open when a fixture removes them (`WinError 32`) | `test_cpp_preflight`, `test_linux_preflight`, `test_make_game_cache`, `test_make_game_prepare`, `test_missing_nup` |
| Named pipe refused (`OSError: [Errno 22]`) | `test_oot_state_tap` |
| Source-reading checks or builder/setup fixtures that disagree with the tag's code | `test_dev_packs`, `test_hdr_encode`, `test_vram_budget_row`, `test_setup_runtime`, `test_setup_runtime_paths`, `test_portable_builder_home`, `test_portable_builder_startup`, `test_portable_setup_start`, `test_portable_setup_transaction`, `test_cpm_discovery`, `test_tested_configurations`, `test_readback_late` |

To compare a branch against this list:

```powershell
& "$t\python\python.exe" -I -B tests\run_all.py --jobs 12 *> run.txt
Select-String run.txt -Pattern '^FAIL\s+\S+\s+(\S+)' | % { $_.Matches[0].Groups[1].Value } | Sort-Object -Unique
```

When upstream is merged in, run the suite again and update this file in the same merge.
