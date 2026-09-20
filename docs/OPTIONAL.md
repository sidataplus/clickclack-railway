# Optional integrations

These remain opt-in. The default must work without any of them.

## GitHub OAuth

After obtaining an actual public HTTPS origin, create the OAuth app and set:

```text
CLICKCLACK_PUBLIC_URL=https://your-actual-chat-origin
CLICKCLACK_GITHUB_CLIENT_ID=...
CLICKCLACK_GITHUB_CLIENT_SECRET=...
CLICKCLACK_GITHUB_ALLOWED_ORG=your-organization
```

Callback: `https://your-actual-chat-origin/api/auth/github/callback`.
For private teams, configure and test the organization gate before publishing
the OAuth login method. Unrestricted OAuth is not equivalent to an invitation
allowlist. Existing local users are not automatically linked by matching email;
plan provider migration instead of assuming identities will merge.

The initializer still supplies the initial local owner on a fresh volume.
Keep local authentication during a controlled OAuth trial; verify ownership and
recovery before disabling `CLICKCLACK_PASSWORD_AUTH_ENABLED`. Update the IaC
source to retain optional variables before applying it again.

## OpenClaw ID

Use upstream's current configuration guide for provider credentials and issuer.
It is a specific provider integration, not this template's generic OIDC adapter.
No OpenClaw account is required by the password-default template.

## Pushover

Set `CLICKCLACK_PUSHOVER_API_TOKEN` in Railway, then users configure their own
Pushover settings in ClickClack. This is optional third-party notification
delivery, not built-in mobile Web Push. No Pushover credential belongs in the
public template defaults.

## R2 uploads

Follow upstream storage configuration and copy existing uploads with a verified
migration procedure. Changing the storage URL does not transfer existing files.
The default volume must remain attached while SQLite lives on it. This wrapper
does not remove the volume or replace the database because uploads move to R2.

## PostgreSQL

This public template's automatic bootstrap and cc-admin helpers explicitly target
local SQLite. Do not merely set `CLICKCLACK_DB` on a populated default deployment.
That could start against an empty different database while old data remains on
the volume.

For an already migrated and independently provisioned PostgreSQL deployment,
set `CC_BOOTSTRAP_MODE=external` with `CLICKCLACK_DB`, retain storage needed for
uploads, and use the upstream admin commands with explicit DB settings. The
wrapper then skips automatic owner creation and rejects SQLite-only cc-admin
operations. This is an advanced escape hatch, not a tested turnkey second
product. A separate advanced template is preferable.

Sources:
- https://docs.clickclack.chat/configuration.html
- https://docs.clickclack.chat/features/auth.html
- https://docs.clickclack.chat/deployment.html
