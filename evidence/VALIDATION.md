# Validation record

Package: ClickClack Railway template v0.1.0
Date: 2026-09-20
Upstream source pin: 05eca831b9ef0ae1924c08b3c81c860d784b6ba3

## Completed checks

- Offline unittest suite: 51 passed in the authoring container (36 runtime and 15 package/author checks).
- Runtime Python content matches the uploaded package: Git blob 3b434b52c3e1d04ae8c437b00ed105d4298dc285.
- Independent GitHub Actions build: SUCCESS at commit 2d9b3a7bf73143590ae5d2c740b1bf2ab80216c0.
- Real-image smoke test in the same job: SUCCESS.

Evidence: https://github.com/sidataplus/clickclack-railway/actions/runs/35531999361

The real-image smoke test exercised the pinned Go application, not the offline
FakeCLI. It verified readiness, frontend loading, password login, password
changes and other-session revocation, adding a normal member, UID 10001,
bootstrap-secret removal from the Go process environment, and account/file
persistence after container recreation. It did not test actual HTTP uploads,
browser interactions, WebSocket reconnection, or Railway-specific behavior.

## Railway canary

Source repository access and the source snapshot succeeded. Initial builds
stopped before Docker stages with the generic error:

> The Dockerfile failed validation. Please check the build logs for more details.

Build logs contained only a builder-scheduling line. Explicit Dockerfile-builder
selection did not resolve it. The exact failing validation was not exposed by
the platform diagnosis. No application had started at this checkpoint.

A syntax-only compatibility revision removes redundant shell-length expansion
and replaces COPY --chmod with a normal COPY plus RUN chmod. Application source,
image digests, runtime code, and password handling remain unchanged. This
revision requires its own CI and Railway results; the earlier success is not
claimed as proof for an unexecuted revision.

## Remaining release gates

Railway end-to-end readiness/login/persistence, browser and WebSocket tests,
backup restoration, installed Railway SDK evaluation, sanitized template draft
creation/testing, public repository visibility, and Marketplace publication.

No Marketplace template ID or deploy link has been generated. Complete
[acceptance](../docs/ACCEPTANCE.md) before publication. Neither the 51 offline
tests nor a successful independent image build alone proves Railway readiness.
