from typing import List, Dict, Set, Optional

class FamilySystem:
    def __init__(self, world: 'World'):
        self.world = world
        self.households: Dict[int, Set[int]] = {}
        self.next_household_id = 1

    def form_household(self, agent1_id: int, agent2_id: int) -> int:
        hid = self.next_household_id
        self.next_household_id += 1
        self.households[hid] = {agent1_id, agent2_id}
        return hid

    def add_child_to_household(self, child_id: int, parent_id: int):
        for hid, members in self.households.items():
            if parent_id in members:
                members.add(child_id)
                return
        hid = self.form_household(parent_id, child_id)

    def household_resource_sharing(self):
        """Share food and money among household members in need"""
        for hid, members in self.households.items():
            alive_members = [self.world.agents[aid] for aid in members if aid in self.world.agents and self.world.agents[aid].alive]
            if not alive_members:
                continue

            total_food = sum(a.food for a in alive_members)
            avg_food = total_food / len(alive_members)
            for a in alive_members:
                a.food = avg_food

            total_money = sum(a.money for a in alive_members)
            avg_money = total_money / len(alive_members)
            for a in alive_members:
                a.money = avg_money

    def step(self) -> List[str]:
        self.household_resource_sharing()
        return []
