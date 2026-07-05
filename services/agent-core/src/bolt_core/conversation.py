"""Conversation store: multi-turn dialogue persistence."""

import json
import sqlite3
import threading
import time
from dataclasses import dataclass, field, asdict


@dataclass(frozen=True)
class ConversationMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str
    tool_call_id: str | None = None
    tool_calls: list | None = None
    timestamp: str = field(default_factory=lambda: str(int(time.time() * 1000)))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        return cls(
            role=data["role"],
            content=data["content"],
            tool_call_id=data.get("tool_call_id"),
            tool_calls=data.get("tool_calls"),
            timestamp=data.get("timestamp", ""),
            metadata=data.get("metadata") or {},
        )


class ConversationStore:
    """SQLite-backed conversation persistence."""

    def __init__(self, db_path: str = ":memory:") -> None:
        self._db_path = db_path
        self._lock = threading.Lock()
        if db_path != ":memory:":
            from pathlib import Path
            Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    tool_call_id TEXT,
                    tool_calls TEXT,
                    timestamp TEXT,
                    metadata TEXT
                )
            """)
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_conv ON messages(conversation_id)")
            conn.commit()

    def add(self, conversation_id: str, message: ConversationMessage) -> None:
        with self._lock, self._conn() as conn:
            conn.execute("""
                INSERT INTO messages
                (conversation_id, role, content, tool_call_id, tool_calls, timestamp, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                conversation_id, message.role, message.content,
                message.tool_call_id,
                json.dumps(message.tool_calls) if message.tool_calls else None,
                message.timestamp,
                json.dumps(message.metadata) if message.metadata else None,
            ))
            conn.commit()

    def history(self, conversation_id: str, limit: int = 50) -> list[ConversationMessage]:
        with self._lock, self._conn() as conn:
            rows = conn.execute("""
                SELECT * FROM messages WHERE conversation_id = ?
                ORDER BY id DESC LIMIT ?
            """, (conversation_id, limit)).fetchall()
        # Reverse to chronological order
        rows = list(reversed(rows))
        return [ConversationMessage(
            role=r["role"], content=r["content"],
            tool_call_id=r["tool_call_id"],
            tool_calls=json.loads(r["tool_calls"]) if r["tool_calls"] else None,
            timestamp=r["timestamp"] or "",
            metadata=json.loads(r["metadata"]) if r["metadata"] else {},
        ) for r in rows]

    def list_conversations(self) -> list[str]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT DISTINCT conversation_id FROM messages ORDER BY conversation_id").fetchall()
        return [r["conversation_id"] for r in rows]

    def delete(self, conversation_id: str) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
            conn.commit()
