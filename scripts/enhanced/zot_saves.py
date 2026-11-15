"""Hookshot Enhanced save manager: verified snapshots of Hookshot's saves, kept outside the game folder.

    python -I scripts/enhanced/zot_saves.py snapshot --hookshot GAME [--label NAME] [--dry-run] [--force]
    python -I scripts/enhanced/zot_saves.py list     [--profile ID]
    python -I scripts/enhanced/zot_saves.py verify   [SNAPSHOT ...]           (every snapshot when none is named)
    python -I scripts/enhanced/zot_saves.py restore  SNAPSHOT --hookshot GAME [--dry-run] [--force]
    python -I scripts/enhanced/zot_saves.py export   SNAPSHOT --zip FILE.zip
    python -I scripts/enhanced/zot_saves.py import   FILE.zip [--label NAME] [--dry-run]
    python -I scripts/enhanced/zot_saves.py prune    --keep N [--profile ID] [--dry-run]
    --store DIR (any command): the snapshot store; default %LOCALAPPDATA%\\HookshotZOT\\snapshots on Windows,
    $XDG_DATA_HOME/hookshot-zot/snapshots on Linux, or $HOOKSHOT_ZOT_SNAPSHOTS when set.

A snapshot is a copy of one profile's save folder (account.sav, option.sav, slot_*/) with a manifest.json that lists
every file's size and SHA-256. A snapshot is written into a hidden folder of the store, checked against its manifest and
only then renamed into place, so a failed copy never leaves a snapshot that looks complete.

restore checks the snapshot first, refuses while Hookshot or an emulator runs (--force skips that check), snapshots
the current save (label "pre-restore") and checks that snapshot, then swaps the save folder's entries for the
snapshot's with renames on the save's own disk (scripts/oot_saves.py swap_in) and checks the result against the
manifest. The save folder ends up holding exactly the snapshot's files.

import only adds a snapshot to the store from a zip made by export: it never writes into a game folder. Its entries are
checked before anything is extracted: no absolute paths, no "..", no links, only the save files' names, size caps,
and every file's hash against the zip's manifest.

Standard library only. Finding the save folder, the running-game check, the link check and the swap are
scripts/oot_saves.py's own, imported unchanged. The guide is docs/enhanced/SAVE_MANAGER.md.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
import re
import shutil
import stat
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("oot_saves", os.path.join(os.path.dirname(HERE), "oot_saves.py"))
oot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oot)

Fail = oot.Fail
FORMAT = "hookshot-zot-snapshot"
FORMAT_VERSION = 1
MANIFEST = "manifest.json"
LABEL = re.compile(r"[A-Za-z0-9_-]{1,40}$")
SNAPSHOT_ID = re.compile(r"\d{8}-\d{6}(-\d+)?(-[A-Za-z0-9_-]{1,40})?$")
# The names a save folder holds (scripts/oot_saves.py, docs/saves.md): the two profile files and the slots' files.
TOP_FILES = ("account.sav", "option.sav")
SLOT = re.compile(r"slot_\d{2,3}$")
SLOT_FILE = re.compile(r"[A-Za-z0-9_.-]{1,64}$")
MAX_FILE = 8 << 20        # (a save file is a few hundred kilobytes at most)
MAX_TOTAL = 256 << 20
MAX_ENTRIES = 4096


# ---- the store ----

def default_store():
    env = os.environ.get("HOOKSHOT_ZOT_SNAPSHOTS")
    if env:
        return env
    if oot.WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "HookshotZOT", "snapshots")
    return os.path.join(oot.data_home(), "hookshot-zot", "snapshots")


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def save_files(folder):
    """Every file of a save folder, as sorted relative paths with '/' separators. Hidden entries (a copy's leftovers
    from scripts/oot_saves.py, '.<name>-incoming-...') are not part of a save and are left out."""
    oot.refuse_links(folder)
    out = []
    for root, dirs, files in os.walk(folder):
        dirs[:] = sorted(d for d in dirs if not d.startswith("."))
        for n in sorted(files):
            if n.startswith("."):
                continue
            rel = os.path.relpath(os.path.join(root, n), folder).replace(os.sep, "/")
            out.append(rel)
    return out


def check_rel(rel):
    """A path a snapshot may hold: account.sav, option.sav, or slot_NN/<file>. Anything else is refused."""
    if "\\" in rel or rel.startswith("/") or ":" in rel:
        raise Fail("%s: not a relative path of a save" % rel)
    parts = rel.split("/")
    if len(parts) == 1 and parts[0] in TOP_FILES:
        return
    if len(parts) == 2 and SLOT.match(parts[0]) and SLOT_FILE.match(parts[1]) and parts[1] not in (".", ".."):
        return
    raise Fail("%s: not a file of a save folder (account.sav, option.sav or slot_NN/<file>)" % rel)


def manifest_for(folder, files, **fields):
    entries = []
    total = 0
    for rel in files:
        check_rel(rel)
        path = os.path.join(folder, *rel.split("/"))
        size = os.path.getsize(path)
        if size > MAX_FILE:
            raise Fail("%s is %d bytes: larger than a save file can be" % (rel, size))
        total += size
        entries.append({"path": rel, "size": size, "sha256": sha256_file(path)})
    if total > MAX_TOTAL:
        raise Fail("the save is %d bytes: larger than a save can be" % total)
    m = {"format": FORMAT, "version": FORMAT_VERSION}
    m.update(fields)
    m["files"] = entries
    return m


def verify_folder(folder, manifest):
    """The problems of folder against manifest (an empty list when it matches exactly)."""
    problems = []
    want = {e["path"]: e for e in manifest.get("files", [])}
    try:
        have = set(save_files(folder))
    except Fail as e:
        return [str(e)]
    for rel in sorted(set(want) - have):
        problems.append("missing: %s" % rel)
    for rel in sorted(have - set(want)):
        problems.append("not in the manifest: %s" % rel)
    for rel in sorted(set(want) & have):
        path = os.path.join(folder, *rel.split("/"))
        e = want[rel]
        if os.path.getsize(path) != e["size"]:
            problems.append("size differs: %s" % rel)
        elif sha256_file(path) != e["sha256"]:
            problems.append("SHA-256 differs: %s" % rel)
    return problems


def read_manifest(snap):
    try:
        with open(os.path.join(snap, MANIFEST), encoding="utf-8") as f:
            m = json.load(f)
    except (OSError, ValueError) as e:
        raise Fail("%s has no readable %s (%s)" % (snap, MANIFEST, e))
    if not isinstance(m, dict) or m.get("format") != FORMAT or not isinstance(m.get("files"), list):
        raise Fail("%s: %s is not a snapshot manifest" % (snap, MANIFEST))
    if m.get("version") != FORMAT_VERSION:
        raise Fail("%s: snapshot format %r, this tool reads %d" % (snap, m.get("version"), FORMAT_VERSION))
    for e in m["files"]:
        if not isinstance(e, dict) or not isinstance(e.get("path"), str) or not isinstance(e.get("size"), int) \
                or not re.fullmatch(r"[0-9a-f]{64}", str(e.get("sha256", ""))):
            raise Fail("%s: a malformed entry in %s" % (snap, MANIFEST))
        check_rel(e["path"])
    return m


def snapshots(store):
    """[(id, path, manifest or None, error or None)], oldest first."""
    out = []
    for n in sorted(oot.subdirs(store)):
        if not SNAPSHOT_ID.match(n):
            continue
        path = os.path.join(store, n)
        try:
            out.append((n, path, read_manifest(path), None))
        except Fail as e:
            out.append((n, path, None, str(e)))
    return out


def find_snapshot(store, ident):
    for n, path, m, err in snapshots(store):
        if n == ident:
            if err:
                raise Fail(err)
            return path, m
    raise Fail("no snapshot %s in %s (list shows them)" % (ident, store))


def new_id(store, label):
    stamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    base, n = stamp, 1
    while True:
        ident = base + ("-%s" % label if label else "")
        if not os.path.lexists(os.path.join(store, ident)):
            return ident
        n += 1
        base = "%s-%d" % (stamp, n)


def write_snapshot(store, label, source_folder, files, fields, dry_run):
    """Copies files of source_folder into a new snapshot of store; returns its id. Hidden staging folder, checked
    against the manifest, then renamed into place."""
    if label is not None and not LABEL.match(label):
        raise Fail("a label is 1 to 40 letters, digits, '-' or '_': %r is not" % label)
    manifest = manifest_for(source_folder, files, **fields)
    ident = new_id(store, label)
    print("%s snapshot %s: %d file(s) from %s" % ("Would make" if dry_run else "Making", ident, len(files), source_folder))
    if dry_run:
        return ident
    os.makedirs(store, exist_ok=True)
    staging = tempfile.mkdtemp(prefix=".incoming-", dir=store)
    try:
        for rel in files:
            dst = os.path.join(staging, *rel.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(source_folder, *rel.split("/")), dst, follow_symlinks=False)
        problems = verify_folder(staging, manifest)
        if problems:
            raise Fail("the copy does not match its source (the save changed while it was copied?): %s"
                       % "; ".join(problems))
        with open(os.path.join(staging, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
            json.dump(manifest, f, indent=1, sort_keys=False)
            f.write("\n")
        # (the manifest is not a save file: verify_folder compares the save files, so it is checked aside)
        os.replace(staging, os.path.join(store, ident))
    except BaseException:
        oot.remove_tree(staging)
        raise
    return ident


def snapshot_files(snap):
    return [f for f in save_files_with_manifest(snap) if f != MANIFEST]


def save_files_with_manifest(snap):
    oot.refuse_links(snap)
    out = []
    for root, dirs, files in os.walk(snap):
        dirs[:] = sorted(dirs)
        for n in sorted(files):
            out.append(os.path.relpath(os.path.join(root, n), snap).replace(os.sep, "/"))
    return out


def verify_snapshot(snap, manifest):
    """verify_folder for a snapshot: its manifest.json is the one file beside the save's."""
    problems = []
    want = {e["path"] for e in manifest["files"]}
    have = set(snapshot_files(snap))
    for rel in sorted(have - want):
        problems.append("not in the manifest: %s" % rel)
    for rel in sorted(want - have):
        problems.append("missing: %s" % rel)
    for e in manifest["files"]:
        if e["path"] in have:
            path = os.path.join(snap, *e["path"].split("/"))
            if os.path.getsize(path) != e["size"]:
                problems.append("size differs: %s" % e["path"])
            elif sha256_file(path) != e["sha256"]:
                problems.append("SHA-256 differs: %s" % e["path"])
    return problems


