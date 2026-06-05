from typing import List, Dict, Any, Optional

class Family:
    def __init__(self, family_id: int, members: List[int], parent_ids: List[int], home_x: int, home_y: int):
        self.id: int = family_id
        self.member_ids: List[int] = members
        self.parent_ids: List[int] = parent_ids
        self.home_x: int = home_x
        self.home_y: int = home_y
        self.shared_savings: float = 0.0

    def add_member(self, agent_id: int):
        if agent_id not in self.member_ids:
            self.member_ids.append(agent_id)

    def remove_member(self, agent_id: int):
        if agent_id in self.member_ids:
            self.member_ids.remove(agent_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "member_ids": self.member_ids,
            "parent_ids": self.parent_ids,
            "home_x": self.home_x,
            "home_y": self.home_y,
            "shared_savings": round(self.shared_savings, 2)
        }

class FamilyRegistry:
    def __init__(self):
        self.families: Dict[int, Family] = {}
        self.next_family_id: int = 1

    def create_family(self, parent_ids: List[int], home_x: int, home_y: int) -> Family:
        new_fam = Family(self.next_family_id, parent_ids.copy(), parent_ids, home_x, home_y)
        self.families[self.next_family_id] = new_fam
        self.next_family_id += 1
        return new_fam
