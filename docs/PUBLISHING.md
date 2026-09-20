# Marketplace publication and kickbacks

This is the public, password-first deployment template. Personal-fork PWA,
SMTP, advanced authentication, and agent features remain a separate product.
The upstream ClickClack application is pinned and unmodified.

## Verified release state on 2026-09-20

- The author deployment reached Railway `SUCCESS` after removing the unsupported
  Dockerfile `VOLUME` instruction. Railway provides the `/app/data` mount instead.
- Fixed-image CI completed successfully, including offline tests, the actual
  Docker build, and real-application authentication/persistence checks:
  https://github.com/sidataplus/clickclack-railway/actions/runs/35532908730
- Author deployment: `242e2424-f6bc-49b7-a49e-b82f5d9fa026`.
- These checks do not establish that a newly generated Marketplace template
  deploys correctly. Complete the fresh-template check below.
- No reusable template was created or published by the connected-tool workflow.
  No Marketplace ID or deployment URL has been recorded by that workflow.
- The source repository was still private at the last check. Do not mistake an
  accessible private canary source for a publicly deployable community source.

`template/settings.json` is a maintainer checklist, NOT a Railway import schema.
Neither it nor the optional `.railway/railway.ts` creates a Marketplace listing
merely by existing in this repository.

## Dashboard publication path

### 1. Make the intended source public

Review this repository and its history, then change
`sidataplus/clickclack-railway` to public in GitHub repository settings. Keep real
`.env`, `.local`, credentials, database files, and uploads out of the repository.
Verify that an unauthenticated visitor can read the Dockerfile and runtime files.

This is a source-repository change, not a change to the live Railway project's
visibility. Keep the author project private. Do not add it as a public demo.

### 2. Create an unpublished draft

In the `clickclack-railway` Railway project, open project Settings, locate
**Generate Template from Project**, and choose **Create Template**. In the
composer, set the template name to **ClickClack**.

Alternatively, use Workspace Settings -> Templates -> New Template and add the
single source service from scratch. Check existing workspace templates before
creating another one, to avoid duplicate listings.

Do not publish a project-derived draft without reviewing EVERY copied variable.
The author project's actual owner email, name, password and concrete domain must
not become defaults for other deployments. Do not attach or copy the author's
existing volume contents.

### 3. Apply these exact defaults in the TEMPLATE composer

| Setting | Value |
| --- | --- |
| Source repository | `sidataplus/clickclack-railway` |
| Branch | `main` |
| Service name | `ClickClack` |
| Build | Root `Dockerfile` |
| Start command | Leave blank; use image ENTRYPOINT/CMD |
| Pre-deploy command | Leave blank; initialization needs the runtime volume |
| Replicas | 1 |
| Serverless/sleep | Off |
| Public networking | Generated HTTPS domain, target port 8080 |
| Health check | `/readyz`, timeout 120 seconds |
| Persistent storage | New volume at `/app/data`, initial size 1024 MB where configurable |
| Restart policy | On failure, bounded retry count |

| Variable | Template value |
| --- | --- |
| `CC_BOOTSTRAP_EMAIL` | Required input, no default; each deployer supplies their own email |
| `CC_BOOTSTRAP_NAME` | `Admin` |
| `CC_BOOTSTRAP_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` |
| `CC_BOOTSTRAP_MODE` | `sqlite` |
| `CLICKCLACK_DATA` | `/app/data` |
| `CLICKCLACK_PASSWORD_AUTH_ENABLED` | `true` |
| `CLICKCLACK_DEV_BOOTSTRAP` | `false` |
| `CLICKCLACK_METRICS_ENABLED` | `false` |
| `PORT` | `8080` |

The password is a **template generator expression**, not an evaluated sample
password. The email field is a required blank input, not the literal text
`Required input`. If `RAILWAY_DOCKERFILE_PATH` is retained, its value is simply
`Dockerfile`. Do not manually set Railway's generated volume/domain variables.

