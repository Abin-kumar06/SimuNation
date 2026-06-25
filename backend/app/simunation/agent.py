import random
import math
from typing import List, Dict, Optional, Tuple, Any
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


class Profession(Enum):
    FARMER = auto()
    MINER = auto()
    BUILDER = auto()
    DOCTOR = auto()
    TEACHER = auto()
    WORKER = auto()
    TRADER = auto()
    MERCHANT = auto()
    UNEMPLOYED = auto()
    CHILD = auto()


class ActionType(Enum):
    MOVE = auto()
    PRODUCE = auto()
    TRADE = auto()
    REST = auto()
    COMMUNICATE = auto()
    STEAL = auto()
    HEAL = auto()
    BUILD = auto()
    TEACH = auto()
    MATE = auto()
    FORAGE = auto()  # Emergency food gathering
    NONE = auto()


@dataclass
class Memory:
    timestep: int
    event_type: str
    details: Dict[str, Any]
    emotional_valence: float
    location: Tuple[int, int]
    involved_agent_id: Optional[int] = None


@dataclass
class Trait:
    greed: float = 0.5
    cooperation: float = 0.5
    risk_tolerance: float = 0.5
    intelligence: float = 0.5
    ambition: float = 0.5
    honor: float = 0.5
    aggression: float = 0.3

    def __post_init__(self):
        for key in self.__dict__:
            val = getattr(self, key)
            setattr(self, key, max(0.0, min(1.0, val)))


FIRST_NAMES = ["James", "Mary", "John", "Patricia", "Robert", "Jennifer", "Michael", "Elizabeth", "William", "Linda", "David", "Barbara", "Richard", "Susan", "Joseph", "Jessica", "Thomas", "Sarah", "Charles", "Karen"]
LAST_NAMES = ["Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller", "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Gonzalez", "Wilson", "Anderson", "Thomas", "Taylor", "Moore", "Jackson", "Martin"]


