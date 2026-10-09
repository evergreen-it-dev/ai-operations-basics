FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY src/ src/
COPY tsconfig.json ./
RUN npm run build

FROM node:22-alpine
WORKDIR /app
COPY --from=build /app/dist dist/
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force
EXPOSE 3701
ENV TEAMS_MCP_HTTP_PORT=3701
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s \
  CMD wget -qO- http://localhost:3701/health || exit 1
CMD ["node", "dist/index.js"]
