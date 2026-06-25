import random
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass, field
from enum import Enum, auto


class TileType(Enum):
    FARM = auto()
    FOREST = auto()
    RIVER = auto()
    VILLAGE = auto()
    TOWN = auto()
    MINE = auto()
    MOUNTAIN = auto()


TILE_PRODUCTION = {
    TileType.FARM: {"food": 8.0, "raw_materials": 0.5},
    TileType.FOREST: {"food": 2.0, "raw_materials": 4.0, "wood": 6.0},
    TileType.RIVER: {"food": 3.0, "water": 10.0},
    TileType.VILLAGE: {"food": 1.0, "services": 2.0},
    TileType.TOWN: {"food": 0.5, "services": 5.0, "trade": 8.0},
    TileType.MINE: {"raw_materials": 10.0, "minerals": 6.0},
    TileType.MOUNTAIN: {"raw_materials": 1.0, "minerals": 2.0},
}

TILE_COLORS = {
    TileType.FARM: "#7CB342",
    TileType.FOREST: "#33691E",
    TileType.RIVER: "#29B6F6",
    TileType.VILLAGE: "#FFCA28",
    TileType.TOWN: "#FFA726",
    TileType.MINE: "#78909C",
    TileType.MOUNTAIN: "#8D6E63",
}


@dataclass
class Tile:
    x: int
    y: int
    tile_type: TileType
    resources: Dict[str, float] = field(default_factory=dict)
    agents_here: List[int] = field(default_factory=list)  # agent IDs
    infrastructure_level: float = 1.0
    owner_id: Optional[int] = None

    def __post_init__(self):
        base = TILE_PRODUCTION.get(self.tile_type, {})
        self.resources = {k: v * (0.8 + random.random() * 0.4) for k, v in base.items()}

    def get_production_multiplier(self, resource: str) -> float:
        base = TILE_PRODUCTION.get(self.tile_type, {}).get(resource, 0)
        return base * self.infrastructure_level * (0.9 + random.random() * 0.2)

    def to_dict(self):
        return {
            "x": self.x,
            "y": self.y,
            "type": self.tile_type.name,
            "resources": self.resources,
            "infrastructure": round(self.infrastructure_level, 2),
            "population": len(self.agents_here),
            "owner": self.owner_id,
        }


