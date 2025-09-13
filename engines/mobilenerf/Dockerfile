FROM python:3.8-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    build-essential \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install PyTorch CPU version for mobile compatibility
RUN pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Clone MobileNeRF
WORKDIR /opt
RUN git clone https://github.com/google-research/google-research.git && \
    cd google-research && \
    git sparse-checkout init --cone && \
    git sparse-checkout set mobilenerf

# Install dependencies
WORKDIR /opt/google-research/mobilenerf
RUN pip3 install -r requirements.txt

# Additional dependencies
RUN pip3 install \
    numpy \
    opencv-python \
    imageio \
    configargparse \
    tqdm \
    matplotlib \
    plyfile \
    scikit-image

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
