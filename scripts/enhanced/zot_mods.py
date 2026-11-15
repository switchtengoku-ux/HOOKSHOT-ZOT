"""Hookshot Enhanced mod manager: the mods folder Hookshot already loads, listed, checked for conflicts, turned on and
off, and kept as named sets. No second loader: it reads and renames folders by host/mods.c's own rules.

    python -I scripts/enhanced/zot_mods.py list      --game GAME                the mods, on and off, in load order
    python -I scripts/enhanced/zot_mods.py conflicts --game GAME [--all]        files more than one mod on supplies
    python -I scripts/enhanced/zot_mods.py disable   MOD --game GAME [--dry-run]
    python -I scripts/enhanced/zot_mods.py enable    MOD --game GAME [--dry-run]
    python -I scripts/enhanced/zot_mods.py profile save NAME --game GAME        the mods on now, kept as NAME
    python -I scripts/enhanced/zot_mods.py profile apply NAME --game GAME [--dry-run]
    python -I scripts/enhanced/zot_mods.py profile list | show NAME | delete NAME
    --mods DIR instead of --game: the folder holding the mods (as HOS_MODS); --store DIR: where profiles are kept
    (default %LOCALAPPDATA%\\HookshotZOT\\mod-profiles, $XDG_DATA_HOME/hookshot-zot/mod-profiles, or $HOOKSHOT_ZOT_MODS).

host/mods.c's rules (docs/mods.md), followed here:
- the mods folder is "mods" in the game folder (beside image.bin), or HOS_MODS;
- a folder holding "romfs" or "exefs", one to four levels below it, is a mod; nothing below a mod is looked at;
- a folder whose name starts with "." is skipped; with "-" or "_" it is off, and so is every mod below it;
- mods load in the order of their whole path below the mods folder, ignoring case: for a file two mods supply, the one
  that sorts last wins; an "exefs" folder is not applied (the code is compiled ahead of time);
- a link to a folder inside a romfs is not followed; links to files are.
A mod is turned off by renaming its own folder with a "_" in front, and on by taking it away. The game indexes mods at
its start: a change takes effect at the next start. Standard library only; the guide is docs/enhanced/MOD_MANAGER.md.
"""
import argparse
import datetime
import importlib.util
import os
import re
import stat
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("oot_saves", os.path.join(os.path.dirname(HERE), "oot_saves.py"))
oot = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(oot)

Fail = oot.Fail
OFF = ("-", "_")
MAX_DEPTH = 4          # (host/mods.c find_mods)
MAX_ROMFS_DEPTH = 32   # (host/mods.c index_romfs)
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_ -]{0,39}$")
PROFILE_HEADER = "# Hookshot Enhanced mod profile: the mods on, one per line (scripts/enhanced/zot_mods.py)"


class Mod:
    def __init__(self, path, rel, on):
        self.path, self.rel, self.on = path, rel, on
        self.romfs = os.path.isdir(os.path.join(path, "romfs"))
        self.exefs = os.path.isdir(os.path.join(path, "exefs"))
        self.files = None

    @property
    def folder(self):
        return os.path.basename(self.path)

    @property
    def key(self):
        """the mod's name with its own off prefix taken away: what it is called, on or off"""
        parts = self.rel.split("/")
        parts[-1] = parts[-1].lstrip("".join(OFF)) or parts[-1]
        return "/".join(parts)


def default_store():
    env = os.environ.get("HOOKSHOT_ZOT_MODS")
    if env:
        return env
    if oot.WINDOWS:
        base = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
        return os.path.join(base, "HookshotZOT", "mod-profiles")
    return os.path.join(oot.data_home(), "hookshot-zot", "mod-profiles")


def mods_root(args):
    if args.mods:
        return args.mods
    if not args.game:
        raise Fail("name the game folder with --game, or the mods folder with --mods")
    if not os.path.isdir(args.game):
        raise Fail("no folder at %s" % args.game)
    return os.path.join(args.game, "mods")


def is_dir_link(path):
    try:
        st = os.lstat(path)
    except OSError:
        return False
    return stat.S_ISLNK(st.st_mode) or bool(getattr(st, "st_file_attributes", 0) & 0x400)


def discover(root):
    """Every mod under root, on and off, in load order (on ones by host/mods.c's order; off ones after, by name)"""
    found = []

    def walk(d, rel, depth, on):
        if depth > 0 and (os.path.isdir(os.path.join(d, "romfs")) or os.path.isdir(os.path.join(d, "exefs"))):
            found.append(Mod(d, rel, on))
            return
        if depth >= MAX_DEPTH:
            return
        try:
            names = sorted(os.listdir(d))
        except OSError:
            return
        for n in names:
            p = os.path.join(d, n)
            if n.startswith(".") or not os.path.isdir(p):
                continue
            walk(p, rel + "/" + n if rel else n, depth + 1, on and not n.startswith(OFF))

    if os.path.isdir(root):
        walk(root, "", 0, True)
    on = sorted((m for m in found if m.on), key=lambda m: m.rel.lower())
    off = sorted((m for m in found if not m.on), key=lambda m: m.key.lower())
    return on + off


