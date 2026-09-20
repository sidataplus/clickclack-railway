"""Offline package and author-tool checks. No Docker/Railway calls are made."""
from __future__ import annotations
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("author", ROOT / "scripts/author.py")
author = importlib.util.module_from_spec(spec)
spec.loader.exec_module(author)

class PackageTests(unittest.TestCase):
    def test_upstream_revision_is_consistently_pinned(self):
        lock = json.loads((ROOT / "upstream.lock.json").read_text())
        content = (ROOT / "Dockerfile").read_text()
        self.assertEqual(content.count("ARG CLICKCLACK_UPSTREAM_REF=" + lock["commit"]), 3)
        for key in ("node_image", "go_image", "runtime_image"):
            self.assertIn(lock[key], content)
        self.assertIn("pnpm@" + lock["pnpm"], content)
        self.assertFalse(lock["source_modifications"])

    def test_single_service_volume_spec(self):
        spec = json.loads((ROOT / "template/settings.json").read_text())
        self.assertEqual(spec["service"]["replicas"], 1)
        self.assertEqual(spec["service"]["volume"]["mountPath"], "/app/data")
        self.assertFalse(spec["service"]["serverless"])
        self.assertEqual(spec["service"]["healthcheck"]["path"], "/readyz")
        self.assertIsNone(spec["service"]["preDeployCommand"])

    def test_template_does_not_contain_author_credentials(self):
        values = json.loads((ROOT / "template/settings.json").read_text())["variables"]
        self.assertIsNone(values["CC_BOOTSTRAP_EMAIL"]["default"])
        self.assertTrue(values["CC_BOOTSTRAP_EMAIL"]["required"])
        self.assertTrue(values["CC_BOOTSTRAP_PASSWORD"]["templateDefault"].startswith("${{secret(32,"))

    def test_iac_has_no_random_secret_generation(self):
        content = (ROOT / ".railway/railway.ts").read_text()
        self.assertIn('from "railway/iac"', content)
        self.assertIn('volumeMounts: { "/app/data": data }', content)
        self.assertNotIn("Math.random", content)
        self.assertNotIn("secret(", content)
        self.assertFalse((ROOT / "railway.json").exists())
        self.assertFalse((ROOT / "railway.toml").exists())

    def test_git_and_docker_ignore_private_author_config(self):
        self.assertIn(".local/", (ROOT / ".gitignore").read_text())
        self.assertIn(".local", (ROOT / ".dockerignore").read_text())

    def test_all_copy_sources_exist(self):
        for p in ("LICENSE", "NOTICE.md", "runtime/cc_runtime.py", "runtime/cc-entrypoint", "runtime/cc-admin"):
            self.assertTrue((ROOT/p).is_file(), p)

    def test_shell_syntax(self):
        result = subprocess.run(["sh", "-n", *map(str, [ROOT/"runtime/cc-entrypoint", ROOT/"runtime/cc-admin",
            ROOT/"scripts/create-template.sh", ROOT/"scripts/publish-template.sh"])], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_publish_refuses_without_release_acknowledgement(self):
        env = dict(os.environ)
        env.pop("CC_PUBLISH_CHECKLIST_PASSED", None)
        result = subprocess.run([str(ROOT/"scripts/publish-template.sh"), "candidate-id"],
                                capture_output=True, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(b"ACCEPTANCE", result.stderr)

    def test_docs_disclose_missing_web_invitation_and_live_validation(self):
        readme = (ROOT/"README.md").read_text()
        self.assertIn("does not add an Admin", readme)
        self.assertIn("have not been completed", readme)

class AuthorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/".local"/"author.json"
        self.state_patch = patch.object(author,"STATE",self.path)
        self.state_patch.start()
        self.addCleanup(self.state_patch.stop)

    def initialize(self):
        with patch.object(sys,"argv",["author.py","init","--repo","sample/clickclack-railway","--email","Owner@example.com"]), patch("builtins.print"):
            return author.main()

    def test_init_creates_private_random_secret(self):
        self.assertEqual(self.initialize(),0)
        data = json.loads(self.path.read_text())
        self.assertGreaterEqual(len(data["CC_BOOTSTRAP_PASSWORD"]),32)
        self.assertEqual(data["CC_BOOTSTRAP_EMAIL"],"owner@example.com")
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode),0o600)

    def test_init_does_not_rotate_on_repeat(self):
        self.initialize()
        original = self.path.read_bytes()
        with self.assertRaises(SystemExit), patch("sys.stderr"):
            self.initialize()
        self.assertEqual(self.path.read_bytes(),original)

    def test_plan_passes_secret_only_in_environment(self):
        self.initialize()
        secret = json.loads(self.path.read_text())["CC_BOOTSTRAP_PASSWORD"]
        with patch.object(sys,"argv",["author.py","plan"]), patch.object(author.shutil,"which",return_value="/mock/railway"), patch.object(author.subprocess,"run") as run, patch("builtins.print"):
            run.return_value.returncode=0
            self.assertEqual(author.main(),0)
        self.assertEqual(run.call_args.args[0],["railway","config","plan"])
        self.assertNotIn(secret,str(run.call_args.args))
        self.assertEqual(run.call_args.kwargs["env"]["CC_BOOTSTRAP_PASSWORD"],secret)

    def test_apply_keeps_confirmation(self):
        self.initialize()
        with patch.object(sys,"argv",["author.py","apply"]), patch.object(author.shutil,"which",return_value="/mock/railway"), patch.object(author.subprocess,"run") as run, patch("builtins.print"):
            run.return_value.returncode=0
            author.main()
        self.assertEqual(run.call_args.args[0],["railway","config","apply"])

    def test_broad_permissions_rejected(self):
        self.initialize()
        self.path.chmod(0o644)
        with patch.object(sys,"argv",["author.py","plan"]), self.assertRaises(SystemExit), patch("sys.stderr"):
            author.main()

    def test_unsafe_repo_rejected(self):
        with patch.object(sys,"argv",["author.py","init","--repo","x; rm -rf /","--email","owner@example.com"]), self.assertRaises(SystemExit), patch("sys.stderr"):
            author.main()
        self.assertFalse(self.path.exists())

if __name__ == "__main__":
    unittest.main()
