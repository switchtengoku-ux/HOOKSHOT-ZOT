"""scripts/enhanced/zot_mods.py, game-free: made-up mods in a temp folder (invented file names, no game data).

- discovery follows host/mods.c: a folder with romfs or exefs one to four levels down is a mod, nothing below a mod is
  looked at, "." folders are skipped, "-" and "_" turn a mod off (and every mod below such a folder);
- load order is the whole path, case ignored, and the later mod wins a shared file; conflicts report it;
- disable and enable rename the mod's own folder, refuse to overwrite, and leave everything on a dry run;
- profiles save the mods on and apply them (others off), reporting a missing one;
- the order rule in the tool matches host/mods.c's (_stricmp on the path below the mods folder).

python -I -B tests/test_enh_mods.py
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zot_mods", ROOT / "scripts" / "enhanced" / "zot_mods.py")
zm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zm)

FILES = {
    "01-first/romfs/Example/message.txt": "first",
    "01-first/romfs/Example/only-first.txt": "first only",
    "02-second/romfs/Example/message.txt": "second",
    "02-second/romfs/UI/ResourceSizeTable.srsizetable": "table",
    "03-third/romfs/UI/ResourceSizeTable.srsizetable": "table 3",
    "_off/romfs/Example/off.txt": "off",
    "-also-off/romfs/Example/x.txt": "off",
    ".hidden/romfs/Example/h.txt": "hidden",
    "contents/title/00-nested/romfs/Example/message.txt": "nested",
    "_pack/inner/romfs/Example/p.txt": "off by its folder",
    "code-only/exefs/patch.txt": "not applied",
    "a/b/c/d/e/romfs/too-deep.txt": "too deep",
}


class ModManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.game = self.root / "game"
        for rel, text in FILES.items():
            p = self.game / "mods" / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text, encoding="utf-8")
        self.store = self.root / "store"

    def tearDown(self):
        self.tmp.cleanup()

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = zm.main(["--store", str(self.store)] + list(argv))
        return code, out.getvalue(), err.getvalue()

    def mods(self):
        return {m.key: m.on for m in zm.discover(str(self.game / "mods"))}

    def test_discovery_follows_the_loader(self):
        mods = zm.discover(str(self.game / "mods"))
        on = [m.rel for m in mods if m.on]
        self.assertEqual(on, ["01-first", "02-second", "03-third", "code-only", "contents/title/00-nested"])
        off = {m.key for m in mods if not m.on}
        self.assertEqual(off, {"off", "also-off", "_pack/inner"})
        self.assertNotIn("hidden", {m.key for m in mods})
        self.assertFalse(any("too-deep" in m.rel or m.rel.startswith("a/") for m in mods))

    def test_conflicts_name_the_winner(self):
        code, out, _ = self.cli("conflicts", "--game", str(self.game))
        self.assertEqual(code, 0)
        self.assertIn("01-first < 02-second < contents/title/00-nested: 1 files, contents/title/00-nested wins", out)
        self.assertIn("02-second < 03-third", out)
        self.assertIn("resource size table", out)
        self.assertNotIn("off.txt", out)

    def test_disable_enable_and_dry_run(self):
        before = sorted(p.name for p in (self.game / "mods").iterdir())
        self.assertEqual(self.cli("disable", "02-second", "--game", str(self.game), "--dry-run")[0], 0)
        self.assertEqual(sorted(p.name for p in (self.game / "mods").iterdir()), before)
        self.assertEqual(self.cli("disable", "02-second", "--game", str(self.game))[0], 0)
        self.assertTrue((self.game / "mods" / "_02-second").is_dir())
        self.assertFalse(self.mods()["02-second"])
        self.assertEqual(self.cli("enable", "02-second", "--game", str(self.game))[0], 0)
        self.assertTrue(self.mods()["02-second"])
        self.assertEqual(self.cli("enable", "off", "--game", str(self.game))[0], 0)
        self.assertTrue((self.game / "mods" / "off").is_dir())

    def test_enable_reports_an_off_folder_above(self):
        code, out, _ = self.cli("enable", "_pack/inner", "--game", str(self.game))
        self.assertEqual(code, 0)
        self.assertIn("folder _pack above it", out)

    def test_rename_never_overwrites(self):
        (self.game / "mods" / "_01-first").mkdir()
        code, _, err = self.cli("disable", "01-first", "--game", str(self.game))
        self.assertEqual(code, 1)
        self.assertIn("already exists", err)
        self.assertTrue((self.game / "mods" / "01-first" / "romfs").is_dir())

    def test_profiles(self):
        self.assertEqual(self.cli("profile", "save", "all", "--game", str(self.game))[0], 0)
        self.cli("disable", "01-first", "--game", str(self.game))
        self.cli("disable", "03-third", "--game", str(self.game))
        self.assertEqual(self.cli("profile", "save", "light", "--game", str(self.game))[0], 0)
        code, out, _ = self.cli("profile", "apply", "all", "--game", str(self.game))
        self.assertEqual(code, 0)
        self.assertTrue(self.mods()["01-first"] and self.mods()["03-third"])
        self.cli("profile", "apply", "light", "--game", str(self.game))
        self.assertFalse(self.mods()["01-first"] or self.mods()["03-third"])
        self.assertTrue(self.mods()["02-second"])
        self.assertIn("light", self.cli("profile", "list")[1])
        (self.store / "ghost.txt").write_text("missing-mod\n02-second\n", encoding="utf-8")
        code, out, _ = self.cli("profile", "apply", "ghost", "--game", str(self.game))
        self.assertIn("Missing: missing-mod", out)
        self.assertEqual(self.cli("profile", "save", "../x", "--game", str(self.game))[0], 1)

    def test_order_rule_matches_the_loader(self):
        source = (ROOT / "host" / "mods.c").read_text(encoding="utf-8")
        self.assertIn("return _stricmp(((const Mod *)a)->name, ((const Mod *)b)->name);", source)
        self.assertIn("if (depth >= 4) return;", source)
        self.assertIn("fd.cFileName[0] == '-' || fd.cFileName[0] == '_'", source)
        self.assertIn('snprintf(slash + 1, sizeof root - (size_t)(slash + 1 - root), "mods");', source)


if __name__ == "__main__":
    unittest.main()
