# ClickClack Railway template

Community deployment template for [OpenClaw ClickClack](https://github.com/openclaw/clickclack).

One service, one persistent volume, SQLite, local-password login, and automatic first-owner setup. The upstream application is pinned and unmodified; the deployment adapter adds safe first-boot initialization and operator account-management helpers.

## Defaults

- One ClickClack service on port 8080.
- SQLite and uploads on a persistent `/app/data` volume.
- Local-password authentication enabled; development authentication disabled.
- First owner created from `CC_BOOTSTRAP_EMAIL`, `CC_BOOTSTRAP_NAME`, and `CC_BOOTSTRAP_PASSWORD` before HTTP starts.
- Existing databases and passwords are not replaced on restart.
- `/readyz` deployment health check.

The initial password is retrieved from Railway Variables. No email is sent, and password replacement is not forced by this version. Change the password after signing in.

## Status

Source publication and the author canary deployment are in progress. This repository is not yet a published Railway Marketplace template. Do not assume that a successful build proves login, persistence, or WebSocket behavior.

## Additional users

Open a Railway service shell and run:

```sh
cc-admin add-user --email alice@example.com --name Alice --generate-password
```

This remains an operator action, not a browser-based invitation screen. Additional users are members, not owners.

## Boundaries

This public-template code is separate from personal ClickClack feature forks. GitHub OAuth, OpenClaw ID, Pushover, PostgreSQL, and R2 are optional. PostgreSQL and R2 require explicit migration planning; changing environment variables does not migrate existing data.

No administrator credentials, application data, or author-specific deployment configuration belong in this repository.
