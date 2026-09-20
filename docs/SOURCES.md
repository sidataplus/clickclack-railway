# Verified source ledger

Inspected 2026-09-20. Runtime pin:
https://github.com/openclaw/clickclack/tree/05eca831b9ef0ae1924c08b3c81c860d784b6ba3

| Source | Used for |
|---|---|
| Upstream Dockerfile at the pinned commit | Build stages, images, assets embedding, runtime directory |
| apps/api/cmd/clickclack/main.go | Existing bootstrap, user create, workspace membership and server flags |
| apps/api/cmd/clickclack/admin_password.go | Password stdin support and exact user-selection flags |
| apps/api/internal/store/sqlite/auth.go | Existing password/account session behavior |
| apps/api/internal/store/sqlite/sqlc/schema.sql | Read-only user, identity, workspace and owner queries |
| LICENSE | MIT attribution and license-copy requirements |
| https://docs.clickclack.chat/features/auth.html | Auth options, password changes, no public signup, identity distinctions |
| https://docs.clickclack.chat/deployment.html | SQLite layout, health checks, native backups |
| https://docs.railway.com/infrastructure-as-code | Current SDK and plan/apply workflow |
| https://github.com/railwayapp/docs/blob/main/content/docs/infrastructure-as-code/reference.md | Exact TypeScript service/volume/preserve helpers |
| https://docs.railway.com/config-as-code/reference | Legacy configuration status |
| https://docs.railway.com/volumes | Runtime-only mounts and volume constraints |
| https://docs.railway.com/cli/domain | Actual generated-domain command and target port |
| https://docs.railway.com/cli/ssh | Remote shell and interactive CLI execution |
| https://docs.railway.com/cli/templates | Actual draft creation and publication commands |
| https://docs.railway.com/templates/create | Template input fields and secret generation |
| https://docs.railway.com/templates/kickbacks | Monetization and support terms |

Reading source is not execution evidence. See evidence/VALIDATION.md for the
separate build/deployment status. Optional providers and advanced storage modes
have not been integration-tested in this package.
