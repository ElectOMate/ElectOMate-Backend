# Multi-stage build: build React app, serve with nginx
FROM node:22-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
# Build with production API base (nginx proxies /v2/graph to backend)
RUN npm run build

FROM nginx:alpine
# Copy built files
COPY --from=builder /app/dist /usr/share/nginx/html
# Nginx config: serve SPA + proxy /v2/graph to backend
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
