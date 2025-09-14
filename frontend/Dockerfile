# Simple Hugo build with TailwindCSS
FROM klakegg/hugo:0.125.0-ext-alpine AS build

WORKDIR /src

# Copy source files
COPY . .

# Install Node.js for TailwindCSS
RUN apk add --no-cache nodejs npm

# Install dependencies and build CSS
RUN npm install
RUN npm run build:css

# Build Hugo site
RUN hugo --minify

# Runtime stage
FROM nginx:alpine

# Copy built site
COPY --from=build /src/public /usr/share/nginx/html

# Copy custom nginx config
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 1313

CMD ["nginx", "-g", "daemon off;"]