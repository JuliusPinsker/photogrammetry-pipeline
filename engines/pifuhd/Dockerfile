FROM nvidia/cuda:11.8-cudnn8-devel-ubuntu20.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    python3 \
    python3-pip \
    python3-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch with CUDA support
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# Clone PIFuHD
WORKDIR /opt
RUN git clone https://github.com/facebookresearch/pifuhd.git
WORKDIR /opt/pifuhd

# Install dependencies
RUN pip3 install -r requirements.txt

# Additional dependencies
RUN pip3 install \
    trimesh \
    scikit-image \
    opencv-python \
    matplotlib \
    tqdm \
    imageio

# Download pre-trained models
RUN mkdir -p checkpoints && \
    cd checkpoints && \
    wget https://dl.fbaipublicfiles.com/pifuhd/checkpoints/pifuhd.pt

# Set environment variables
ENV CUDA_HOME=/usr/local/cuda

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
