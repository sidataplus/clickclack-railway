#!/usr/bin/env python3
"""Real-image integration checks. Requires Docker; never substitutes the FakeCLI.

Creates and removes only its own uniquely named test container/volume. Secrets
are generated per test, passed via a private env file/stdin, and never printed.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import tempfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def docker(*args: str, input: str | None = None, allow_failure: bool = False) -> str:
    result = subprocess.run(["docker", *args], input=input, text=True,
                            capture_output=True, timeout=180, check=False)
    if result.returncode and not allow_failure:
        raise RuntimeError(f"Docker {args[0]} failed; captured output was withheld to avoid exposing credentials.")
    return result.stdout.strip()


def request(base: str, path: str, body: dict | None = None, token: str | None = None) -> tuple[int, object]:
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = Request(base + path, data=None if body is None else json.dumps(body).encode(), headers=headers)
    try:
        with urlopen(req, timeout=15) as response:
            data = response.read()
            code = response.status
    except HTTPError as error:
        data, code = error.read(), error.code
    try:
        return code, json.loads(data)
    except (ValueError, UnicodeDecodeError):
        return code, data.decode(errors="replace")


def login(base: str, email: str, password: str) -> str:
    code, result = request(base, "/api/auth/password/login", {"identifier": email, "password": password})
    if code != 200 or not isinstance(result, dict):
        raise RuntimeError(f"Password login returned HTTP {code}; expected 200.")
    # The documented APIs issue a bearer-capable session. Fail if the response
    # changes, rather than silently bypassing authentication in this test.
    token = result.get("token") or result.get("session_token")
    session = result.get("session")
    if not token and isinstance(session, dict):
        token = session.get("token")
    if not isinstance(token, str) or not token:
        raise RuntimeError("Login response has no recognized session token; inspect pinned upstream contract.")
    return token


def ready(name: str) -> str:
    base = "http://" + docker("port", name, "8080/tcp").splitlines()[0]
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        try:
            if request(base, "/readyz")[0] == 200:
                return base
        except (URLError, TimeoutError, OSError):
            pass
        time.sleep(1)
    raise RuntimeError("Readiness did not succeed. Inspect sanitized container logs locally.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--image", default="clickclack-railway:test")
    args = parser.parse_args()
    if not shutil.which("docker"):
        raise SystemExit("Docker is required; no real-image tests have run.")
    suffix = secrets.token_hex(6)
    name, volume = f"cc-test-{suffix}", f"cc-test-data-{suffix}"
    email = "owner@example.com"
    original, replacement, member_password = (secrets.token_urlsafe(24) for _ in range(3))
    volume_created = False
    container_created = False
    with tempfile.TemporaryDirectory(prefix="cc-smoke-") as tmp:
        env_file = Path(tmp) / "container.env"
        fd = os.open(env_file, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w") as f:
            f.write(f"CC_BOOTSTRAP_EMAIL={email}\nCC_BOOTSTRAP_NAME=Owner\nCC_BOOTSTRAP_PASSWORD={original}\n")
        try:
            docker("volume", "create", volume)
            volume_created = True
            def launch() -> None:
                nonlocal container_created
                docker("run", "-d", "--name", name, "--env-file", str(env_file),
                       "-v", f"{volume}:/app/data", "-p", "127.0.0.1::8080", args.image)
                container_created = True
            launch()
            base = ready(name)
            if request(base, "/api/me")[0] not in (401, 403):
                raise RuntimeError("Anonymous account access was not rejected.")
            if request(base, "/")[0] != 200:
                raise RuntimeError("Embedded frontend did not load.")
            token = login(base, email, original)
            if request(base, "/api/me", token=token)[0] != 200:
                raise RuntimeError("Authenticated /api/me failed.")
            second_token = login(base, email, original)
            code, _ = request(base, "/api/auth/password/change",
                              {"current_password": original, "new_password": replacement}, token)
            if code not in (200, 204):
                raise RuntimeError(f"Password change returned HTTP {code}.")
            if request(base, "/api/me", token=second_token)[0] not in (401,403):
                raise RuntimeError("Other session was not revoked after user-initiated password change.")
            if request(base, "/api/auth/password/login", {"identifier": email, "password": original})[0] != 401:
                raise RuntimeError("Replaced password was still accepted.")
            docker("exec", "-i", name, "cc-admin", "add-user", "--email", "member@example.com",
                   "--name", "Member", "--password-stdin", input=member_password)
            member_token = login(base, "member@example.com", member_password)
            if request(base, "/api/me", token=member_token)[0] != 200:
                raise RuntimeError("New member authentication failed.")
            # Test actual file persistence, not merely the existence of a mount.
            docker("exec", "--user", "10001:10001", name, "python3", "-c",
                   "from pathlib import Path; p=Path('/app/data/uploads'); p.mkdir(exist_ok=True); (p/'smoke-sentinel.txt').write_text('retained')")
            uid_check = docker("exec", name, "python3", "-c",
                               "from pathlib import Path; s=Path('/proc/1/status').read_text(); print(next(x for x in s.splitlines() if x.startswith('Uid:')))")
            if not all(x == "10001" for x in uid_check.split()[1:]):
                raise RuntimeError("ClickClack PID 1 is not running exclusively as UID 10001.")
            scrubbed = docker("exec", "--user", "10001:10001", name, "python3", "-c",
                             "from pathlib import Path; e=Path('/proc/1/environ').read_bytes(); print(b'CC_BOOTSTRAP_PASSWORD=' not in e)")
            if scrubbed != "True":
                raise RuntimeError("Bootstrap password remains in the Go server environment.")
            docker("stop", name)
            docker("rm", name)
            container_created = False
            launch()  # Same volume AND original bootstrap variables, new process/container.
            base = ready(name)
            login(base, email, replacement)
            login(base, "member@example.com", member_password)
            users = json.loads(docker("exec", name, "cc-admin", "users"))
            if len(users) != 2:
                raise RuntimeError("Container recreation changed user cardinality.")
            persisted = docker("exec", "--user", "10001:10001", name, "cat", "/app/data/uploads/smoke-sentinel.txt")
            if persisted != "retained":
                raise RuntimeError("Volume data did not survive container recreation.")
            if request(base, "/api/auth/password/login", {"identifier": email, "password": original})[0] != 401:
                raise RuntimeError("Restart reapplied the bootstrap password.")
            print("PASS: real-image readiness, frontend, auth, native password rotation/session revocation, new member, UID, secret scrubbing, and recreation/persistence.")
            print("Still required: Railway-specific acceptance, browser UI, real upload/download, and WebSocket reconnect.")
        finally:
            if container_created:
                docker("rm", "-f", name, allow_failure=True)
            if volume_created:
                docker("volume", "rm", volume, allow_failure=True)

if __name__ == "__main__":
    main()
