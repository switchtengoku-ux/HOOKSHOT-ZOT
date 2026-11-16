"""Hookshot Enhanced: carry the Enhanced layer from this repository to another fork of the same game (a Longshot Enhanced).

    python -I scripts/enhanced/port_to.py TARGET --product longshot [--ref enhanced/main] [--base v2.3.1] [--apply]

TARGET is a clean git checkout of the other fork (its Enhanced branch). --product names a profile in
scripts/enhanced/products/ (or a JSON file): the target's names (its options file, switch prefix, stores, saves script)
and its menu's Graphics rows.
Without --apply nothing in TARGET changes: the port is made in a throwaway worktree of TARGET and reported.

What a port does, from --ref of this repository (a commit, not the working tree):
- the layer, copied whole: host/enh_*, gpu/vk/enh_*, scripts/enhanced/*.py and products/*.json, tests/test_enh_*.py;
  a layer file the last port brought and --ref no longer has is removed;
- the product files, host/enh_product.h and scripts/enhanced/enh_product.py, made from --ref's with the profile's names
  (docs/enhanced/ARCHITECTURE.md, "The product layer");
- the hooks, the small (enhanced) edits to upstream files: the diff of those files from --base (or from the commit the
  last port came from) to --ref, applied with git apply --3way. A hunk that does not apply is left as a conflict to
  resolve by hand, and a hooked file the target does not have is skipped and reported;
- scripts/enhanced/ported_from.json in TARGET: the commit ported, the profile and the layer's files, so the next port
  starts from there.
Never ported (each fork keeps its own): CLAUDE.md, .github/, docs/enhanced/, scripts/enhanced/build_windows.ps1.

TARGET's object store receives this repository's commits (a git fetch, no branch or tag), which git apply --3way needs.
--apply refuses a TARGET with changes to tracked files, and leaves the result for review: nothing is committed or pushed.
Exit status: 0 done, 1 conflicts to resolve, 2 refused. Standard library and git only.
"""
import argparse
import datetime
import fnmatch
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SOURCE = os.path.dirname(os.path.dirname(HERE))
PRODUCTS = os.path.join(HERE, "products")
LAYER = ("host/enh_*", "gpu/vk/enh_*", "scripts/enhanced/*.py", "scripts/enhanced/products/*.json", "tests/test_enh_*.py")
PRODUCT_C = "host/enh_product.h"
PRODUCT_PY = "scripts/enhanced/enh_product.py"
NEVER = ("CLAUDE.md", ".github/*", "docs/enhanced/*", "scripts/enhanced/build_windows.ps1")
MANIFEST = "scripts/enhanced/ported_from.json"
FORMAT = "enhanced-port"
KEYS = ("product", "options", "env_prefix", "env_file", "store_win", "store_posix", "store_env_prefix", "version_file",
        "saves_script", "saves_program", "snapshot_format")
C_NAMES = (("product", "ENH_PRODUCT"), ("options", "ENH_OPTIONS"), ("env_prefix", "ENH_ENV_PREFIX"),
           ("env_file", "ENH_ENV_FILE"), ("store_win", "ENH_STORE_WIN"), ("store_posix", "ENH_STORE_POSIX"),
           ("store_env_prefix", "ENH_STORE_ENV_PREFIX"))
PY_NAMES = (("product", "PRODUCT"), ("options", "OPTIONS"), ("saves_script", "SAVES_SCRIPT"),
            ("saves_program", "SAVES_PROGRAM"), ("store_win", "STORE_WIN"), ("store_posix", "STORE_POSIX"),
            ("store_env_prefix", "STORE_ENV_PREFIX"), ("snapshot_format", "SNAPSHOT_FORMAT"))


class Fail(Exception):
    pass


def git(repo, *args, data=None, check=True):
    r = subprocess.run(["git", "-C", repo] + list(args), input=data, capture_output=True)
    if check and r.returncode:
        raise Fail("git %s: %s" % (" ".join(args[:3]), r.stderr.decode("utf-8", "replace").strip()))
    return r


