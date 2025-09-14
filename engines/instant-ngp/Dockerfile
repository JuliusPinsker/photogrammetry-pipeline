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
    libosmesa6-dev \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Instant-NGP - pinned to stable commit (Sept 2025)
WORKDIR /opt
RUN git clone --recursive https://github.com/NVlabs/instant-ngp.git && \
    cd instant-ngp && \
    git checkout be57ba8b80e2ba4925af6c0014fd153cd62fde2c && \
    git submodule update --init --recursive && \
    cmake . -B build && \
    cmake --build build --config RelWithDebInfo -j$(nproc)

# Install Python dependencies
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
RUN pip3 install \
    numpy \
    opencv-python \
    imageio \
    imageio-ffmpeg \
    configargparse \
    tensorboard \
    tqdm \
    matplotlib \
    plyfile \
    trimesh

# Set environment variables
ENV CUDA_HOME=/usr/local/cuda
ENV PATH="/opt/instant-ngp/build:$PATH"

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
