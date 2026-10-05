FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
# Vite inlines import.meta.env.VITE_* at build time, so it must be a build
# arg, not a runtime env var. Empty string (K8s default) makes API calls
# relative; docker-compose passes an absolute URL since nginx here doesn't
# proxy /arrivals to the app container.
ARG VITE_API_URL=""
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
