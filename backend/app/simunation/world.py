import random
from typing import List, Dict, Tuple, Any

class Tile:
    def __init__(self, x: int, y: int, tile_type: str):
        self.x: int = x
        self.y: int = y
        self.type: str = tile_type  # "Farm", "Forest", "River", "Village", "Town", "Mine", "Mountain"
        
        # Local resources capacity
        self.resources: Dict[str, float] = {
            "food_multiplier": 1.0,
            "raw_materials": 0.0
        }
        
        if tile_type == "Farm":
            self.resources["food_multiplier"] = 1.5
        elif tile_type == "Mine":
            self.resources["raw_materials"] = 1000.0
        elif tile_type == "Forest":
            self.resources["raw_materials"] = 500.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "x": self.x,
            "y": self.y,
            "type": self.type
        }

class MapGrid:
    def __init__(self, width: int = 100, height: int = 100):
        self.width: int = width
        self.height: int = height
        self.grid: List[List[Tile]] = []
        self._generate_map()

    def _generate_map(self):
        """Generates structured geographic layout on a 100x100 grid."""
        river_cols = [50 + int(10 * (y / self.height)) + (1 if y % 15 == 0 else 0) for y in range(self.height)]
        
        # Town and village centers
        towns = [(30, 30), (70, 75)]
        villages = [(20, 75), (80, 25), (45, 50)]
        mountains = [(85, 85), (90, 80), (10, 15), (15, 10)]

        for y in range(self.height):
            row = []
            for x in range(self.width):
                # Default is Plain / Forest
                t_type = "Forest" if random.random() < 0.25 else "Farm"

                # Rivers
                if abs(x - river_cols[y]) < 3:
                    t_type = "River"
                # Mountains
                elif any(abs(x - mx) + abs(y - my) < 8 for mx, my in mountains):
                    # Mineral mines scattered in mountains
                    t_type = "Mine" if random.random() < 0.25 else "Mountain"
                # Towns
                elif any(abs(x - tx) + abs(y - ty) < 6 for tx, ty in towns):
                    t_type = "Town"
                # Villages
                elif any(abs(x - vx) + abs(y - vy) < 4 for vx, vy in villages):
                    t_type = "Village"

                row.append(Tile(x, y, t_type))
            self.grid.append(row)

    def get_tile(self, x: int, y: int) -> Tile:
        # Clamped boundaries
        x = max(0, min(self.width - 1, x))
        y = max(0, min(self.height - 1, y))
        return self.grid[y][x]

    def find_nearest_tile_type(self, start_x: int, start_y: int, tile_type: str) -> Tuple[int, int]:
        """Finds closest tile of a specific type (BFS search)."""
        visited = set()
        queue = [(start_x, start_y)]
        
        while queue:
            cx, cy = queue.pop(0)
            if (cx, cy) in visited:
                continue
            visited.add((cx, cy))
            
            # Check clamp boundaries
            if 0 <= cx < self.width and 0 <= cy < self.height:
                if self.grid[cy][cx].type == tile_type:
                    return cx, cy
                
                # Add neighbors
                for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                    nx, ny = cx + dx, cy + dy
                    if 0 <= nx < self.width and 0 <= ny < self.height and (nx, ny) not in visited:
                        queue.append((nx, ny))
                        
        return start_x, start_y  # Fallback