# ---- Hookshot's side ----

def hookshot_save(args):
    """(profile id, save folder, game folder) of Hookshot: --hookshot on Windows, as scripts/oot_saves.py finds it."""
    _, found = oot.locate(oot.HOOKSHOT, args.hookshot, "--hookshot")
    profile, folder = oot.pick(found, "Hookshot", "--profile <id>", args.profile)
    return profile, folder


def hookshot_version(game):
    """The version line of the game folder's hookshot_version.txt (make_game.py writes it), or None."""
    if not game:
        return None
    for name in ("hookshot_version.txt", os.path.join("bin", "hookshot_version.txt")):
        try:
            with open(os.path.join(game, name), encoding="utf-8", errors="replace") as f:
                for line in f:
                    if line.startswith("version="):
                        return line.strip()[len("version="):] or None
        except OSError:
            continue
    return None


def refuse_running(args, what):
    if args.dry_run or args.force:
        return
    busy = oot.running_games()
    if busy:
        raise Fail("close %s first (or pass --force): a running game can write its save during the %s"
                   % (" and ".join(busy), what))


def take_snapshot(args, store, label):
    profile, folder = hookshot_save(args)
    files = save_files(folder)
    if not files:
        raise Fail("%s holds no save files" % folder)
    fields = {"created": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
              "label": label, "profile": profile, "source": os.path.abspath(folder),
              "hookshot_version": hookshot_version(args.hookshot)}
    return write_snapshot(store, label, folder, files, fields, args.dry_run)


