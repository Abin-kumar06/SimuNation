import sqlite3
import json
import os
from typing import List, Dict, Any, Optional
import numpy as np

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "village_memories.db")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS agent_memories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id INTEGER,
            agent_name TEXT,
            timestep INTEGER,
            memory_text TEXT,
            importance INTEGER,
            embedding TEXT,  -- JSON list of floats
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_agent_memory(agent_id: int, agent_name: str, timestep: int, memory_text: str, importance: int, embedding: Optional[List[float]] = None):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    embedding_str = json.dumps(embedding) if embedding else None
    cursor.execute("""
        INSERT INTO agent_memories (agent_id, agent_name, timestep, memory_text, importance, embedding)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (agent_id, agent_name, timestep, memory_text, importance, embedding_str))
    conn.commit()
    conn.close()

def get_agent_memories(agent_id: int) -> List[Dict[str, Any]]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, agent_id, agent_name, timestep, memory_text, importance, embedding, timestamp
        FROM agent_memories
        WHERE agent_id = ?
        ORDER BY timestep DESC
    """, (agent_id,))
    rows = cursor.fetchall()
    conn.close()

    memories = []
    for r in rows:
        emb = None
        if r["embedding"]:
            try:
                emb = json.loads(r["embedding"])
            except Exception:
                pass
        memories.append({
            "id": r["id"],
            "agent_id": r["agent_id"],
            "agent_name": r["agent_name"],
            "timestep": r["timestep"],
            "memory_text": r["memory_text"],
            "importance": r["importance"],
            "embedding": emb,
            "timestamp": r["timestamp"]
        })
    return memories

def cosine_similarity(v1: List[float], v2: List[float]) -> float:
    if not v1 or not v2:
        return 0.0
    arr1 = np.array(v1, dtype=np.float32)
    arr2 = np.array(v2, dtype=np.float32)
    norm1 = np.linalg.norm(arr1)
    norm2 = np.linalg.norm(arr2)
    if norm1 == 0.0 or norm2 == 0.0:
        return 0.0
    return float(np.dot(arr1, arr2) / (norm1 * norm2))

def retrieve_relevant_memories(agent_id: int, query_embedding: List[float], limit: int = 5) -> List[Dict[str, Any]]:
    memories = get_agent_memories(agent_id)
    if not memories or not query_embedding:
        return memories[:limit]

    scored_memories = []
    for m in memories:
        sim = 0.0
        if m["embedding"]:
            sim = cosine_similarity(query_embedding, m["embedding"])
        scored_memories.append((sim, m))

    # Sort by similarity descending
    scored_memories.sort(key=lambda x: x[0], reverse=True)
    return [item[1] for item in scored_memories[:limit]]

# Initialize DB on import
init_db()
