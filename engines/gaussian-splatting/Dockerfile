FROM nvidia/cuda:11.8-cudnn8-devel-ubuntu20.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential \
    python3 \
    python3-pip \
    python3-dev \
    libeigen3-dev \
    libglfw3-dev \
    libglew-dev \
    libxinerama-dev \
    libxcursor-dev \
    libxi-dev \
    libgl1-mesa-dev \
    libglu1-mesa-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Clone and install 3D Gaussian Splatting
WORKDIR /opt
RUN git clone https://github.com/graphdeco-inria/gaussian-splatting --recursive
WORKDIR /opt/gaussian-splatting

# Install submodules
RUN pip3 install -r requirements.txt

# Install simple-knn
RUN pip3 install /opt/gaussian-splatting/submodules/simple-knn

# Install diff-gaussian-rasterization
RUN pip3 install /opt/gaussian-splatting/submodules/diff-gaussian-rasterization

# Set environment variables
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="/opt/gaussian-splatting:$PATH"

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
