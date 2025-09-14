// Upload functionality with FilePond
class UploadManager {
    constructor() {
        this.pond = null;
        this.selectedDataset = null;
        this.selectedResolution = 'images';
        this.init();
    }

    init() {
        // Initialize FilePond
        const uploadElement = document.getElementById('image-upload');
        if (uploadElement) {
            this.pond = FilePond.create(uploadElement, {
                allowMultiple: true,
                acceptedFileTypes: ['image/*'],
                maxFiles: 100,
                dropOnPage: true,
                dropOnElement: false,
                server: {
                    process: '/api/upload',
                    revert: '/api/revert'
                },
                labelIdle: 'Drag & Drop your images or <span class="filepond--label-action">Browse</span>'
            });

            // Handle file additions
            this.pond.on('addfile', (error, file) => {
                if (!error) {
                    this.updateUploadStatus();
                }
            });

            this.pond.on('removefile', (error, file) => {
                this.updateUploadStatus();
            });
        }

        this.setupEventListeners();
        this.checkGPUStatus();
    }

    setupEventListeners() {
        // Dataset selection
        document.querySelectorAll('.dataset-card').forEach(card => {
            card.addEventListener('click', (e) => {
                if (!e.target.classList.contains('resolution-selector')) {
                    this.selectDataset(card.dataset.dataset);
                }
            });
        });

        // Resolution selectors
        document.querySelectorAll('.resolution-selector').forEach(select => {
            select.addEventListener('change', (e) => {
                e.stopPropagation();
                this.selectedResolution = e.target.value;
                this.selectDataset(e.target.dataset.dataset);
            });
        });

        // Tool selection
        document.querySelectorAll('input[name="tools"]').forEach(checkbox => {
            checkbox.addEventListener('change', () => {
                this.updateUploadStatus();
            });
        });

        // Control buttons
        document.getElementById('start-reconstruction')?.addEventListener('click', () => {
            this.startReconstruction();
        });

        document.getElementById('clear-images')?.addEventListener('click', () => {
            this.clearImages();
        });

        // Upload area click
        document.getElementById('upload-area')?.addEventListener('click', () => {
            document.getElementById('image-upload').click();
        });
    }

    selectDataset(dataset) {
        // Remove previous selection
        document.querySelectorAll('.dataset-card').forEach(card => {
            card.classList.remove('ring-2', 'ring-primary-500', 'bg-primary-50');
        });

        // Highlight selected dataset
        const selectedCard = document.querySelector(`[data-dataset="${dataset}"]`);
        if (selectedCard) {
            selectedCard.classList.add('ring-2', 'ring-primary-500', 'bg-primary-50');
        }

        this.selectedDataset = dataset;
        this.loadDatasetImages();
        this.updateUploadStatus();
    }

    async loadDatasetImages() {
        if (!this.selectedDataset) return;

        try {
            const response = await fetch(`/api/dataset/${this.selectedDataset}/${this.selectedResolution}`);
            const images = await response.json();
            
            // Clear existing files
            this.pond.removeFiles();

            // Add dataset images as preview
            const uploadArea = document.getElementById('upload-area');
            uploadArea.innerHTML = `
                <div class="text-center">
                    <svg class="mx-auto h-12 w-12 text-green-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
                    </svg>
                    <p class="text-lg text-gray-600 mb-2">Dataset "${this.selectedDataset}" loaded</p>
                    <p class="text-sm text-gray-500">${images.length} images from ${this.selectedResolution} folder</p>
                </div>
            `;

        } catch (error) {
            console.error('Failed to load dataset:', error);
        }
    }

    updateUploadStatus() {
        const selectedTools = document.querySelectorAll('input[name="tools"]:checked');
        const hasImages = this.pond?.getFiles().length > 0 || this.selectedDataset;
        const startButton = document.getElementById('start-reconstruction');

        if (startButton) {
            startButton.disabled = !hasImages || selectedTools.length === 0;
            startButton.textContent = this.selectedDataset ? 
                `Reconstruct ${this.selectedDataset} (${this.selectedResolution})` : 
                'Start Reconstruction';
        }
    }

