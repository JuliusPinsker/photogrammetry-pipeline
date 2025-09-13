FROM ubuntu:22.04

# Install Node.js, npm, and Hugo dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    tar \
    && curl -fsSL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Install Hugo
RUN wget https://github.com/gohugoio/hugo/releases/download/v0.120.4/hugo_extended_0.120.4_linux-amd64.tar.gz && \
    tar -xzf hugo_extended_0.120.4_linux-amd64.tar.gz && \
    mv hugo /usr/local/bin/ && \
    rm hugo_extended_0.120.4_linux-amd64.tar.gz

# Set working directory
WORKDIR /app

# Copy package.json for npm dependencies
COPY package*.json ./
RUN npm install

# Copy Hugo site
COPY . .

# Build the site
RUN npm run build

# Install serve to serve static files
RUN npm install -g serve

# Expose port
EXPOSE 8080

# Serve the built site
CMD ["serve", "-s", "public", "-l", "8080"]
