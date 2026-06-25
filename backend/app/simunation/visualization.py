"""Generates render-ready world state for the frontend"""
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
import math
import random


@dataclass
class RenderTile:
    x: int
    y: int
    type: str
    variant: int  # 0-3 for visual variety
    infrastructure: float
    building: Optional[str]  # "house", "market", "mine_shaft", "farm_plot"
    agents_here: List[int]
    resource_indicators: List[str]  # ["growing", "harvested", "depleted"]


@dataclass
class RenderAgent:
    id: int
    x: float  # Float for smooth interpolation
    y: float
    profession: str
    activity: str  # "walking", "farming", "mining", "trading", "resting", "dead"
    facing: str  # "n", "s", "e", "w"
    health_pct: float
    hunger_pct: float
    age_stage: str  # "child", "adult", "elder"
    carrying: Optional[str]  # "food_basket", "ore", "tools"
    is_starving: bool
    is_sleeping: bool


class WorldRenderer:
    """Converts simulation state into render-ready structures"""
    
    TILE_VARIANTS = {
        "FARM": 4,
        "FOREST": 3,
        "RIVER": 2,
        "VILLAGE": 2,
        "TOWN": 3,
        "MINE": 2,
        "MOUNTAIN": 3,
    }
    
    BUILDING_THRESHOLDS = {
        "FARM": ("farm_plot", 1.0),
        "VILLAGE": ("house", 1.5),
        "TOWN": ("market", 2.0),
        "MINE": ("mine_shaft", 1.0),
    }
    
    def __init__(self, world: 'World'):
        self.world = world
        self.agent_prev_positions: Dict[int, Tuple[float, float]] = {}
        self.agent_smoothed: Dict[int, Tuple[float, float]] = {}
        
    def render_frame(self, viewport: Optional[Tuple[int, int, int, int]] = None) -> Dict:
        """Generate complete render frame"""
        return {
            "tiles": self._render_tiles(viewport),
            "agents": self._render_agents(),
            "settlements": self._detect_settlements(),
            "trade_routes": self._detect_trade_routes(),
            "events": self._extract_visual_events(),
            "time_of_day": self._calculate_time(),
            "season": self._calculate_season(),
        }
    
    def _render_tiles(self, viewport: Optional[Tuple[int, int, int, int]] = None) -> List[RenderTile]:
        tiles = []
        for row in self.world.grid:
            for tile in row:
                if viewport:
                    if not (viewport[0] <= tile.x <= viewport[2] and viewport[1] <= tile.y <= viewport[3]):
                        continue
                # Determine building based on infrastructure
                building = None
                if tile.tile_type.name in self.BUILDING_THRESHOLDS:
                    btype, threshold = self.BUILDING_THRESHOLDS[tile.tile_type.name]
                    if tile.infrastructure_level >= threshold:
                        building = btype
                
                # Resource indicators
                indicators = []
                if tile.tile_type.name == "FARM" and tile.resources.get("food", 0) > 5:
                    indicators.append("growing" if tile.resources["food"] > 6 else "harvested")
                elif tile.tile_type.name == "MINE" and tile.resources.get("minerals", 0) < 2:
                    indicators.append("depleted")
                
                tiles.append(RenderTile(
                    x=tile.x,
                    y=tile.y,
                    type=tile.tile_type.name.lower(),
                    variant=tile.x % self.TILE_VARIANTS.get(tile.tile_type.name, 1),
                    infrastructure=round(tile.infrastructure_level, 1),
                    building=building,
                    agents_here=tile.agents_here,
                    resource_indicators=indicators,
                ))
        return tiles
    
    def _render_agents(self) -> List[RenderAgent]:
        agents = []
        for agent in self.world.agents.values():
            if not agent.alive:
                # Render dead bodies for a few steps then remove
                if self.world.timestep - getattr(agent, '_death_timestep', self.world.timestep) < 5:
                    agents.append(RenderAgent(
                        id=agent.id,
                        x=float(agent.x),
                        y=float(agent.y),
                        profession=agent.profession.name.lower(),
                        activity="dead",
                        facing="s",
                        health_pct=0,
                        hunger_pct=0,
                        age_stage="adult",
                        carrying=None,
                        is_starving=False,
                        is_sleeping=False,
                    ))
                continue
            
            # Smooth movement
            prev = self.agent_prev_positions.get(agent.id, (float(agent.x), float(agent.y)))
            curr = (float(agent.x), float(agent.y))
            
            # Lerp for visual smoothness
            smooth_x = prev[0] * 0.3 + curr[0] * 0.7
            smooth_y = prev[1] * 0.3 + curr[1] * 0.7
            self.agent_smoothed[agent.id] = (smooth_x, smooth_y)
            self.agent_prev_positions[agent.id] = curr
            
            # Determine activity
            activity = "idle"
            if agent.energy < 20:
                activity = "resting"
            elif agent.profession.name == "FARMER" and agent.world.get_tile(agent.x, agent.y).tile_type.name == "FARM":
                activity = "farming"
            elif agent.profession.name == "MINER" and agent.world.get_tile(agent.x, agent.y).tile_type.name == "MINE":
                activity = "mining"
            elif agent.food < 20:
                activity = "foraging"
            elif agent.partner_id and abs(agent.x - agent.world.agents.get(agent.partner_id, agent).x) <= 2:
                activity = "social"
            
            # Determine facing from movement direction
            dx = smooth_x - prev[0]
            dy = smooth_y - prev[1]
            if abs(dx) > abs(dy):
                facing = "e" if dx > 0 else "w"
            else:
                facing = "s" if dy > 0 else "n"
            
            age_stage = "child" if agent.is_child else "elder" if agent.age > 60 else "adult"
            
            # Carrying visual
            carrying = None
            if agent.profession.name in ("FARMER", "TRADER") and agent.food > 30:
                carrying = "food_basket"
            elif agent.profession.name == "MINER" and agent.money > 20:
                carrying = "ore"
            
            agents.append(RenderAgent(
                id=agent.id,
                x=smooth_x,
                y=smooth_y,
                profession=agent.profession.name.lower(),
                activity=activity,
                facing=facing,
                health_pct=agent.health / 100.0,
                hunger_pct=agent.food / 100.0,
                age_stage=age_stage,
                carrying=carrying,
                is_starving=agent.food < 20,
                is_sleeping=agent.energy < 15,
            ))
        
        return agents
    
    def _detect_settlements(self) -> List[Dict]:
        """Find clusters of agents + infrastructure = named settlements"""
        settlements = []
        visited = set()
        
        for row in self.world.grid:
            for tile in row:
                if (tile.x, tile.y) in visited:
                    continue
                if tile.infrastructure_level >= 1.5 and len(tile.agents_here) >= 2:
                    # Flood fill to find settlement bounds
                    cluster = self._flood_fill_settlement(tile.x, tile.y, visited)
                    if len(cluster) >= 3:
                        cx = sum(t[0] for t in cluster) / len(cluster)
                        cy = sum(t[1] for t in cluster) / len(cluster)
                        population = sum(len(self.world.grid[y][x].agents_here) for x, y in cluster)
                        
                        # Name generation based on dominant profession
                        profs = {}
                        for x, y in cluster:
                            for aid in self.world.grid[y][x].agents_here:
                                a = self.world.agents.get(aid)
                                if a:
                                    profs[a.profession.name] = profs.get(a.profession.name, 0) + 1
                        
                        dominant = max(profs.keys(), key=lambda p: profs[p]) if profs else "Village"
                        name = self._generate_settlement_name(dominant, len(settlements))
                        
                        settlements.append({
                            "name": name,
                            "x": cx,
                            "y": cy,
                            "population": population,
                            "dominant_profession": dominant.lower(),
                            "size": len(cluster),
                        })
        
        return settlements
    
    def _flood_fill_settlement(self, start_x: int, start_y: int, visited: set) -> List[Tuple[int, int]]:
        """Find connected high-infrastructure tiles"""
        cluster = []
        stack = [(start_x, start_y)]
        
        while stack:
            x, y = stack.pop()
            if (x, y) in visited or x < 0 or x >= self.world.width or y < 0 or y >= self.world.height:
                continue
            
            tile = self.world.grid[y][x]
            if tile.infrastructure_level < 1.0 and len(tile.agents_here) < 2:
                continue
            
            visited.add((x, y))
            cluster.append((x, y))
            
            # Check neighbors
            for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                nx, ny = x + dx, y + dy
                if (nx, ny) not in visited:
                    stack.append((nx, ny))
        
        return cluster
    
    def _generate_settlement_name(self, dominant_prof: str, index: int) -> str:
        prefixes = {
            "FARMER": ["Wheat", "Harvest", "Green", "Meadow"],
            "MINER": ["Iron", "Deep", "Stone", "Ore"],
            "TRADER": ["Market", "Gold", "Merchant", "Trade"],
            "BUILDER": ["New", "Brick", "Stone", "Craft"],
            "DOCTOR": ["Healer", "Well", "Care", "Health"],
            "TEACHER": ["Wise", "Book", "Learn", "Scholar"],
        }
        suffixes = ["ford", "ton", "ville", "burg", "haven", "stead", "port", "cross"]
        
        prefix = random.choice(prefixes.get(dominant_prof, ["Oak", "River", "North"]))
        suffix = suffixes[index % len(suffixes)]
        return f"{prefix}{suffix}"
    
    def _detect_trade_routes(self) -> List[Dict]:
        """Find paths between settlements where trade occurred"""
        routes = []
        settlements = self._detect_settlements()
        
        if len(settlements) < 2:
            return routes
        
        # Check recent trade memories for inter-settlement commerce
        for agent in self.world.agents.values():
            if not agent.alive:
                continue
            for mem in agent.memory[-10:]:
                if mem.event_type == "trade" and "partner" in mem.details:
                    partner_id = mem.details["partner"]
                    partner = self.world.agents.get(partner_id)
                    if partner and partner.alive:
                        # Check if they're from different settlement clusters
                        dist = math.sqrt((agent.x - partner.x)**2 + (agent.y - partner.y)**2)
                        if dist > 5:  # Long-distance trade
                            routes.append({
                                "from": (agent.x, agent.y),
                                "to": (partner.x, partner.y),
                                "volume": mem.details.get("amount", 0),
                                "resource": mem.details.get("bought") or mem.details.get("sold"),
                            })
        
        # Deduplicate similar routes
        unique_routes = []
        for route in routes:
            is_duplicate = False
            for existing in unique_routes:
                if (abs(route["from"][0] - existing["from"][0]) < 3 and 
                    abs(route["to"][0] - existing["to"][0]) < 3):
                    is_duplicate = True
                    break
            if not is_duplicate:
                unique_routes.append(route)
        
        return unique_routes[:10]  # Limit for performance
    
    def _extract_visual_events(self) -> List[Dict]:
        """Convert recent events into visual notifications"""
        events = []
        
        # Check for recent deaths
        recent_deaths = [a for a in self.world.agents.values() 
                        if not a.alive and getattr(a, '_death_timestep', 0) > self.world.timestep - 3]
        if recent_deaths:
            events.append({
                "type": "death",
                "severity": "high" if len(recent_deaths) > 3 else "medium",
                "message": f"{len(recent_deaths)} deaths reported",
                "location": (recent_deaths[0].x, recent_deaths[0].y) if recent_deaths else (0, 0),
            })
        
        # Check for births
        recent_births = [a for a in self.world.agents.values() 
                        if a.is_child and a.age < 0.5]
        if recent_births:
            events.append({
                "type": "birth",
                "severity": "low",
                "message": f"New child born: {recent_births[0].id}",
                "location": (recent_births[0].x, recent_births[0].y),
            })
        
        # Check for crimes
        recent_crimes = [a for a in self.world.agents.values() 
                        for m in a.memory[-5:] if m.event_type == "crime"]
        if recent_crimes:
            events.append({
                "type": "crime",
                "severity": "high",
                "message": "Crime wave detected",
                "location": recent_crimes[0].location,
            })
        
        return events
    
    def _calculate_time(self) -> str:
        """Day/night cycle based on timestep"""
        cycle = self.world.timestep % 24
        if 6 <= cycle < 12:
            return "morning"
        elif 12 <= cycle < 18:
            return "day"
        elif 18 <= cycle < 22:
            return "evening"
        else:
            return "night"
    
    def _calculate_season(self) -> str:
        """Season affects farm yields visually"""
        cycle = (self.world.timestep // 24) % 4
        seasons = ["spring", "summer", "autumn", "winter"]
        return seasons[cycle]
    
    def to_json(self, viewport: Optional[Tuple[int, int, int, int]] = None) -> Dict:
        """Serialize for API/WebSocket"""
        frame = self.render_frame(viewport)
        return {
            "tiles": [
                {
                    "x": t.x, "y": t.y,
                    "type": t.type,
                    "variant": t.variant,
                    "building": t.building,
                    "agents": len(t.agents_here),
                    "indicators": t.resource_indicators,
                }
                for t in frame["tiles"]
            ],
            "agents": [
                {
                    "id": a.id,
                    "x": round(a.x, 2), "y": round(a.y, 2),
                    "profession": a.profession,
                    "activity": a.activity,
                    "facing": a.facing,
                    "health": round(a.health_pct, 2),
                    "hunger": round(a.hunger_pct, 2),
                    "age_stage": a.age_stage,
                    "carrying": a.carrying,
                    "starving": a.is_starving,
                    "sleeping": a.is_sleeping,
                }
                for a in frame["agents"]
            ],
            "settlements": frame["settlements"],
            "trade_routes": frame["trade_routes"],
            "events": frame["events"],
            "time": frame["time_of_day"],
            "season": frame["season"],
            "timestep": self.world.timestep,
        }
