# Railway IaC authoring

This directory is for the template maintainer's dedicated canary project.
Marketplace deployments use the saved template graph and do not need this SDK.

Install `railway` from npm using `pnpm add -D --save-exact railway`, and commit
the actual resolved package version and generated lockfile before release.
The SDK could not be installed or evaluated in the offline authoring runtime;
no package version or successful live plan has been invented.

`railway.ts` uses the documented TypeScript DSL from `railway/iac`. It declares
one GitHub-backed service, one volume, one replica, and a `/readyz` healthcheck.
The Dockerfile supplies startup. Generated Railway domains are created through
`railway domain` or the dashboard, not the IaC file.

Run `scripts/author.py init`, `plan`, and `apply` from the repository root.
The first command creates stable, gitignored author credentials; the other two
invoke the actual Railway CLI, retaining its normal confirmation behavior.

Only apply this whole-project specification to a NEW dedicated project.
Railway treats omitted resources in a whole-project file as deletions. Adding
services or optional variables through the dashboard requires reconciling the
IaC first, for example by reviewing `railway config pull` output. Never blindly
apply a stale graph. Do not use `--include-variables` when pulling a configuration
that contains secrets for version control.

`preserve()` retains an already existing Railway variable; it does not generate
a password and cannot initialize a missing secret. It is used only when no
bootstrap value is supplied by the author helper. Do not keep reapplying the
author helper after deliberately deleting bootstrap variables; reconcile the
specification to preserve that operational change.

The default volume placement is `us-west2`, 1024 MB. Choose service placement
compatible with the volume during canary setup; review plan capacity restrictions.
Set `CC_VOLUME_REGION` and `CC_VOLUME_SIZE_MB` before planning other placements.
Changing an existing volume's region or reducing capacity is not routine tuning.

References:
- https://docs.railway.com/infrastructure-as-code
- https://docs.railway.com/infrastructure-as-code/reference
- https://docs.railway.com/cli/domain
