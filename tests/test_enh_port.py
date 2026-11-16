"""scripts/enhanced/port_to.py, game-free: the Enhanced layer carried from a made-up source repository to a made-up
target fork that shares its history (as Longshot shares Hookshot's), in temp folders only.

- the product profiles: both load, and hookshot.json gives back this repository's own product files unchanged;
- a dry run changes nothing in the target; --apply copies the layer, makes the product files from the profile, applies
  the hooks with the target's own edits kept, skips a hooked file the target lacks, never ports CLAUDE.md or docs, and
  writes the manifest;
- the same commit again is a no-op; a later commit ports only what changed since (a layer file gone is removed, a new
  hook applied alone); a hook against a line the target changed is a conflict (exit 1);
- refused (exit 2): a target with changes, the source itself, a profile whose switch prefix is not the product's.

python -I -B tests/test_enh_port.py
"""
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
TOOL = ROOT / "scripts" / "enhanced" / "port_to.py"
spec = importlib.util.spec_from_file_location("port_to", TOOL)
port = importlib.util.module_from_spec(spec)
spec.loader.exec_module(port)
ENV = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.invalid", GIT_COMMITTER_NAME="t",
           GIT_COMMITTER_EMAIL="t@example.invalid")
MAIN = "".join("line %d of the upstream file\n" % i for i in range(1, 21))


def git(repo, *args):
    r = subprocess.run(["git", "-C", str(repo)] + list(args), capture_output=True, text=True, env=ENV)
    assert r.returncode == 0, "git %s: %s" % (" ".join(args), r.stderr)
    return r.stdout.strip()


def write(repo, rel, text):
    p = Path(repo, *rel.split("/"))
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8", newline="")


def commit(repo, msg):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", msg)
    return git(repo, "rev-parse", "HEAD")


