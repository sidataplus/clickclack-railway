# Operator runbook

## Accounts

Enter the deployed container using `railway ssh --service ClickClack`.
Do not use `railway run` or a local shell as a substitute: those run locally
and do not give these helpers access to the live mounted database.

```sh
cc-admin workspaces
cc-admin users
cc-admin add-user --email alice@example.com --name Alice --generate-password
```

Generated passwords are printed only to an interactive terminal. Treat terminal
recordings as sensitive. Without `--generate-password`, the helper prompts twice
without echo. For automation, use `--password-stdin` from a secret manager or
secure pipe; never pass a password as a command-line argument.

The helper delegates to actual upstream commands:
`admin user create --workspace ...`, then `admin user set-password --user ...`.
It does not enable public signup or grant ownership. Existing emails are rejected
without changing a password or role. Email addresses are local identifiers;
creating one does not prove that someone controls that email inbox.

With multiple workspaces, choose `--workspace` explicitly. For membership in
additional workspaces, use upstream `admin member add --workspace ...
--created-by OWNER_USER_ID --user USER_ID --role member` after verifying IDs.
Use native role-management UI/APIs for other authorization changes.

If account creation succeeds but setting its password fails, the helper prints
the user ID and a recovery instruction. Do not recreate the account:

```sh
cc-admin set-password --user usr_ACTUAL_ID
```

That operation is explicit account recovery, not a harmless change of startup
variables. It does not automatically revoke existing sessions. The normal
user-initiated password-change flow revokes the user's other sessions.

## First login and credential rotation

Read the first owner's email and initial password from Railway Variables.
Change the password in ClickClack's Account settings. The bootstrap password is
not enforced as one-time or expiring; this package does not modify upstream's
password policy/UI. Remove `CC_BOOTSTRAP_PASSWORD` after successful rotation.
A normal restart with an existing DB works without the bootstrap variables.
Never expect changing an environment variable to reset an existing account.

## Offboarding and compromise

Remove the person's workspace access through the application's supported admin
controls and verify that existing browser and API sessions can no longer read
that workspace. Treat account removal, token revocation, and IdP membership as
separate checks when optional OAuth/bots are enabled.

Do not assume that changing the person's password or removing a GitHub org
membership instantly revokes all ClickClack sessions. During a suspected
compromise, isolate or stop the affected service if authorization cannot be
contained, preserve a backup, and use the pinned upstream session/admin tools.
There is no invented `cc-admin revoke-all` command in this package.

## Backups and restores

Use Railway volume backups where available for the plan, and test restoration
to a separate project. A volume is not itself a backup. Keep an independent
encrypted copy according to your retention policy. Protect exports as credentials
and private messages may be present.

For a consistent SQLite database snapshot, use the upstream online backup command
as the application user, not `cp clickclack.db` while WAL is active:

```sh
# Inside the service. Use a fresh output filename and restrictive permissions.
mkdir -p /app/data/backups
chown 10001:10001 /app/data/backups
su -s /bin/sh clickclack -c \
  'umask 077; clickclack backup --data /app/data --out /app/data/backups/snapshot.db'
```

The shown `su` command assumes the Railway shell starts as root; when already
UID 10001, invoke `clickclack backup` directly. Schedule and transfer backups
using your own existing backup process, not a second mandatory service.

Database snapshots do not include uploaded bytes. Capture `uploads/` as well;
for a mutually consistent full backup, quiesce writes and take a full volume
backup/snapshot. Restore while the application is stopped, including necessary
journals when restoring a physical SQLite snapshot. Verify `PRAGMA quick_check`,
file ownership UID/GID 10001, account login, and attachment download in an
isolated restoration before replacing production. Never restore an old database
over a running newer schema.

## Fail-closed startup

A missing or wrong Railway volume mount stops startup. Existing empty/corrupt
SQLite databases and orphan journals are not overwritten. Capture the complete
volume, inspect it, and restore a valid backup. For an intentionally empty
existing database, an operator can use native `admin bootstrap` and
`admin user set-password` after verifying no valuable data is present; repairing
ownership may also be necessary. Do not delete a volume just to make health green.

An interrupted initial setup before database publication is safe to retry.
The initializer stages the database on the same volume, sets the password, then
publishes an integrity-checked snapshot without overwriting a preexisting file.
The server is not listening during this procedure.

## Upgrades

Back up first. Change the pinned upstream commit and base-image pins together
with `upstream.lock.json`, then run offline, real-image, and live acceptance
checks. Do not automatically follow `main`. Migrations can prevent safe binary
rollback; database restoration and app rollback must be planned together.
Expect brief deployment downtime with one instance and one attached volume.
Keep serverless/sleep off for the intended always-connected chat experience.
