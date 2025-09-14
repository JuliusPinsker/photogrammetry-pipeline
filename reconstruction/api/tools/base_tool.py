from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Callable

class ReconstructionTool(ABC):
    """Abstract base class for 3D reconstruction tools."""
    
    @abstractmethod
    async def run(
        self,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run the reconstruction tool."""
        pass
    
    @abstractmethod
    def check_availability(self) -> bool:
        """Check if the tool is available and properly installed."""
        pass
    
    @abstractmethod
    def get_version(self) -> str:
        """Get the tool version."""
        pass
    
    @abstractmethod
    def get_type(self) -> str:
        """Get the tool type (e.g., 'SfM', 'MVS', 'Combined')."""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """Get a brief description of the tool."""
        pass