    async startReconstruction() {
        const selectedTools = Array.from(document.querySelectorAll('input[name="tools"]:checked'))
            .map(cb => cb.value);
        
        const maxResolution = document.getElementById('max-resolution').value;

        // Show progress section
        document.getElementById('progress-section').classList.remove('hidden');
        document.getElementById('results-section').classList.add('hidden');

        // Reset progress bars
        selectedTools.forEach(tool => {
            document.getElementById(`progress-${tool}`).style.width = '0%';
            document.getElementById(`status-${tool}`).textContent = 'Starting...';
        });

        try {
            const payload = {
                tools: selectedTools,
                maxResolution: parseInt(maxResolution),
                dataset: this.selectedDataset,
                resolution: this.selectedResolution
            };

            if (!this.selectedDataset && this.pond) {
                // Upload custom images
                payload.images = this.pond.getFiles().map(file => file.file);
            }

            const response = await fetch('/api/reconstruct', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(payload)
            });

            const result = await response.json();
            this.trackReconstruction(result.jobId);

        } catch (error) {
            console.error('Reconstruction failed:', error);
            alert('Failed to start reconstruction. Please try again.');
        }
    }

    async trackReconstruction(jobId) {
        const pollInterval = setInterval(async () => {
            try {
                const response = await fetch(`/api/status/${jobId}`);
                const status = await response.json();

                // Update progress bars
                Object.entries(status.tools).forEach(([tool, data]) => {
                    const progressBar = document.getElementById(`progress-${tool}`);
                    const statusText = document.getElementById(`status-${tool}`);
                    
                    if (progressBar) progressBar.style.width = `${data.progress}%`;
                    if (statusText) statusText.textContent = data.status;
                });

                // Check if all tools are complete
                const allComplete = Object.values(status.tools).every(tool => 
                    tool.status === 'completed' || tool.status === 'failed'
                );

                if (allComplete) {
                    clearInterval(pollInterval);
                    this.showResults(status);
                }

            } catch (error) {
                console.error('Failed to fetch status:', error);
                clearInterval(pollInterval);
            }
        }, 2000);
    }

    showResults(status) {
        document.getElementById('results-section').classList.remove('hidden');
        
        Object.entries(status.tools).forEach(([tool, data]) => {
            if (data.status === 'completed') {
                // Initialize 3D viewer for this tool
                window.viewer3D?.loadModel(tool, data.output);
                
                // Update metrics
                document.getElementById(`points-${tool}`).textContent = data.metrics?.points || 'N/A';
                document.getElementById(`time-${tool}`).textContent = data.metrics?.processingTime || 'N/A';
                document.getElementById(`memory-${tool}`).textContent = data.metrics?.memoryUsed || 'N/A';
            }
        });
    }

    clearImages() {
        if (this.pond) {
            this.pond.removeFiles();
        }
        
        // Reset dataset selection
        document.querySelectorAll('.dataset-card').forEach(card => {
            card.classList.remove('ring-2', 'ring-primary-500', 'bg-primary-50');
        });
        
        this.selectedDataset = null;
        
        // Reset upload area
        const uploadArea = document.getElementById('upload-area');
        uploadArea.innerHTML = `
            <svg class="mx-auto h-12 w-12 text-gray-400 mb-4" stroke="currentColor" fill="none" viewBox="0 0 48 48">
                <path d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
            </svg>
            <p class="text-lg text-gray-600 mb-2">Drag and drop images here</p>
            <p class="text-sm text-gray-500">or click to browse files</p>
        `;
        
        this.updateUploadStatus();
    }

    async checkGPUStatus() {
        try {
            const response = await fetch('/api/gpu-status');
            const status = await response.json();
            
            const gpuStatusElement = document.getElementById('gpu-status');
            const dot = gpuStatusElement.querySelector('.w-2');
            const text = gpuStatusElement.querySelector('span');
            
            if (status.available) {
                dot.className = 'w-2 h-2 bg-green-500 rounded-full';
                text.textContent = `GPU: ${status.name}`;
            } else {
                dot.className = 'w-2 h-2 bg-orange-500 rounded-full';
                text.textContent = 'GPU: CPU Mode';
            }
        } catch (error) {
            console.error('Failed to check GPU status:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.uploadManager = new UploadManager();
});