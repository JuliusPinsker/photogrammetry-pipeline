// 3D Model Viewer using Three.js
class Viewer3D {
    constructor() {
        this.viewers = new Map();
        this.init();
    }

    init() {
        // Initialize viewers for each tool
        const tools = ['COLMAP', 'OpenMVS', 'PMVS2', 'AliceVision', 'OpenSfM'];
        tools.forEach(tool => {
            this.initViewer(tool);
        });
    }

    initViewer(tool) {
        const container = document.getElementById(`viewer-${tool}`);
        if (!container) return;

        // Scene setup
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf5f5f5);

        // Camera setup
        const camera = new THREE.PerspectiveCamera(
            75,
            container.clientWidth / container.clientHeight,
            0.1,
            1000
        );
        camera.position.set(0, 0, 5);

        // Renderer setup
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setSize(container.clientWidth, container.clientHeight);
        renderer.shadowMap.enabled = true;
        renderer.shadowMap.type = THREE.PCFSoftShadowMap;
        
        container.appendChild(renderer.domElement);

        // Controls
        const controls = new THREE.OrbitControls(camera, renderer.domElement);
        controls.enableDamping = true;
        controls.dampingFactor = 0.05;
        controls.enableZoom = true;
        controls.enablePan = true;

        // Lighting
        const ambientLight = new THREE.AmbientLight(0x404040, 0.6);
        scene.add(ambientLight);

        const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
        directionalLight.position.set(10, 10, 5);
        directionalLight.castShadow = true;
        directionalLight.shadow.mapSize.width = 2048;
        directionalLight.shadow.mapSize.height = 2048;
        scene.add(directionalLight);

        // Grid helper
        const gridHelper = new THREE.GridHelper(10, 10, 0x888888, 0xcccccc);
        scene.add(gridHelper);

        // Store viewer components
        this.viewers.set(tool, {
            scene,
            camera,
            renderer,
            controls,
            container,
            pointCloud: null,
            mesh: null
        });

        // Animation loop
        const animate = () => {
            requestAnimationFrame(animate);
            controls.update();
            renderer.render(scene, camera);
        };
        animate();

        // Handle window resize
        window.addEventListener('resize', () => {
            this.handleResize(tool);
        });