class Port(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="enh-port-test-"))
        self.src, self.dst = self.tmp / "src", self.tmp / "dst"
        self.src.mkdir()
        git(self.src, "init", "-q", "-b", "main")
        git(self.src, "config", "core.autocrlf", "false")
        write(self.src, "host/hos_main.c", MAIN)
        write(self.src, "readme.md", "upstream readme\n")
        commit(self.src, "upstream")
        git(self.src, "tag", "base")
        # the fork's work: the layer, the product files, hooks, and what is never ported
        write(self.src, "host/enh_product.h", (ROOT / "host" / "enh_product.h").read_text(encoding="utf-8"))
        write(self.src, "scripts/enhanced/enh_product.py",
              (ROOT / "scripts" / "enhanced" / "enh_product.py").read_text(encoding="utf-8"))
        write(self.src, "host/enh_old.c", "/* a feature */\n")
        write(self.src, "gpu/vk/enh_menu_x.inc", "// rows\n")
        write(self.src, "tests/test_enh_x.py", "print('ok')\n")
        write(self.src, "host/hos_main.c", MAIN.replace("line 10 of", "hos_enh_hook();   /* (enhanced) Hookshot */\nline 10 of"))
        write(self.src, "readme.md", "upstream readme\n| a row |\n")
        write(self.src, "CLAUDE.md", "fork rules\n")
        write(self.src, "docs/enhanced/X.md", "doc\n")
        self.first = commit(self.src, "enhanced")
        # the other fork: the same history to base, then its own edits (one far from the hook), no readme.md
        git(self.tmp, "clone", "-q", "--no-local", "-c", "core.autocrlf=false", str(self.src), str(self.dst))
        git(self.dst, "checkout", "-q", "-b", "other", "base")
        write(self.dst, "host/hos_main.c", MAIN.replace("line 1 of", "line 1 (the other fork's) of"))
        os.remove(self.dst / "readme.md")
        commit(self.dst, "the other fork")
        git(self.dst, "remote", "remove", "origin")

    def tearDown(self):
        subprocess.run(["git", "-C", str(self.dst), "worktree", "prune"], capture_output=True)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_tool(self, *args, target=None, ref="main"):
        cmd = [sys.executable, "-I", str(TOOL), str(target or self.dst), "--product", "longshot", "--ref", ref,
               "--base", "base", "--source", str(self.src)] + list(args)
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV)
        return r.returncode, r.stdout, r.stderr

    def test_profiles(self):
        for name in ("hookshot", "longshot"):
            port.load_profile(name)
        p = port.load_profile("hookshot")
        for rel, make in ((port.PRODUCT_C, port.product_c), (port.PRODUCT_PY, port.product_py)):
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertEqual(make(text, p), text, "hookshot.json does not match %s" % rel)
        bad = dict(p, env_prefix="OTHER_ENH_")
        path = self.tmp / "bad.json"
        path.write_text(json.dumps(bad), encoding="utf-8")
        with self.assertRaises(port.Fail):
            port.load_profile(str(path))

    def test_dry_run_then_apply(self):
        before = git(self.dst, "rev-parse", "HEAD")
        code, out, err = self.run_tool()
        self.assertEqual(code, 0, out + err)
        self.assertIn("Dry run", out)
        self.assertIn("host/enh_old.c", out)
        self.assertIn("readme.md", out)                       # (skipped: the target has none)
        self.assertEqual(git(self.dst, "status", "--porcelain"), "")
        self.assertFalse((self.dst / "host" / "enh_old.c").exists())
        self.assertEqual(git(self.dst, "rev-parse", "HEAD"), before)
        self.assertEqual(git(self.dst, "worktree", "list").count("\n"), 0, "the dry run's worktree was left")

        code, out, err = self.run_tool("--apply")
        self.assertEqual(code, 0, out + err)
        for rel in ("host/enh_old.c", "gpu/vk/enh_menu_x.inc", "tests/test_enh_x.py"):
            self.assertTrue((self.dst / rel).is_file(), rel)
        self.assertFalse((self.dst / "CLAUDE.md").exists())
        self.assertFalse((self.dst / "docs").exists())
        self.assertFalse((self.dst / "readme.md").exists())
        h = (self.dst / "host" / "enh_product.h").read_text(encoding="utf-8")
        self.assertIn('#define ENH_PRODUCT "Longshot"', h)
        self.assertIn('#define ENH_ENV_PREFIX "LONGSHOT_ENH_"', h)
        py = (self.dst / "scripts" / "enhanced" / "enh_product.py").read_text(encoding="utf-8")
        self.assertIn('SAVES_SCRIPT = "longshot_saves.py"', py)
        self.assertIn('"longshot_version.txt"', py)
        main = (self.dst / "host" / "hos_main.c").read_text(encoding="utf-8")
        self.assertIn("hos_enh_hook();", main)
        self.assertIn("line 1 (the other fork's) of", main)
        self.assertIn("review", out)                          # (the hook line names Hookshot)
        m = json.loads((self.dst / "scripts" / "enhanced" / "ported_from.json").read_text(encoding="utf-8"))
        self.assertEqual(m["source_commit"], self.first)
        self.assertIn("host/enh_old.c", m["layer"])
        commit(self.dst, "port 1")

        code, out, _ = self.run_tool("--apply")
        self.assertEqual(code, 0)
        self.assertIn("already ported", out)

        # a later commit: a layer file gone, one new, one more hook
        os.remove(self.src / "host" / "enh_old.c")
        write(self.src, "host/enh_new.c", "/* another */\n")
        write(self.src, "host/hos_main.c", (self.src / "host" / "hos_main.c").read_text(encoding="utf-8")
              .replace("line 16 of", "hos_enh_second();   /* (enhanced) */\nline 16 of"))
        second = commit(self.src, "more")
        code, out, err = self.run_tool("--apply")
        self.assertEqual(code, 0, out + err)
        self.assertFalse((self.dst / "host" / "enh_old.c").exists())
        self.assertTrue((self.dst / "host" / "enh_new.c").is_file())
        main = (self.dst / "host" / "hos_main.c").read_text(encoding="utf-8")
        self.assertEqual(main.count("hos_enh_hook();"), 1)
        self.assertIn("hos_enh_second();", main)
        m = json.loads((self.dst / "scripts" / "enhanced" / "ported_from.json").read_text(encoding="utf-8"))
        self.assertEqual((m["source_commit"], m["base"]), (second, self.first))

    def test_conflict(self):
        write(self.dst, "host/hos_main.c", MAIN.replace("line 10 of", "line 10 (changed by the other fork) of"))
        commit(self.dst, "an edit where the hook goes")
        code, out, err = self.run_tool()
        self.assertEqual(code, 1, out + err)
        self.assertIn("conflict", out)
        self.assertEqual(git(self.dst, "status", "--porcelain"), "")
        code, out, err = self.run_tool("--apply")
        self.assertEqual(code, 1, out + err)
        self.assertIn("host/hos_main.c", out.split("conflict", 1)[1])

    def test_refused(self):
        write(self.dst, "host/hos_main.c", "changed\n")
        code, _, err = self.run_tool("--apply")
        self.assertEqual(code, 2)
        self.assertIn("changes to tracked files", err)
        code, _, err = self.run_tool(target=self.src)
        self.assertEqual(code, 2)
        self.assertIn("this repository", err)


if __name__ == "__main__":
    unittest.main()
