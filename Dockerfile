# Community deployment wrapper. Upstream ClickClack source is not patched.
FROM alpine:3.24@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b AS source
RUN apk add --no-cache ca-certificates git
WORKDIR /src
ARG CLICKCLACK_UPSTREAM_REF=05eca831b9ef0ae1924c08b3c81c860d784b6ba3
RUN printf '%s' "$CLICKCLACK_UPSTREAM_REF" | grep -Eq '^[a-f0-9]{40}$' \
 && git init \
 && git remote add origin https://github.com/openclaw/clickclack.git \
 && git fetch --depth 1 origin "$CLICKCLACK_UPSTREAM_REF" \
 && git checkout --detach FETCH_HEAD \
 && test "$(git rev-parse HEAD)" = "$CLICKCLACK_UPSTREAM_REF" \
 && rm -rf .git

FROM node:26-alpine@sha256:ef24c5053d50fdc3e4e56eb4e7ddb7861874ab0fdc797046ba897581deb8e868 AS web
WORKDIR /src
RUN npm install -g pnpm@12.4.1
COPY --from=source /src/ /src/
ARG CLICKCLACK_UPSTREAM_REF=05eca831b9ef0ae1924c08b3c81c860d784b6ba3
ENV CLICKCLACK_WEB_VERSION=$CLICKCLACK_UPSTREAM_REF
RUN pnpm install --frozen-lockfile && pnpm build

FROM golang:1.27.1-alpine@sha256:cf6fca6641884b8433441b2b0652976f975e1d0fdd26d177eaaf8596087f3125 AS api
WORKDIR /src
COPY --from=source /src/ /src/
RUN go mod download
COPY --from=web /src/apps/api/internal/webassets/dist apps/api/internal/webassets/dist
ARG CLICKCLACK_UPSTREAM_REF=05eca831b9ef0ae1924c08b3c81c860d784b6ba3
RUN go build -trimpath -ldflags "-s -w -X main.version=railway-0.1.0 -X main.commit=$CLICKCLACK_UPSTREAM_REF" \
    -o /out/clickclack ./apps/api/cmd/clickclack

FROM alpine:3.24@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b
RUN apk add --no-cache ca-certificates python3 \
 && python3 -c 'import sqlite3, fcntl' \
 && addgroup -g 10001 clickclack \
 && adduser -D -H -u 10001 -G clickclack clickclack \
 && mkdir -p /app/data /opt/clickclack-railway /usr/share/licenses/clickclack \
 && chown 10001:10001 /app/data
WORKDIR /app
COPY --from=api /out/clickclack /usr/local/bin/clickclack
COPY --from=source /src/LICENSE /usr/share/licenses/clickclack/LICENSE
COPY runtime/cc_runtime.py /opt/clickclack-railway/cc_runtime.py
COPY runtime/cc-entrypoint runtime/cc-admin /usr/local/bin/
RUN chmod 0755 /usr/local/bin/cc-entrypoint /usr/local/bin/cc-admin
COPY LICENSE NOTICE.md /usr/share/licenses/clickclack-railway/
ENV CLICKCLACK_DATA=/app/data \
    CLICKCLACK_PASSWORD_AUTH_ENABLED=true \
    CLICKCLACK_DEV_BOOTSTRAP=false \
    CLICKCLACK_METRICS_ENABLED=false \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
# Root is used only to initialize the mount permissions. The entrypoint drops
# to UID/GID 10001 before provisioning accounts or starting the Go server.
USER root
EXPOSE 8080
VOLUME ["/app/data"]
ENTRYPOINT ["/usr/local/bin/cc-entrypoint"]
CMD ["serve"]