def romfs_files(mod):
    """{romfs key (lower case, '/'): host path} of a mod's files, as host/mods.c indexes them"""
    if mod.files is not None:
        return mod.files
    out = {}
    top = os.path.join(mod.path, "romfs")
    if os.path.isdir(top) and not is_dir_link(top):
        def walk(d, rel, depth):
            if depth > MAX_ROMFS_DEPTH:
                return
            try:
                names = sorted(os.listdir(d))
            except OSError:
                return
            for n in names:
                p = os.path.join(d, n)
                k = (rel + "/" + n if rel else n).replace("\\", "/").lower()
                if os.path.isdir(p):
                    if not is_dir_link(p):
                        walk(p, k, depth + 1)
                else:
                    out[k] = p
        walk(top, "", 0)
    mod.files = out
    return out


def find(mods, name):
    """The mod called name: its path below the mods folder, or its folder's name, with or without its off prefix"""
    want = name.replace("\\", "/").strip("/").lower()
    bare = want.lstrip("".join(OFF))
    hits = [m for m in mods if want in (m.rel.lower(), m.key.lower())]
    if not hits:
        hits = [m for m in mods if m.folder.lower() in (want, bare) or m.folder.lower().lstrip("".join(OFF)) == bare]
    if not hits:
        raise Fail("no mod called %s (list shows them)" % name)
    if len(hits) > 1:
        raise Fail("%s names %d mods: give its path below the mods folder (%s)" % (name, len(hits), ", ".join(m.rel for m in hits)))
    return hits[0]


def blocked_by(mod, root):
    """the folder above the mod whose name turns it off (it stays off while that is so), or None"""
    parts = mod.rel.split("/")[:-1]
    for i, p in enumerate(parts):
        if p.startswith(OFF):
            return "/".join(parts[:i + 1])
    return None


def rename(mod, new_folder, dry_run):
    dst = os.path.join(os.path.dirname(mod.path), new_folder)
    if os.path.lexists(dst):
        raise Fail("%s already exists: rename one of them by hand first" % dst)
    print("%s %s -> %s" % ("Would rename" if dry_run else "Renaming", mod.path, new_folder))
    if not dry_run:
        os.rename(mod.path, dst)


def set_on(mod, root, on, dry_run):
    if on:
        if mod.on:
            print("%s is on already" % mod.key)
            return False
        if mod.folder.startswith(OFF):
            rename(mod, mod.folder.lstrip("".join(OFF)) or mod.folder, dry_run)
        above = blocked_by(mod, root)
        if above:
            print("Note: %s is also off because the folder %s above it starts with %s; rename that one to turn it on"
                  % (mod.key, above, above.split("/")[-1][0]))
        return True
    if not mod.on and mod.folder.startswith(OFF):
        print("%s is off already" % mod.key)
        return False
    rename(mod, "_" + mod.folder, dry_run)
    return True


# ---- the commands ----

def cmd_list(args, store):
    root = mods_root(args)
    mods = discover(root)
    print("Mods in %s (load order: for a file two mods supply, the later one wins):" % root)
    n = 0
    for m in mods:
        if m.on:
            n += 1
        notes = []
        if m.exefs:
            notes.append("exefs not applied")
        if not m.romfs:
            notes.append("no romfs")
        above = None if m.on else blocked_by(m, root)
        if above:
            notes.append("off by the folder %s" % above)
        files = len(romfs_files(m)) if m.romfs else 0
        print("  %s %-40s %5d files%s" % ("%3d." % n if m.on else " off", m.key, files,
                                          "  (" + "; ".join(notes) + ")" if notes else ""))
    if not mods:
        print("  (none: a mod is a folder with a romfs folder in it, in %s)" % root)


def cmd_conflicts(args, store):
    mods = [m for m in discover(mods_root(args)) if m.on and m.romfs]
    owners = {}
    for m in mods:
        for k in romfs_files(m):
            owners.setdefault(k, []).append(m)
    clashes = {k: v for k, v in owners.items() if len(v) > 1}
    if not clashes:
        print("No conflicts: no file is supplied by more than one mod that is on")
        return
    pairs = {}
    for k, v in clashes.items():
        pairs.setdefault(tuple(m.key for m in v), []).append(k)
    print("%d files are supplied by more than one mod (the last one named wins):" % len(clashes))
    for names, keys in sorted(pairs.items(), key=lambda kv: -len(kv[1])):
        print("  %s: %d files, %s wins" % (" < ".join(names), len(keys), names[-1]))
        for k in sorted(keys)[:None if args.all else 5]:
            print("      %s" % k)
        if not args.all and len(keys) > 5:
            print("      ... %d more (--all)" % (len(keys) - 5))
    tables = [k for k in clashes if "resourcesizetable" in k.replace("_", "").replace(".", "")]
    if tables:
        print("Note: more than one mod has the resource size table (%s): only the winner's is used, so a mod whose files"
              " need more memory may need its entries in the winning table (docs/mods.md)" % ", ".join(sorted(tables)))