# ---- the commands ----

def cmd_snapshot(args, store):
    refuse_running(args, "snapshot")
    ident = take_snapshot(args, store, args.label)
    if not args.dry_run:
        print("Done: %s" % os.path.join(store, ident))


def cmd_list(args, store):
    snaps = snapshots(store)
    print("Snapshots in %s:" % store)
    shown = 0
    for n, path, m, err in snaps:
        if err:
            print("  %s  (unreadable: %s)" % (n, err))
            shown += 1
            continue
        if args.profile and str(m.get("profile", "")).lower() != args.profile.lower():
            continue
        slot_names = sorted({e["path"].split("/")[0] for e in m["files"] if "/" in e["path"]})
        size = sum(e["size"] for e in m["files"])
        print("  %s  profile %s, %d slot(s), %d file(s), %d KB%s%s" % (
            n, m.get("profile") or "?", len(slot_names), len(m["files"]), (size + 1023) // 1024,
            ", Hookshot %s" % m["hookshot_version"] if m.get("hookshot_version") else "",
            ", imported" if m.get("imported_from") else ""))
        shown += 1
    if not shown:
        print("  (none)")


def cmd_verify(args, store):
    snaps = snapshots(store)
    if args.snapshots:
        names = {n for n, _, _, _ in snaps}
        for s in args.snapshots:
            if s not in names:
                raise Fail("no snapshot %s in %s" % (s, store))
        snaps = [s for s in snaps if s[0] in args.snapshots]
    bad = 0
    for n, path, m, err in snaps:
        problems = [err] if err else verify_snapshot(path, m)
        print("  %s  %s" % (n, "OK" if not problems else "DAMAGED: " + "; ".join(problems)))
        bad += bool(problems)
    if not snaps:
        print("  (no snapshots)")
    if bad:
        raise Fail("%d snapshot(s) do not match their manifest" % bad)


