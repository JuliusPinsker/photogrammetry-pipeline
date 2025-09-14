FROM ubuntu:20.04

# Avoid interactive prompts during installation
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    cmake \
    build-essential \
    libboost-program-options-dev \
    libboost-filesystem-dev \
    libboost-graph-dev \
    libboost-system-dev \
    libboost-test-dev \
    libeigen3-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libceres-dev \
    python3 \
    python3-pip \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Download and compile COLMAP - pinned to stable commit (3.8 release)
WORKDIR /opt
RUN git clone https://github.com/colmap/colmap.git && \
    cd colmap && \
    git checkout 3.8 && \
    mkdir build && \
    cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    make install

# Create workspace directory
WORKDIR /workspace

# Copy reconstruction script
COPY reconstruct.py /workspace/
COPY requirements.txt /workspace/
RUN pip3 install -r requirements.txt

# Make script executable
RUN chmod +x /workspace/reconstruct.py

CMD ["python3", "/workspace/reconstruct.py"]
