# Validation record

Package: ClickClack Railway template v0.1.0
Date: 2026-09-20
Upstream source pin: 05eca831b9ef0ae1924c08b3c81c860d784b6ba3
Tested application/build revision: 0f87e26925957423cbbb4bc694da460582eaded1

## Completed checks

- Offline unittest suite: 51 passed in the authoring container (36 runtime and 15 package/author checks).
- GitHub Actions offline-tests job: SUCCESS on the tested revision, including runtime/package tests and Python/shell syntax checks.
- Actual Docker build: SUCCESS on the tested revision.
- Real-image authentication and persistence smoke test: SUCCESS on the tested revision.

Latest CI evidence:
https://github.com/sidataplus/clickclack-railway/actions/runs/35532335293

The earlier build revision 2d9b3a7bf73143590ae5d2c740b1bf2ab80216c0 also passed its Docker build and real-image smoke test:
https://github.com/sidataplus/clickclack-railway/actions/runs/35531999361

The real-image smoke test exercised the pinned Go application, not the offline
FakeCLI. It verified readiness, frontend loading, password login, native password
changes and other-session revocation, adding a normal member, UID 10001,
bootstrap-secret removal from the Go process environment, and account/file
persistence after container recreation. It did not test actual HTTP uploads,
browser interactions, WebSocket reconnection, or Railway-specific behavior.

## Railway canary: BLOCKED

Source repository access and source snapshots succeeded. The existing service
is connected to this repository's main branch, with its original volume, domain,
configuration, and bootstrap credentials retained. No replacement service was
created and no volume was deleted.

Latest tested Railway deployment: 27c833ac-1515-4650-a90b-d02924985033
Application/build revision: 0f87e26925957423cbbb4bc694da460582eaded1
Terminal state: FAILED
Failure stage: BUILD_IMAGE

The platform reports:

> The Dockerfile failed validation. Please check the build logs for more details.

The only build log is a Metal-builder scheduling line. No Docker stage output,
failed instruction, line number, or runtime logs are exposed. Consequently the
application is not running, and live owner login has not been verified.

Controls attempted: explicit Dockerfile selection; RAILWAY_DOCKERFILE_PATH;
removing redundant shell-length expansion; and replacing COPY --chmod with a
normal COPY plus RUN chmod. The compatibility revision passes independent CI
but still fails Railway validation. The exact cause remains unidentified; this
is not evidence that the source permissions or password implementation failed.

Reproduction details and next investigation:
https://github.com/sidataplus/clickclack-railway/issues/1

Do not continue redeploying the same revision without new diagnostic evidence.
Obtain the underlying validator error or a reproducible compatibility fix, then
observe a Railway SUCCESS and complete live acceptance.

## Remaining release gates

- Resolve Railway's pre-build validation failure.
- Verify live HTTPS readiness, owner login, user creation, actual uploads,
  browser interaction, WebSocket recovery, and restart/redeploy persistence.
- Exercise backup restoration and record resource usage.
- Evaluate the installed Railway SDK before claiming the optional IaC is tested.
- Make the intended public source available; repository visibility is currently private.
- Create, sanitize, and test a real template draft with unique per-deployment secrets.
- Publish the Marketplace listing only after release acceptance.

No Marketplace template ID or Deploy on Railway URL has been generated. Complete
[acceptance](../docs/ACCEPTANCE.md) before publication. Successful image tests are
not a substitute for a successful Railway deployment.

This evidence-only update does not change the tested application, Dockerfile,
runtime, or test code.
