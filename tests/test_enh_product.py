"""Hookshot Enhanced's product layer, game-free: the Enhanced files name the product only through host/enh_product.h and
scripts/enhanced/enh_product.py, so the same files can be carried to another fork of the same game (docs/enhanced/
ARCHITECTURE.md).

- no string literal or identifier in host/enh_* and gpu/vk/enh_* (comments aside) names Hookshot, except enh_product.h;
- no string in scripts/enhanced/*.py (docstrings aside) names Hookshot, except enh_product.py and the kept aliases
  (--hookshot, an older snapshot's hookshot_version);
- the C header and its Python twin give the same names;
- enh_env and enh_store_env read <prefix><name>, compiled and run;
- the Python stores, the snapshot formats read, and zot_saves.py's --game with its --hookshot alias.

python -I -B tests/test_enh_product.py [--cc clang]
"""
import argparse
import ast
import importlib.util
import os
from pathlib import Path
import re
import subprocess
import tempfile
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
RUN_ALL_ARGS = ["--cc", "clang"]
NAME = re.compile(r"hookshot", re.I)
PY_ALLOWED = {"--hookshot", "hookshot_version"}


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def c_code(text):
    """The text without its comments (strings kept)."""
    out, i, n = [], 0, len(text)
    while i < n:
        if text.startswith("//", i):
            j = text.find("\n", i)
            i = n if j < 0 else j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            i = n if j < 0 else j + 2
            out.append(" ")
        elif text[i] in "\"'":
            q, j = text[i], i + 1
            while j < n and text[j] != q:
                j += 2 if text[j] == "\\" else 1
            out.append(text[i:j + 1])
            i = j + 1
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def check_c_files():
    files = sorted(list((ROOT / "host").glob("enh_*")) + list((ROOT / "gpu" / "vk").glob("enh_*")))
    assert len(files) >= 10, "the Enhanced C and C++ files were not found"
    bad = []
    for f in files:
        if f.name == "enh_product.h":
            continue
        for k, line in enumerate(c_code(f.read_text(encoding="utf-8")).splitlines(), 1):
            if NAME.search(line):
                bad.append("%s:%d: %s" % (f.relative_to(ROOT).as_posix(), k, line.strip()))
    assert not bad, "the product named outside host/enh_product.h:\n  " + "\n  ".join(bad)
    return len(files)


def check_py_files():
    files = sorted((ROOT / "scripts" / "enhanced").glob("*.py"))
    bad = []
    for f in files:
        if f.name == "enh_product.py":
            continue
        tree = ast.parse(f.read_text(encoding="utf-8"))
        docs = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef)) and node.body:
                first = node.body[0]
                if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                    docs.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docs:
                if NAME.search(node.value) and node.value not in PY_ALLOWED:
                    bad.append("%s:%d: %r" % (f.relative_to(ROOT).as_posix(), node.lineno, node.value[:80]))
    assert not bad, "the product named outside scripts/enhanced/enh_product.py:\n  " + "\n  ".join(bad)
    return len(files)


def check_twins(product):
    header = (ROOT / "host" / "enh_product.h").read_text(encoding="utf-8")
    defines = dict(re.findall(r'#define (ENH_\w+) "([^"]*)"', header))
    for c_name, py_name in (("ENH_PRODUCT", "PRODUCT"), ("ENH_OPTIONS", "OPTIONS"), ("ENH_STORE_WIN", "STORE_WIN"),
                            ("ENH_STORE_POSIX", "STORE_POSIX"), ("ENH_STORE_ENV_PREFIX", "STORE_ENV_PREFIX")):
        assert defines.get(c_name) == getattr(product, py_name), \
            "host/enh_product.h %s and enh_product.py %s differ" % (c_name, py_name)
    assert defines["ENH_ENV_PREFIX"].startswith(defines["ENH_STORE_ENV_PREFIX"].split("_")[0] + "_"), \
        "the switches' prefix is not the product's: host/hos_main.c's env file would leave them out"