        // Show placeholder
        this.showPlaceholder(tool);
    }

    showPlaceholder(tool) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        // Create placeholder geometry
        const geometry = new THREE.BoxGeometry(2, 2, 2);
        const material = new THREE.MeshLambertMaterial({ 
            color: 0xdddddd,
            transparent: true,
            opacity: 0.3
        });
        const cube = new THREE.Mesh(geometry, material);
        
        // Add wireframe
        const wireframe = new THREE.WireframeGeometry(geometry);
        const line = new THREE.LineSegments(wireframe, 
            new THREE.LineBasicMaterial({ color: 0x999999 })
        );
        
        const group = new THREE.Group();
        group.add(cube);
        group.add(line);
        
        viewer.scene.add(group);
        viewer.placeholder = group;

        // Add loading text
        this.showLoadingText(tool, 'Waiting for reconstruction...');
    }

    showLoadingText(tool, text) {
        const container = this.viewers.get(tool)?.container;
        if (!container) return;

        // Remove existing loading overlay
        const existingOverlay = container.querySelector('.loading-overlay');
        if (existingOverlay) {
            existingOverlay.remove();
        }

        // Create loading overlay
        const overlay = document.createElement('div');
        overlay.className = 'loading-overlay absolute inset-0 bg-black bg-opacity-50 flex items-center justify-center text-white text-sm';
        overlay.innerHTML = `
            <div class="text-center">
                <div class="animate-spin rounded-full h-8 w-8 border-b-2 border-white mx-auto mb-2"></div>
                <div>${text}</div>
            </div>
        `;
        
        container.style.position = 'relative';
        container.appendChild(overlay);
    }

    hideLoadingText(tool) {
        const container = this.viewers.get(tool)?.container;
        if (!container) return;

        const overlay = container.querySelector('.loading-overlay');
        if (overlay) {
            overlay.remove();
        }
    }

    async loadModel(tool, outputPath) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        this.showLoadingText(tool, 'Loading 3D model...');

        try {
            // Remove placeholder
            if (viewer.placeholder) {
                viewer.scene.remove(viewer.placeholder);
                viewer.placeholder = null;
            }

            // Remove existing models
            if (viewer.pointCloud) {
                viewer.scene.remove(viewer.pointCloud);
                viewer.pointCloud = null;
            }
            if (viewer.mesh) {
                viewer.scene.remove(viewer.mesh);
                viewer.mesh = null;
            }

            // Determine file type and load accordingly
            if (outputPath.endsWith('.ply')) {
                await this.loadPLY(tool, outputPath);
            } else if (outputPath.endsWith('.obj')) {
                await this.loadOBJ(tool, outputPath);
            } else {
                throw new Error('Unsupported file format');
            }

            // Fit camera to model
            this.fitCameraToModel(tool);
            
            this.hideLoadingText(tool);

        } catch (error) {
            console.error(`Failed to load model for ${tool}:`, error);
            this.showError(tool, 'Failed to load 3D model');
        }
    }

    async loadPLY(tool, path) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        return new Promise((resolve, reject) => {
            const loader = new THREE.PLYLoader();
            loader.load(
                `/results/${path}`,
                (geometry) => {
                    // Create point cloud
                    const material = new THREE.PointsMaterial({
                        size: 0.01,
                        vertexColors: geometry.hasAttribute('color')
                    });
                    
                    const pointCloud = new THREE.Points(geometry, material);
                    viewer.scene.add(pointCloud);
                    viewer.pointCloud = pointCloud;
                    
                    resolve(geometry);
                },
                (progress) => {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    this.showLoadingText(tool, `Loading: ${percent}%`);
                },
                (error) => {
                    reject(error);
                }
            );
        });
    }

    async loadOBJ(tool, path) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        return new Promise((resolve, reject) => {
            const loader = new THREE.OBJLoader();
            loader.load(
                `/results/${path}`,
                (object) => {
                    // Apply material to mesh
                    object.traverse((child) => {
                        if (child.isMesh) {
                            child.material = new THREE.MeshLambertMaterial({
                                color: 0x888888,
                                side: THREE.DoubleSide
                            });
                        }
                    });
                    
                    viewer.scene.add(object);
                    viewer.mesh = object;
                    
                    resolve(object);
                },
                (progress) => {
                    const percent = Math.round((progress.loaded / progress.total) * 100);
                    this.showLoadingText(tool, `Loading: ${percent}%`);
                },
                (error) => {
                    reject(error);
                }
            );
        });
    }

    fitCameraToModel(tool) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        const model = viewer.pointCloud || viewer.mesh;
        if (!model) return;

        // Calculate bounding box
        const box = new THREE.Box3().setFromObject(model);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());

        // Position camera
        const maxDim = Math.max(size.x, size.y, size.z);
        const distance = maxDim * 2;
        
        viewer.camera.position.copy(center);
        viewer.camera.position.z += distance;
        viewer.camera.lookAt(center);

        // Update controls
        viewer.controls.target.copy(center);
        viewer.controls.update();
    }

    showError(tool, message) {
        const container = this.viewers.get(tool)?.container;
        if (!container) return;

        this.hideLoadingText(tool);

        const errorOverlay = document.createElement('div');
        errorOverlay.className = 'error-overlay absolute inset-0 bg-red-100 flex items-center justify-center text-red-800 text-sm';
        errorOverlay.innerHTML = `
            <div class="text-center">
                <svg class="mx-auto h-8 w-8 text-red-500 mb-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                <div>${message}</div>
            </div>
        `;
        
        container.appendChild(errorOverlay);
    }

    handleResize(tool) {
        const viewer = this.viewers.get(tool);
        if (!viewer) return;

        const container = viewer.container;
        const width = container.clientWidth;
        const height = container.clientHeight;

        viewer.camera.aspect = width / height;
        viewer.camera.updateProjectionMatrix();
        viewer.renderer.setSize(width, height);
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.viewer3D = new Viewer3D();
});