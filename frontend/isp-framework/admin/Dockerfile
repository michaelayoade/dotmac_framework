# Multi-stage Dockerfile for Next.js Admin Portal

# Stage 1: Dependencies
FROM node:20-alpine AS deps
RUN apk add --no-cache libc6-compat
WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY isp-framework/admin/package.json ./isp-framework/admin/
COPY packages/headless/package.json ./packages/headless/
COPY packages/primitives/package.json ./packages/primitives/
COPY packages/styled-components/package.json ./packages/styled-components/

# Install dependencies
RUN pnpm install --frozen-lockfile

# Stage 2: Development (for hot-reload during development)
FROM node:20-alpine AS development
WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

# Copy dependencies from deps stage
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/isp-framework/admin/node_modules ./isp-framework/admin/node_modules
COPY --from=deps /app/packages/*/node_modules ./packages/*/node_modules

# Copy package files
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY isp-framework/admin/package.json ./isp-framework/admin/
COPY packages/headless/package.json ./packages/headless/
COPY packages/primitives/package.json ./packages/primitives/
COPY packages/styled-components/package.json ./packages/styled-components/

# Copy source code
COPY . .

# Set development environment
ENV NODE_ENV development
ENV NEXT_TELEMETRY_DISABLED 1

EXPOSE 3000

# Development command with hot-reload
CMD ["pnpm", "--filter", "@dotmac/admin-app", "dev"]

# Stage 3: Builder
FROM node:20-alpine AS builder
WORKDIR /app

# Install pnpm
RUN corepack enable && corepack prepare pnpm@8.15.0 --activate

# Copy dependencies
COPY --from=deps /app/node_modules ./node_modules
COPY --from=deps /app/isp-framework/admin/node_modules ./isp-framework/admin/node_modules
COPY --from=deps /app/packages/*/node_modules ./packages/*/node_modules

# Copy source code
COPY . .

# Build the application
ENV NEXT_TELEMETRY_DISABLED 1
ENV NODE_ENV production
RUN pnpm --filter @dotmac/admin-app build

# Stage 4: Runner
FROM node:20-alpine AS runner
WORKDIR /app

# Install curl for health checks
RUN apk add --no-cache curl

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Create non-root user
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy necessary files
COPY --from=builder /app/isp-framework/admin/public ./isp-framework/admin/public
COPY --from=builder /app/isp-framework/admin/.next/standalone ./
COPY --from=builder /app/isp-framework/admin/.next/static ./isp-framework/admin/.next/static
COPY --from=builder /app/isp-framework/admin/server.js ./isp-framework/admin/

# Set permissions
RUN chown -R nextjs:nodejs /app

USER nextjs

EXPOSE 3000

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"
ENV SHUTDOWN_GRACE_PERIOD 30000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:3000/api/health || exit 1

# Start with custom server for graceful shutdown
CMD ["node", "isp-framework/admin/server.js"]