# Local / desktop Docker edition. Production Pages build is unchanged.
# Do not set VITE_API_URL — the SPA must call /api on the same origin (nginx).

FROM node:20-alpine AS build
WORKDIR /web

COPY apps/web/package.json apps/web/package-lock.json ./
RUN npm ci

COPY apps/web/ ./
RUN npm run build

FROM nginx:1.27-alpine
COPY deploy/nginx-local.conf /etc/nginx/conf.d/default.conf
COPY --from=build /web/dist /usr/share/nginx/html
EXPOSE 80
