FROM node:20-alpine AS deps
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
ARG BACKEND_URL=http://api:8000
ENV BACKEND_URL=$BACKEND_URL
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
ENV BACKEND_URL=http://api:8000
ENV HOSTNAME=0.0.0.0
ENV PORT=3000
COPY --from=builder /app/package.json ./
COPY --from=builder /app/package-lock.json ./
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/next.config.ts ./
EXPOSE 3000
HEALTHCHECK --interval=15s --timeout=5s --retries=5 CMD wget -qO- http://127.0.0.1:3000/fa || exit 1
CMD ["npm", "run", "start", "--", "-H", "0.0.0.0", "-p", "3000"]
