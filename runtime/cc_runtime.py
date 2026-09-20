#!/usr/bin/env python3
"""Small deployment adapter. ClickClack remains the authentication authority.

Application records are written only by the pinned upstream CLI. SQLite is read
for safety checks; the only database copy is an offline first-boot snapshot.
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import getpass
import json
import os
from pathlib import Path
import re
import secrets
import sqlite3
import subprocess
import sys
import tempfile
from typing import Callable, Iterator, Mapping, Sequence
from urllib.parse import urlparse

APP_UID = 10001
APP_GID = 10001
BINARY = "/usr/local/bin/clickclack"
BOOTSTRAP_KEYS = ("CC_BOOTSTRAP_EMAIL", "CC_BOOTSTRAP_NAME", "CC_BOOTSTRAP_PASSWORD")


class SetupError(RuntimeError):
    """An actionable, secret-free deployment error."""


def clean_environment(env: Mapping[str, str]) -> dict[str, str]:
    return {k: v for k, v in env.items() if k not in BOOTSTRAP_KEYS}


def validate_email(value: str) -> str:
    value = value.strip().lower()
    if len(value) > 254 or not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", value):
        raise SetupError("Provide a valid email address, without a display name.")
    return value


def validate_password(value: str) -> str:
    if not 16 <= len(value) <= 256 or any(c in value for c in ("\x00", "\r", "\n")):
        raise SetupError("Password must contain 16–256 characters and no line breaks.")
    if "${{" in value or value in {"change-me", "REPLACE_ME", "your-password-here"}:
        raise SetupError("Replace the password placeholder; template expressions must be evaluated by Railway.")
    return value


def validate_name(value: str) -> str:
    value = value.strip()
    if not value or len(value) > 100 or any(ord(c) < 32 for c in value):
        raise SetupError("Display name must be 1–100 characters, without control characters.")
    return value


def run_cli(arguments: Sequence[str], data: Path, password: str | None = None) -> str:
    env = clean_environment(os.environ)
    # Every operation in this adapter has an explicit SQLite data location.
    env.pop("CLICKCLACK_DB", None)
    env["CLICKCLACK_DATA"] = str(data)
    command = [BINARY, *arguments, "--data", str(data), "--db", ""]
    try:
        result = subprocess.run(command, input=password, text=True, capture_output=True,
                                env=env, timeout=120, check=False)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise SetupError("ClickClack admin command could not complete; check the binary and volume.") from exc
    if result.returncode:
        # Do not echo arbitrary subprocess output into deployment logs.
        raise SetupError(f"ClickClack admin operation failed (exit {result.returncode}); inspect the volume and upstream CLI compatibility.")
    return result.stdout.strip()


def read_db(path: Path) -> sqlite3.Connection:
    if path.is_symlink() or not path.is_file():
        raise SetupError("Expected a regular existing SQLite database, not a symlink.")
    try:
        connection = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10)
        connection.execute("PRAGMA query_only=ON")
        connection.row_factory = sqlite3.Row
        return connection
    except sqlite3.Error as exc:
        raise SetupError("Cannot inspect the SQLite database; no data was replaced.") from exc


@contextlib.contextmanager
def db_reader(path: Path) -> Iterator[sqlite3.Connection]:
    db = read_db(path)
    try:
        yield db
    except sqlite3.Error as exc:
        raise SetupError("SQLite schema/read check failed; no automatic repair or replacement was attempted.") from exc
    finally:
        db.close()


@contextlib.contextmanager
def operation_lock(data: Path) -> Iterator[None]:
    flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(data / ".cc-admin.lock", flags, 0o600)
        with os.fdopen(fd, "w") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            yield
    except BlockingIOError as exc:
        raise SetupError("Another template admin operation is running; retry after it finishes.") from exc


def sync_directory(directory: Path) -> None:
    fd = os.open(directory, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def bootstrap(data: Path, env: Mapping[str, str], cli: Callable = run_cli) -> bool:
    """Publish a fully provisioned DB once. Return False for existing instances.

    No HTTP server runs during this step. A crash before publication leaves the
    live DB absent, so retry is safe. Publication uses a no-overwrite hard link.
    An existing database is NEVER overwritten, even when it is empty/corrupt.
    """
    db_path = data / "clickclack.db"
    with operation_lock(data):
        if db_path.exists() or db_path.is_symlink():
            with db_reader(db_path) as db:
                count = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            if count == 0:
                raise SetupError("Existing database has no users. Refusing to replace it; use the documented operator recovery procedure.")
            return False
        # Orphan journals can indicate an interrupted restore. Do not discard them.
        if any((data / ("clickclack.db" + suffix)).exists() for suffix in ("-wal", "-shm", "-journal")):
            raise SetupError("Found SQLite journals without their database. Restore the database before starting.")
        email = validate_email(env.get("CC_BOOTSTRAP_EMAIL", ""))
        name = validate_name(env.get("CC_BOOTSTRAP_NAME", "Admin"))
        password = validate_password(env.get("CC_BOOTSTRAP_PASSWORD", ""))
        with tempfile.TemporaryDirectory(prefix=".cc-first-boot-", dir=data) as temporary:
            stage = Path(temporary)
            user_id = cli(["admin", "bootstrap", "--name", name, "--email", email], stage)
            if not re.fullmatch(r"usr_[A-Za-z0-9_-]+", user_id):
                raise SetupError("Unexpected upstream bootstrap output; the live database was not published.")
            cli(["admin", "user", "set-password", "--user", user_id], stage, password)
            source = stage / "clickclack.db"
            snapshot = stage / "publish.db"
            with db_reader(source) as db:
                if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] != 1:
                    raise SetupError("Fresh bootstrap did not create exactly one user.")
                owners = db.execute("SELECT COUNT(*) FROM workspace_members WHERE user_id=? AND role='owner'", (user_id,)).fetchone()[0]
                if owners != 1:
                    raise SetupError("Fresh bootstrap did not create exactly one owner membership.")
                destination = sqlite3.connect(snapshot)
                try:
                    db.backup(destination)
                    destination.execute("PRAGMA journal_mode=DELETE")
                    if destination.execute("PRAGMA quick_check").fetchone()[0] != "ok":
                        raise SetupError("Fresh SQLite snapshot failed integrity validation.")
                finally:
                    destination.close()
            os.chmod(snapshot, 0o600)
            with snapshot.open("rb") as handle:
                os.fsync(handle.fileno())
            try:
                os.link(snapshot, db_path)
            except FileExistsError as exc:
                raise SetupError("A database appeared during bootstrap; refusing to overwrite it.") from exc
            sync_directory(data)
        return True


def data_path(env: Mapping[str, str]) -> Path:
    path = Path(env.get("CLICKCLACK_DATA", "/app/data"))
    if not path.is_absolute() or path == Path("/") or path.is_symlink():
        raise SetupError("CLICKCLACK_DATA must be an absolute, non-root directory, not a symlink.")
    if env.get("RAILWAY_ENVIRONMENT_ID"):
        mount = env.get("RAILWAY_VOLUME_MOUNT_PATH", "")
        if not mount or Path(mount).resolve() != path.resolve():
            raise SetupError("Attach a Railway volume at CLICKCLACK_DATA (default /app/data) before deploying.")
    return path


def prepare_data_and_drop_privileges(data: Path) -> None:
    os.umask(0o077)
    data.mkdir(parents=True, exist_ok=True)
    if os.geteuid() == 0:
        # A newly mounted Railway volume is root-owned. Only its top-level
        # directory is adjusted, not an unbounded recursive tree on every boot.
        os.chown(data, APP_UID, APP_GID)
        os.chmod(data, 0o700)
        os.setgroups([])
        os.setgid(APP_GID)
        os.setuid(APP_UID)
    if not os.access(data, os.R_OK | os.W_OK | os.X_OK):
        raise SetupError("Data directory is not writable by UID 10001; repair volume ownership.")


def effective_environment(env: Mapping[str, str]) -> dict[str, str]:
    result = clean_environment(env)
    if env.get("CLICKCLACK_DEV_BOOTSTRAP", "false").lower() not in {"false", "0", ""}:
        raise SetupError("Dev authentication is forbidden in this public template.")
    result["CLICKCLACK_DEV_BOOTSTRAP"] = "false"
    result.setdefault("CLICKCLACK_PASSWORD_AUTH_ENABLED", "true")
    result.setdefault("CLICKCLACK_METRICS_ENABLED", "false")
    port = env.get("PORT", "8080")
    if not port.isdecimal() or not 1 <= int(port) <= 65535:
        raise SetupError("PORT must be an integer from 1 to 65535.")
    result["PORT"] = port
    public_url = env.get("CLICKCLACK_PUBLIC_URL", "")
    if not public_url and env.get("RAILWAY_PUBLIC_DOMAIN"):
        public_url = "https://" + env["RAILWAY_PUBLIC_DOMAIN"]
    if public_url:
        parsed = urlparse(public_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
            raise SetupError("CLICKCLACK_PUBLIC_URL must be an HTTPS origin without a path or credentials.")
        result["CLICKCLACK_PUBLIC_URL"] = public_url.rstrip("/")
    return result


def start() -> None:
    env = dict(os.environ)
    final_env = effective_environment(env)
    data = data_path(env)
    mode = env.get("CC_BOOTSTRAP_MODE", "sqlite")
    if mode not in {"sqlite", "external"}:
        raise SetupError("CC_BOOTSTRAP_MODE must be sqlite or external.")
    if mode == "sqlite" and env.get("CLICKCLACK_DB", ""):
        raise SetupError("Default bootstrap manages SQLite in CLICKCLACK_DATA. External databases need CC_BOOTSTRAP_MODE=external and explicit migration/provisioning.")
    if mode == "external" and not env.get("CLICKCLACK_DB", ""):
        raise SetupError("External database mode requires CLICKCLACK_DB and an already provisioned owner.")
    prepare_data_and_drop_privileges(data)
    if mode == "sqlite":
        created = bootstrap(data, env)
        print("Owner initialized. Retrieve the generated password from Railway Variables; change it after sign-in."
              if created else "Existing database retained; bootstrap credentials were not reapplied.", file=sys.stderr, flush=True)
    final_env["CLICKCLACK_DATA"] = str(data)
    # Replace the Python initializer: the Go server is PID 1 and receives SIGTERM.
    os.execve(BINARY, [BINARY, "serve", "--addr", ":" + final_env["PORT"],
                       "--data", str(data), "--dev-bootstrap=false"], final_env)


def list_workspaces(data: Path) -> list[dict]:
    with db_reader(data / "clickclack.db") as db:
        return [dict(row) for row in db.execute("SELECT id, name FROM workspaces ORDER BY created_at, id")]


def resolve_workspace(data: Path, requested: str | None) -> str:
    workspaces = list_workspaces(data)
    if requested:
        if any(w["id"] == requested for w in workspaces):
            return requested
        raise SetupError("Workspace ID not found. Run cc-admin workspaces.")
    if len(workspaces) != 1:
        raise SetupError("Specify --workspace because this instance does not have exactly one workspace.")
    return workspaces[0]["id"]


def add_user(data: Path, email: str, name: str, password: str,
             workspace: str | None = None, cli: Callable = run_cli) -> str:
    email, name, password = validate_email(email), validate_name(name), validate_password(password)
    with operation_lock(data):
        workspace_id = resolve_workspace(data, workspace)
        with db_reader(data / "clickclack.db") as db:
            existing = db.execute("SELECT DISTINCT user_id FROM identities WHERE lower(email)=?", (email,)).fetchall()
        if existing:
            raise SetupError("An account already uses this email. No password or role was changed; use the explicit set-password command for recovery.")
        user_id = cli(["admin", "user", "create", "--email", email, "--name", name,
                       "--workspace", workspace_id], data)
        if not re.fullmatch(r"usr_[A-Za-z0-9_-]+", user_id):
            raise SetupError("Unexpected upstream user-create response; inspect cc-admin users before retrying.")
        try:
            cli(["admin", "user", "set-password", "--user", user_id], data, password)
        except SetupError as exc:
            raise SetupError(f"Account {user_id} was created but password delivery did not complete. Recover with cc-admin set-password --user {user_id}; do not recreate it.") from exc
        return user_id


def input_password(stdin: bool, generated: bool) -> tuple[str, bool]:
    if generated:
        if not sys.stdout.isatty():
            raise SetupError("Generated credentials are shown only in an interactive terminal, never deployment/CI logs. Use --password-stdin for automation.")
        return secrets.token_urlsafe(24), True
    if stdin:
        value = sys.stdin.read(1026)
        if len(value) > 1025:
            raise SetupError("Password input exceeds its size limit.")
        return validate_password(value.removesuffix("\n").removesuffix("\r")), False
    if not sys.stdin.isatty():
        raise SetupError("Use an interactive terminal or --password-stdin.")
    first = getpass.getpass("Temporary password: ")
    if first != getpass.getpass("Confirm password: "):
        raise SetupError("Passwords did not match.")
    return validate_password(first), False


def admin(argv: Sequence[str]) -> None:
    parser = argparse.ArgumentParser(prog="cc-admin")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("workspaces")
    sub.add_parser("users")
    create = sub.add_parser("add-user")
    create.add_argument("--email", required=True)
    create.add_argument("--name", required=True)
    create.add_argument("--workspace")
    reset = sub.add_parser("set-password")
    reset.add_argument("--user", required=True)
    for command in (create, reset):
        group = command.add_mutually_exclusive_group()
        group.add_argument("--password-stdin", action="store_true")
        group.add_argument("--generate-password", action="store_true")
    args = parser.parse_args(argv)
    if os.environ.get("CLICKCLACK_DB") or os.environ.get("CC_BOOTSTRAP_MODE", "sqlite") != "sqlite":
        raise SetupError("cc-admin helpers target the default SQLite template. Use upstream admin commands for an external database.")
    data = data_path(os.environ)
    prepare_data_and_drop_privileges(data)
    if args.command == "workspaces":
        print(json.dumps(list_workspaces(data), indent=2))
        return
    if args.command == "users":
        with db_reader(data / "clickclack.db") as db:
            rows = db.execute("SELECT u.id, u.display_name, u.kind, group_concat(DISTINCT i.email) AS emails FROM users u LEFT JOIN identities i ON i.user_id=u.id GROUP BY u.id ORDER BY u.created_at, u.id")
            print(json.dumps([dict(row) for row in rows], indent=2))
        return
    password, display = input_password(args.password_stdin, args.generate_password)
    if args.command == "add-user":
        user_id = add_user(data, args.email, args.name, password, args.workspace)
    else:
        if not re.fullmatch(r"usr_[A-Za-z0-9_-]+", args.user):
            raise SetupError("Invalid user ID.")
        with operation_lock(data):
            run_cli(["admin", "user", "set-password", "--user", args.user], data, password)
        user_id = args.user
    print(f"Password provisioned for {user_id}. Ask the user to change it after sign-in.")
    if display:
        print(f"Temporary password (copy once): {password}")
    if args.command == "set-password":
        print("Note: upstream admin password reset does not revoke existing sessions. Follow the offboarding runbook.", file=sys.stderr)


def main(argv: Sequence[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    try:
        if not args or args == ["serve"]:
            start()
        elif args[0] == "admin":
            admin(args[1:])
        else:
            raise SetupError("Use the default serve command or cc-admin for template administration.")
        return 0
    except (SetupError, OSError, sqlite3.Error) as exc:
        print(f"ClickClack setup error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
