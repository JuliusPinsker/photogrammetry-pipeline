# 3D Reconstruction Comparison Platform

A dockerized platform to compare 5 non-neural 3D reconstruction tools using a modern web interface.

## Features

- **🔧 5 Reconstruction Tools**: COLMAP, OpenMVS, PMVS2, AliceVision, OpenSfM
- **🎨 Modern Web Interface**: Hugo + TailwindCSS frontend with drag-and-drop
- **🖥️ GPU Auto-Detection**: Automatic CUDA support detection
- **📊 Real-time Visualization**: Three.js-powered 3D model viewer
- **🐳 Fully Dockerized**: Complete containerized environment
- **📱 Responsive Design**: Mobile-friendly interface
- **🧪 Headless Testing**: Automated testing with Selenium

## Quick Start

### Prerequisites

- Docker Engine ≥ 24.0
- Docker Compose
- NVIDIA Container Toolkit (for GPU support)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/JuliusPinsker/photogrammetry-pipeline.git
   cd photogrammetry-pipeline
   ```

2. **Setup environment variables**
   ```bash
   cp .env.example .env
   # Edit .env to configure GPU and other settings
   ```

3. **Build and start services**
   ```bash
   # CPU-only mode
   docker-compose up --build
   
   # GPU-enabled mode (requires NVIDIA Docker)
   GPU_ENABLED=true docker-compose up --build
   ```

4. **Access the platform**
   - Frontend: http://localhost:1313
   - API docs: http://localhost:8000/docs

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    Frontend     │    │ Reconstruction  │    │    Testing      │
│   Hugo + CSS    │◄──►│   FastAPI       │    │   Selenium      │
│   Port: 1313    │    │   Port: 8000    │    │   Pytest       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                    ┌─────────────────┐
                    │   Docker        │
                    │   Volumes       │
                    └─────────────────┘
```

## Dataset Structure

Place your datasets in the following structure:

```
360_scenes/
├── bicycle/
│   ├── images/          # Normal resolution
│   ├── images_2/        # 2K resolution  
│   ├── images_4/        # 4K resolution
│   ├── images_8/        # 8K resolution
│   ├── sparse/          # Sparse images
│   └── poses_bounds.npy # Camera poses (optional)
├── bonsai/
├── counter/
├── flowers/
├── garden/
├── kitchen/
└── treehill/
```

## Usage

### Web Interface

1. **Select Tools**: Choose which reconstruction tools to compare
2. **Upload Images**: Drag and drop images or select a pre-loaded dataset
3. **Configure**: Set maximum resolution and other parameters
4. **Reconstruct**: Start the reconstruction process
5. **Compare**: View and compare 3D models in real-time

### API Usage

```python
import requests

# Start reconstruction
response = requests.post('http://localhost:8000/reconstruct', json={
    'tools': ['COLMAP', 'OpenMVS'],
    'dataset': 'bicycle',
    'resolution': 'images_2',
    'maxResolution': 2048
})

job_id = response.json()['jobId']

# Check status
status = requests.get(f'http://localhost:8000/status/{job_id}')
print(status.json())
```

## Testing

Run the complete test suite:

```bash
# Run all tests
docker-compose --profile testing up --build testing

# Run specific tests
docker-compose run --rm testing pytest tests/test_reconstruction.py -v

# Generate HTML report
docker-compose run --rm testing pytest tests/ --html=reports/test_report.html
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GPU_ENABLED` | Enable GPU acceleration | `false` |
| `DATASET_PATH` | Path to datasets | `/datasets` |
| `MAX_IMAGE_SIZE` | Maximum image resolution | `2048` |
| `FRONTEND_PORT` | Frontend port | `1313` |

### Tool Versions (Pinned)

| Tool | Repository | Commit | Docker Base |
|------|------------|--------|-------------|
| COLMAP | [colmap/colmap](https://github.com/colmap/colmap) | `d2ab8db` | Ubuntu 22.04 |
| OpenMVS | [cdcseacave/openMVS](https://github.com/cdcseacave/openMVS) | `c5c4aa0` | Ubuntu 22.04 |
| PMVS2 | [pmoulon/CMVS-PMVS](https://github.com/pmoulon/CMVS-PMVS) | `a8a35d1` | Ubuntu 22.04 |
| AliceVision | [alicevision/meshroom](https://github.com/alicevision/meshroom) | `b2c6a10` | Ubuntu 22.04 |
| OpenSfM | [mapillary/opensfm](https://github.com/mapillary/opensfm) | `e91d6c3` | Ubuntu 22.04 |

## Development

### Frontend Development

```bash
cd frontend
npm install
npm run watch:css  # Watch TailwindCSS changes
hugo server --bind 0.0.0.0 --port 1313
```

### Backend Development

```bash
cd reconstruction
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Adding New Tools

1. Create a new tool class in `reconstruction/api/tools/`
2. Inherit from `ReconstructionTool`
3. Implement required methods
4. Add to `ReconstructionManager`

## GPU Support

### NVIDIA Setup

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update && sudo apt-get install -y nvidia-docker2
sudo systemctl restart docker
```

### Verification

```bash
# Test GPU detection
docker-compose run --rm reconstruction nvidia-smi

# Check GPU status via API
curl http://localhost:8000/gpu-status
```

## Performance Comparison

The platform provides detailed metrics for each tool:

- **Processing Time**: Total reconstruction time
- **Memory Usage**: Peak memory consumption
- **Point Count**: Number of 3D points generated
- **Quality Metrics**: Reconstruction accuracy (if ground truth available)

## Troubleshooting

### Common Issues

1. **GPU not detected**
   ```bash
   # Check NVIDIA drivers
   nvidia-smi
   
   # Verify Docker GPU support
   docker run --rm --gpus all nvidia/cuda:11.0-base nvidia-smi
   ```

2. **Frontend not loading**
   ```bash
   # Check service logs
   docker-compose logs frontend
   
   # Verify port availability
   netstat -tlnp | grep 1313
   ```

3. **Reconstruction fails**
   ```bash
   # Check reconstruction service logs
   docker-compose logs reconstruction
   
   # Verify tool availability
   curl http://localhost:8000/tools
   ```

### Debugging

```bash
# Access container shell
docker-compose exec frontend sh
docker-compose exec reconstruction bash

# View real-time logs
docker-compose logs -f
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## References

- [COLMAP Documentation](https://colmap.github.io/)
- [OpenMVS Documentation](https://github.com/cdcseacave/openMVS)
- [Hugo Documentation](https://gohugo.io/documentation/)
- [TailwindCSS Documentation](https://tailwindcss.com/docs)
- [Three.js Documentation](https://threejs.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)

## Citation

If you use this platform in your research, please cite:

```bibtex
@software{photogrammetry_platform_2025,
  title={3D Reconstruction Comparison Platform},
  author={Julius Pinsker},
  year={2025},
  url={https://github.com/JuliusPinsker/photogrammetry-pipeline}
}
```