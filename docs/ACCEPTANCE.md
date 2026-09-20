# Publication acceptance checklist

Release: ______  Upstream commit: ______  Author: ______  Date: ______
Record actual evidence; empty boxes mean incomplete, not implied success.

## Source and image

- [ ] Confirm repository is public and source/branding are accurately attributed.
- [ ] Run all offline tests and inspect results.
- [ ] Build the pinned Docker image successfully.
- [ ] Run tests/smoke_container.py against that real image.
- [ ] Review actual image dependencies/security findings for the release.
- [ ] Install Railway SDK, record its exact version/lock, evaluate a non-destructive plan.

## Fresh Railway author deployment

- [ ] Exactly one service and one attached /app/data volume.
- [ ] Dockerfile build selected; no build/predeploy writes expected on the volume.
- [ ] One replica, appropriate volume/service placement, sleep disabled.
- [ ] /readyz returns 200 after owner setup; no secret logged on success/failure.
- [ ] Railway HTTPS domain renders the app; cookie, Origin and WebSocket behavior work.
- [ ] Dev authentication endpoints reject production use.
- [ ] Initial owner login works; a random visitor cannot self-register.
- [ ] Change owner password; old password stops working.
- [ ] Restart AND redeploy; changed password and data survive.
- [ ] Remove bootstrap secret after changing it; restart still works.
- [ ] Add a second human with cc-admin, confirm member rather than owner role.
- [ ] Second human changes password successfully.
- [ ] Send a channel message and thread reply; confirm another browser sees both.
- [ ] Upload/download an attachment, redeploy, and download it again.
- [ ] Reconnect after a WebSocket interruption; inspect durable message recovery.
- [ ] Inspect idle RAM, CPU, volume growth and measured usage; publish only observed costs.
- [ ] Restore a database-and-uploads backup into an isolated deployment and verify it.

## Sanitized Marketplace draft

- [ ] Create an unpublished draft from the author project.
- [ ] Replace real author email with a REQUIRED blank input.
- [ ] Replace real author password with Railway's per-deployment secret expression.
- [ ] Remove author domains, tokens, project IDs and optional provider credentials.
- [ ] Confirm real public source repository and reviewed branch are selected.
- [ ] Confirm HTTP domain and /app/data volume are part of the template graph.
- [ ] Deploy TWO fresh copies with distinct owner emails; verify different generated passwords.
- [ ] Repeat first-login, add-user, persistence and backup checks on the draft deployment.
- [ ] Confirm one deployment's credentials cannot authenticate to the other.
- [ ] Verify marketplace text discloses CLI user creation and absent email recovery.
- [ ] Add maintainer profile, source link and private security-reporting contact.
- [ ] Publish; record actual template ID/link and revenue attribution.
- [ ] Configure Template Queue support ownership and review current kickback terms.

Do not set CC_PUBLISH_CHECKLIST_PASSED=yes until every applicable gate above
has actual evidence. Passing offline tests alone is insufficient.
