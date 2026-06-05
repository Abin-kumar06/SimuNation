import random
from typing import Dict, Any, List

class WorldEvent:
    def __init__(self, name: str, duration: int, description: str, modifiers: Dict[str, float]):
        self.name: str = name
        self.duration: int = duration
        self.max_duration: int = duration
        self.description: str = description
        self.modifiers: Dict[str, float] = modifiers  # e.g., {"food_multiplier": 0.5}

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "duration": self.duration,
            "max_duration": self.max_duration,
            "description": self.description
        }

class EventManager:
    def __init__(self):
        self.active_events: List[WorldEvent] = []
        self.history: List[Dict[str, Any]] = []

    def get_multiplier(self, key: str) -> float:
        val = 1.0
        for event in self.active_events:
            if key in event.modifiers:
                val *= event.modifiers[key]
        return val

    def step_events(self, step: int) -> List[str]:
        logs = []
        
        # Age existing events
        for event in list(self.active_events):
            event.duration -= 1
            if event.duration <= 0:
                self.active_events.remove(event)
                logs.append(f"🌤️ Event Ended: The {event.name} has concluded.")

        # Randomly roll for a new event (3% chance per step if no events are active)
        if not self.active_events and random.random() < 0.04:
            new_event = self._generate_random_event(step)
            self.active_events.append(new_event)
            self.history.append({
                "step": step,
                "name": new_event.name,
                "description": new_event.description
            })
            logs.append(f"📢 Event Alert: {new_event.name} has started! {new_event.description}")
            
        return logs

    def _generate_random_event(self, step: int) -> WorldEvent:
        events_pool = [
            {
                "name": "Drought",
                "duration": 8,
                "description": "Severe lack of rain. Crops are drying out, dropping food production.",
                "modifiers": {"food_production": 0.4, "happiness": 0.85}
            },
            {
                "name": "Disease Outbreak",
                "duration": 6,
                "description": "An infectious epidemic is spreading. Health levels are falling.",
                "modifiers": {"health_drain": 2.0, "happiness": 0.75}
            },
            {
                "name": "Economic Boom",
                "duration": 10,
                "description": "Markets are thriving. Higher labor wages and worker satisfaction.",
                "modifiers": {"wage_multiplier": 1.5, "happiness": 1.25}
            },
            {
                "name": "Resource Discovery",
                "duration": 5,
                "description": "A rich vein of mineral ore has been found, doubling miner yield.",
                "modifiers": {"mine_production": 2.5}
            },
            {
                "name": "Market Crash",
                "duration": 7,
                "description": "Panic in the trading halls. Prices and trust levels plummet.",
                "modifiers": {"price_deflation": 0.7, "happiness": 0.8}
            }
        ]
        
        sel = random.choice(events_pool)
        return WorldEvent(sel["name"], sel["duration"], sel["description"], sel["modifiers"])
