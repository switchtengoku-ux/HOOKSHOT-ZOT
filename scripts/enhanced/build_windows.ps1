<#
.SYNOPSIS
  Builds Hookshot from this clone on Windows with the Hookshot Builder's own tools (docs/enhanced/BUILD_WINDOWS.md).

.DESCRIPTION
  Sets what HookshotBuilder's Runner.cs sets for nx2/make_game.py (EMSDK, RX_CPM, WGPU_NATIVE, the llvm-mingw compiler,
  the DLSS SDK when present) and runs make_game.py with the builder's Python. The builder must have been run once, so
  that %LOCALAPPDATA%\HookshotBuilder\versions\<version>\HookshotBuilder\tools exists. The first run copies the builder's
  prebuilt files (third_party\*.dll/.lib/.exe/.sha1 and work\) into the clone; git ignores them.

.EXAMPLE
  .\scripts\enhanced\build_windows.ps1 -Nup "G:\EMU\NS2\game.nup" -Out G:\EMU\NS2\ZOT-DEV -Work H:\HOOKSHOT-ZOT-WORK -Language fr
#>
param(
    [Parameter(Mandatory = $true)][string]$Nup,
    [Parameter(Mandatory = $true)][string]$Out,
    [Parameter(Mandatory = $true)][string]$Work,
    [string]$Language = "en-US",
    [string]$BuilderVersion = "v2.3.1",
    [switch]$NoDlss,
    [switch]$CheckOnly
)
$ErrorActionPreference = "Stop"
$repo = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
$home_ = Join-Path $env:LOCALAPPDATA "HookshotBuilder"
$tools = Join-Path $home_ "versions\$BuilderVersion\HookshotBuilder\tools"
if (-not (Test-Path (Join-Path $tools "python\python.exe"))) {
    throw "No Hookshot Builder tools at $tools : run HookshotBuilder.exe $BuilderVersion once first."
}
# (-LiteralPath: dump names have [brackets], which -Path reads as wildcards)
if (-not (Test-Path -LiteralPath $Nup)) { throw "No game file at $Nup" }

# The prebuilt files a clone lacks (readme: Build from source, Windows)
$prebuilt = @("a64-kit\lift\a64emit.dll", "a64-kit\lift\a64emit.dll.sha1", "a64-kit\lift\a64emit.lib",
              "a64-kit\tools\lld-link.exe", "sdl2\SDL2.dll", "sdl2\SDL3.dll", "zbic\zbic.dll", "zbic\zbic.lib")
foreach ($f in $prebuilt) {
    $dst = Join-Path $repo "third_party\$f"
    if (-not (Test-Path $dst)) { Copy-Item (Join-Path $tools "third_party\$f") $dst }
}
$workFiles = Join-Path $repo "work"
if (-not (Test-Path (Join-Path $workFiles "hot_funcs.txt"))) {
    New-Item -ItemType Directory -Force $workFiles | Out-Null
    Copy-Item (Join-Path $tools "work\*") $workFiles -Recurse
}

New-Item -ItemType Directory -Force (Join-Path $Work "tmp") | Out-Null
$env:TEMP = Join-Path $Work "tmp"
$env:TMP = $env:TEMP
$env:PYTHONIOENCODING = "utf-8"
$env:HOOKSHOT_MINGW = Join-Path $tools "llvm-mingw"
$env:EMSDK = Join-Path $tools "emsdk"
$env:RX_CPM = Join-Path $tools "cpm"
$env:WGPU_NATIVE = Join-Path $tools "wgpu-native"
$env:HOOKSHOT_NO_UPDATE_CHECK = "1"
$ngx = Join-Path $home_ "ngx-sdk"
if (-not $NoDlss -and (Test-Path (Join-Path $ngx "include"))) { $env:HOOKSHOT_NGX_SDK = $ngx }
else { Remove-Item Env:HOOKSHOT_NGX_SDK -ErrorAction SilentlyContinue }

$argv = @("-I", (Join-Path $repo "nx2\make_game.py"), "--nup", $Nup, "--out", $Out, "--work", $Work,
          "--language", $Language, "--log", (Join-Path $Work "build.log"))
if ($CheckOnly) { $argv += "--check" }
Push-Location $repo
try {
    & (Join-Path $tools "python\python.exe") @argv
    if ($LASTEXITCODE -ne 0) { throw "make_game.py failed (exit $LASTEXITCODE): see $(Join-Path $Work 'build.log')" }
} finally {
    Pop-Location
}
