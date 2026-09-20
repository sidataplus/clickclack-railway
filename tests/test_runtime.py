"""Offline contract tests. FakeCLI is NOT the upstream Go implementation."""
from __future__ import annotations
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("cc_runtime", ROOT / "runtime/cc_runtime.py")
cc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cc)

# Minimal, explicitly synthetic fixture using inspected upstream table names.
SCHEMA = """
CREATE TABLE users (id TEXT PRIMARY KEY, display_name TEXT NOT NULL, kind TEXT NOT NULL DEFAULT 'human', created_at TEXT NOT NULL);
CREATE TABLE identities (id TEXT PRIMARY KEY, user_id TEXT NOT NULL, email TEXT NOT NULL);
CREATE TABLE workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE workspace_members (workspace_id TEXT, user_id TEXT, role TEXT, PRIMARY KEY(workspace_id,user_id));
CREATE TABLE test_only_passwords (user_id TEXT PRIMARY KEY, digest TEXT);
"""
ENV = {"CC_BOOTSTRAP_EMAIL": "owner@example.com", "CC_BOOTSTRAP_NAME": "Owner", "CC_BOOTSTRAP_PASSWORD": "synthetic-test-secret-123456"}


class FakeCLI:
    def __init__(self):
        self.calls = []
        self.fail_password = False
        self.bad_id = False
        self.before_return = None

    def __call__(self, args, data, password=None):
        self.calls.append((list(args), str(data), password))
        def option(name):
            return args[args.index(name) + 1]
        db = sqlite3.connect(data / "clickclack.db")
        try:
            if args[:2] == ["admin", "bootstrap"]:
                db.executescript(SCHEMA)
                db.execute("INSERT INTO users VALUES ('usr_owner',?,'human','2026')", (option("--name"),))
                db.execute("INSERT INTO identities VALUES ('idn_owner','usr_owner',?)", (option("--email"),))
                db.execute("INSERT INTO workspaces VALUES ('wsp_main','ClickClack','2026')")
                db.execute("INSERT INTO workspace_members VALUES ('wsp_main','usr_owner','owner')")
                db.commit()
                return "unexpected output" if self.bad_id else "usr_owner"
            if args[:3] == ["admin", "user", "create"]:
                uid = "usr_new_" + str(db.execute("SELECT COUNT(*) FROM users").fetchone()[0])
                db.execute("INSERT INTO users VALUES (?,?,'human','2026')", (uid, option("--name")))
                db.execute("INSERT INTO identities VALUES (?,?,?)", ("idn_"+uid, uid, option("--email")))
                db.execute("INSERT INTO workspace_members VALUES (?,?,'member')", (option("--workspace"), uid))
                db.commit()
                return uid
            if args[:3] == ["admin", "user", "set-password"]:
                if self.fail_password:
                    raise cc.SetupError("Synthetic command failure")
                uid = option("--user")
                # This test fixture is not used in the image and is not an auth implementation.
                db.execute("INSERT OR REPLACE INTO test_only_passwords VALUES (?,?)", (uid, hashlib.sha256(password.encode()).hexdigest()))
                db.commit()
                if self.before_return:
                    self.before_return()
                return "password set"
            raise AssertionError(args)
        finally:
            db.close()


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data = Path(self.tmp.name)
        self.cli = FakeCLI()

    def tearDown(self):
        self.tmp.cleanup()

    def seed(self):
        self.assertTrue(cc.bootstrap(self.data, ENV, self.cli))

    def test_first_boot_creates_one_owner(self):
        self.seed()
        with cc.db_reader(self.data / "clickclack.db") as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM users").fetchone()[0], 1)
            self.assertEqual(db.execute("SELECT role FROM workspace_members").fetchone()[0], "owner")
        self.assertEqual(len(self.cli.calls), 2)

    def test_restart_does_not_reset_password(self):
        self.seed()
        before = (self.data / "clickclack.db").read_bytes()
        self.assertFalse(cc.bootstrap(self.data, {**ENV, "CC_BOOTSTRAP_PASSWORD": "new-but-ignored-1234"}, self.cli))
        self.assertEqual(len(self.cli.calls), 2)
        self.assertEqual(before, (self.data / "clickclack.db").read_bytes())

    def test_restart_does_not_need_bootstrap_environment(self):
        self.seed()
        self.assertFalse(cc.bootstrap(self.data, {}, self.cli))

    def test_changed_email_does_not_create_another_owner(self):
        self.seed()
        self.assertFalse(cc.bootstrap(self.data, {**ENV, "CC_BOOTSTRAP_EMAIL": "other@example.com"}, self.cli))
        self.assertEqual(len(self.cli.calls), 2)

    def test_password_failure_does_not_publish_partial_database(self):
        self.cli.fail_password = True
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertFalse((self.data / "clickclack.db").exists())
        self.assertEqual(list(self.data.glob(".cc-first-boot-*")), [])

    def test_password_failure_is_retryable(self):
        self.cli.fail_password = True
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, ENV, self.cli)
        self.cli.fail_password = False
        self.seed()

    def test_unexpected_bootstrap_output_is_rejected(self):
        self.cli.bad_id = True
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertFalse((self.data / "clickclack.db").exists())

    def test_does_not_overwrite_corrupt_database(self):
        path = self.data / "clickclack.db"
        path.write_bytes(b"do not overwrite")
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertEqual(path.read_bytes(), b"do not overwrite")
        self.assertFalse(self.cli.calls)

    def test_existing_empty_user_table_is_not_replaced(self):
        db = sqlite3.connect(self.data / "clickclack.db")
        db.executescript(SCHEMA)
        db.close()
        with self.assertRaisesRegex(cc.SetupError, "no users"):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertFalse(self.cli.calls)

    def test_orphan_wal_is_not_ignored(self):
        (self.data / "clickclack.db-wal").write_bytes(b"journal")
        with self.assertRaisesRegex(cc.SetupError, "journals"):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertFalse(self.cli.calls)

    def test_database_symlink_is_rejected(self):
        target = self.data / "important.db"
        target.write_bytes(b"preserve")
        (self.data / "clickclack.db").symlink_to(target)
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertEqual(target.read_bytes(), b"preserve")

    def test_late_database_creation_is_not_overwritten(self):
        self.cli.before_return = lambda: (self.data / "clickclack.db").write_bytes(b"other writer")
        with self.assertRaisesRegex(cc.SetupError, "appeared"):
            cc.bootstrap(self.data, ENV, self.cli)
        self.assertEqual((self.data / "clickclack.db").read_bytes(), b"other writer")

    def test_missing_password_fails_before_cli(self):
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, {"CC_BOOTSTRAP_EMAIL": "a@example.com"}, self.cli)
        self.assertFalse(self.cli.calls)

    def test_invalid_email_fails_before_cli(self):
        with self.assertRaises(cc.SetupError):
            cc.bootstrap(self.data, {**ENV, "CC_BOOTSTRAP_EMAIL": "bad"}, self.cli)
        self.assertFalse(self.cli.calls)

    def test_password_not_in_process_arguments(self):
        self.seed()
        self.assertNotIn(ENV["CC_BOOTSTRAP_PASSWORD"], json.dumps([x[0] for x in self.cli.calls]))
        self.assertEqual(self.cli.calls[1][2], ENV["CC_BOOTSTRAP_PASSWORD"])

    def test_database_permissions(self):
        self.seed()
        self.assertEqual((self.data / "clickclack.db").stat().st_mode & 0o777, 0o600)

    def test_add_user_to_only_workspace(self):
        self.seed()
        uid = cc.add_user(self.data, "Alice@Example.com", "Alice", "alice-temporary-secret-123", cli=self.cli)
        with cc.db_reader(self.data / "clickclack.db") as db:
            self.assertEqual(db.execute("SELECT role FROM workspace_members WHERE user_id=?", (uid,)).fetchone()[0], "member")
            self.assertEqual(db.execute("SELECT email FROM identities WHERE user_id=?", (uid,)).fetchone()[0], "alice@example.com")

    def test_add_duplicate_never_resets_account(self):
        self.seed()
        calls = len(self.cli.calls)
        with self.assertRaisesRegex(cc.SetupError, "already uses"):
            cc.add_user(self.data, "OWNER@example.com", "Duplicate", "different-password-12345", cli=self.cli)
        self.assertEqual(len(self.cli.calls), calls)

    def test_multiple_workspaces_require_selection(self):
        self.seed()
        with sqlite3.connect(self.data / "clickclack.db") as db:
            db.execute("INSERT INTO workspaces VALUES ('wsp_second','Other','2026')")
        with self.assertRaisesRegex(cc.SetupError, "--workspace"):
            cc.add_user(self.data, "a@example.com", "Alice", "alice-temporary-secret-123", cli=self.cli)
        uid = cc.add_user(self.data, "a@example.com", "Alice", "alice-temporary-secret-123", "wsp_second", self.cli)
        with cc.db_reader(self.data / "clickclack.db") as db:
            self.assertEqual(db.execute("SELECT workspace_id FROM workspace_members WHERE user_id=?", (uid,)).fetchone()[0], "wsp_second")

    def test_unknown_workspace_fails_before_creating_user(self):
        self.seed()
        calls = len(self.cli.calls)
        with self.assertRaises(cc.SetupError):
            cc.add_user(self.data, "a@example.com", "Alice", "alice-temporary-secret-123", "wsp_no", self.cli)
        self.assertEqual(calls, len(self.cli.calls))

    def test_partial_add_user_reports_explicit_recovery(self):
        self.seed()
        self.cli.fail_password = True
        with self.assertRaisesRegex(cc.SetupError, "cc-admin set-password --user usr_new_1"):
            cc.add_user(self.data, "a@example.com", "Alice", "alice-temporary-secret-123", cli=self.cli)

    def test_railway_missing_volume_is_rejected(self):
        with self.assertRaisesRegex(cc.SetupError, "Attach a Railway volume"):
            cc.data_path({"RAILWAY_ENVIRONMENT_ID": "env", "CLICKCLACK_DATA": str(self.data)})

    def test_railway_matching_volume_accepted(self):
        self.assertEqual(cc.data_path({"RAILWAY_ENVIRONMENT_ID": "env", "RAILWAY_VOLUME_MOUNT_PATH": str(self.data), "CLICKCLACK_DATA": str(self.data)}), self.data)

    def test_railway_mismatched_volume_rejected(self):
        with self.assertRaises(cc.SetupError):
            cc.data_path({"RAILWAY_ENVIRONMENT_ID": "env", "RAILWAY_VOLUME_MOUNT_PATH": "/other", "CLICKCLACK_DATA": str(self.data)})

    def test_dev_auth_rejected(self):
        with self.assertRaisesRegex(cc.SetupError, "forbidden"):
            cc.effective_environment({"CLICKCLACK_DEV_BOOTSTRAP": "true"})

    def test_env_strips_all_bootstrap_values(self):
        effective = cc.effective_environment({**ENV, "GITHUB_TOKEN": "unrelated"})
        for key in cc.BOOTSTRAP_KEYS:
            self.assertNotIn(key, effective)
        self.assertEqual(effective["GITHUB_TOKEN"], "unrelated")

    def test_railway_domain_sets_https_origin(self):
        self.assertEqual(cc.effective_environment({"RAILWAY_PUBLIC_DOMAIN": "cc.up.railway.app"})["CLICKCLACK_PUBLIC_URL"], "https://cc.up.railway.app")

    def test_custom_domain_wins(self):
        env = cc.effective_environment({"RAILWAY_PUBLIC_DOMAIN": "cc.up.railway.app", "CLICKCLACK_PUBLIC_URL": "https://chat.example.com/"})
        self.assertEqual(env["CLICKCLACK_PUBLIC_URL"], "https://chat.example.com")

    def test_bad_origins_rejected(self):
        for url in ["http://example.com", "https://u:p@example.com", "https://example.com/path", "https://example.com?x=1", "https://example.com#x"]:
            with self.subTest(url=url), self.assertRaises(cc.SetupError):
                cc.effective_environment({"CLICKCLACK_PUBLIC_URL": url})

    def test_bad_ports_rejected(self):
        for port in ["0", "65536", "abc", ":8080", "8080;false"]:
            with self.subTest(port=port), self.assertRaises(cc.SetupError):
                cc.effective_environment({"PORT": port})

    def test_generated_secret_not_printed_to_non_tty(self):
        with patch.object(cc.sys, "stdout", io.StringIO()), self.assertRaises(cc.SetupError):
            cc.input_password(False, True)

    def test_template_expression_is_not_a_password(self):
        with self.assertRaises(cc.SetupError):
            cc.validate_password('${{secret(32)}}not-evaluated')

    def test_sql_reader_is_readonly(self):
        self.seed()
        with cc.db_reader(self.data / "clickclack.db") as db:
            with self.assertRaises(sqlite3.OperationalError):
                db.execute("DELETE FROM users")

    def test_shell_metacharacters_are_plain_password_data(self):
        secret = "safe;$(touch x)|&'\"password-123"
        self.assertEqual(cc.validate_password(secret), secret)

    def test_cli_subprocess_uses_stdin_and_scrubbed_env(self):
        result = type("Result", (), {"returncode": 0, "stdout": "password set"})()
        with patch.dict(os.environ, ENV), patch.object(cc.subprocess, "run", return_value=result) as run:
            cc.run_cli(["admin", "user", "set-password", "--user", "usr_owner"], self.data, ENV["CC_BOOTSTRAP_PASSWORD"])
        self.assertNotIn(ENV["CC_BOOTSTRAP_PASSWORD"], repr(run.call_args.args))
        self.assertEqual(run.call_args.kwargs["input"], ENV["CC_BOOTSTRAP_PASSWORD"])
        self.assertNotIn("CC_BOOTSTRAP_PASSWORD", run.call_args.kwargs["env"])
        self.assertNotIn("shell", run.call_args.kwargs)

    def test_subprocess_error_does_not_echo_output(self):
        result = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "a-secret"})()
        with patch.object(cc.subprocess, "run", return_value=result), self.assertRaises(cc.SetupError) as error:
            cc.run_cli(["admin", "bootstrap"], self.data)
        self.assertNotIn("a-secret", str(error.exception))


if __name__ == "__main__":
    unittest.main()
