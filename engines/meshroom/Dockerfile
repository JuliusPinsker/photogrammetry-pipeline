FROM ubuntu:20.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    python3 \
    python3-pip \
    libqt5core5a \
    libqt5gui5 \
    libqt5widgets5 \
    libqt5opengl5 \
    libqt5svg5 \
    qt5-default \
    libboost-all-dev \
    libeigen3-dev \
    libceres-dev \
    libopencv-dev \
    libgmp-dev \
    libmpfr-dev \
    && rm -rf /var/lib/apt/lists/*

# Download and install Meshroom
WORKDIR /opt
RUN wget https://github.com/alicevision/Meshroom/releases/download/v2023.3.0/Meshroom-2023.3.0-linux.tar.gz && \
    tar -xzf Meshroom-2023.3.0-linux.tar.gz && \
    mv Meshroom-2023.3.0 meshroom && \
    rm Meshroom-2023.3.0-linux.tar.gz

# Set environment variables
ENV PATH="/opt/meshroom:$PATH"
ENV ALICEVISION_ROOT="/opt/meshroom/aliceVision"

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
