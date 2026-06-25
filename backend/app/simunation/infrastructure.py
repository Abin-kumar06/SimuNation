"""Road networks, building placement, urban planning, and vehicle AI for 3D visualization"""
import random
import math
import heapq
from typing import List, Dict, Tuple, Set, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum, auto
from .terrain import TerrainGenerator


class ZoneType(Enum):
    RESIDENTIAL = auto()   # Houses, apartments
    COMMERCIAL = auto()    # Shops, markets, restaurants
    INDUSTRIAL = auto()    # Mines, factories, farms (outskirts)
    PUBLIC = auto()        # Government, schools, hospitals, parks
    TRANSPORT = auto()     # Bus stops, train stations, parking
    ROAD = auto()


class RoadType(Enum):
    DIRT = auto()
    PAVED = auto()
    HIGHWAY = auto()
    BRIDGE = auto()


@dataclass
class Building:
    id: int
    x: float
    y: float
    zone_type: ZoneType
    building_type: str
    height: float
    width: float
    depth: float
    color: str
    secondary_color: str
    owner_id: Optional[int] = None
    occupants: List[int] = field(default_factory=list)
    max_occupants: int = 4
    floors: int = 1
    has_sign: bool = False
    sign_text: str = ""
    lit_windows: int = 0  # For night visualization
    z: float = 0.0
    ground_normal: Tuple[float, float, float] = (0.0, 1.0, 0.0)
    foundation_depth: float = 0.5
    rotation: float = 0.0


@dataclass
class RoadNode:
    x: float
    y: float
    id: int
    connections: List[int] = field(default_factory=list)  # Connected node IDs


@dataclass
class RoadSegment:
    start_node_id: int
    end_node_id: int
    width: float
    road_type: RoadType
    one_way: bool = False
    traffic_count: int = 0
    elevation_profile: List[Tuple[float, float, float]] = field(default_factory=list)


@dataclass
class Vehicle:
    id: int
    type: str  # "car", "bus", "truck", "cart", "ambulance", "police"
    route_node_ids: List[int]  # Path as sequence of node IDs
    current_node_idx: int = 0
    progress: float = 0.0  # 0.0 to 1.0 between current and next node
    speed: float = 0.15
    color: str = "#FFFFFF"
    cargo_type: Optional[str] = None
    cargo_amount: float = 0.0
    max_cargo: float = 10.0
    is_emergency: bool = False
    headlight_on: bool = False
    brake_light_on: bool = False


@dataclass
class BusRoute:
    id: int
    name: str
    stops: List[int]  # Node IDs
    vehicles: List[int] = field(default_factory=list)  # Vehicle IDs
    frequency: int = 20  # Steps between buses


