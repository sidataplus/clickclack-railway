# Publishing and kickback plan

## Separate products

This public template is a minimal deployment wrapper around unmodified upstream
ClickClack. Keep personal-fork PWA, SMTP, sophisticated auth, and agent features
in a separate repository/template. Public-template maintenance should not require
tracking a second application feature branch.

## Real Railway objects, not invented schema

`template/settings.json` is an exact maintainer checklist for the Railway template
composer. It is NOT an importable platform schema. `.railway/railway.ts` is
actual Railway IaC for the author project; neither file alone creates a public
Marketplace listing.

Create a working canary project, pass acceptance, then use the real command:

```sh
scripts/create-template.sh
# Equivalent: railway templates create --json
```

It creates an unpublished draft, matching Generate Template in the dashboard.
Treat the response and copied variables as sensitive. The script's `.local/`
output is gitignored and deliberately not printed.

Open the generated draft in Railway and apply `template/settings.json`:
owner email required with no author default; owner password generated separately
for each deployment; all other default-service settings preconfigured. Do not
publish your canary credentials or your organization's access rules.

Validate fresh instances from the draft, then publish:

```sh
CC_PUBLISH_CHECKLIST_PASSED=yes \
  scripts/publish-template.sh ACTUAL_TEMPLATE_ID
```

This passes `template/marketplace.md` as the overview with the Bots category.
Record the actual returned URL; only then add a Deploy on Railway button and
an upstream documentation PR. Do not label the template official or verified
unless OpenClaw/Railway has granted that status.

## Kickbacks

Railway's current kickback rates and eligibility must be reviewed at publication:
https://docs.railway.com/templates/kickbacks

This is the normal template-author route. Do not assume eligibility for the
separate upstream technology-partner program merely because this community
wrapper is open source. No income estimate is guaranteed by this package.

The useful funnel is successful deployment, first owner login, second user added,
and retained usage. Avoid adding services solely to increase spend. Monitor the
Railway template metrics and support queue; do not add hidden application
telemetry for monetization. Measure idle cost and disclose the date, region and
plan rather than claiming a universal monthly price.

Suggested support triage: build failure; missing/wrong volume; readiness failure;
first login; second-user provisioning; recovery/backup; optional OAuth. Do not
request live secrets or uploaded chat databases in public support threads.

Sources:
- https://docs.railway.com/cli/templates
- https://docs.railway.com/templates/create
- https://docs.railway.com/templates/kickbacks
- https://docs.railway.com/templates/partners
- https://railway.com/open-source-kickback
