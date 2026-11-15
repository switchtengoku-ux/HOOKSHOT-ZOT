"""scripts/enhanced/zot_graphics.py, game-free: graphics profiles saved from and put back into a made-up
hookshot_options.ini in a temp folder; the running-game check replaced.

- GRAPHICS_KEYS is exactly the Insert menu's Graphics rows as gpu/vk/vk_menu.cpp saves them (its rows and ini_key);
- save keeps only the Graphics lines; apply changes only them, keeps every other line and its order, appends missing
  keys, merges a repeated key, backs the file up first, and leaves the file alone on a dry run or while a game runs;
- names and values that are not a profile's are refused.

python -I -B tests/test_enh_graphics.py
"""
import contextlib
import importlib.util
import io
from pathlib import Path
import re
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("zot_graphics", ROOT / "scripts" / "enhanced" / "zot_graphics.py")
zg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(zg)

OPTIONS = """quality_preset=0
ultrawide=1
output_res=2560x1440
dlss=2
sharpness=60
frame_rate_cap=1
hdr=0
volume=100
enh_music_volume=150
pad_a=0x10
key_a=32
microphone_device=Microphone (DualSense)
"""


def menu_graphics_keys():
    menu = (ROOT / "gpu" / "vk" / "vk_menu.cpp").read_text(encoding="utf-8")
    body = menu[menu.index("const char* ini_key(const Row& r) {"):]
    body = body[:body.index("\n}\n")]
    by_field = dict(re.findall(r'r\.value == &opts\.(\w+)\) return "([^"]+)"', body))
    keys = []
    for name, field in re.findall(r'\{TAB_GRAPHICS, "([^"]+)", &opts\.(\w+)', menu):
        keys.append(by_field.get(field) or name.lower().replace(" ", "_"))
    return keys


class GraphicsProfileTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.game = self.root / "game"
        self.game.mkdir()
        self.ini = self.game / "hookshot_options.ini"
        self.ini.write_text(OPTIONS, encoding="utf-8")
        self.store = self.root / "store"
        self.running = mock.patch.object(zg.oot, "running_games", return_value=[])
        self.running.start()

    def tearDown(self):
        self.running.stop()
        self.tmp.cleanup()

    def cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = zg.main(["--store", str(self.store)] + list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_keys_are_the_menus_graphics_rows(self):
        self.assertEqual(list(zg.GRAPHICS_KEYS), menu_graphics_keys())

    def test_save_keeps_only_graphics(self):
        code, _, err = self.cli("save", "4K", "--game", str(self.game))
        self.assertEqual(code, 0, err)
        text = (self.store / "4K.ini").read_text(encoding="utf-8")
        self.assertIn("output_res=2560x1440", text)
        self.assertNotIn("volume", text)
        self.assertNotIn("pad_a", text)
        code, _, err = self.cli("save", "4K", "--game", str(self.game))
        self.assertEqual(code, 1, "an existing profile is not overwritten without --replace")
        self.assertEqual(self.cli("save", "4K", "--game", str(self.game), "--replace")[0], 0)

    def test_apply_changes_graphics_lines_only(self):
        self.cli("save", "before", "--game", str(self.game))
        changed = OPTIONS.replace("output_res=2560x1440", "output_res=3440x1440").replace("dlss=2", "dlss=0")
        changed = changed.replace("volume=100", "volume=40") + "dlss=5\n"   # (a repeated key: the last one counts)
        self.ini.write_text(changed, encoding="utf-8")
        code, out, err = self.cli("apply", "before", "--game", str(self.game))
        self.assertEqual(code, 0, err)
        lines = self.ini.read_text(encoding="utf-8").splitlines()
        self.assertIn("output_res=2560x1440", lines)
        self.assertEqual([l for l in lines if l.startswith("dlss=")], ["dlss=2"])
        self.assertIn("volume=40", lines)                      # (not a Graphics line: as the player left it)
        self.assertIn("microphone_device=Microphone (DualSense)", lines)
        self.assertLess(lines.index("quality_preset=0"), lines.index("volume=40"))   # (the order kept)
        backups = list((self.store / "backups").iterdir())
        self.assertEqual(len(backups), 1)
        self.assertIn("output_res=3440x1440", backups[0].read_text(encoding="utf-8"))

    def test_apply_appends_missing_keys(self):
        (self.store).mkdir()
        (self.store / "full.ini").write_text("vram_budget=5\nanisotropic_filtering=4\n", encoding="utf-8")
        self.assertEqual(self.cli("apply", "full", "--game", str(self.game))[0], 0)
        lines = self.ini.read_text(encoding="utf-8").splitlines()
        self.assertEqual(lines[-2:], ["anisotropic_filtering=4", "vram_budget=5"])   # (the menu's order)

    def test_dry_run_and_running_game_change_nothing(self):
        self.cli("save", "p", "--game", str(self.game))
        self.ini.write_text(OPTIONS.replace("hdr=0", "hdr=2"), encoding="utf-8")
        before = self.ini.read_text(encoding="utf-8")
        code, out, _ = self.cli("apply", "p", "--game", str(self.game), "--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("hdr", out)
        self.assertEqual(self.ini.read_text(encoding="utf-8"), before)
        with mock.patch.object(zg.oot, "running_games", return_value=["Hookshot"]):
            code, _, err = self.cli("apply", "p", "--game", str(self.game))
        self.assertEqual(code, 1)
        self.assertIn("close Hookshot", err)
        self.assertEqual(self.ini.read_text(encoding="utf-8"), before)

    def test_bad_names_and_values(self):
        self.assertEqual(self.cli("save", "../x", "--game", str(self.game))[0], 1)
        self.store.mkdir()
        (self.store / "bad.ini").write_text("output_res=$(evil)\n", encoding="utf-8")
        code, _, err = self.cli("apply", "bad", "--game", str(self.game))
        self.assertEqual(code, 1)
        self.assertEqual(self.ini.read_text(encoding="utf-8"), OPTIONS)

    def test_list_show_diff_delete(self):
        self.cli("save", "Perf 120", "--game", str(self.game))
        code, out, _ = self.cli("list")
        self.assertIn("Perf 120", out)
        self.assertIn("output_res=2560x1440", self.cli("show", "Perf 120")[1])
        self.assertIn("already", self.cli("diff", "Perf 120", "--game", str(self.game))[1])
        self.assertEqual(self.cli("delete", "Perf 120")[0], 0)
        self.assertEqual(self.cli("show", "Perf 120")[0], 1)


if __name__ == "__main__":
    unittest.main()