FIXTURE = r'''
#include <stdio.h>
#include <string.h>
#include "enh_product.h"
#ifdef _WIN32
#include <stdlib.h>
static void set(const char *n, const char *v) { _putenv_s(n, v); }
#else
static void set(const char *n, const char *v) { setenv(n, v, 1); }
#endif
int main(void) {
    char name[96];
    snprintf(name, sizeof name, "%s%s", ENH_ENV_PREFIX, "TEST_SWITCH");
    if (enh_env("TEST_SWITCH")) { fprintf(stderr, "set before the test\n"); return 1; }
    set(name, "7");
    const char *v = enh_env("TEST_SWITCH");
    if (!v || strcmp(v, "7")) { fprintf(stderr, "enh_env does not read %s\n", name); return 1; }
    snprintf(name, sizeof name, "%s%s", ENH_STORE_ENV_PREFIX, "TEST_STORE");
    set(name, "x");
    v = enh_store_env("TEST_STORE");
    if (!v || strcmp(v, "x")) { fprintf(stderr, "enh_store_env does not read %s\n", name); return 1; }
    printf("enh_env and enh_store_env read %s* and %s*\n", ENH_ENV_PREFIX, ENH_STORE_ENV_PREFIX);
    return 0;
}
'''


def check_c_helpers(cc):
    with tempfile.TemporaryDirectory() as tmp:
        src, exe = Path(tmp) / "fixture.c", Path(tmp) / "fixture.exe"
        src.write_text(FIXTURE, encoding="utf-8")
        subprocess.run([cc, "-std=c11", "-Wall", "-Wextra", "-Werror", "-I", str(ROOT / "host"), str(src), "-o", str(exe)],
                       check=True)
        out = subprocess.run([str(exe)], capture_output=True, text=True)
        if out.returncode:
            raise SystemExit(out.stderr or "the fixture failed")
        return out.stdout.strip()


def check_python(product):
    oot = product.saves_module()
    with mock.patch.dict(os.environ, {product.STORE_ENV_PREFIX + "SNAPSHOTS": "elsewhere"}):
        assert product.store(oot, "snapshots", "SNAPSHOTS") == "elsewhere", "a store's variable does not move it"
    env = {k: v for k, v in os.environ.items() if not k.startswith(product.STORE_ENV_PREFIX)}
    env["LOCALAPPDATA"] = "LAD"
    with mock.patch.dict(os.environ, env, clear=True), mock.patch.object(oot, "WINDOWS", True):
        assert product.store(oot, "snapshots", "SNAPSHOTS") == os.path.join("LAD", product.STORE_WIN, "snapshots")
    assert product.program(oot) is oot.HOOKSHOT or product.SAVES_PROGRAM != "HOOKSHOT"
    assert product.SNAPSHOT_FORMATS.match(product.SNAPSHOT_FORMAT), "the product does not read its own snapshots"
    assert product.SNAPSHOT_FORMATS.match("longshot-zot-snapshot"), "another fork's snapshots are not read"
    for bad in ("", "zot-snapshot", "hookshot-zot-snapshot2", "../x-zot-snapshot"):
        assert not product.SNAPSHOT_FORMATS.match(bad), "%r taken as a snapshot format" % bad
    saves = load(ROOT / "scripts" / "enhanced" / "zot_saves.py", "zot_saves")
    p = saves.parser()
    for flag in ("--game", "--hookshot"):
        a = p.parse_args(["snapshot", flag, "G"])
        assert a.game == "G", "zot_saves.py snapshot %s is not the game folder" % flag
    graphics = load(ROOT / "scripts" / "enhanced" / "zot_graphics.py", "zot_graphics")
    assert graphics.OPTIONS == product.OPTIONS and product.ENHANCED in graphics.HEADER
    mods = load(ROOT / "scripts" / "enhanced" / "zot_mods.py", "zot_mods")
    assert product.ENHANCED in mods.PROFILE_HEADER


def main():
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--cc", default="clang")
    args = p.parse_args()
    product = load(ROOT / "scripts" / "enhanced" / "enh_product.py", "enh_product")
    n_c = check_c_files()
    n_py = check_py_files()
    check_twins(product)
    helpers = check_c_helpers(args.cc)
    check_python(product)
    print("PASS: %d C/C++ and %d Python Enhanced files name the product only through enh_product; %s; stores, "
          "snapshot formats and --game/--hookshot" % (n_c, n_py, helpers))


if __name__ == "__main__":
    main()
