"""
Persistent Memory System for Nova AI Agent.
3-layer architecture: Working Memory (context window), Episodic Memory (SQLite),
and Semantic Memory (user profile key-value store).
"""

import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from config.settings import settings

class MemoryManager:
    """Manages long-term memory storage and retrieval for the Nova AI Agent."""

    def __init__(self):
        self._stats_cache = None
        self._init_db()

    @property
    def db_path(self) -> Path:
        return settings.DATA_DIR / "nova_memory.db"

    def _get_conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the SQLite database schema."""
        try:
            with self._get_conn() as conn:
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS episodic_memory (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        timestamp TEXT NOT NULL,
                        user_message TEXT NOT NULL,
                        assistant_response TEXT NOT NULL,
                        tools_used TEXT DEFAULT '[]'
                    );

                    CREATE TABLE IF NOT EXISTS semantic_memory (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    );

                    CREATE INDEX IF NOT EXISTS idx_episodic_timestamp
                        ON episodic_memory(timestamp);
                """)
            self._stats_cache = self._compute_stats()
        except Exception as e:
            print(f"[Memory] DB init error: {e}", file=sys.stderr)

    def _compute_stats(self) -> dict:
        """Computes the stats from database."""
        try:
            with self._get_conn() as conn:
                total_episodes = conn.execute(
                    "SELECT COUNT(*) as n FROM episodic_memory"
                ).fetchone()["n"]
                total_facts = conn.execute(
                    "SELECT COUNT(*) as n FROM semantic_memory"
                ).fetchone()["n"]
            return {
                "total_conversations": total_episodes,
                "known_facts": total_facts,
                "db_path": str(self.db_path)
            }
        except Exception:
            return {"total_conversations": 0, "known_facts": 0, "db_path": str(self.db_path)}

    # ── Episodic Memory (past conversations) ──────────────────────────────

    def save_interaction(self, user_message: str, assistant_response: str, tools_used: list = None):
        """Save a conversation turn to episodic memory."""
        try:
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO episodic_memory
                       (timestamp, user_message, assistant_response, tools_used)
                       VALUES (?, ?, ?, ?)""",
                    (
                        datetime.now().isoformat(),
                        user_message,
                        assistant_response,
                        json.dumps(tools_used or [])
                    )
                )
            if self._stats_cache:
                self._stats_cache["total_conversations"] += 1
        except Exception as e:
            print(f"[Memory] Save interaction error: {e}", file=sys.stderr)

    def search_memory(self, query: str, limit: int = 5) -> str:
        """
        Search episodic memory for relevant past interactions.
        Uses simple keyword search (sufficient for SQLite without vectors).
        """
        try:
            query_words = [w.lower().strip() for w in query.split() if len(w) > 3]
            if not query_words:
                return self._get_recent_memory(limit)

            # Build a LIKE query for each significant word
            conditions = " OR ".join(
                ["LOWER(user_message) LIKE ? OR LOWER(assistant_response) LIKE ?" for _ in query_words]
            )
            params = []
            for word in query_words:
                params.extend([f"%{word}%", f"%{word}%"])

            with self._get_conn() as conn:
                rows = conn.execute(
                    f"""SELECT timestamp, user_message, assistant_response
                        FROM episodic_memory
                        WHERE {conditions}
                        ORDER BY timestamp DESC
                        LIMIT ?""",
                    params + [limit]
                ).fetchall()

            if not rows:
                return f"No memories found matching '{query}'. This may be a new topic."

            lines = [f"Found {len(rows)} relevant memory entries:\n"]
            for row in rows:
                ts = row["timestamp"][:16].replace("T", " ")
                lines.append(f"[{ts}] You asked: {row['user_message'][:100]}")
                lines.append(f"  I answered: {row['assistant_response'][:150]}\n")

            return "\n".join(lines)

        except Exception as e:
            print(f"[Memory] Search error: {e}", file=sys.stderr)
            return "Memory search encountered an error."

    def _get_recent_memory(self, limit: int = 5) -> str:
        """Return the most recent interactions."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    """SELECT timestamp, user_message, assistant_response
                       FROM episodic_memory
                       ORDER BY timestamp DESC LIMIT ?""",
                    (limit,)
                ).fetchall()

            if not rows:
                return "No conversation history found yet."

            lines = ["Recent conversation history:\n"]
            for row in rows:
                ts = row["timestamp"][:16].replace("T", " ")
                lines.append(f"[{ts}] You: {row['user_message'][:100]}")
                lines.append(f"  Nova: {row['assistant_response'][:150]}\n")

            return "\n".join(lines)
        except Exception as e:
            return f"Could not retrieve memory: {e}"

    # ── Semantic Memory (user facts & preferences) ─────────────────────────

    def save_fact(self, key: str, value: str) -> str:
        """Store a user fact or preference."""
        try:
            key_clean = key.strip().lower().replace(" ", "_")
            with self._get_conn() as conn:
                conn.execute(
                    """INSERT INTO semantic_memory (key, value, updated_at)
                       VALUES (?, ?, ?)
                       ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at""",
                    (key_clean, value.strip(), datetime.now().isoformat())
                )
            self._stats_cache = self._compute_stats()
            return f"Remembered: {key} = {value}"
        except Exception as e:
            print(f"[Memory] Save fact error: {e}", file=sys.stderr)
            return f"Could not save memory: {e}"

    def get_user_profile(self) -> str:
        """Return all known facts about the user."""
        try:
            with self._get_conn() as conn:
                rows = conn.execute(
                    "SELECT key, value, updated_at FROM semantic_memory ORDER BY key"
                ).fetchall()

            if not rows:
                return "No user facts stored yet."

            lines = ["User Profile / Known Facts:\n"]
            for row in rows:
                ts = row["updated_at"][:16].replace("T", " ")
                lines.append(f"  {row['key']}: {row['value']}  (saved {ts})")

            return "\n".join(lines)
        except Exception as e:
            return f"Could not retrieve user profile: {e}"

    def get_stats(self) -> dict:
        """Return memory statistics for the UI dashboard."""
        if self._stats_cache is None:
            self._stats_cache = self._compute_stats()
        return self._stats_cache


# Global memory manager instance
memory_manager = MemoryManager()
