# Multi-stage build for Hugo + TailwindCSS
FROM node:18-alpine AS build

WORKDIR /src

# Copy package files
COPY package*.json ./

# Install Node dependencies
RUN npm install

# Copy source files
COPY . .

# Build CSS with TailwindCSS
RUN npm run build:css

# Install Hugo
RUN apk add --no-cache wget \
    && wget https://github.com/gohugoio/hugo/releases/download/v0.111.3/hugo_extended_0.111.3_linux-amd64.tar.gz \
    && tar -xzf hugo_extended_0.111.3_linux-amd64.tar.gz \
    && mv hugo /usr/local/bin/ \
    && rm hugo_extended_0.111.3_linux-amd64.tar.gz

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