def cmd_switch(args, store, on):
    root = mods_root(args)
    mod = find(discover(root), args.mod)
    if set_on(mod, root, on, args.dry_run) and not args.dry_run:
        print("Done: %s is %s from the next start of the game" % (mod.key, "on" if on else "off"))


def profile_path(store, name):
    if not NAME.match(name or ""):
        raise Fail("a profile name is 1 to 40 letters, digits, spaces, '-' or '_', starting with a letter or digit: %r is not"
                   % name)
    return os.path.join(store, name + ".txt")


def read_profile(store, name):
    path = profile_path(store, name)
    if not os.path.isfile(path):
        raise Fail("no mod profile %s in %s" % (name, store))
    with open(path, encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.lstrip().startswith("#")]


def cmd_profile(args, store):
    if args.action == "list":
        names = sorted(n[:-4] for n in (os.listdir(store) if os.path.isdir(store) else []) if n.endswith(".txt"))
        print("Mod profiles in %s:" % store)
        for n in names:
            try:
                print("  %-24s %d mods on" % (n, len(read_profile(store, n))))
            except Fail as e:
                print("  %-24s (%s)" % (n, e))
        if not names:
            print("  (none)")
        return
    if not args.name:
        raise Fail("profile %s needs a name" % args.action)
    if args.action == "show":
        for k in read_profile(store, args.name):
            print(k)
        return
    if args.action == "delete":
        path = profile_path(store, args.name)
        if not os.path.isfile(path):
            raise Fail("no mod profile %s" % args.name)
        os.remove(path)
        print("Deleted mod profile %s" % args.name)
        return
    root = mods_root(args)
    mods = discover(root)
    if args.action == "save":
        path = profile_path(store, args.name)
        if os.path.exists(path) and not args.replace:
            raise Fail("mod profile %s exists: pass --replace to overwrite it" % args.name)
        on = [m.key for m in mods if m.on]
        os.makedirs(store, exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write("%s\n# saved %s from %s\n" % (PROFILE_HEADER, datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), root))
            f.write("".join(k + "\n" for k in on))
        print("Saved mod profile %s: %d mods on" % (args.name, len(on)))
        return
    # apply: the profile's mods on, every other mod off
    wanted = {k.lower() for k in read_profile(store, args.name)}
    known = {m.key.lower() for m in mods}
    changed = 0
    for m in mods:
        changed += set_on(m, root, m.key.lower() in wanted, args.dry_run) is True
    for k in sorted(wanted - known):
        print("Missing: %s is in the profile but not in %s" % (k, root))
    print("%s %d change(s); the game loads them at its next start" % ("Would make" if args.dry_run else "Made", changed))


def parser():
    p = argparse.ArgumentParser(prog="zot_mods.py", description=__doc__.split("\n\n")[0])
    p.add_argument("--store", metavar="DIR", help="where mod profiles are kept (default: %s)" % default_store())
    sub = p.add_subparsers(dest="command", required=True)

    def where(q):
        q.add_argument("--game", metavar="GAME", help="the game folder (its mods folder is used)")
        q.add_argument("--mods", metavar="DIR", help="the mods folder itself (as HOS_MODS)")

    q = sub.add_parser("list", help="the mods, on and off, in load order")
    where(q)
    q = sub.add_parser("conflicts", help="files more than one mod that is on supplies, and which one wins")
    where(q)
    q.add_argument("--all", action="store_true", help="every file, not the first five of each pair")
    for name in ("enable", "disable"):
        q = sub.add_parser(name, help="turn a mod %s (its folder renamed)" % ("on" if name == "enable" else "off"))
        q.add_argument("mod")
        where(q)
        q.add_argument("--dry-run", action="store_true")
    q = sub.add_parser("profile", help="named sets of mods: save, apply, list, show, delete")
    q.add_argument("action", choices=["save", "apply", "list", "show", "delete"])
    q.add_argument("name", nargs="?")
    where(q)
    q.add_argument("--replace", action="store_true", help="save: overwrite a profile of that name")
    q.add_argument("--dry-run", action="store_true")
    return p


def main(argv=None):
    args = parser().parse_args(sys.argv[1:] if argv is None else list(argv))
    store = os.path.abspath(args.store or default_store())
    try:
        if args.command == "list":
            cmd_list(args, store)
        elif args.command == "conflicts":
            cmd_conflicts(args, store)
        elif args.command in ("enable", "disable"):
            cmd_switch(args, store, args.command == "enable")
        else:
            cmd_profile(args, store)
    except (Fail, OSError) as e:
        print("error: %s" % e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