class Agent:
    _id_counter = 0

    def __init__(
        self,
        x: int,
        y: int,
        world: 'World',
        age: int = 0,
        is_child: bool = False,
        parents: Optional[Tuple[int, int]] = None,
        inherited_traits: Optional[Trait] = None,
    ):
        Agent._id_counter += 1
        self.id = Agent._id_counter
        self.name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        self.last_action = "Spawned"

        self.x = x
        self.y = y
        self.world = world

        # State
        self.age = age
        self.alive = True
        self.is_child = is_child
        self.parents = parents or ()

        # Resources — INCREASED starting food to prevent immediate starvation
        self.money = 50.0 if not is_child else 0.0
        self.food = 80.0 if not is_child else 40.0  # INCREASED from 50/20
        self.health = 100.0
        self.energy = 100.0
        self.happiness = 50.0
        self.housing_level = 1

        # Starvation tracking — grace period before health damage
        self.starvation_steps = 0

        # Traits
        if inherited_traits:
            self.traits = self._mutate_traits(inherited_traits)
        else:
            self.traits = Trait(
                greed=random.random(),
                cooperation=random.random(),
                risk_tolerance=random.random(),
                intelligence=random.random(),
                ambition=random.random(),
                honor=random.random(),
                aggression=random.random(),
            )

        # Profession
        self.profession = Profession.CHILD if is_child else self._roll_profession()

        # Social
        self.trust_scores: Dict[int, float] = {}
        self.relationships: Dict[int, str] = {}
        self.partner_id: Optional[int] = None
        self.children_ids: List[int] = []

        # Memory
        self.memory: List[Memory] = []
        self.memory_capacity = 20 + int(self.traits.intelligence * 50)
        self.known_prices: Dict[str, float] = {}
        self.subjective_reputations: Dict[int, float] = {}

        # Goals
        self.current_goal: str = "survive"
        self.goal_priority: float = 1.0

        # Register in world
        tile = world.get_tile(x, y)
        if tile:
            tile.agents_here.append(self.id)
        world.agents[self.id] = self

    # --- Properties for frontend compatibility ---
    @property
    def role(self) -> str:
        return self.profession.name

    @property
    def is_alive(self) -> bool:
        return self.alive

    @property
    def trait_percentages(self) -> Dict[str, int]:
        return {
            "greed": int(self.traits.greed * 100),
            "cooperation": int(self.traits.cooperation * 100),
            "risk_tolerance": int(self.traits.risk_tolerance * 100),
            "intelligence": int(self.traits.intelligence * 100),
            "ambition": int(self.traits.ambition * 100),
            "honor": int(self.traits.honor * 100),
            "aggression": int(self.traits.aggression * 100),
        }

    # Additional fields for compatibility
    @property
    def starvation_ticks(self) -> int:
        return self.starvation_steps

    @property
    def greed(self) -> float:
        return self.traits.greed * 100

    @property
    def cooperation(self) -> float:
        return self.traits.cooperation * 100

    @property
    def risk_tolerance(self) -> float:
        return self.traits.risk_tolerance * 100

    @property
    def intelligence(self) -> float:
        return self.traits.intelligence * 100

    @property
    def ambition(self) -> float:
        return self.traits.ambition * 100

    def _mutate_traits(self, parent_traits: Trait) -> Trait:
        return Trait(
            greed=self._mutate_value(parent_traits.greed),
            cooperation=self._mutate_value(parent_traits.cooperation),
            risk_tolerance=self._mutate_value(parent_traits.risk_tolerance),
            intelligence=self._mutate_value(parent_traits.intelligence),
            ambition=self._mutate_value(parent_traits.ambition),
            honor=self._mutate_value(parent_traits.honor),
            aggression=self._mutate_value(parent_traits.aggression),
        )

    def _mutate_value(self, val: float) -> float:
        mutation = random.gauss(0, 0.1)
        return max(0.0, min(1.0, val + mutation))

    def _roll_profession(self) -> Profession:
        weights = {
            Profession.FARMER: 0.25,      # INCREASED farmers
            Profession.MINER: 0.15,
            Profession.BUILDER: 0.08,
            Profession.DOCTOR: 0.05,
            Profession.TEACHER: 0.05,
            Profession.WORKER: 0.15,
            Profession.TRADER: 0.12,
            Profession.MERCHANT: 0.08,
            Profession.UNEMPLOYED: 0.07,
        }
        professions = list(weights.keys())
        probs = list(weights.values())
        return random.choices(professions, weights=probs)[0]

    def perceive(self) -> Dict[str, Any]:
        current_tile = self.world.get_tile(self.x, self.y)
        neighbors = self.world.get_neighbors(self.x, self.y, radius=2)
        nearby_agents = self.world.get_agents_in_radius(self.x, self.y, radius=3)
        nearby_agents = [aid for aid in nearby_agents if aid != self.id]

        return {
            "current_tile": current_tile,
            "neighbors": neighbors,
            "nearby_agents": nearby_agents,
            "self_state": {
                "food": self.food,
                "money": self.money,
                "health": self.health,
                "energy": self.energy,
                "happiness": self.happiness,
            },
            "time": self.world.timestep,
        }

    def decide(self, perception: Dict[str, Any]) -> Tuple[ActionType, Dict[str, Any]]:
        self._update_goal()

        utilities = {}

        # CRITICAL: If starving, forage is always available as fallback
        if self.food < 25:
            utilities[ActionType.FORAGE] = self._utility_forage(perception)
            utilities[ActionType.PRODUCE] = self._utility_produce(perception)
            utilities[ActionType.TRADE] = self._utility_trade(perception, "buy_food")
            if self.traits.greed > 0.7 and self.food < 15 and self.money < 10:
                utilities[ActionType.STEAL] = self._utility_steal(perception)

        elif self.food < 40:
            utilities[ActionType.PRODUCE] = self._utility_produce(perception)
            utilities[ActionType.FORAGE] = self._utility_forage(perception) * 0.5

        if self.energy < 25:
            utilities[ActionType.REST] = self._utility_rest()

        if self.health < 40:
            utilities[ActionType.REST] = max(utilities.get(ActionType.REST, 0), self._utility_rest() * 1.5)

        # Economic actions when stable
        if self.food >= 40 and self.energy >= 30:
            utilities[ActionType.PRODUCE] = self._utility_produce(perception)
            utilities[ActionType.TRADE] = self._utility_trade(perception, "sell_goods")

        # Social actions
        if self.age >= 18 and not self.is_child and self.partner_id is None and self.food > 30:
            utilities[ActionType.MATE] = self._utility_mate(perception)

        # Profession-specific
        if self.profession == Profession.DOCTOR and self.food > 30:
            utilities[ActionType.HEAL] = self._utility_heal(perception)
        elif self.profession == Profession.BUILDER and self.food > 30:
            utilities[ActionType.BUILD] = self._utility_build(perception)
        elif self.profession == Profession.TEACHER and self.food > 30:
            utilities[ActionType.TEACH] = self._utility_teach(perception)

        # Movement
        utilities[ActionType.MOVE] = self._utility_move(perception)

        # Default
        if not utilities:
            return ActionType.REST, {}

        actions = list(utilities.keys())
        vals = list(utilities.values())
        temperature = 0.5 + (1 - self.traits.intelligence) * 0.5
        exp_vals = [math.exp(v / temperature) for v in vals]
        total = sum(exp_vals)
        probs = [v / total for v in exp_vals]

        chosen = random.choices(actions, weights=probs)[0]
        params = self._get_action_params(chosen, perception)
        return chosen, params

    def _update_goal(self):
        if self.food < 20:
            self.current_goal = "find_food"
            self.goal_priority = 1.0
        elif self.health < 40:
            self.current_goal = "recover_health"
            self.goal_priority = 0.9
        elif self.energy < 25:
            self.current_goal = "rest"
            self.goal_priority = 0.8
        elif self.money < 20:
            self.current_goal = "earn_money"
            self.goal_priority = 0.6
        elif self.happiness < 40:
            self.current_goal = "seek_happiness"
            self.goal_priority = 0.5
        elif self.traits.ambition > 0.7:
            self.current_goal = "gain_status"
            self.goal_priority = 0.4
        else:
            self.current_goal = "maintain"
            self.goal_priority = 0.3

    def _utility_forage(self, perception: Dict) -> float:
        """Emergency food gathering — works on any tile but low yield"""
        urgency = max(0, (30 - self.food) / 30)
        return urgency * 1.2  # High utility when starving

    def _utility_produce(self, perception: Dict) -> float:
        tile = perception["current_tile"]
        if not tile:
            return 0.0

        profession_bonus = {
            Profession.FARMER: TileType.FARM,
            Profession.MINER: TileType.MINE,
            Profession.WORKER: TileType.FOREST,
        }

        bonus = 0.3
        if profession_bonus.get(self.profession) == tile.tile_type:
            bonus = 1.0

        need = max(0, (50 - self.food) / 50)
        energy_ok = 1.0 if self.energy > 10 else 0.3  # Can still produce with low energy
        return bonus * (0.5 + need) * energy_ok

    def _utility_trade(self, perception: Dict, mode: str) -> float:
        nearby = perception["nearby_agents"]
        if not nearby:
            return 0.0

        potential = []
        for aid in nearby:
            other = self.world.agents.get(aid)
            if other and other.alive:
                trust = self.trust_scores.get(aid, 0.0)
                potential.append((aid, trust))

        if not potential:
            return 0.0

        avg_trust = sum(t for _, t in potential) / len(potential)
        trade_skill = 0.5
        if self.profession in (Profession.TRADER, Profession.MERCHANT):
            trade_skill = 1.0

        if mode == "buy_food":
            urgency = max(0, (30 - self.food) / 30)
            return urgency * avg_trust * trade_skill * 1.5
        else:
            return avg_trust * trade_skill * 0.7

    def _utility_steal(self, perception: Dict) -> float:
        if self.traits.greed < 0.6 or self.traits.aggression < 0.4:
            return 0.0

        nearby = perception["nearby_agents"]
        victims = []
        for aid in nearby:
            other = self.world.agents.get(aid)
            if other and other.alive and other.money > 20:
                trust = self.trust_scores.get(aid, 0.0)
                if trust < 0.3:
                    victims.append(aid)

        if not victims:
            return 0.0

        desperation = max(0, (20 - self.food) / 20)
        return desperation * self.traits.greed * (1 - self.traits.honor) * 2.0

    def _utility_rest(self) -> float:
        return max(0, (100 - self.energy) / 100) * 0.8

    def _utility_mate(self, perception: Dict) -> float:
        if self.is_child or self.age < 18:
            return 0.0

        nearby = perception["nearby_agents"]
        candidates = []
        for aid in nearby:
            other = self.world.agents.get(aid)
            if other and other.alive and not other.is_child and other.age >= 18 and other.partner_id is None:
                if aid not in self.children_ids and aid not in self.parents:
                    trust = self.trust_scores.get(aid, 0.0)
                    attraction = (self.traits.cooperation + other.traits.cooperation) / 2
                    candidates.append((aid, trust + attraction))

        if not candidates:
            return 0.0

        best = max(candidates, key=lambda x: x[1])
        return best[1] * 0.5 * (self.happiness / 100)

    def _utility_heal(self, perception: Dict) -> float:
        nearby = perception["nearby_agents"]
        injured = []
        for aid in nearby:
            other = self.world.agents.get(aid)
            if other and other.alive and other.health < 60:
                injured.append(aid)

        if not injured:
            return 0.1
        return len(injured) * 0.3 * self.traits.cooperation

    def _utility_build(self, perception: Dict) -> float:
        tile = perception["current_tile"]
        if tile and tile.tile_type in (TileType.VILLAGE, TileType.TOWN):
            return 0.4 * self.traits.ambition
        return 0.1

    def _utility_teach(self, perception: Dict) -> float:
        nearby = perception["nearby_agents"]
        students = [aid for aid in nearby if self.world.agents.get(aid) and self.world.agents[aid].is_child]
        return len(students) * 0.2 * self.traits.cooperation

    def _utility_move(self, perception: Dict) -> float:
        current = perception["current_tile"]
        if not current:
            return 0.0

        goal_bonus = 0.0
        if self.current_goal == "find_food":
            if current.tile_type in (TileType.FARM, TileType.FOREST, TileType.TOWN):
                goal_bonus = 0.2
            else:
                goal_bonus = 0.6

        exploration = self.traits.risk_tolerance * 0.2
        return goal_bonus + exploration

    def _get_action_params(self, action: ActionType, perception: Dict) -> Dict[str, Any]:
        params = {}

        if action == ActionType.MOVE:
            dx, dy = self._pick_direction()
            params = {"dx": dx, "dy": dy}

        elif action == ActionType.FORAGE:
            params = {"intensity": 0.5 + self.traits.intelligence * 0.5}

        elif action == ActionType.TRADE:
            nearby = perception["nearby_agents"]
            if nearby:
                best = max(nearby, key=lambda aid: self.trust_scores.get(aid, 0.0))
                params = {"partner_id": best, "mode": "buy" if self.food < 30 else "sell"}

        elif action == ActionType.STEAL:
            nearby = perception["nearby_agents"]
            victims = [aid for aid in nearby
                      if self.world.agents.get(aid)
                      and self.world.agents[aid].money > 20
                      and self.trust_scores.get(aid, 0.0) < 0.3]
            if victims:
                params = {"victim_id": random.choice(victims)}

        elif action == ActionType.MATE:
            nearby = perception["nearby_agents"]
            candidates = [aid for aid in nearby
                         if self.world.agents.get(aid)
                         and not self.world.agents[aid].is_child
                         and self.world.agents[aid].age >= 18
                         and self.world.agents[aid].partner_id is None]
            if candidates:
                best = max(candidates, key=lambda aid: self.trust_scores.get(aid, 0.0))
                params = {"partner_id": best}

        elif action == ActionType.HEAL:
            nearby = perception["nearby_agents"]
            injured = [aid for aid in nearby
                      if self.world.agents.get(aid)
                      and self.world.agents[aid].health < 60]
            if injured:
                params = {"patient_id": random.choice(injured)}

        elif action == ActionType.PRODUCE:
            params = {"resource": self._pick_resource_to_produce()}

        return params

    def _pick_direction(self) -> Tuple[int, int]:
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0), (1, 1), (-1, -1), (1, -1), (-1, 1)]

        if self.current_goal == "find_food":
            best_dir = (0, 0)
            best_score = -1
            for dx, dy in directions:
                tile = self.world.get_tile(self.x + dx, self.y + dy)
                if tile and tile.tile_type in (TileType.FARM, TileType.FOREST, TileType.TOWN):
                    score = tile.resources.get("food", 0)
                    if score > best_score:
                        best_score = score
                        best_dir = (dx, dy)
            if best_dir != (0, 0):
                return best_dir

        if random.random() < self.traits.risk_tolerance:
            return random.choice(directions)
        else:
            return random.choice([(0, 1), (0, -1), (1, 0), (-1, 0)])

    def _pick_resource_to_produce(self) -> str:
        tile = self.world.get_tile(self.x, self.y)
        if not tile:
            return "food"

        profession_resources = {
            Profession.FARMER: "food",
            Profession.MINER: "raw_materials",
            Profession.WORKER: "wood",
        }

        default = profession_resources.get(self.profession, "food")
        if tile.resources.get(default, 0) > 0:
            return default

        if tile.resources:
            return max(tile.resources.keys(), key=lambda k: tile.resources[k])
        return "food"

    def act(self, action: ActionType, params: Dict[str, Any]) -> List[str]:
        logs = []

        if action == ActionType.MOVE:
            dx = params.get("dx", 0)
            dy = params.get("dy", 0)
            new_x = max(0, min(self.world.width - 1, self.x + dx))
            new_y = max(0, min(self.world.height - 1, self.y + dy))
            if (new_x, new_y) != (self.x, self.y):
                self.world.move_agent(self.id, self.x, self.y, new_x, new_y)
                self.x, self.y = new_x, new_y
                self.energy -= 1  # REDUCED from 2
                logs.append(f"Agent {self.id} moved to ({new_x}, {new_y})")

        elif action == ActionType.FORAGE:
            # Emergency food gathering — works anywhere but low yield
            intensity = params.get("intensity", 0.5)
            tile = self.world.get_tile(self.x, self.y)
            base_food = 1.5 if tile and tile.tile_type == TileType.FOREST else 0.8
            found = base_food * intensity * (0.5 + self.traits.intelligence * 0.5)
            self.food += found
            self.energy -= 1
            logs.append(f"Agent {self.id} foraged {found:.1f} food")

        elif action == ActionType.PRODUCE:
            resource = params.get("resource", "food")
            tile = self.world.get_tile(self.x, self.y)
            if tile:
                amount = tile.get_production_multiplier(resource) * (0.5 + self.traits.intelligence * 0.5)
                if resource == "food":
                    self.food += amount
                    logs.append(f"Agent {self.id} ({self.profession.name}) produced {amount:.1f} food")
                else:
                    value = amount * self.world.get_price(resource)
                    self.money += value
                    logs.append(f"Agent {self.id} produced {amount:.1f} {resource} worth ${value:.1f}")

                self.energy -= 3  # REDUCED from 5

        elif action == ActionType.TRADE:
            partner_id = params.get("partner_id")
            mode = params.get("mode", "buy")
            if partner_id and partner_id in self.world.agents:
                partner = self.world.agents[partner_id]
                if partner.alive:
                    logs.extend(self._execute_trade(partner, mode))

        elif action == ActionType.STEAL:
            victim_id = params.get("victim_id")
            if victim_id and victim_id in self.world.agents:
                victim = self.world.agents[victim_id]
                if victim.alive:
                    logs.extend(self._execute_crime(victim))

        elif action == ActionType.REST:
            self.energy = min(100, self.energy + 25)  # INCREASED from 20
            self.health = min(100, self.health + 3)   # INCREASED from 2
            logs.append(f"Agent {self.id} rested (energy: {self.energy:.0f})")

        elif action == ActionType.HEAL:
            patient_id = params.get("patient_id")
            if patient_id and patient_id in self.world.agents:
                patient = self.world.agents[patient_id]
                if patient.alive:
                    heal_amount = 25 * (0.5 + self.traits.intelligence * 0.5)  # INCREASED
                    patient.health = min(100, patient.health + heal_amount)
                    fee = 5.0
                    patient.money -= fee
                    self.money += fee
                    self._update_trust(patient_id, 0.1)
                    logs.append(f"Agent {self.id} healed Agent {patient_id} for ${fee}")

        elif action == ActionType.BUILD:
            tile = self.world.get_tile(self.x, self.y)
            if tile and tile.tile_type in (TileType.VILLAGE, TileType.TOWN):
                cost = 10.0
                if self.money >= cost:
                    self.money -= cost
                    tile.infrastructure_level += 0.1
                    logs.append(f"Agent {self.id} improved infrastructure at ({self.x}, {self.y})")

        elif action == ActionType.TEACH:
            nearby = self.world.get_agents_in_radius(self.x, self.y, 2)
            children = [aid for aid in nearby if self.world.agents.get(aid) and self.world.agents[aid].is_child]
            for child_id in children:
                child = self.world.agents[child_id]
                child.traits.intelligence = min(1.0, child.traits.intelligence + 0.02)
            if children:
                logs.append(f"Agent {self.id} taught {len(children)} children")

        elif action == ActionType.MATE:
            partner_id = params.get("partner_id")
            if partner_id and partner_id in self.world.agents:
                partner = self.world.agents[partner_id]
                if partner.alive and partner.partner_id is None and self.partner_id is None:
                    self.partner_id = partner_id
                    partner.partner_id = self.id
                    self.relationships[partner_id] = "spouse"
                    partner.relationships[self.id] = "spouse"
                    self._update_trust(partner_id, 0.5)
                    partner._update_trust(self.id, 0.5)
                    logs.append(f"Agent {self.id} and Agent {partner_id} partnered")

        # Passive metabolism cost
        self.energy -= 0.5  # REDUCED from 1.0
        if logs:
            self.last_action = logs[-1]
        return logs

    def _execute_trade(self, partner: 'Agent', mode: str) -> List[str]:
        logs = []
        trust = self.trust_scores.get(partner.id, 0.0)

        if mode == "buy" and self.food < 40:
            price = self.world.get_price("food") * (1 - trust * 0.2)
            max_affordable = self.money / price if price > 0 else 0
            amount = min(15, partner.food * 0.3, max_affordable)  # REDUCED from 20

            if amount > 1 and self.money >= price * amount:
                self.money -= price * amount
                partner.money += price * amount
                self.food += amount
                partner.food -= amount

                self._update_trust(partner.id, 0.05)
                partner._update_trust(self.id, 0.05)
                self._add_memory("trade", {"partner": partner.id, "bought": "food", "amount": amount, "price": price}, 0.2)
                partner._add_memory("trade", {"partner": self.id, "sold": "food", "amount": amount, "price": price}, 0.2)

                logs.append(f"Agent {self.id} bought {amount:.1f} food from Agent {partner.id} for ${price*amount:.1f}")
                self.world._trades_this_step = getattr(self.world, '_trades_this_step', 0) + 1

        elif mode == "sell" and self.food > 60:
            price = self.world.get_price("food") * (1 + trust * 0.1)
            amount = min(self.food - 50, 15, partner.money / price if price > 0 else 0)  # REDUCED from 20

            if amount > 1 and partner.money >= price * amount:
                self.money += price * amount
                partner.money -= price * amount
                self.food -= amount
                partner.food += amount

                self._update_trust(partner.id, 0.05)
                partner._update_trust(self.id, 0.05)
                self._add_memory("trade", {"partner": partner.id, "sold": "food", "amount": amount, "price": price}, 0.2)
                partner._add_memory("trade", {"partner": self.id, "bought": "food", "amount": amount, "price": price}, 0.2)

                logs.append(f"Agent {self.id} sold {amount:.1f} food to Agent {partner.id} for ${price*amount:.1f}")
                self.world._trades_this_step = getattr(self.world, '_trades_this_step', 0) + 1

        return logs

    def _execute_crime(self, victim: 'Agent') -> List[str]:
        logs = []
        success_chance = 0.6 + self.traits.aggression * 0.3 - victim.traits.intelligence * 0.2
        success = random.random() < success_chance

        if success:
            stolen = min(victim.money * 0.3, 50.0)
            victim.money -= stolen
            self.money += stolen

            self._update_trust(victim.id, -0.5)
            victim._update_trust(self.id, -0.8)
            victim._add_memory("crime", {"criminal": self.id, "stolen": stolen}, -0.9)
            self._add_memory("crime", {"victim": victim.id, "stolen": stolen}, -0.3)

            nearby = self.world.get_agents_in_radius(self.x, self.y, 5)
            for aid in nearby:
                if aid != self.id and aid != victim.id:
                    other = self.world.agents.get(aid)
                    if other:
                        other.subjective_reputations[self.id] = other.subjective_reputations.get(self.id, 0.0) - 0.3

            logs.append(f"CRIME: Agent {self.id} robbed Agent {victim.id} of ${stolen:.1f}!")
            self.world._crimes_this_step = getattr(self.world, '_crimes_this_step', 0) + 1

            if random.random() < 0.3:
                self.health -= 15
                logs.append(f"Agent {self.id} was injured during the crime")
        else:
            victim._update_trust(self.id, -0.3)
            self.energy -= 10
            logs.append(f"Agent {self.id} attempted to rob Agent {victim.id} but failed")

        return logs

    def _update_trust(self, other_id: int, delta: float):
        current = self.trust_scores.get(other_id, 0.0)
        self.trust_scores[other_id] = max(-1.0, min(1.0, current + delta))

    def _add_memory(self, event_type: str, details: Dict, valence: float):
        memory = Memory(
            timestep=self.world.timestep,
            event_type=event_type,
            details=details,
            emotional_valence=valence,
            location=(self.x, self.y),
            involved_agent_id=details.get("partner") or details.get("criminal") or details.get("victim"),
        )
        self.memory.append(memory)
        if len(self.memory) > self.memory_capacity:
            self.memory.pop(0)

    def update_metabolism(self):
        """Daily resource consumption — BALANCED to prevent death spirals"""
        # Children consume less
        if self.is_child:
            self.food -= 0.5
            self.energy -= 0.3
        else:
            self.food -= 1.5  # REDUCED from 2.0
            self.energy -= 0.5  # REDUCED (passive already handles some)

        self.age += 0.1

        # Starvation tracking with grace period
        if self.food < 0:
            self.food = 0
            self.starvation_steps += 1
        else:
            self.starvation_steps = 0

        # Health effects — GRACE PERIOD before damage
        if self.starvation_steps >= 3:
            self.health -= 3  # Damage starts after 3 steps of zero food
        elif self.food > 50:
            self.health = min(100, self.health + 1)

        # Energy effects
        if self.energy < 0:
            self.energy = 0
            if self.starvation_steps >= 2:
                self.health -= 2

        # Happiness
        base_happiness = 50
        modifiers = [
            (self.food - 50) * 0.3,
            (self.health - 50) * 0.2,
            (self.money - 50) * 0.1,
            len(self.relationships) * 5,
        ]
        if self.partner_id:
            modifiers.append(10)
        if self.is_child:
            modifiers.append(5)  # Children are naturally happier

        self.happiness = max(0, min(100, base_happiness + sum(modifiers)))

        # Death check
        if self.health <= 0 or self.age > 80:
            self.alive = False
            if not hasattr(self, '_death_timestep'):
                self._death_timestep = self.world.timestep
            self.world._deaths_this_step = getattr(self.world, '_deaths_this_step', 0) + 1
            tile = self.world.get_tile(self.x, self.y)
            if tile and self.id in tile.agents_here:
                tile.agents_here.remove(self.id)

        # Child growth
        if self.is_child and self.age >= 18:
            self.is_child = False
            self.profession = self._roll_profession()
            self.money = 30  # Coming of age stipend

    def reproduce(self) -> Optional['Agent']:
        if not self.partner_id or self.is_child or self.age < 18 or self.age > 50:
            return None

        partner = self.world.agents.get(self.partner_id)
        if not partner or not partner.alive or partner.is_child:
            return None

        # REDUCED cost to make reproduction more viable
        if self.money < 20 or partner.money < 20:
            return None

        if random.random() > 0.08:  # Slightly reduced from 0.1
            return None

        child_x = max(0, min(self.world.width - 1, self.x + random.randint(-1, 1)))
        child_y = max(0, min(self.world.height - 1, self.y + random.randint(-1, 1)))

        child = Agent(
            x=child_x, y=child_y,
            world=self.world,
            age=0, is_child=True,
            parents=(self.id, partner.id),
            inherited_traits=self.traits,
        )

        self.children_ids.append(child.id)
        partner.children_ids.append(child.id)
        self.relationships[child.id] = "parent"
        partner.relationships[child.id] = "parent"
        child.relationships[self.id] = "child"
        child.relationships[partner.id] = "child"

        self.money -= 10  # REDUCED from 15
        partner.money -= 10

        self.world._births_this_step = getattr(self.world, '_births_this_step', 0) + 1
        return child

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "x": self.x,
            "y": self.y,
            "age": round(self.age, 1),
            "alive": self.alive,
            "is_child": self.is_child,
            "profession": self.profession.name,
            "role": self.role,  # Compatibility property
            "money": round(self.money, 1),
            "food": round(self.food, 1),
            "health": round(self.health, 1),
            "energy": round(self.energy, 1),
            "happiness": round(self.happiness, 1),
            "housing_level": self.housing_level,
            "partner_id": self.partner_id,
            "children_count": len(self.children_ids),
            "trust_count": len(self.trust_scores),
            "goal": self.current_goal,
            "starvation_steps": self.starvation_steps,
            "traits": {
                "greed": round(self.traits.greed, 2),
                "cooperation": round(self.traits.cooperation, 2),
                "intelligence": round(self.traits.intelligence, 2),
                "ambition": round(self.traits.ambition, 2),
                "honor": round(self.traits.honor, 2),
                "aggression": round(self.traits.aggression, 2),
            },
            "trait_percentages": self.trait_percentages,  # Compatibility property
        }


# Import here to avoid circular reference issues
from .world import World, TileType
