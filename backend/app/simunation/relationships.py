from typing import Dict, List, Any, Optional

class Bond:
    def __init__(self, agent_id_1: int, agent_id_2: int, strength: float, bond_type: str):
        self.agent_id_1 = agent_id_1
        self.agent_id_2 = agent_id_2
        self.strength = strength
        self.bond_type = bond_type
        self.last_interaction_step = 0

class SocialEngine:
    def __init__(self, world: 'World'):
        self.world = world
        self.bonds: Dict[tuple, Bond] = {}

    def get_bond(self, id1: int, id2: int) -> Optional[Bond]:
        key = (min(id1, id2), max(id1, id2))
        return self.bonds.get(key)

    def update_bond(self, id1: int, id2: int, strength: float, bond_type: str):
        key = (min(id1, id2), max(id1, id2))
        if key in self.bonds:
            self.bonds[key].strength = max(-1.0, min(1.0, strength))
            self.bonds[key].bond_type = bond_type
            self.bonds[key].last_interaction_step = self.world.timestep
        else:
            self.bonds[key] = Bond(key[0], key[1], strength, bond_type)
            self.bonds[key].last_interaction_step = self.world.timestep

    def decay_bonds(self):
        """Decay bonds over time if they haven't interacted recently"""
        keys_to_remove = []
        for key, bond in self.bonds.items():
            if self.world.timestep - bond.last_interaction_step > 50:
                bond.strength *= 0.95
                if abs(bond.strength) < 0.05:
                    keys_to_remove.append(key)
        for key in keys_to_remove:
            del self.bonds[key]

    def step(self) -> List[str]:
        self.decay_bonds()
        return []
