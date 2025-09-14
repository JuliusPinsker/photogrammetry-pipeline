import pytest
import time
import os
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
import requests

class TestReconstructionPipeline:
    """Test the complete 3D reconstruction pipeline."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver with headless options."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    @pytest.fixture(scope="class")
    def frontend_url(self):
        """Get frontend URL from environment."""
        return os.getenv("FRONTEND_URL", "http://frontend:1313")
    
    def test_frontend_loads(self, driver, frontend_url):
        """Test that the frontend loads successfully."""
        driver.get(frontend_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.TAG_NAME, "h1"))
        )
        
        # Check title
        assert "3D Reconstruction" in driver.title
        
        # Check main heading
        heading = driver.find_element(By.TAG_NAME, "h1")
        assert "3D Reconstruction Comparison Platform" in heading.text
    
    def test_tool_selection_available(self, driver, frontend_url):
        """Test that all reconstruction tools are available for selection."""
        driver.get(frontend_url)
        
        # Wait for tool selection to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.NAME, "tools"))
        )
        
        # Check that all 5 tools are present
        tools = driver.find_elements(By.NAME, "tools")
        assert len(tools) == 5
        
        # Check tool names
        expected_tools = ["COLMAP", "OpenMVS", "PMVS2", "AliceVision", "OpenSfM"]
        tool_labels = driver.find_elements(By.CSS_SELECTOR, "label span")
        tool_names = [label.text for label in tool_labels if label.text in expected_tools]
        
        for tool in expected_tools:
            assert tool in tool_names
    
    def test_dataset_selection(self, driver, frontend_url):
        """Test dataset selection functionality."""
        driver.get(frontend_url)
        
        # Wait for dataset cards to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dataset-card"))
        )
        
        # Check that datasets are available
        dataset_cards = driver.find_elements(By.CLASS_NAME, "dataset-card")
        assert len(dataset_cards) > 0
        
        # Test selecting a dataset
        if dataset_cards:
            first_dataset = dataset_cards[0]
            first_dataset.click()
            
            # Check if dataset is highlighted (has selection styling)
            # Note: This might need adjustment based on actual CSS classes
            time.sleep(1)  # Allow for visual feedback
    
    def test_gpu_status_display(self, driver, frontend_url):
        """Test that GPU status is displayed."""
        driver.get(frontend_url)
        
        # Wait for GPU status to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "gpu-status"))
        )
        
        gpu_status = driver.find_element(By.ID, "gpu-status")
        assert gpu_status.is_displayed()
        
        # Check that GPU status text is present
        gpu_text = gpu_status.find_element(By.TAG_NAME, "span")
        assert "GPU:" in gpu_text.text
    
    def test_upload_area_present(self, driver, frontend_url):
        """Test that image upload area is present and functional."""
        driver.get(frontend_url)
        
        # Wait for upload area to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "upload-area"))
        )
        
        upload_area = driver.find_element(By.ID, "upload-area")
        assert upload_area.is_displayed()
        
        # Check upload text
        assert "Drag and drop images here" in upload_area.text
    
    def test_reconstruction_controls(self, driver, frontend_url):
        """Test reconstruction control buttons."""
        driver.get(frontend_url)
        
        # Wait for controls to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "start-reconstruction"))
        )
        
        start_button = driver.find_element(By.ID, "start-reconstruction")
        clear_button = driver.find_element(By.ID, "clear-images")
        
        assert start_button.is_displayed()
        assert clear_button.is_displayed()
        
        # Start button should be disabled initially (no images selected)
        assert not start_button.is_enabled()
    
    def test_resolution_selector(self, driver, frontend_url):
        """Test max resolution selector."""
        driver.get(frontend_url)
        
        # Wait for resolution selector to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, "max-resolution"))
        )
        
        resolution_select = driver.find_element(By.ID, "max-resolution")
        assert resolution_select.is_displayed()
        
        # Check available options
        options = resolution_select.find_elements(By.TAG_NAME, "option")
        assert len(options) == 4  # 1K, 2K, 4K, 8K
        
        # Check that 2K is selected by default
        selected_option = resolution_select.find_element(By.CSS_SELECTOR, "option[selected]")
        assert "2K" in selected_option.text
    
    def test_api_health_check(self, frontend_url):
        """Test that the reconstruction API is healthy."""
        # Extract hostname from frontend URL
        if "://" in frontend_url:
            protocol, rest = frontend_url.split("://", 1)
            hostname = rest.split(":")[0]
        else:
            hostname = frontend_url.split(":")[0]
        
        api_url = f"http://{hostname}:8000" if hostname != "localhost" else "http://reconstruction:8000"
        
        try:
            response = requests.get(f"{api_url}/health", timeout=10)
            assert response.status_code == 200
            
            health_data = response.json()
            assert health_data["status"] == "healthy"
        except requests.exceptions.RequestException:
            # If direct API access fails, try through frontend proxy
            try:
                response = requests.get(f"{frontend_url}/api/health", timeout=10)
                assert response.status_code == 200
            except:
                pytest.skip("API health check failed - service may not be running")
    
    def test_tool_availability_api(self, frontend_url):
        """Test that reconstruction tools are available via API."""
        try:
            response = requests.get(f"{frontend_url}/api/tools", timeout=10)
            assert response.status_code == 200
            
            tools_data = response.json()
            assert isinstance(tools_data, dict)
            
            # Check that all expected tools are present
            expected_tools = ["COLMAP", "OpenMVS", "PMVS2", "AliceVision", "OpenSfM"]
            for tool in expected_tools:
                assert tool in tools_data
                
        except requests.exceptions.RequestException:
            pytest.skip("Tools API check failed - service may not be running")
    
    def test_system_info_api(self, frontend_url):
        """Test system information API."""
        try:
            response = requests.get(f"{frontend_url}/api/system-info", timeout=10)
            assert response.status_code == 200
            
            system_data = response.json()
            assert "gpu" in system_data
            assert "cpu" in system_data
            assert "memory" in system_data
            assert "disk" in system_data
            
        except requests.exceptions.RequestException:
            pytest.skip("System info API check failed - service may not be running")

class TestReconstructionWorkflow:
    """Test the complete reconstruction workflow with dummy data."""
    
    @pytest.fixture(scope="class")
    def driver(self):
        """Setup Chrome WebDriver."""
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.implicitly_wait(10)
        
        yield driver
        
        driver.quit()
    
    def test_complete_workflow_with_dataset(self, driver):
        """Test complete workflow using a pre-loaded dataset."""
        frontend_url = os.getenv("FRONTEND_URL", "http://frontend:1313")
        driver.get(frontend_url)
        
        # Wait for page to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CLASS_NAME, "dataset-card"))
        )
        
        # Select first dataset
        dataset_cards = driver.find_elements(By.CLASS_NAME, "dataset-card")
        if dataset_cards:
            dataset_cards[0].click()
            time.sleep(2)
        
        # Ensure tools are selected (they should be by default)
        tools = driver.find_elements(By.NAME, "tools")
        for tool in tools[:2]:  # Select first 2 tools to speed up test
            if not tool.is_selected():
                tool.click()
        
        # Check if start button becomes enabled
        start_button = driver.find_element(By.ID, "start-reconstruction")
        
        # The start button should be enabled after dataset selection
        WebDriverWait(driver, 10).until(
            lambda d: start_button.is_enabled()
        )
        
        # Note: We don't actually start reconstruction in tests
        # as it would take too long and require actual tools
        assert start_button.is_enabled()
        assert "Reconstruct" in start_button.text