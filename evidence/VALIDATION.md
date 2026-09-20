# Validation record

Package: ClickClack Railway template v0.1.0
Date: 2026-09-20
Upstream source pin: 05eca831b9ef0ae1924c08b3c81c860d784b6ba3
Deployed application/build revision: c2677bd1a54cd2b74a07a51a68924889c83d494d
Regression-test revision: 117ec28061e03c3df1cf837425eef362025264a1

## Railway canary: SUCCESS

Deployment `242e2424-f6bc-49b7-a49e-b82f5d9fa026` reached **SUCCESS**.
The connected Railway API returned runtime logs confirming:

- The existing persistent volume mounted.
- The first owner was initialized before HTTP started.
- ClickClack started on port 8080.
- Railway's GET `/readyz` returned HTTP 200.

The original Railway volume remains mounted at `/app/data`. No replacement
service was created, no volume was deleted, and no credential was reset during
this fix. The generated domain is `clickclack-production.up.railway.app`.

These are platform/runtime observations. A separate public HTTPS probe could
not be completed from the authoring environment: the container had a DNS
resolution failure and the web fetch tool could not access the endpoint.
Interactive browser login has not been verified. Do not equate the readiness
check with full end-to-end acceptance.

## Root cause and fix

The operator supplied the specific diagnostic:

```text
dockerfile invalid: docker VOLUME at Line 56 is not supported, use Railway Volumes
```

The Dockerfile incorrectly declared `VOLUME ["/app/data"]` even though the
Railway service already had its persistent volume configured. Commit `c2677bd`
removes that instruction. This was a template compatibility error, not evidence
of a Railway outage. Successful generic Docker builds did not catch this
platform-specific restriction.

Commit `117ec28` adds `tests/test_railway_compatibility.py`. Its check fails
against the verified pre-fix Dockerfile and passes against the fixed Dockerfile.
All **52 offline tests passed** in the authoring container. The current GitHub
Actions offline-tests job also completed successfully.

Current fix/regression CI run:
https://github.com/sidataplus/clickclack-railway/actions/runs/35532908730

At the 19:39 UTC evidence check, that run's separate real-image build/smoke job
was still in progress. No completed result for that job is claimed here.

Resolved incident:
https://github.com/sidataplus/clickclack-railway/issues/1

## Prior independent image validation

Revision `0f87e26925957423cbbb4bc694da460582eaded1` passed offline tests,
Docker build, and real-image authentication/persistence smoke checks:
https://github.com/sidataplus/clickclack-railway/actions/runs/35532335293

The earlier revision `2d9b3a7bf73143590ae5d2c740b1bf2ab80216c0` also passed:
https://github.com/sidataplus/clickclack-railway/actions/runs/35531999361

Those smoke tests used the real pinned Go application, not FakeCLI. They covered
readiness, frontend loading, password login/change, other-session revocation,
adding a normal member, UID 10001, bootstrap-secret removal from the Go process
environment, and account/file persistence after container recreation. They did
not verify actual HTTP uploads, interactive browser behavior, WebSocket
reconnection, or Railway-specific runtime behavior.

## Remaining release gates

- Verify public HTTPS access, live owner login, member creation, actual uploads,
  browser interaction, WebSocket recovery, and restart/redeploy persistence.
- Exercise backup restoration and record resource usage.
- Evaluate the installed Railway SDK before claiming optional IaC is tested.
- Make the intended public source available before Marketplace release.
- Create, sanitize, and test a real template draft with unique per-deployment secrets.
- Publish the Marketplace listing only after release acceptance.

No Marketplace template ID or Deploy on Railway URL has been generated.
Complete [acceptance](../docs/ACCEPTANCE.md) before publication.