def out(repo, *args):
    return git(repo, *args).stdout.decode("utf-8").strip()


def matches(path, patterns):
    return any(fnmatch.fnmatchcase(path, p) for p in patterns)


def load_profile(name):
    path = name if name.endswith(".json") else os.path.join(PRODUCTS, name + ".json")
    try:
        with open(path, encoding="utf-8") as f:
            profile = json.load(f)
    except (OSError, ValueError) as e:
        raise Fail("no readable product profile %s (%s)" % (path, e))
    missing = [k for k in KEYS if not isinstance(profile.get(k), str) or not profile[k]]
    if missing:
        raise Fail("%s: missing %s" % (path, ", ".join(missing)))
    for k in KEYS:
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", profile[k]):
            raise Fail("%s: %s is not a plain name: %r" % (path, k, profile[k]))
    keys = profile.get("graphics_keys")
    if not isinstance(keys, list) or not keys or not all(isinstance(k, str) and re.fullmatch(r"[a-z0-9_-]+", k) for k in keys):
        raise Fail("%s: graphics_keys must list the Graphics rows' option keys" % path)
    if not profile["env_prefix"].startswith(profile["store_env_prefix"].split("_")[0] + "_"):
        raise Fail("%s: env_prefix must start with the product's own prefix, the one its env file takes" % path)
    return profile


def product_c(text, p):
    for key, name in C_NAMES:
        text, n = re.subn(r'(#define %s ")[^"]*(")' % name, lambda m: m.group(1) + p[key] + m.group(2), text)
        if n != 1:
            raise Fail("%s: no single #define %s to set" % (PRODUCT_C, name))
    return text


def product_py(text, p):
    for key, name in PY_NAMES:
        text, n = re.subn(r'^(%s = ")[^"]*(")' % name, lambda m: m.group(1) + p[key] + m.group(2), text, flags=re.M)
        if n != 1:
            raise Fail("%s: no single %s to set" % (PRODUCT_PY, name))
    v = p["version_file"]
    text, n = re.subn(r'^VERSION_FILES = \("[^"]*", os\.path\.join\("bin", "[^"]*"\)\)',
                      lambda m: 'VERSION_FILES = ("%s", os.path.join("bin", "%s"))' % (v, v), text, flags=re.M)
    if n != 1:
        raise Fail("%s: no single VERSION_FILES to set" % PRODUCT_PY)
    keys = ", ".join('"%s"' % k for k in p["graphics_keys"])
    lines, line = [], "   "
    for word in keys.split(" "):   # (wrapped at 120 columns, as the file is)
        if len(line) + 1 + len(word) > 120:
            lines.append(line)
            line = "   "
        line += " " + word
    block = "GRAPHICS_KEYS = (\n" + "\n".join(lines + [line]) + ",\n)"
    text, n = re.subn(r"^GRAPHICS_KEYS = \(\n.*?\n\)", lambda m: block, text, flags=re.M | re.S)
    if n != 1:
        raise Fail("%s: no single GRAPHICS_KEYS to set" % PRODUCT_PY)
    return text


def blob(sha, path):
    return git(SOURCE, "show", "%s:%s" % (sha, path)).stdout


def plan(sha, base, previous):
    """(layer files, hooked files and their status, the hooks' diff) of the source at sha."""
    files = out(SOURCE, "ls-tree", "-r", "--name-only", sha).splitlines()
    layer = sorted(f for f in files if matches(f, LAYER) and f not in (PRODUCT_C, PRODUCT_PY))
    for f in (PRODUCT_C, PRODUCT_PY):
        if f not in files:
            raise Fail("%s has no %s: the product layer is older than this tool" % (sha[:8], f))
    since = previous or base
    changed = []
    for line in out(SOURCE, "diff", "--no-renames", "--name-status", since, sha).splitlines():
        status, path = line.split("\t", 1)
        if matches(path, LAYER) or path in (PRODUCT_C, PRODUCT_PY) or matches(path, NEVER):
            continue
        changed.append((status, path))
    return layer, changed, since