def cmd_restore(args, store):
    snap, manifest = find_snapshot(store, args.snapshot)
    problems = verify_snapshot(snap, manifest)
    if problems:
        raise Fail("snapshot %s does not match its manifest, nothing was restored: %s" % (args.snapshot, "; ".join(problems)))
    profile, dst = hookshot_save(args)
    if manifest.get("profile") and str(manifest["profile"]).lower() != profile.lower():
        print("Note: snapshot %s is of profile %s, the save folder is profile %s" % (args.snapshot, manifest["profile"], profile))
    refuse_running(args, "restore")
    new = sorted({e["path"].split("/")[0] for e in manifest["files"]})
    old = sorted(n for n in os.listdir(dst) if not n.startswith("."))
    print("%s %s into %s (replacing %s)" % ("Would restore" if args.dry_run else "Restoring", args.snapshot, dst,
                                            ", ".join(old) or "nothing"))
    if args.dry_run:
        print("Dry run: nothing was changed")
        return
    # 1. the current save, kept first and checked
    if old:
        before = take_snapshot(args, store, "pre-restore")
        bpath, bman = find_snapshot(store, before)
        problems = verify_snapshot(bpath, bman)
        if problems:
            raise Fail("the pre-restore snapshot %s did not check out, nothing was restored: %s" % (before, "; ".join(problems)))
        print("Current save kept as snapshot %s" % before)
    else:
        before = None
    # 2. the snapshot copied onto the save's disk, then swapped in by renames (oot_saves.swap_in)
    incoming = tempfile.mkdtemp(prefix=".%s-incoming-" % os.path.basename(dst), dir=os.path.dirname(os.path.abspath(dst)))
    aside = None
    try:
        for e in manifest["files"]:
            target = os.path.join(incoming, *e["path"].split("/"))
            os.makedirs(os.path.dirname(target), exist_ok=True)
            shutil.copy2(os.path.join(snap, *e["path"].split("/")), target, follow_symlinks=False)
        problems = verify_folder(incoming, manifest)
        if problems:
            raise Fail("the copy of the snapshot does not check out, nothing was restored: %s" % "; ".join(problems))
        aside = oot.swap_in(dst, incoming, new, old, before and os.path.join(store, before))
    except BaseException:
        if not oot.remove_tree(incoming):
            print("Could not delete %s: delete it by hand" % incoming, file=sys.stderr)
        raise
    for p in (incoming, aside):
        if p and not oot.remove_tree(p):
            print("Restored, but could not delete %s: delete it by hand" % p, file=sys.stderr)
    # 3. the result checked
    problems = verify_folder(dst, manifest)
    if problems:
        raise Fail("the restored save does not match snapshot %s: %s%s" % (
            args.snapshot, "; ".join(problems), " (the save from before is snapshot %s)" % before if before else ""))
    print("Done: %s restored and checked%s" % (args.snapshot, "; the save from before is snapshot %s" % before if before else ""))


