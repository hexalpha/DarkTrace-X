FROM node:22-alpine AS build
ENV DOCKER_BUILD=true
WORKDIR /app
RUN corepack enable
COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

FROM node:22-alpine AS runtime
ENV NODE_ENV=production
WORKDIR /app
RUN addgroup -S -g 10001 app && adduser -S -D -u 10001 -G app app
COPY --from=build /app/public ./public
COPY --from=build /app/.next/standalone ./
COPY --from=build /app/.next/static ./.next/static
USER app
ENV HOSTNAME=0.0.0.0
EXPOSE 3000
CMD ["node", "server.js"]
