"""scripts/enhanced/zot_saves.py, game-free: snapshots, verify, restore with its pre-restore snapshot, zip export and
import (and the zip checks), prune, dry runs and the running-game guard. Made-up save files in temp folders only;
the running-game check is replaced, so no process list is read.

python -I -B tests/test_enh_saves.py
"""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
import zipfile
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zot_saves", ROOT / "scripts" / "enhanced" / "zot_saves.py")
zot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zot)

UID = "0123456789abcdef0123456789abcdef"


def make_game(game, tag, slot_names=("slot_00", "slot_01")):
    """A Windows-layout game folder (<game>/user/save/<uid>) with a made-up save; returns the save folder."""
    save = game / "user" / "save" / UID
    save.mkdir(parents=True, exist_ok=True)
    (save / "account.sav").write_bytes(b"account-" + tag)
    (save / "option.sav").write_bytes(b"option-" + tag)
    for s in slot_names:
        (save / s).mkdir(exist_ok=True)
        (save / s / "progress.sav").write_bytes(b"progress-" + tag + s.encode())
        (save / s / "caption.sav").write_bytes(b"caption-" + tag + s.encode())
    (game / "hookshot_version.txt").write_text("version=v2.3.1\n", encoding="utf-8")
    return save


def tree(folder):
    return {p.relative_to(folder).as_posix(): p.read_bytes() for p in sorted(folder.rglob("*")) if p.is_file()}


class SaveManagerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.game = self.root / "game"
        self.store = self.root / "store"
        self.save = make_game(self.game, b"A")
        self.running = mock.patch.object(zot.oot, "running_games", return_value=[])
        self.running.start()

    def tearDown(self):
        self.running.stop()
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = zot.main(["--store", str(self.store)] + list(argv))
        return code, out.getvalue(), err.getvalue()

    def snap(self, label=None):
        args = ["snapshot", "--hookshot", str(self.game)] + (["--label", label] if label else [])
        code, out, err = self.run_cli(*args)
        self.assertEqual(code, 0, err)
        ids = [n for n, _, _, _ in zot.snapshots(str(self.store))]
        return ids[-1]

    def test_snapshot_copies_every_file_with_its_hash(self):
        ident = self.snap("first")
        self.assertTrue(ident.endswith("-first"))
        snap = self.store / ident
        m = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(m["format"], "hookshot-zot-snapshot")
        self.assertEqual(m["profile"], UID)
        self.assertEqual(m["hookshot_version"], "v2.3.1")
        self.assertEqual({e["path"] for e in m["files"]}, set(tree(self.save)))
        files = tree(snap)
        files.pop("manifest.json")
        self.assertEqual(files, tree(self.save))
        code, out, _ = self.run_cli("verify")
        self.assertEqual(code, 0)
        self.assertIn("OK", out)
        self.assertEqual([p.name for p in self.store.iterdir() if p.name.startswith(".")], [])

    def test_snapshot_leaves_the_save_untouched(self):
        before = tree(self.save)
        self.snap()
        self.assertEqual(tree(self.save), before)

    def test_dry_run_snapshot_writes_nothing(self):
        code, out, err = self.run_cli("snapshot", "--hookshot", str(self.game), "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertIn("Would make", out)
        self.assertFalse(self.store.exists())

    def test_bad_label_is_refused(self):
        code, _, err = self.run_cli("snapshot", "--hookshot", str(self.game), "--label", "../x")
        self.assertEqual(code, 1)
        self.assertIn("label", err)

    def test_verify_reports_a_damaged_snapshot(self):
        ident = self.snap()
        (self.store / ident / "slot_00" / "progress.sav").write_bytes(b"changed")
        code, out, err = self.run_cli("verify")
        self.assertEqual(code, 1)
        self.assertIn("DAMAGED", out)
        self.assertIn("slot_00/progress.sav", out)
        (self.store / ident / "extra.sav").write_bytes(b"x")
        code, out, _ = self.run_cli("verify", ident)
        self.assertIn("not in the manifest: extra.sav", out)

    def test_restore_puts_the_snapshot_back_and_keeps_the_current_save(self):
        ident = self.snap("good")
        good = tree(self.save)
        # the save moves on: a slot changes, a new slot appears
        (self.save / "slot_00" / "progress.sav").write_bytes(b"later")
        (self.save / "slot_02").mkdir()
        (self.save / "slot_02" / "progress.sav").write_bytes(b"new slot")
        later = tree(self.save)
        code, out, err = self.run_cli("restore", ident, "--hookshot", str(self.game))
        self.assertEqual(code, 0, err)
        self.assertEqual(tree(self.save), good)
        pre = [n for n, _, _, _ in zot.snapshots(str(self.store)) if n.endswith("-pre-restore")]
        self.assertEqual(len(pre), 1)
        kept = tree(self.store / pre[0])
        kept.pop("manifest.json")
        self.assertEqual(kept, later)
        self.assertEqual([p.name for p in self.save.parent.iterdir() if p.name.startswith(".")], [])

    def test_restore_dry_run_changes_nothing(self):
        ident = self.snap()
        (self.save / "option.sav").write_bytes(b"other")
        before = tree(self.save)
        code, out, err = self.run_cli("restore", ident, "--hookshot", str(self.game), "--dry-run")
        self.assertEqual(code, 0, err)
        self.assertEqual(tree(self.save), before)
        self.assertEqual(len(zot.snapshots(str(self.store))), 1)

    def test_restore_refuses_a_damaged_snapshot(self):
        ident = self.snap()
        (self.store / ident / "account.sav").write_bytes(b"damaged")
        (self.save / "option.sav").write_bytes(b"current")
        before = tree(self.save)
        code, _, err = self.run_cli("restore", ident, "--hookshot", str(self.game))
        self.assertEqual(code, 1)
        self.assertIn("does not match", err)
        self.assertEqual(tree(self.save), before)

    def test_restore_and_snapshot_refuse_while_a_game_runs(self):
        ident = self.snap()
        before = tree(self.save)
        with mock.patch.object(zot.oot, "running_games", return_value=["Hookshot"]):
            code, _, err = self.run_cli("restore", ident, "--hookshot", str(self.game))
            self.assertEqual(code, 1)
            self.assertIn("close Hookshot", err)
            code, _, err = self.run_cli("snapshot", "--hookshot", str(self.game))
            self.assertEqual(code, 1)
        self.assertEqual(tree(self.save), before)
        self.assertEqual(len(zot.snapshots(str(self.store))), 1)

    def test_export_and_import_round_trip(self):
        ident = self.snap("trip")
        out_zip = self.root / "trip.zip"
        code, out, err = self.run_cli("export", ident, "--zip", str(out_zip))
        self.assertEqual(code, 0, err)
        code, _, err = self.run_cli("export", ident, "--zip", str(out_zip))
        self.assertEqual(code, 1, "an existing zip is never overwritten")
        code, out, err = self.run_cli("import", str(out_zip), "--label", "back")
        self.assertEqual(code, 0, err)
        back = [n for n, _, _, _ in zot.snapshots(str(self.store)) if n.endswith("-back")]
        self.assertEqual(len(back), 1)
        a, b = tree(self.store / ident), tree(self.store / back[0])
        a.pop("manifest.json"), b.pop("manifest.json")
        self.assertEqual(a, b)
        self.assertEqual(self.run_cli("verify")[0], 0)

    def bad_zip(self, entries, manifest=None, name="bad"):
        path = self.root / (name + ".zip")
        if path.exists():
            path.unlink()
        with zipfile.ZipFile(path, "w") as z:
            if manifest is not None:
                z.writestr("manifest.json", json.dumps(manifest))
            for name, data in entries.items():
                z.writestr(name, data)
        return path

    def manifest(self, files):
        import hashlib
        return {"format": "hookshot-zot-snapshot", "version": 1, "files": [
            {"path": k, "size": len(v), "sha256": hashlib.sha256(v).hexdigest()} for k, v in files.items()]}

    def test_import_refuses_unsafe_or_wrong_zips(self):
        good = {"account.sav": b"a", "slot_00/progress.sav": b"p"}
        cases = {
            "../evil.sav": self.bad_zip({"../evil.sav": b"x"}, {"format": "hookshot-zot-snapshot", "version": 1, "files": []}, "dots"),
            "absolute": self.bad_zip({"/etc/x": b"x"}, self.manifest({}), "absolute"),
            "not a save file": self.bad_zip({"hookshot.exe": b"x"}, self.manifest({}), "exe"),
            "no manifest": self.bad_zip(good, None, "nomanifest"),
        }
        for why, path in cases.items():
            with self.subTest(why):
                code, _, err = self.run_cli("import", str(path))
                self.assertEqual(code, 1, why)
        tampered = dict(good)
        m = self.manifest(good)
        tampered["slot_00/progress.sav"] = b"q"
        code, _, err = self.run_cli("import", str(self.bad_zip(tampered, m)))
        self.assertEqual(code, 1)
        self.assertIn("SHA-256 differs", err)
        extra = dict(good, **{"option.sav": b"o"})
        code, _, err = self.run_cli("import", str(self.bad_zip(extra, self.manifest(good))))
        self.assertEqual(code, 1)
        self.assertEqual(zot.snapshots(str(self.store)) if self.store.exists() else [], [])
        if self.store.exists():
            self.assertEqual([p.name for p in self.store.iterdir()], [])

    def test_prune_keeps_the_newest_of_each_profile(self):
        ids = [self.snap("n%d" % i) for i in range(3)]
        code, out, _ = self.run_cli("prune", "--keep", "1", "--dry-run")
        self.assertEqual(code, 0)
        self.assertEqual(len(zot.snapshots(str(self.store))), 3)
        code, out, _ = self.run_cli("prune", "--keep", "1")
        self.assertEqual(code, 0)
        self.assertEqual([n for n, _, _, _ in zot.snapshots(str(self.store))], ids[-1:])

    def test_list_shows_snapshots(self):
        ident = self.snap("shown")
        code, out, _ = self.run_cli("list")
        self.assertEqual(code, 0)
        self.assertIn(ident, out)
        self.assertIn("2 slot(s)", out)


if __name__ == "__main__":
    unittest.main()
