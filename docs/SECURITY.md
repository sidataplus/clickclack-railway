# Security scope and invariants

This adapter is not a security audit of ClickClack and is not approval to store
regulated clinical data. Use an appropriate organizational review before any
sensitive production use.

## Runtime boundary

The image starts as root only to fix the top-level root-owned volume mount.
It drops supplementary groups, GID, and UID to 10001 before any provisioning or
Go server startup. Python then execs ClickClack, so the Go server becomes PID 1.
The service does not retain a privileged Python worker. Imported files must
already have compatible ownership; no recursive ownership sweep is performed.

Owner credentials are never placed in CLI argv or deployment logs by this code.
Passwords go to upstream over stdin. Bootstrap values are removed from the
child CLI and long-running server environments. They remain visible to authorized
Railway administrators in service configuration until removed; this is not
protection against a Railway account or host administrator.

## Provisioning boundary

Dev authentication is forbidden. All application-account writes use the pinned
upstream CLI and password subsystem. Read-only SQLite queries only inspect
known schema fields. Temporary staging and final database files use restrictive
permissions. The final database is published with a same-filesystem no-overwrite
hard link only after setup succeeds.

The initializer never adopts/reset-passwords for an existing user. Even an empty
existing DB is a manual recovery case. Operator CLI access is privileged and
must be limited to actual deployment administrators. Local email fields are not
verified emails. New members must be added intentionally by an operator.

## Not implemented here

- Forced first-login password replacement or password expiry.
- Browser-based invitation/registration, SMTP, or emailed password recovery.
- MFA for local passwords, generic OIDC, or account auto-linking by email.
- Independent all-session revocation in the helper.
- Encryption of chat content against the service/database administrator.
- Native Web Push/PWA changes or a clinical authorization model.

A user-initiated native password change has different session semantics from
an operator's native set-password command. Do not confuse the latter with a
complete response to account compromise.

## Supply chain and disclosure

Application source and base images are pinned, but OS packages installed from
Alpine repositories are not a fully reproducible package snapshot. Maintain
security updates intentionally; immutable pins are not a substitute for patching.
CI builds against the real pinned app before publication. Dependency updates
must not silently switch the image to a different application revision.

Use private disclosure channels for credential or access-control vulnerabilities.
Never place passwords, live database exports, session tokens, or private messages
in public template-support threads. Add a maintainer-controlled private security
contact to the repository before Marketplace publication.
