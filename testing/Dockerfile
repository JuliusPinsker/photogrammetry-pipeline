FROM python:3.10-slim

# Install system dependencies for Selenium
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Install ChromeDriver
RUN CHROME_DRIVER_VERSION=$(curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE) \
    && wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/$CHROME_DRIVER_VERSION/chromedriver_linux64.zip \
    && unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/ \
    && rm /tmp/chromedriver.zip \
    && chmod +x /usr/local/bin/chromedriver

# Install Python dependencies
RUN pip install --no-cache-dir \
    pytest==7.4.3 \
    selenium==4.15.2 \
    requests==2.31.0 \
    pytest-html==4.1.1 \
    pytest-xvfb==3.0.0

WORKDIR /app

# Copy test files
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV DISPLAY=:99

CMD ["pytest", "/tests", "-v", "--html=/app/reports/report.html", "--self-contained-html"]