def cmd_export(args, store):
    snap, manifest = find_snapshot(store, args.snapshot)
    problems = verify_snapshot(snap, manifest)
    if problems:
        raise Fail("snapshot %s does not match its manifest, not exported: %s" % (args.snapshot, "; ".join(problems)))
    out = os.path.abspath(args.zip)
    if os.path.lexists(out):
        raise Fail("%s already exists: choose another name" % out)
    tmp = out + ".partial"
    try:
        # (the source folder's path stays out of the zip: it can name the player's user folder)
        shared = {k: v for k, v in manifest.items() if k != "source"}
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr(MANIFEST, json.dumps(shared, indent=1) + "\n")
            for e in manifest["files"]:
                z.write(os.path.join(snap, *e["path"].split("/")), e["path"])
        os.replace(tmp, out)
    except BaseException:
        if os.path.lexists(tmp):
            os.remove(tmp)
        raise
    print("Exported %s to %s (%d file(s)). It holds your saves: keep it private." % (args.snapshot, out, len(manifest["files"])))


def zip_entries(z):
    """The zip's entries checked before anything is extracted: {name: ZipInfo}."""
    infos = z.infolist()
    if len(infos) > MAX_ENTRIES:
        raise Fail("the zip has %d entries: not a snapshot" % len(infos))
    out, total = {}, 0
    for i in infos:
        name = i.filename
        if i.is_dir():
            if not SLOT.match(name.rstrip("/")):
                raise Fail("%s: a folder that is not a slot" % name)
            continue
        mode = (i.external_attr >> 16) & 0o170000
        if mode and mode != stat.S_IFREG:
            raise Fail("%s: not a plain file (a link?)" % name)
        if name != MANIFEST:
            check_rel(name)
        if name in out:
            raise Fail("%s twice in the zip" % name)
        if i.file_size > MAX_FILE:
            raise Fail("%s is %d bytes: larger than a save file can be" % (name, i.file_size))
        total += i.file_size
        out[name] = i
    if total > MAX_TOTAL:
        raise Fail("the zip unpacks to %d bytes: not a snapshot" % total)
    if MANIFEST not in out:
        raise Fail("the zip has no %s: not a snapshot made by export" % MANIFEST)
    return out


def cmd_import(args, store):
    if args.label is not None and not LABEL.match(args.label):
        raise Fail("a label is 1 to 40 letters, digits, '-' or '_': %r is not" % args.label)
    src = os.path.abspath(args.zipfile)
    with zipfile.ZipFile(src) as z:
        entries = zip_entries(z)
        try:
            manifest = json.loads(z.read(MANIFEST).decode("utf-8"))
        except ValueError as e:
            raise Fail("the zip's %s is not JSON (%s)" % (MANIFEST, e))
        listed = {e.get("path") for e in manifest.get("files", []) if isinstance(e, dict)}
        if set(entries) - {MANIFEST} != listed:
            raise Fail("the zip's files and its manifest's list differ")
        staging_parent = store if not args.dry_run else None
        if args.dry_run:
            check_dir = tempfile.mkdtemp(prefix="zot-import-check-")
        else:
            os.makedirs(store, exist_ok=True)
            check_dir = tempfile.mkdtemp(prefix=".incoming-", dir=staging_parent)
        try:
            for name, info in entries.items():
                target = os.path.join(check_dir, *name.split("/"))
                os.makedirs(os.path.dirname(target), exist_ok=True)
                with z.open(info) as f, open(target, "wb") as o:
                    shutil.copyfileobj(f, o)
            m = read_manifest(check_dir)
            problems = verify_snapshot(check_dir, m)
            if problems:
                raise Fail("the zip does not match its manifest, nothing was imported: %s" % "; ".join(problems))
            label = args.label if args.label is not None else "imported"
            ident = new_id(store, label)
            if args.dry_run:
                print("Would import %s as snapshot %s (%d file(s), checked)" % (src, ident, len(m["files"])))
                return
            m["imported_from"] = os.path.basename(src)
            m["label"] = label
            with open(os.path.join(check_dir, MANIFEST), "w", encoding="utf-8", newline="\n") as f:
                json.dump(m, f, indent=1)
                f.write("\n")
            os.replace(check_dir, os.path.join(store, ident))
            check_dir = None
        finally:
            if check_dir:
                oot.remove_tree(check_dir)
    print("Imported %s as snapshot %s (checked). restore puts it into a game." % (src, ident))


