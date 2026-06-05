from typing import Dict, List, Any

class MemoryEntry:
    def __init__(self, description: str, trust_change: int, step: int):
        self.description: str = description
        self.trust_change: int = trust_change
        self.step: int = step

    def to_dict(self) -> Dict[str, Any]:
        return {
            "description": self.description,
            "trustChange": self.trust_change,
            "step": self.step
        }

class RelationshipManager:
    def __init__(self):
        # Maps target_agent_id -> trust score (clamped between -100 and 100)
        self.trust_scores: Dict[int, float] = {}
        # Maps target_agent_id -> list of MemoryEntry
        self.memories: Dict[int, List[MemoryEntry]] = {}

    def get_trust(self, agent_id: int) -> float:
        return self.trust_scores.get(agent_id, 0.0)

    def modify_trust(self, agent_id: int, change: float, description: str, step: int):
        current = self.trust_scores.get(agent_id, 0.0)
        new_trust = max(-100.0, min(100.0, current + change))
        self.trust_scores[agent_id] = round(new_trust, 2)

        # Log memory of this interaction
        if agent_id not in self.memories:
            self.memories[agent_id] = []
        
        self.memories[agent_id].append(MemoryEntry(description, int(change), step))
        if len(self.memories[agent_id]) > 10:
            self.memories[agent_id].pop(0)

    def get_memories_as_list(self) -> List[Dict[str, Any]]:
        flat_memories = []
        for agent_id, mems in self.memories.items():
            for m in mems:
                entry = m.to_dict()
                entry["target_agent_id"] = agent_id
                flat_memories.append(entry)
        # Sort by step desc
        flat_memories.sort(key=lambda x: x["step"], reverse=True)
        return flat_memories[:20]  # Return last 20 memories total