def run_port(root, sha, base, previous, profile, prev_layer, source_product):
    """Makes the port in root (the target, or a throwaway worktree of it): the report as a dict."""
    layer, changed, since = plan(sha, base, previous)
    rep = {"new": [], "changed": [], "same": [], "removed": [], "generated": [], "hooked": [], "conflicts": [],
           "skipped": [], "review": []}
    for path in layer:
        data = blob(sha, path)
        dst = os.path.join(root, *path.split("/"))
        old = None
        if os.path.isfile(dst):
            with open(dst, "rb") as f:
                old = f.read()
        if old == data:
            rep["same"].append(path)
            continue
        rep["new" if old is None else "changed"].append(path)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "wb") as f:
            f.write(data)
    for path in sorted(set(prev_layer) - set(layer)):
        dst = os.path.join(root, *path.split("/"))
        if os.path.isfile(dst):
            os.remove(dst)
            rep["removed"].append(path)
    for path, make in ((PRODUCT_C, product_c), (PRODUCT_PY, product_py)):
        text = make(blob(sha, path).decode("utf-8"), profile)
        dst = os.path.join(root, *path.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, "w", encoding="utf-8", newline="") as f:
            f.write(text)
        rep["generated"].append(path)
    hooks = []
    # (git's own names, in their exact case: a Windows disk would find README.md for readme.md)
    tracked = set(out(root, "-c", "core.quotepath=false", "ls-files").splitlines())
    for status, path in changed:
        if status != "A" and path not in tracked:
            rep["skipped"].append(path)
        else:
            hooks.append(path)
    if hooks:
        patch = git(SOURCE, "diff", "--no-renames", "--full-index", "--binary", since, sha, "--", *hooks).stdout
        name = re.compile(re.escape(source_product), re.I)
        current = None
        for line in patch.decode("utf-8", "replace").splitlines():
            if line.startswith("+++ "):
                current = line[6:] if line.startswith("+++ b/") else None
            elif line.startswith("+") and current and name.search(line) and "(%s)" % source_product.lower() not in line:
                rep["review"].append("%s: %s" % (current, line[1:].strip()[:120]))
        r = git(root, "apply", "--3way", "--whitespace=nowarn", "-", data=patch, check=False)
        unmerged = out(root, "diff", "--name-only", "--diff-filter=U").splitlines()
        rep["conflicts"] = sorted(unmerged)
        rep["hooked"] = sorted(set(hooks) - set(unmerged))
        if r.returncode and not unmerged:
            raise Fail("git apply: %s" % r.stderr.decode("utf-8", "replace").strip())
    manifest = {"format": FORMAT, "version": 1, "source_commit": sha, "base": since, "profile": profile["product"],
                "ported": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "layer": layer}
    dst = os.path.join(root, *MANIFEST.split("/"))
    with open(dst, "w", encoding="utf-8", newline="\n") as f:
        json.dump(manifest, f, indent=1)
        f.write("\n")
    return rep


def report(rep, applied, target):
    def section(title, items):
        if items:
            print("%s (%d):" % (title, len(items)))
            for i in items:
                print("  " + i)
    section("New layer files", rep["new"])
    section("Changed layer files", rep["changed"])
    if rep["same"]:
        print("Unchanged layer files: %d" % len(rep["same"]))
    section("Removed (the last port's, gone from the source)", rep["removed"])
    section("Product files made from the profile", rep["generated"])
    section("Hooks applied", rep["hooked"])
    section("Hooks in conflict: resolve by hand", rep["conflicts"])
    section("Hooks skipped: the target has no such file", rep["skipped"])
    section("Added hook lines naming the source product: review", rep["review"])
    if applied:
        print("Done in %s: review with git status and git diff, then commit. Nothing was committed or pushed." % target)
    else:
        print("Dry run: %s is unchanged. Run again with --apply to make the port there." % target)