class World:
    def __init__(self, width: int = 100, height: int = 100, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.width = width
        self.height = height
        self.grid: List[List[Tile]] = []
        self.agents: Dict[int, 'Agent'] = {}  # Forward reference
        self.timestep = 0
        self.market_prices: Dict[str, float] = {
            "food": 5.0,
            "raw_materials": 3.0,
            "wood": 2.0,
            "minerals": 8.0,
            "services": 4.0,
        }
        self.price_history: List[Dict[str, float]] = []
        self.events_log: List[str] = []

        self._generate_terrain()

    def _generate_terrain(self):
        """Procedural terrain generation using simplex-like noise approximation"""
        # Use numpy for fast noise generation
        noise = np.random.rand(self.height, self.width)

        for y in range(self.height):
            row = []
            for x in range(self.width):
                n = noise[y, x]
                # Determine tile type based on noise value and position
                if n < 0.15:
                    ttype = TileType.RIVER
                elif n < 0.35:
                    ttype = TileType.FOREST
                elif n < 0.50:
                    ttype = TileType.FARM
                elif n < 0.65:
                    ttype = TileType.MOUNTAIN
                elif n < 0.80:
                    ttype = TileType.MINE
                elif n < 0.90:
                    ttype = TileType.VILLAGE
                else:
                    ttype = TileType.TOWN

                # Cluster towns and villages
                if ttype == TileType.TOWN:
                    # Ensure towns aren't too isolated
                    pass

                tile = Tile(x, y, ttype)
                row.append(tile)
            self.grid.append(row)

        # Post-process: ensure connectivity and resource distribution
        self._ensure_village_clusters()
        self._place_rivers()

    def _ensure_village_clusters(self):
        """Ensure villages and towns are somewhat clustered"""
        for _ in range(5):
            for y in range(1, self.height - 1):
                for x in range(1, self.width - 1):
                    neighbors = [
                        self.grid[y-1][x].tile_type,
                        self.grid[y+1][x].tile_type,
                        self.grid[y][x-1].tile_type,
                        self.grid[y][x+1].tile_type,
                    ]
                    if self.grid[y][x].tile_type == TileType.FARM:
                        if sum(1 for n in neighbors if n in (TileType.VILLAGE, TileType.TOWN)) >= 2:
                            if random.random() < 0.3:
                                self.grid[y][x].tile_type = TileType.VILLAGE

    def _place_rivers(self):
        """Ensure rivers form connected waterways"""
        if self.width < 20:
            # Simple straight river down the middle for small grids
            for y in range(self.height):
                x = self.width // 2
                self.grid[y][x].tile_type = TileType.RIVER
            return

        # Simple river path generation
        for _ in range(3):
            x = random.randint(10, self.width - 10)
            y = random.randint(0, self.height - 1)
            for step in range(self.height):
                if 0 <= y < self.height and 0 <= x < self.width:
                    self.grid[y][x].tile_type = TileType.RIVER
                y += random.choice([-1, 0, 1])
                x += random.choice([-1, 0, 1])
                y = max(0, min(self.height - 1, y))
                x = max(0, min(self.width - 1, x))

    def get_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.grid[y][x]
        return None

    def get_neighbors(self, x: int, y: int, radius: int = 1) -> List[Tile]:
        """Get tiles within Manhattan distance radius"""
        tiles = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius:
                    tile = self.get_tile(x + dx, y + dy)
                    if tile:
                        tiles.append(tile)
        return tiles

    def get_agents_in_radius(self, x: int, y: int, radius: int = 3) -> List[int]:
        """Get agent IDs within radius"""
        agents = []
        for dy in range(-radius, radius + 1):
            for dx in range(-radius, radius + 1):
                if abs(dx) + abs(dy) <= radius:
                    tile = self.get_tile(x + dx, y + dy)
                    if tile:
                        agents.extend(tile.agents_here)
        return agents

    def move_agent(self, agent_id: int, old_x: int, old_y: int, new_x: int, new_y: int):
        """Move agent between tiles"""
        old_tile = self.get_tile(old_x, old_y)
        new_tile = self.get_tile(new_x, new_y)
        if old_tile and agent_id in old_tile.agents_here:
            old_tile.agents_here.remove(agent_id)
        if new_tile:
            new_tile.agents_here.append(agent_id)

    def update_market_prices(self):
        """Update prices based on supply/demand signals from last timestep"""
        # Simple adaptive pricing
        for resource in self.market_prices:
            # Random walk with mean reversion
            change = (random.random() - 0.5) * 0.2
            self.market_prices[resource] *= (1 + change)
            self.market_prices[resource] = max(0.5, self.market_prices[resource])

        self.price_history.append(dict(self.market_prices))

    def get_price(self, resource: str) -> float:
        return self.market_prices.get(resource, 5.0)

    def calculate_gini(self) -> float:
        """Calculate Gini coefficient of wealth inequality"""
        wealths = [a.money for a in self.agents.values() if a.alive]
        if len(wealths) < 2:
            return 0.0
        wealths = sorted(wealths)
        n = len(wealths)
        cumsum = np.cumsum(wealths)
        return (n + 1 - 2 * np.sum(cumsum) / cumsum[-1]) / n if cumsum[-1] > 0 else 0.0

    def get_stats(self) -> dict:
        alive = [a for a in self.agents.values() if a.alive]
        starving = [a for a in alive if a.food < 20]
        dead = [a for a in self.agents.values() if not a.alive]

        avg_food_price = self.market_prices.get("food", 5.0)

        return {
            "timestep": self.timestep,
            "population_alive": len(alive),
            "population_starving": len(starving),
            "population_dead": len(dead),
            "average_food_price": avg_food_price,
            "gini_coefficient": self.calculate_gini(),
            "total_wealth": sum(a.money for a in alive),
            "average_happiness": np.mean([a.happiness for a in alive]) if alive else 0,
            "average_age": np.mean([a.age for a in alive]) if alive else 0,
            "births_this_timestep": getattr(self, '_births_this_step', 0),
            "deaths_this_timestep": getattr(self, '_deaths_this_step', 0),
            "crimes_this_timestep": getattr(self, '_crimes_this_step', 0),
            "trades_this_timestep": getattr(self, '_trades_this_step', 0),
        }

    def to_dict(self):
        """Serialize world state for API"""
        return {
            "width": self.width,
            "height": self.height,
            "timestep": self.timestep,
            "prices": self.market_prices,
            "stats": self.get_stats(),
            "grid": [[t.to_dict() for t in row] for row in self.grid],
        }
