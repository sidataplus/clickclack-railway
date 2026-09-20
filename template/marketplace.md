# ClickClack

Deploy self-hosted chat for humans and AI agents with **one service, one persistent
volume, and local-password login**. No OAuth app registration, SMTP server, or
separate database service is required for the default setup.

This is an independent community deployment of
[ClickClack](https://github.com/openclaw/clickclack). The application is pinned to
an unmodified upstream revision; a small deployment adapter handles first-owner
setup and operator account-management commands.

## Included in this template

SQLite stores application data, and the `/app/data` Railway volume stores the
database and uploaded files. The service uses Railway HTTPS and a `/readyz`
readiness check. Authentication is enabled before the application starts serving
requests, with an automatically initialized owner account.

Bring your own agent runtime or bot integration. This template deploys the chat
application, not an LLM provider or autonomous-agent execution service.

## First sign-in

Enter your administrator email in the deployment form. After the service becomes
healthy, open its generated HTTPS domain and sign in using that email and the
value of **`CC_BOOTSTRAP_PASSWORD`** in the service's **Variables** tab.

Change the initial password in ClickClack account settings after signing in.
No email is sent. Password replacement is recommended but is not enforced by a
first-login gate. Restarting or redeploying does not reapply the initial password.
The bootstrap variables are not password-reset controls.

## Add teammates

An operator with Railway access can use an interactive service shell:

```sh
railway ssh --service ClickClack
# Run inside the deployed container:
cc-admin add-user --email alice@example.com --name Alice --generate-password
```

The helper adds a normal member, not another owner. Share the generated password
privately and ask the teammate to change it after login. Specify
`--workspace WORKSPACE_ID` when the instance contains multiple workspaces.

This template does **not** add a browser invitation screen, public registration,
or emailed password recovery. Teammates do not need Railway accounts to chat;
only the operator needs deployment access to create their local accounts.

## Optional integrations

GitHub OAuth, an optional GitHub organization gate, OpenClaw ID, and Pushover
remain upstream configuration options. They are disabled unless configured.
PostgreSQL and R2 require additional setup and a deliberate data-migration plan;
changing a variable does not migrate an existing SQLite database or local files.

Personal-fork PWA/Web Push, SMTP invitations, and custom agent features are not
bundled into this community template. See the
[optional integration guide](https://github.com/sidataplus/clickclack-railway/blob/main/docs/OPTIONAL.md).

## Operations and support

Use one replica and keep service sleeping disabled. This is a single-instance
small-team deployment, not high availability; expect brief interruptions during
redeployment. Railway compute and storage charges depend on your usage and plan.
No fixed monthly bill is promised.

Preserve the `/app/data` volume and maintain backups. A persistent volume is not
an off-site backup. Do not delete it to recover a login: use the documented
operator password-reset procedure instead.

The [operator guide](https://github.com/sidataplus/clickclack-railway/blob/main/docs/OPERATIONS.md)
covers adding users, password recovery, backups, and restoration. For deployment
help, use this template's Railway discussion page. Report application issues to
upstream only after separating them from template/deployment issues.

Never include passwords, session or bot tokens, private messages, or database
files in public support requests.

## Attribution

ClickClack is developed by OpenClaw and its contributors under the MIT license.
This [community template](https://github.com/sidataplus/clickclack-railway) does not
imply official endorsement or Railway verification.
