# Multi-stage build with conditional GPU support
ARG GPU_AVAILABLE=false

# GPU-enabled base image
FROM nvidia/cuda:12.1.1-cudnn8-devel-ubuntu22.04 AS gpu-base
ENV DEBIAN_FRONTEND=noninteractive

# CPU-only base image
FROM ubuntu:22.04 AS cpu-base
ENV DEBIAN_FRONTEND=noninteractive

# Select base image based on GPU availability
FROM ${GPU_AVAILABLE:+gpu-base} AS base

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    wget \
    curl \
    pkg-config \
    libeigen3-dev \
    libboost-all-dev \
    libsuitesparse-dev \
    libfreeimage-dev \
    libmetis-dev \
    libgoogle-glog-dev \
    libgflags-dev \
    libglew-dev \
    qtbase5-dev \
    libqt5opengl5-dev \
    libcgal-dev \
    libcgal-qt5-dev \
    python3 \
    python3-pip \
    python3-dev \
    libopencv-dev \
    libtbb-dev \
    libomp-dev \
    libatlas-base-dev \
    liblapack-dev \
    libblas-dev \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    fastapi==0.104.1 \
    uvicorn[standard]==0.24.0 \
    pydantic==2.5.0 \
    numpy==1.24.3 \
    opencv-python==4.8.1.78 \
    Pillow==10.1.0 \
    psutil==5.9.6 \
    aiofiles==23.2.1

# Set working directory
WORKDIR /app

# Build COLMAP
FROM base AS colmap-build
RUN git clone https://github.com/colmap/colmap.git /tmp/colmap
WORKDIR /tmp/colmap
RUN git checkout d2ab8db
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    make install

# Build OpenMVS
FROM base AS openmvs-build
RUN git clone https://github.com/cdcseacave/openMVS.git /tmp/openMVS
WORKDIR /tmp/openMVS
RUN git checkout c5c4aa0
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    make install

# Build PMVS2
FROM base AS pmvs2-build
RUN git clone https://github.com/pmoulon/CMVS-PMVS.git /tmp/CMVS-PMVS
WORKDIR /tmp/CMVS-PMVS
RUN git checkout a8a35d1
RUN mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release && \
    make -j$(nproc) && \
    make install

# Build AliceVision (Meshroom)
FROM base AS alicevision-build
RUN git clone --recursive https://github.com/alicevision/meshroom.git /tmp/meshroom
WORKDIR /tmp/meshroom
RUN git checkout b2c6a10
# Note: AliceVision requires complex build process, simplified for demo
RUN pip3 install -e .

# Build OpenSfM
FROM base AS opensfm-build
RUN git clone https://github.com/mapillary/opensfm.git /tmp/opensfm
WORKDIR /tmp/opensfm
RUN git checkout e91d6c3
RUN pip3 install -e .

# Final runtime image
FROM base AS runtime

# Copy built tools from build stages
COPY --from=colmap-build /usr/local/bin/colmap /usr/local/bin/
COPY --from=colmap-build /usr/local/lib/libcolmap* /usr/local/lib/
COPY --from=openmvs-build /usr/local/bin/*MVS* /usr/local/bin/
COPY --from=openmvs-build /usr/local/lib/libOpenMVS* /usr/local/lib/
COPY --from=pmvs2-build /usr/local/bin/pmvs2 /usr/local/bin/
COPY --from=pmvs2-build /usr/local/bin/cmvs /usr/local/bin/
COPY --from=alicevision-build /tmp/meshroom /opt/meshroom
COPY --from=opensfm-build /tmp/opensfm /opt/opensfm

# Update library cache
RUN ldconfig

# Copy application code
COPY . /app
WORKDIR /app

# Create necessary directories
RUN mkdir -p /datasets /results /test_data

# Add startup script
COPY scripts/startup.sh /app/startup.sh
RUN chmod +x /app/startup.sh

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["/app/startup.sh"]