class InfrastructureManager:
    _building_id_counter = 0
    _vehicle_id_counter = 0

    def __init__(self, world: 'World'):
        self.world = world
        self.terrain = TerrainGenerator(world.width, world.height, seed=42)
        self.buildings: Dict[int, Building] = {}
        self.road_nodes: Dict[int, RoadNode] = {}
        self.road_segments: List[RoadSegment] = []
        self.vehicles: Dict[int, Vehicle] = {}
        
        self.settlement_centers: Dict[str, Tuple[float, float]] = {}
        self.zone_map: Dict[Tuple[int, int], ZoneType] = {}  # Tile coord -> zone
        
        # Building type pools for variety
        self.house_colors = ["#D4A574", "#C4956A", "#B8875E", "#A67952", "#D2691E", "#CD853F", "#DEB887"]
        self.shop_signs = ["MARKET", "BAKERY", "TOOLS", "TAVERN", "BANK", "PHARMACY", "GENERAL"]
        
        self._generate_infrastructure()

    def _generate_infrastructure(self):
        """Master generation pipeline"""
        self._find_settlement_centers()
        self._generate_road_network()
        self._place_buildings()

    def _find_settlement_centers(self):
        """Find clusters of village/town tiles using flood fill"""
        visited = set()
        
        for y in range(self.world.height):
            for x in range(self.world.width):
                if (x, y) in visited:
                    continue
                    
                tile = self.world.get_tile(x, y)
                if not tile or tile.tile_type.name not in ('VILLAGE', 'TOWN'):
                    continue
                
                # Flood fill cluster
                cluster = []
                stack = [(x, y)]
                while stack:
                    cx, cy = stack.pop()
                    if (cx, cy) in visited or not (0 <= cx < self.world.width and 0 <= cy < self.world.height):
                        continue
                    
                    ct = self.world.get_tile(cx, cy)
                    if ct and ct.tile_type.name in ('VILLAGE', 'TOWN'):
                        visited.add((cx, cy))
                        cluster.append((cx, cy))
                        for dx, dy in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
                            stack.append((cx + dx, cy + dy))
                
                if len(cluster) >= 3:
                    cx = sum(c[0] for c in cluster) / len(cluster)
                    cy = sum(c[1] for c in cluster) / len(cluster)
                    name = self._generate_settlement_name(len(self.settlement_centers))
                    self.settlement_centers[name] = (cx, cy)
                    
                    # Mark tiles as zoned
                    for tx, ty in cluster:
                        self.zone_map[(tx, ty)] = ZoneType.RESIDENTIAL if random.random() > 0.3 else ZoneType.COMMERCIAL

    def _generate_settlement_name(self, index: int) -> str:
        prefixes = ["New", "Old", "East", "West", "North", "South", "Green", "Oak", "Pine", "Willow", "River", "Lake", "Hill", "Gold", "Iron"]
        suffixes = ["ford", "ton", "ville", "burg", "haven", "stead", "port", "cross", "field", "wood", "dale", "ham"]
        return f"{random.choice(prefixes)}{random.choice(suffixes)}"

    def _generate_road_network(self):
        """Generate road network connecting all settlements with MST"""
        centers = list(self.settlement_centers.values())
        if len(centers) < 2:
            return
        
        center_nodes = []
        for cx, cy in centers:
            node_id = self._add_road_node(cx, cy)
            center_nodes.append(node_id)
        
        # Minimum Spanning Tree
        connected = {center_nodes[0]}
        remaining = set(center_nodes[1:])
        
        while remaining:
            best_edge = None
            best_cost = float('inf')
            
            for c1 in connected:
                n1 = self.road_nodes[c1]
                for c2 in remaining:
                    n2 = self.road_nodes[c2]
                    dist = math.hypot(n1.x - n2.x, n1.y - n2.y)
                    cost = dist * (0.8 + random.random() * 0.4)
                    if cost < best_cost:
                        best_cost = cost
                        best_edge = (c1, c2, dist)
            
            if best_edge:
                n1_id, n2_id, dist = best_edge
                self._add_road_segment(n1_id, n2_id, RoadType.PAVED if dist < 30 else RoadType.HIGHWAY)
                connected.add(n2_id)
                remaining.remove(n2_id)

        # Connect to mines and farms
        for sx, sy in centers:
            nearest_farm = self._find_nearest_resource(sx, sy, 'FARM')
            if nearest_farm:
                fx, fy = nearest_farm
                if math.hypot(sx - fx, sy - fy) < 30:
                    farm_node = self._add_road_node(fx, fy)
                    settle_node = self._find_nearest_node(sx, sy)
                    if settle_node is not None:
                        self._add_road_segment(settle_node, farm_node, RoadType.DIRT)
            
            nearest_mine = self._find_nearest_resource(sx, sy, 'MINE')
            if nearest_mine:
                mx, my = nearest_mine
                if math.hypot(sx - mx, sy - my) < 35:
                    mine_node = self._add_road_node(mx, my)
                    settle_node = self._find_nearest_node(sx, sy)
                    if settle_node is not None:
                        self._add_road_segment(settle_node, mine_node, RoadType.DIRT)

    def _add_road_node(self, x: float, y: float) -> int:
        node_id = len(self.road_nodes)
        self.road_nodes[node_id] = RoadNode(x=x, y=y, id=node_id)
        return node_id

    def _add_road_segment(self, node1_id: int, node2_id: int, road_type: RoadType):
        n1 = self.road_nodes[node1_id]
        if node2_id in n1.connections:
            return
            
        n2 = self.road_nodes[node2_id]
        width = {RoadType.DIRT: 2.0, RoadType.PAVED: 3.0, RoadType.HIGHWAY: 4.0, RoadType.BRIDGE: 3.0}[road_type]
        
        num_samples = max(8, int(math.hypot(n2.x - n1.x, n2.y - n1.y) * 2))
        elevation_profile = []
        for i in range(num_samples + 1):
            t = i / num_samples
            px = n1.x + (n2.x - n1.x) * t
            py = n1.y + (n2.y - n1.y) * t
            pz = self.terrain.get_height(px, py)
            elevation_profile.append((px, py, pz))
            
        self.road_segments.append(RoadSegment(
            start_node_id=node1_id,
            end_node_id=node2_id,
            width=width,
            road_type=road_type,
            elevation_profile=elevation_profile,
        ))
        
        n1.connections.append(node2_id)
        self.road_nodes[node2_id].connections.append(node1_id)

    def _find_nearest_resource(self, x: float, y: float, tile_type: str) -> Optional[Tuple[float, float]]:
        best = None
        best_dist = float('inf')
        for ry in range(self.world.height):
            for rx in range(self.world.width):
                tile = self.world.get_tile(rx, ry)
                if tile and tile.tile_type.name == tile_type:
                    dist = math.hypot(x - rx, y - ry)
                    if dist < best_dist:
                        best_dist = dist
                        best = (rx, ry)
        return best

    def _find_nearest_node(self, x: float, y: float) -> Optional[int]:
        best = None
        best_dist = float('inf')
        for node_id, node in self.road_nodes.items():
            dist = math.hypot(x - node.x, y - node.y)
            if dist < best_dist:
                best_dist = dist
                best = node_id
        return best

    def _place_buildings(self):
        """Place buildings ALONG ROADS, not scattered randomly"""
        for seg in self.road_segments:
            start = self.road_nodes[seg.start_node_id]
            end = self.road_nodes[seg.end_node_id]
            
            dx = end.x - start.x
            dy = end.y - start.y
            length = math.hypot(dx, dy)
            if length < 0.1:
                continue
                
            perp_x = -dy / length
            perp_y = dx / length
            
            road_angle = math.atan2(dx, dy)
            
            num_buildings = max(2, int(length / 3))
            
            for i in range(num_buildings):
                t = (i + 1) / (num_buildings + 1)
                road_x = start.x + dx * t
                road_y = start.y + dy * t
                
                offset = random.choice([-1, 1]) * random.uniform(1.5, 3.0)
                bx = road_x + perp_x * offset
                by = road_y + perp_y * offset
                
                if offset > 0:
                    rotation = road_angle + math.pi / 2
                else:
                    rotation = road_angle - math.pi / 2
                
                if seg.road_type == RoadType.HIGHWAY:
                    btype = random.choice(["gas_station", "motel", "warehouse"])
                    zone = ZoneType.COMMERCIAL
                elif seg.road_type == RoadType.PAVED:
                    if random.random() < 0.7:
                        btype = random.choice(["house", "apartment", "house"])
                        zone = ZoneType.RESIDENTIAL
                    else:
                        btype = random.choice(["shop", "restaurant", "cafe", "bank"])
                        zone = ZoneType.COMMERCIAL
                else:  # DIRT
                    btype = random.choice(["farm_house", "barn", "shed"])
                    zone = ZoneType.INDUSTRIAL
                
                bz = self.terrain.get_height(bx, by) if hasattr(self, 'terrain') else 0
                normal = self.terrain.get_normal(bx, by) if hasattr(self, 'terrain') else (0.0, 1.0, 0.0)
                
                dims = {
                    "house": (2.5, 2.5, 3.0),
                    "apartment": (3.5, 3.0, 5.0),
                    "shop": (4.0, 3.5, 2.5),
                    "restaurant": (5.0, 4.0, 3.0),
                    "cafe": (3.0, 3.0, 2.5),
                    "bank": (6.0, 4.0, 4.0),
                    "school": (8.0, 6.0, 3.5),
                    "hospital": (7.0, 5.0, 4.0),
                    "factory": (10.0, 8.0, 5.0),
                    "warehouse": (12.0, 8.0, 4.0),
                    "gas_station": (6.0, 5.0, 3.0),
                    "motel": (8.0, 4.0, 3.0),
                    "farm_house": (3.0, 2.5, 2.5),
                    "barn": (5.0, 4.0, 3.5),
                    "shed": (2.0, 2.0, 2.0),
                }
                
                w, d, h = dims.get(btype, (3.0, 3.0, 3.0))
                
                colors = {
                    "house": random.choice(["#E8D5C4", "#D4C4B0", "#C4B49E", "#DEB887"]),
                    "apartment": random.choice(["#B0C4DE", "#A0B4CE", "#90A4BE", "#A9A9A9"]),
                    "shop": random.choice(["#F5DEB3", "#FFE4B5", "#DEB887", "#D2B48C"]),
                    "restaurant": "#CD5C5C",
                    "cafe": "#8B4513",
                    "bank": "#DAA520",
                    "school": "#87CEEB",
                    "hospital": "#F0F8FF",
                    "factory": "#696969",
                    "warehouse": "#8B7355",
                    "gas_station": "#FF6347",
                    "motel": "#DDA0DD",
                    "farm_house": "#F4A460",
                    "barn": "#8B4513",
                    "shed": "#A0522D",
                }
                
                self._add_building(
                    bx, by, bz,
                    zone, btype,
                    height=h, width=w, depth=d,
                    color=colors.get(btype, "#CCCCCC"),
                    secondary_color="#8B4513",
                    ground_normal=normal,
                    has_sign=btype in ("shop", "restaurant", "cafe", "bank", "gas_station", "motel"),
                    sign_text=btype.upper() if btype in ("shop", "bank") else "",
                    rotation=rotation
                )

    def _add_building(self, x: float, y: float, z: float, zone: ZoneType, btype: str, height: float, width: float, depth: float, color: str, secondary_color: str, ground_normal: Tuple[float, float, float], has_sign: bool = False, sign_text: str = "", floors: int = 1, rotation: float = 0.0):
        InfrastructureManager._building_id_counter += 1
        self.buildings[InfrastructureManager._building_id_counter] = Building(
            id=InfrastructureManager._building_id_counter,
            x=x, y=y,
            z=z,
            ground_normal=ground_normal,
            foundation_depth=0.5,
            zone_type=zone,
            building_type=btype,
            height=height,
            width=width,
            depth=depth,
            color=color,
            secondary_color=secondary_color,
            has_sign=has_sign,
            sign_text=sign_text,
            floors=floors,
            rotation=rotation,
        )

    def spawn_vehicle(self, start: Tuple[float, float], end: Tuple[float, float], vehicle_type: str = "car") -> Optional[Vehicle]:
        start_node = self._find_nearest_node(start[0], start[1])
        end_node = self._find_nearest_node(end[0], end[1])
        if start_node is None or end_node is None or start_node == end_node:
            return None

        route = self._find_path_astar(start_node, end_node)
        if not route or len(route) < 2:
            return None

        InfrastructureManager._vehicle_id_counter += 1
        colors = ["#ef4444", "#3b82f6", "#10b981", "#eab308", "#ffffff"]
        vehicle = Vehicle(
            id=InfrastructureManager._vehicle_id_counter,
            type=vehicle_type,
            route_node_ids=route,
            speed=random.uniform(0.1, 0.25),
            color=random.choice(colors),
        )
        self.vehicles[vehicle.id] = vehicle
        return vehicle

    def _find_path_astar(self, start_id: int, end_id: int) -> List[int]:
        """A* Pathfinding on Road Nodes Graph"""
        open_set = []
        heapq.heappush(open_set, (0, start_id))
        came_from = {}
        g_score = {node_id: float('inf') for node_id in self.road_nodes}
        g_score[start_id] = 0
        f_score = {node_id: float('inf') for node_id in self.road_nodes}
        
        n_end = self.road_nodes[end_id]
        f_score[start_id] = math.hypot(self.road_nodes[start_id].x - n_end.x, self.road_nodes[start_id].y - n_end.y)

        while open_set:
            current_id = heapq.heappop(open_set)[1]
            if current_id == end_id:
                path = []
                while current_id in came_from:
                    path.append(current_id)
                    current_id = came_from[current_id]
                path.append(start_id)
                path.reverse()
                return path

            current_node = self.road_nodes[current_id]
            for neighbor_id in current_node.connections:
                neighbor = self.road_nodes[neighbor_id]
                tentative_g_score = g_score[current_id] + math.hypot(current_node.x - neighbor.x, current_node.y - neighbor.y)
                
                if tentative_g_score < g_score[neighbor_id]:
                    came_from[neighbor_id] = current_id
                    g_score[neighbor_id] = tentative_g_score
                    h = math.hypot(neighbor.x - n_end.x, neighbor.y - n_end.y)
                    f_score[neighbor_id] = tentative_g_score + h
                    heapq.heappush(open_set, (f_score[neighbor_id], neighbor_id))
        
        return []

    def update_vehicles(self):
        to_remove = []
        for vid, vehicle in self.vehicles.items():
            vehicle.progress += vehicle.speed
            if vehicle.progress >= 1.0:
                vehicle.progress = 0.0
                vehicle.current_node_idx += 1
                if vehicle.current_node_idx >= len(vehicle.route_node_ids) - 1:
                    to_remove.append(vid)
            
        for vid in to_remove:
            del self.vehicles[vid]

    def to_3d_render(self) -> Dict:
        return {
            "terrain": {
                "width": self.world.width,
                "height": self.world.height,
                "heightmap": self.terrain.heightmap.tolist(),
                "max_height": float(self.terrain.heightmap.max()),
            },
            "buildings": [
                {
                    "id": b.id,
                    "x": b.x,
                    "y": b.y,
                    "z": b.z,
                    "ground_normal": b.ground_normal,
                    "foundation_depth": b.foundation_depth,
                    "height": b.height,
                    "width": b.width,
                    "depth": b.depth,
                    "type": b.building_type,
                    "color": b.color,
                    "zone": b.zone_type.name,
                    "sign": b.sign_text if b.has_sign else None,
                    "rotation": b.rotation,
                }
                for b in self.buildings.values()
            ],
            "roads": [
                {
                    "start": [self.road_nodes[r.start_node_id].x, self.road_nodes[r.start_node_id].y],
                    "end": [self.road_nodes[r.end_node_id].x, self.road_nodes[r.end_node_id].y],
                    "width": r.width,
                    "type": r.road_type.name.lower(),
                    "elevation_profile": r.elevation_profile,
                }
                for r in self.road_segments
            ],
            "vehicles": [
                {
                    "id": v.id,
                    "type": v.type,
                    "x": self.road_nodes[v.route_node_ids[v.current_node_idx]].x + (self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].x - self.road_nodes[v.route_node_ids[v.current_node_idx]].x) * v.progress,
                    "y": self.road_nodes[v.route_node_ids[v.current_node_idx]].y + (self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].y - self.road_nodes[v.route_node_ids[v.current_node_idx]].y) * v.progress,
                    "z": self.terrain.get_height(
                        self.road_nodes[v.route_node_ids[v.current_node_idx]].x + (self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].x - self.road_nodes[v.route_node_ids[v.current_node_idx]].x) * v.progress,
                        self.road_nodes[v.route_node_ids[v.current_node_idx]].y + (self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].y - self.road_nodes[v.route_node_ids[v.current_node_idx]].y) * v.progress
                    ),
                    "color": v.color,
                    "rotation": math.atan2(
                        self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].x - self.road_nodes[v.route_node_ids[v.current_node_idx]].x,
                        self.road_nodes[v.route_node_ids[v.current_node_idx + 1]].y - self.road_nodes[v.route_node_ids[v.current_node_idx]].y
                    ),
                }
                for v in self.vehicles.values()
                if v.current_node_idx < len(v.route_node_ids) - 1
            ],
            "settlements": [
                {
                    "name": name,
                    "x": pos[0],
                    "y": pos[1],
                }
                for name, pos in self.settlement_centers.items()
            ],
        }
