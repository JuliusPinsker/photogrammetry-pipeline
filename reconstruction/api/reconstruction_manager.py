import asyncio
import subprocess
import time
import os
import json
import shutil
from pathlib import Path
from typing import Dict, Any, Callable, Optional
import psutil

from .tools.colmap_tool import ColmapTool
from .tools.openmvs_tool import OpenMVSTool
from .tools.pmvs2_tool import PMVS2Tool
from .tools.alicevision_tool import AliceVisionTool
from .tools.opensfm_tool import OpenSfMTool

class ReconstructionManager:
    """Manages reconstruction processes for multiple tools."""
    
    def __init__(self):
        self.tools = {
            'COLMAP': ColmapTool(),
            'OpenMVS': OpenMVSTool(),
            'PMVS2': PMVS2Tool(),
            'AliceVision': AliceVisionTool(),
            'OpenSfM': OpenSfMTool()
        }
        
        self.active_processes = {}
    
    async def run_tool(
        self,
        tool: str,
        input_path: str,
        output_path: str,
        max_resolution: int = 2048,
        progress_callback: Optional[Callable[[int], None]] = None
    ) -> Dict[str, Any]:
        """Run a specific reconstruction tool."""
        
        if tool not in self.tools:
            raise ValueError(f"Unknown tool: {tool}")
        
        tool_instance = self.tools[tool]
        
        # Create output directory
        os.makedirs(output_path, exist_ok=True)
        
        start_time = time.time()
        process = psutil.Process()
        start_memory = process.memory_info().rss
        
        try:
            # Run the tool
            result = await tool_instance.run(
                input_path=input_path,
                output_path=output_path,
                max_resolution=max_resolution,
                progress_callback=progress_callback
            )
            
            end_time = time.time()
            end_memory = process.memory_info().rss
            
            # Calculate metrics
            processing_time = end_time - start_time
            memory_used = max(end_memory - start_memory, 0)
            
            # Get point count if available
            point_count = self._count_points(result.get('output_file', ''))
            
            return {
                'tool': tool,
                'status': 'completed',
                'output_file': result.get('output_file', ''),
                'metrics': {
                    'processingTime': f"{processing_time:.2f}s",
                    'memoryUsed': f"{memory_used / 1024 / 1024:.1f}MB",
                    'points': point_count,
                    'success': result.get('success', False)
                }
            }
            
        except Exception as e:
            end_time = time.time()
            processing_time = end_time - start_time
            
            return {
                'tool': tool,
                'status': 'failed',
                'output_file': '',
                'error': str(e),
                'metrics': {
                    'processingTime': f"{processing_time:.2f}s",
                    'memoryUsed': '0MB',
                    'points': 0,
                    'success': False
                }
            }
    
    def _count_points(self, output_file: str) -> int:
        """Count points in output file."""
        if not output_file or not os.path.exists(output_file):
            return 0
        
        try:
            if output_file.endswith('.ply'):
                return self._count_ply_points(output_file)
            elif output_file.endswith('.obj'):
                return self._count_obj_vertices(output_file)
            else:
                return 0
        except:
            return 0
    
    def _count_ply_points(self, ply_file: str) -> int:
        """Count points in PLY file."""
        try:
            with open(ply_file, 'r') as f:
                for line in f:
                    if line.startswith('element vertex'):
                        return int(line.split()[-1])
            return 0
        except:
            return 0
    
    def _count_obj_vertices(self, obj_file: str) -> int:
        """Count vertices in OBJ file."""
        try:
            count = 0
            with open(obj_file, 'r') as f:
                for line in f:
                    if line.startswith('v '):
                        count += 1
            return count
        except:
            return 0
    
    def get_tool_status(self) -> Dict[str, Any]:
        """Get status of all reconstruction tools."""
        status = {}
        
        for tool_name, tool_instance in self.tools.items():
            try:
                available = tool_instance.check_availability()
                version = tool_instance.get_version()
                
                status[tool_name] = {
                    'available': available,
                    'version': version,
                    'type': tool_instance.get_type(),
                    'description': tool_instance.get_description()
                }
            except Exception as e:
                status[tool_name] = {
                    'available': False,
                    'version': 'unknown',
                    'error': str(e)
                }
        
        return status
    
    def stop_all_processes(self):
        """Stop all active reconstruction processes."""
        for process_id, process in self.active_processes.items():
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
        
        self.active_processes.clear()