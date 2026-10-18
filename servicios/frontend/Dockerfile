# Node y herramientas de desarrollo solo existen en la etapa de compilación.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# Variables públicas de compilación; no introducir secretos.
ARG VITE_API_URL=""
ARG VITE_PERMISSIONS_API_URL=""
ARG VITE_SESSION_INACTIVITY_MINUTES="5"
ARG VITE_PORTAL_ORIGIN=""
ARG VITE_PERMISSIONS_GRID_ORIGIN=""
ENV VITE_API_URL=${VITE_API_URL} \
    VITE_PERMISSIONS_API_URL=${VITE_PERMISSIONS_API_URL} \
    VITE_SESSION_INACTIVITY_MINUTES=${VITE_SESSION_INACTIVITY_MINUTES} \
    VITE_PORTAL_ORIGIN=${VITE_PORTAL_ORIGIN} \
    VITE_PERMISSIONS_GRID_ORIGIN=${VITE_PERMISSIONS_GRID_ORIGIN}
RUN npm run build \
    && node container/write-nginx-config.mjs

# Imagen mínima: únicamente servidor estático, configuración y bundle.
FROM nginx:stable-alpine-slim AS runtime
COPY --from=build /app/nginx.conf /etc/nginx/nginx.conf
COPY --from=build /app/dist /usr/share/nginx/html
USER nginx
EXPOSE 5173
STOPSIGNAL SIGQUIT
ENTRYPOINT ["nginx"]
CMD ["-g", "daemon off;"]
