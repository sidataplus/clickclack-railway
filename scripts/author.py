#!/usr/bin/env python3
"""Persist author-demo credentials locally and call Railway's actual IaC CLI.

Never creates a Marketplace listing automatically. Run in a dedicated linked
project. Local bootstrap values are not suitable defaults for a public template.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".local" / "author.json"

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="command", required=True)
    init = s.add_parser("init")
    init.add_argument("--repo", required=True)
    init.add_argument("--email", required=True)
    init.add_argument("--name", default="Admin")
    init.add_argument("--region", default="us-west2")
    for cmd in ("plan", "apply"):
        s.add_parser(cmd)
    args = p.parse_args()
    if args.command == "init":
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", args.repo):
            p.error("--repo must be owner/repository")
        if not re.fullmatch(r"[^\s@<>]+@[^\s@<>]+\.[^\s@<>]+", args.email):
            p.error("--email must be a valid email address")
        os.umask(0o077)
        STATE.parent.mkdir(exist_ok=True, mode=0o700)
        values = {"CC_TEMPLATE_REPO": args.repo, "CC_BOOTSTRAP_EMAIL": args.email.lower(),
                  "CC_BOOTSTRAP_NAME": args.name, "CC_BOOTSTRAP_PASSWORD": secrets.token_urlsafe(24),
                  "CC_VOLUME_REGION": args.region}
        try:
            fd = os.open(STATE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            p.error("Author config already exists. It was not overwritten; reuse it for plan/apply.")
        with os.fdopen(fd, "w") as f:
            json.dump(values, f, indent=2)
            f.write("\n")
        print("Created private .local/author.json. No credentials were printed. Do not commit or publish this file.")
        return 0
    if not STATE.is_file() or STATE.is_symlink():
        p.error("Run author.py init first; refusing missing or symlinked configuration.")
    if STATE.stat().st_mode & 0o077:
        p.error("Restrict .local/author.json to chmod 600 before proceeding.")
    if not shutil.which("railway"):
        p.error("Install and authenticate the official Railway CLI first.")
    values = json.loads(STATE.read_text())
    if not isinstance(values, dict) or not all(isinstance(k,str) and isinstance(v,str) for k,v in values.items()):
        p.error("Invalid author configuration")
    env = dict(os.environ)
    env.update(values)
    print("Using the linked Railway project. Review the plan for unexpected or destructive changes.")
    print("Treat plan output as sensitive. Apply keeps the Railway CLI's normal confirmation prompt.")
    return subprocess.run(["railway", "config", args.command], cwd=ROOT, env=env, check=False).returncode

if __name__ == "__main__":
    raise SystemExit(main())
