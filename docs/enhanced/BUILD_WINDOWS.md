# Building on Windows (Hookshot Enhanced)

The fork builds from a clone with **the Hookshot Builder's own tools**: nothing else to install. Verified on
2026-11-15 with v2.3.1 unmodified (Windows 11, Ryzen 7 5700X, 32 GB, RTX 4070 Ti SUPER): build exit 0, shaders
prepared (32 916 pipelines), game folder complete.

## What you need

- Your own supported dump (`.nup`, program `0400486024DEC000`, update v131072, build `e0f3ccfa`).
- `HookshotBuilder.exe` **v2.3.1** run once, so that its tools exist in
  `%LOCALAPPDATA%\HookshotBuilder\versions\v2.3.1\HookshotBuilder\tools` (llvm-mingw clang 23.1.5, Python 3.14 with
  numpy/zstandard/pillow, `cpm` Vulkan headers and FFmpeg, `wgpu-native`, emsdk, the prebuilt `third_party` files and
  `work` profile files).
- Disk: about 26 GB in the output folder (extracted game files and shaders) and about 4 GB of build files in the work
  folder. Choose a work folder on a disk with room: by default make_game.py puts it in `%LOCALAPPDATA%\HookshotBuilder`.
- The DLSS SDK, if the builder downloaded it (`%LOCALAPPDATA%\HookshotBuilder\ngx-sdk`): used when present.

Python from python.org or Miniconda is not needed: the builder's Python has the modules the build and the tests use.

## Build

```powershell
cd H:\PROJET-IA\FORKS\HOOKSHOT-ZOT
.\scripts\enhanced\build_windows.ps1 `
    -Nup "G:\EMU\NS2\The Legend of Zelda Ocarina of Time [0400486024dec000][v131072].nup" `
    -Out G:\EMU\NS2\ZOT-DEV -Work H:\PROJET-IA\FORKS\HOOKSHOT-ZOT-WORK -Language fr
```

`-CheckOnly` only checks the dump's version. `-NoDlss` builds without DLSS. The log is `<Work>\build.log`.

The script does what HookshotBuilder's `Runner.cs` does for `nx2/make_game.py`: it sets `HOOKSHOT_MINGW`, `EMSDK`,
`RX_CPM`, `WGPU_NATIVE`, `HOOKSHOT_NGX_SDK` and `TEMP` (into the work folder), copies the builder's prebuilt files into
the clone once (`third_party\...\*.dll/.lib/.exe/.sha1`, `work\`; all ignored by git) and runs make_game.py with the
builder's Python.

Timing on the reference PC: reading and extracting the `.nup`, then translating, then compiling (about 15 minutes),
then preparing shaders.

## The result

A folder built from a clone has **no launcher and no updater**: `hookshot.exe` in the output folder is the game. So it
never offers to replace the fork with an upstream release. The saves are in `<Out>\user\save\<user id>\`.

Never build into the player's own install (`G:\EMU\NS2\ZOT`): use a separate folder, and copy saves into it (or use
[SAVE_MANAGER.md](SAVE_MANAGER.md)).

## Tests

```powershell
$t = "$env:LOCALAPPDATA\HookshotBuilder\versions\v2.3.1\HookshotBuilder\tools"
$env:PATH = "$t\llvm-mingw\bin;$env:PATH"
& "$t\python\python.exe" -I -B tests\run_all.py --jobs 12
```

The known failures of this PC are in [TEST_BASELINE.md](TEST_BASELINE.md).