def main(argv=None):
    p = argparse.ArgumentParser(prog="port_to.py", description=__doc__.split("\n\n")[0])
    p.add_argument("target", help="a clean git checkout of the other fork")
    p.add_argument("--product", required=True, help="a profile in scripts/enhanced/products/ (longshot) or a JSON file")
    p.add_argument("--ref", default="enhanced/main", help="the commit of this repository to port (default enhanced/main)")
    p.add_argument("--base", default="v2.3.1", help="where this fork left upstream, for a first port (default v2.3.1)")
    p.add_argument("--apply", action="store_true", help="make the port in TARGET (default: a dry run)")
    p.add_argument("--source", default=os.path.dirname(os.path.dirname(HERE)), help=argparse.SUPPRESS)   # (the tests' own source repository)
    args = p.parse_args(argv)
    global SOURCE
    SOURCE = os.path.abspath(args.source)
    try:
        profile = load_profile(args.product)
        target = os.path.abspath(args.target)
        if git(target, "rev-parse", "--git-dir", check=False).returncode:
            raise Fail("%s is not a git checkout" % target)
        top = os.path.normcase(os.path.realpath(out(target, "rev-parse", "--show-toplevel")))
        if top == os.path.normcase(os.path.realpath(out(SOURCE, "rev-parse", "--show-toplevel"))):
            raise Fail("the target is this repository")
        sha = out(SOURCE, "rev-parse", "--verify", args.ref + "^{commit}")
        base = out(SOURCE, "rev-parse", "--verify", args.base + "^{commit}")
        if git(SOURCE, "merge-base", "--is-ancestor", base, sha, check=False).returncode:
            raise Fail("--base %s is not an ancestor of --ref %s" % (args.base, args.ref))
        source_product = re.search(r'^PRODUCT = "([^"]+)"', blob(sha, PRODUCT_PY).decode("utf-8"), re.M).group(1)
        previous, prev_layer = None, []
        mpath = os.path.join(target, *MANIFEST.split("/"))
        if os.path.isfile(mpath):
            with open(mpath, encoding="utf-8") as f:
                m = json.load(f)
            if m.get("format") != FORMAT:
                raise Fail("%s is not a port manifest" % mpath)
            previous, prev_layer = m["source_commit"], m.get("layer", [])
            if previous == sha:
                print("%s is already ported at %s: nothing to do." % (target, sha[:8]))
                return 0
            if git(SOURCE, "merge-base", "--is-ancestor", previous, sha, check=False).returncode:
                raise Fail("the last port came from %s, which --ref %s does not contain" % (previous[:8], args.ref))
        if args.apply and out(target, "status", "--porcelain", "--untracked-files=no"):
            raise Fail("%s has changes to tracked files: commit or stash them first" % target)
        if git(target, "fetch", "--quiet", "--no-tags", SOURCE, sha, check=False).returncode:   # (a commit by name when
            git(target, "fetch", "--quiet", "--no-tags", SOURCE, args.ref)                     #  the source refuses one by id)
        print("Porting %s (%s) to %s as %s%s" % (args.ref, sha[:8], target, profile["product"],
                                               "" if args.apply else " (dry run)"))
        if args.apply:
            rep = run_port(target, sha, base, previous, profile, prev_layer, source_product)
        else:
            tmp = tempfile.mkdtemp(prefix="enh-port-")
            tree = os.path.join(tmp, "tree")
            try:
                git(target, "worktree", "add", "--detach", "--quiet", tree, "HEAD")
                rep = run_port(tree, sha, base, previous, profile, prev_layer, source_product)
            finally:
                git(target, "worktree", "remove", "--force", tree, check=False)
                git(target, "worktree", "prune", check=False)
                shutil.rmtree(tmp, ignore_errors=True)
        report(rep, args.apply, target)
        return 1 if rep["conflicts"] else 0
    except Fail as e:
        print("port_to.py: %s" % e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
