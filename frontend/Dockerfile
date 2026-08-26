# Rashid Agent frontend (Next.js) — Chabokan npm/node mirrors
# Build context: repository root

ARG NODE_IMAGE=mirror2.chabokan.net/library/node:20-alpine

FROM ${NODE_IMAGE} AS deps
WORKDIR /app
RUN npm config set fetch-retries 5 \
    && npm config set fetch-retry-mintimeout 20000 \
    && npm config set fetch-retry-maxtimeout 120000 \
    && npm config set strict-ssl false
COPY frontend/package.json frontend/package-lock.json ./
# Prefer Chabokan; fall back to npmmirror then npmjs (Iran-friendly).
RUN --mount=type=cache,target=/root/.npm \
    (npm config set registry https://mirror2.chabokan.net/npm/ && npm ci) \
    || (echo ">>> Chabokan npm failed; trying registry.npmmirror.com..." \
        && npm config set registry https://registry.npmmirror.com/ && npm ci) \
    || (echo ">>> npmmirror failed; trying registry.npmjs.org..." \
        && npm config set registry https://registry.npmjs.org/ && npm ci)

FROM ${NODE_IMAGE} AS builder
WORKDIR /app
RUN npm config set registry https://mirror2.chabokan.net/npm/ \
    && npm config set strict-ssl false
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
ARG BACKEND_URL=http://api:8000
ENV BACKEND_URL=$BACKEND_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN npm run build

FROM ${NODE_IMAGE} AS runner
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    BACKEND_URL=http://api:8000 \
    HOSTNAME=0.0.0.0 \
    PORT=3000

RUN apk add --no-cache wget \
    || true

COPY --from=builder /app/public ./public
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static

EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 --start-period=30s \
    CMD wget -qO- http://127.0.0.1:3000/fa || exit 1
CMD ["node", "server.js"]
