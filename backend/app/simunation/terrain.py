import numpy as np
import random
from typing import Tuple, Optional

class TerrainGenerator:
    """Procedural terrain heightmap using layered noise"""
    
    def __init__(self, width: int, height: int, seed: Optional[int] = None):
        if seed is not None:
            np.random.seed(seed)
            random.seed(seed)
        
        self.width = width
        self.height = height
        self.heightmap = self._generate_heightmap()
        
    def _generate_heightmap(self) -> np.ndarray:
        """Generate smooth terrain using simple averaging passes"""
        base = np.random.rand(self.height, self.width)
        
        heightmap = base.copy()
        for _ in range(8):
            heightmap = (heightmap + 
                         np.roll(heightmap, 1, axis=0) + 
                         np.roll(heightmap, -1, axis=0) +
                         np.roll(heightmap, 1, axis=1) + 
                         np.roll(heightmap, -1, axis=1)) / 5.0
        
        min_val = heightmap.min()
        max_val = heightmap.max()
        if max_val > min_val:
            heightmap = (heightmap - min_val) / (max_val - min_val)
        
        heightmap = heightmap * 6.0  # Max height 6 units
        return heightmap
    
    def get_height(self, x: float, y: float) -> float:
        """Sample height at world coordinates (bilinear interpolation)"""
        x = max(0.0, min(self.width - 1.001, x))
        y = max(0.0, min(self.height - 1.001, y))
        
        x0, y0 = int(x), int(y)
        x1, y1 = x0 + 1, y0 + 1
        
        fx, fy = x - x0, y - y0
        
        h00 = self.heightmap[y0, x0]
        h10 = self.heightmap[y0, x1]
        h01 = self.heightmap[y1, x0]
        h11 = self.heightmap[y1, x1]
        
        return (h00 * (1 - fx) * (1 - fy) +
                h10 * fx * (1 - fy) +
                h01 * (1 - fx) * fy +
                h11 * fx * fy)
    
    def get_normal(self, x: float, y: float) -> Tuple[float, float, float]:
        """Calculate surface normal at point for proper building orientation"""
        h = 0.5
        hL = self.get_height(x - h, y)
        hR = self.get_height(x + h, y)
        hD = self.get_height(x, y - h)
        hU = self.get_height(x, y + h)
        
        normal = np.array([hL - hR, 2.0, hD - hU])
        norm = np.linalg.norm(normal)
        if norm > 0:
            normal = normal / norm
        else:
            normal = np.array([0.0, 1.0, 0.0])
        return float(normal[0]), float(normal[1]), float(normal[2])
