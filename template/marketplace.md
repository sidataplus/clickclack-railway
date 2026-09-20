# ClickClack

An independent community Railway deployment of the open-source
[ClickClack](https://github.com/openclaw/clickclack) chat application.
It uses a pinned, unmodified upstream application plus a small deployment adapter.

## What you deploy

One application service and one persistent volume. SQLite stores application data;
local storage keeps uploads. Local-password authentication is enabled. External
OAuth providers, SMTP, and additional databases are not required.

## First sign-in

Enter your administrator email when deploying. Once the service is healthy,
open its Railway HTTPS domain. Your email is the login identifier; retrieve the
generated initial password from `CC_BOOTSTRAP_PASSWORD` in the service Variables.
Change it in ClickClack account settings after signing in. No email is sent.
Password replacement is recommended but is not enforced as a first-login gate.

Restarting or redeploying preserves accounts and uploaded files. Bootstrap
variables apply only when no live database exists; they are not password-reset
controls. Keep the attached volume and maintain backups.

## Add teammates

An operator with Railway access can open an interactive service shell:

```sh
railway ssh --service ClickClack
cc-admin add-user --email alice@example.com --name Alice --generate-password
```

Share the generated password privately and ask the user to change it after login.
This template does not add a browser invitation screen, open self-registration,
or emailed password recovery. Team members do not need Railway accounts to chat;
only the operator needs deployment access to provision them.

## Optional integrations

GitHub OAuth with an organization gate, OpenClaw ID, and Pushover can be enabled
using upstream configuration. R2 uploads and PostgreSQL require deliberate data
migration and additional setup. They are not enabled by this default template.

## Operational scope

Suitable for a single-instance small-team deployment. This is not a highly
available service. Use one replica with the attached volume, keep sleep disabled,
and expect brief downtime during deployment. Railway compute and volume usage
are billed according to your plan; no fixed monthly price is promised.

Do not delete the data volume to reset login. Use operator recovery and backups.
Do not put passwords, session tokens, or private messages in public support requests.

## Attribution

ClickClack is developed by OpenClaw and its contributors under the MIT license.
This template is community-maintained and does not imply official endorsement.
