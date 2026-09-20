# ClickClack Railway template

**Independent community template, v0.1.0. Not yet a published Marketplace listing.**

One service, one persistent volume, SQLite, local-password login, and automatic first-owner setup. No OAuth registration, SMTP, Redis, proxy, or external identity service is needed for the default deployment.

```text
Railway HTTPS domain
        |
   ClickClack :8080
   password login
   embedded web UI
        |
  /app/data volume
  + clickclack.db
  + uploads/
```

The Docker build fetches unmodified upstream ClickClack at commit `05eca831b9ef0ae1924c08b3c81c860d784b6ba3`. This repository adds deployment initialization and CLI conveniences, not a custom chat UI or agent runtime. See [upstream.lock.json](upstream.lock.json) and [NOTICE.md](NOTICE.md).

## Validation and publication status

The source is now in `sidataplus/clickclack-railway`, and an author Railway canary has been provisioned. Initial Railway builds failed before any Docker stages, with a generic Dockerfile-validation error. An independent GitHub Actions Docker build and real-application smoke test are used to diagnose this separately from the 51 offline wrapper tests.

Railway end-to-end acceptance and Marketplace publication **have not been completed**. See [validation evidence](evidence/VALIDATION.md) and [release acceptance](docs/ACCEPTANCE.md). A successful source upload or offline test is not a successful deployment.

## First deployment

The public template will ask for the administrator's email and generate an initial password. In a manually configured service, supply an actual unique password of at least 16 characters, not a literal template expression.

Set the variables in [template/settings.json](template/settings.json), attach a volume at `/app/data`, configure port 8080 and `/readyz`, use one replica, and disable serverless/sleep. Leave start and pre-deploy commands unset: the image initializes the mounted data directory before starting HTTP. Generate a Railway HTTPS domain; the wrapper derives the public origin from `RAILWAY_PUBLIC_DOMAIN`.

Sign in with `CC_BOOTSTRAP_EMAIL` and the value of `CC_BOOTSTRAP_PASSWORD` in Railway Variables. No email is sent. This is an initial password, not an enforced first-login reset flow. Change it in account settings after signing in.

Initialization publishes a fully provisioned SQLite database without replacing an existing file. Restarts, redeployments, and changes to bootstrap variables do not reset an existing password. After confirming setup and changing the password, the generated bootstrap secret may be removed from Railway. Restores onto empty storage then need explicit credential provisioning.

## Run the tests

```sh
python3 -m unittest discover -s tests -p 'test_*.py' -v
docker build -t clickclack-railway:test .
python3 tests/smoke_container.py --image clickclack-railway:test
```

Offline tests use an explicitly synthetic CLI fixture. The smoke runner uses the real image and checks readiness, frontend loading, authentication, password changes, session revocation, adding a member, privilege dropping, secret scrubbing, and persistence after container recreation. It removes only its own test container and volume.

## Add people

```sh
railway ssh --service ClickClack
# Inside the service, in an interactive terminal:
cc-admin add-user --email alice@example.com --name Alice --generate-password
```

The helper creates a native human account and normal member membership, then displays a generated password only in the interactive terminal. Share it through a trusted channel and ask the user to change it. With multiple workspaces, specify `--workspace WORKSPACE_ID`.

This version **does not add an Admin → Invite web screen**. Additional user provisioning is still an operator action. See [operations](docs/OPERATIONS.md).

## Optional author IaC

For a new, dedicated canary project, install the current `railway` SDK with `pnpm add -D --save-exact railway` and record its resolved lockfile before release. Then use:

```sh
python3 scripts/author.py init --repo sidataplus/clickclack-railway --email admin@example.com
python3 scripts/author.py plan
python3 scripts/author.py apply
```

The helper keeps stable author credentials in gitignored `.local/author.json` with mode 0600. Treat plan output as sensitive. Do not apply a whole-project specification blindly to an existing shared project. See [.railway/README.md](.railway/README.md).

## Publish the Marketplace template

Only after [acceptance](docs/ACCEPTANCE.md):

```sh
scripts/create-template.sh
```

Sanitize the unpublished draft: remove author-specific IDs, email, secrets, and domains; make the email a required input; replace the copied password with the per-deployment secret generator from `template/settings.json`. Ensure the source repository is public. Deploy a fresh copy of the sanitized draft and repeat acceptance.

```sh
CC_PUBLISH_CHECKLIST_PASSED=yes scripts/publish-template.sh ACTUAL_TEMPLATE_ID
```

No deploy button or template URL is invented in this repository. Use the actual ID returned by Railway. See [publishing](docs/PUBLISHING.md).

## Optional integrations and boundaries

GitHub OAuth with an optional organization gate, OpenClaw ID, and Pushover are upstream options and remain disabled unless configured. PostgreSQL and R2 are advanced migrations, not transparent variable switches. See [optional integrations](docs/OPTIONAL.md).

This is a single-instance small-team deployment, not high availability. Persistent storage is not an off-site backup. Authentication and authorization remain upstream responsibilities; this wrapper does not introduce a password-hashing implementation or public invitation endpoint. Personal application forks remain separate.

See [security](docs/SECURITY.md) and [sources](docs/SOURCES.md).