Remove copied OAuth credentials, organization restrictions, Pushover keys,
custom domains, fixed public/callback URLs, and unrelated variables. Optional
integrations are configured by deployers later. Never modify the live canary's
variables to perform this sanitization: edit the draft instead.

### 4. Test the draft as a new deployment

Use a new test project and new administrator email/password. Verify that the
password generator actually produces a credential rather than passing its
expression literally. Check `SUCCESS`, HTTPS, first login, changing the password,
adding a normal member, and restart persistence. Complete the remaining checks
in [ACCEPTANCE.md](ACCEPTANCE.md). Record the result; the successful author
instance is not evidence that the draft has been sanitized or tested.

Retain any failed fresh-template evidence and fix the template before publishing.
Do not delete the author volume or reset its credentials as a test.

### 5. Publish the listing

From Workspace Settings -> Templates, choose **Publish** on the tested draft.

| Listing field | Value |
| --- | --- |
| Name | `ClickClack` |
| Category | `Bots` |
| Short description | `Self-hosted chat for humans and AI agents. Password-first setup, SQLite, and persistent uploads.` |
| Overview | Copy the complete [template/marketplace.md](../template/marketplace.md) |
| Demo project | Leave empty; the author's private instance is not a public demo |
| Attribution | Independent community template; no official or verified claim |

After publishing, open the actual Marketplace page while signed out and confirm
that it displays the intended source, description, and deploy configuration.
Record the real template ID, URL, publishing workspace, and publication date.
Only then add a Deploy on Railway button pointing to that real URL. Do not invent
a slug or use the live chat hostname as the template URL.

## CLI alternative

Use an authenticated current Railway CLI on your own machine. The ChatGPT
Railway connection is not automatically a local CLI login.

```sh
# Inspect drafts and listings first.
railway templates list --workspace 503033c0-ab41-476c-9906-4426eaa77592 --json

# Creates an UNPUBLISHED draft from the specified author project.
# Treat copied settings and the command output as sensitive until sanitized.
railway templates create \
  --project 8887e3f7-1edc-49f2-9aa3-8da2ef5986ee \
  --environment c014ac6c-bfe5-4f09-8782-6413e19f3d0a \
  --json
```

Apply the sanitization and fresh-deployment checks above in the composer before
running this command from the repository checkout:

```sh
# Replace ACTUAL_TEMPLATE_ID with the ID returned by Railway.
railway templates publish ACTUAL_TEMPLATE_ID \
  --category Bots \
  --description "Self-hosted chat for humans and AI agents. Password-first setup, SQLite, and persistent uploads." \
  --readme-file template/marketplace.md \
  --demo-project none \
  --json
```

The existing `scripts/create-template.sh` and `scripts/publish-template.sh` are
convenience wrappers. Their checklist acknowledgement is an operator assertion,
not automatic proof that credentials were removed or a fresh deployment passed.

## Kickback handling

Terms checked on 2026-09-20: eligible published templates receive 15% of
attributable usage, with another 10% for support participation. Railway says the
full 25% applies when there are no support questions. Unpublished drafts do not
qualify. Earnings go to Railway credits by default; cash withdrawal requires
separate account setup. Publication does not select or change payout preferences.

Enable Template Queue email notifications and answer questions in Central
Station. Use the normal template-author program; do not claim upstream
technology-partner status. No earnings are guaranteed.

Optimize for successful first login, easy second-user provisioning, and retained
usage, not unnecessary services. Do not add hidden application telemetry. Never
request passwords, session tokens, private messages, or databases in public
support threads.

## Primary references

- Creation, volumes, and generated secrets: https://docs.railway.com/templates/create
- Publishing and sharing: https://docs.railway.com/templates/publish-and-share
- CLI commands: https://docs.railway.com/cli/templates
- Eligibility, rates, support and payouts: https://docs.railway.com/templates/kickbacks
- Separate technology-partner program: https://docs.railway.com/templates/partners