def cmd_prune(args, store):
    if args.keep < 1:
        raise Fail("--keep is at least 1")
    groups = {}
    for n, path, m, err in snapshots(store):
        if err:
            continue   # (a damaged snapshot is never deleted by prune: verify reports it, the player decides)
        prof = str(m.get("profile") or "?")
        if args.profile and prof.lower() != args.profile.lower():
            continue
        groups.setdefault(prof, []).append((n, path))
    gone = 0
    for prof, items in sorted(groups.items()):
        for n, path in items[:-args.keep]:
            print("%s %s (profile %s)" % ("Would delete" if args.dry_run else "Deleting", n, prof))
            if not args.dry_run:
                if not oot.remove_tree(path):
                    raise Fail("could not delete %s" % path)
            gone += 1
    print("%s %d snapshot(s); kept the newest %d of each profile" % ("Would delete" if args.dry_run else "Deleted", gone, args.keep))


COMMANDS = {"snapshot": cmd_snapshot, "list": cmd_list, "verify": cmd_verify, "restore": cmd_restore,
            "export": cmd_export, "import": cmd_import, "prune": cmd_prune}


def parser():
    p = argparse.ArgumentParser(prog="zot_saves.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--store", metavar="DIR", help="the snapshot store (default: %s)" % default_store())
    sub = p.add_subparsers(dest="command", required=True)

    def game(q, required):
        q.add_argument("--hookshot", metavar="GAME", required=required and oot.WINDOWS,
                       help="Hookshot's game folder (Windows) or data folder (Linux)")
        q.add_argument("--profile", metavar="ID", help="the profile, when the game folder has several")

    q = sub.add_parser("snapshot", help="copy the current save into a new, checked snapshot")
    game(q, True)
    q.add_argument("--label", help="a name for it (letters, digits, '-', '_')")
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--force", action="store_true", help="even if a game seems to be running")
    q = sub.add_parser("list", help="the snapshots in the store")
    q.add_argument("--profile", metavar="ID")
    q = sub.add_parser("verify", help="check snapshots against their manifest")
    q.add_argument("snapshots", nargs="*")
    q = sub.add_parser("restore", help="put a snapshot into the game (the current save is snapshotted first)")
    q.add_argument("snapshot")
    game(q, True)
    q.add_argument("--dry-run", action="store_true")
    q.add_argument("--force", action="store_true", help="even if a game seems to be running")
    q = sub.add_parser("export", help="a snapshot as a zip file")
    q.add_argument("snapshot")
    q.add_argument("--zip", required=True, metavar="FILE")
    q = sub.add_parser("import", help="a zip made by export, added to the store as a snapshot")
    q.add_argument("zipfile")
    q.add_argument("--label")
    q.add_argument("--dry-run", action="store_true")
    q = sub.add_parser("prune", help="delete all but the newest snapshots of each profile")
    q.add_argument("--keep", type=int, required=True)
    q.add_argument("--profile", metavar="ID")
    q.add_argument("--dry-run", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    store = os.path.abspath(args.store or default_store())
    try:
        COMMANDS[args.command](args, store)
    except Fail as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    except (OSError, zipfile.BadZipFile) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
