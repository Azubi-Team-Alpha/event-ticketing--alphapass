# ── Stage 1: Build the React Application ────────────────────────
FROM node:20-alpine AS build

WORKDIR /app

# Install dependencies first for better caching
COPY package*.json ./
RUN npm ci

# Copy code and build
COPY . .
RUN npm run build


# ── Stage 2: Serve with Nginx Alpine ────────────────────────────
FROM nginx:1.25-alpine AS production

# Copy built assets from builder stage
COPY --from=build /app/dist /usr/share/nginx/html

# Copy custom nginx configuration for client-side routing
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
