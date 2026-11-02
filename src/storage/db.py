import os
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any

DEFAULT_DB_DIR = Path.home() / ".local" / "share" / "agent-browser"
DEFAULT_DB_PATH = DEFAULT_DB_DIR / "agent_browser.db"

class DatabaseManager:
    """Manages SQLite storage for profiles, active sessions, actions, and scrapes."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self):
        with self.get_connection() as conn:
            conn.executescript("""
            CREATE TABLE IF NOT EXISTS profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                path TEXT NOT NULL,
                is_temp INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                last_used_at TEXT NOT NULL,
                notes TEXT DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_uuid TEXT UNIQUE NOT NULL,
                profile_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                ended_at TEXT,
                initial_url TEXT,
                status TEXT DEFAULT 'active'
            );

            CREATE TABLE IF NOT EXISTS session_actions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_uuid TEXT NOT NULL,
                step_idx INTEGER NOT NULL,
                url TEXT NOT NULL,
                title TEXT,
                operation TEXT NOT NULL,
                target_element TEXT,
                confidence REAL,
                latency_ms REAL,
                timestamp TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS scrapes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT NOT NULL,
                title TEXT NOT NULL,
                file_path TEXT NOT NULL,
                word_count INTEGER,
                profile_name TEXT,
                scraped_at TEXT NOT NULL
            );
            """)

    # --- Profile Operations ---

    def register_profile(self, name: str, path: str, is_temp: bool = False, notes: str = "") -> Dict[str, Any]:
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO profiles (name, path, is_temp, is_active, created_at, last_used_at, notes)
            VALUES (?, ?, ?, 0, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                path = excluded.path,
                last_used_at = excluded.last_used_at;
            """, (name, path, 1 if is_temp else 0, now, now, notes))
            row = conn.execute("SELECT * FROM profiles WHERE name = ?", (name,)).fetchone()
            return dict(row)

    def list_profiles(self) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM profiles ORDER BY last_used_at DESC").fetchall()
            return [dict(r) for r in rows]

    def get_profile(self, name: str) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE name = ?", (name,)).fetchone()
            return dict(row) if row else None

    def get_active_profile(self) -> Optional[Dict[str, Any]]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM profiles WHERE is_active = 1").fetchone()
            return dict(row) if row else None

    def set_active_profile(self, name: str):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("UPDATE profiles SET is_active = 0")
            conn.execute("UPDATE profiles SET is_active = 1, last_used_at = ? WHERE name = ?", (now, name))

    def delete_profile(self, name: str) -> bool:
        with self.get_connection() as conn:
            cur = conn.execute("DELETE FROM profiles WHERE name = ?", (name,))
            return cur.rowcount > 0

    # --- Session & Action Operations ---

    def start_session(self, session_uuid: str, profile_name: str, initial_url: str = ""):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO sessions (session_uuid, profile_name, started_at, initial_url, status)
            VALUES (?, ?, ?, ?, 'active')
            """, (session_uuid, profile_name, now, initial_url))

    def record_action(self, session_uuid: str, step_idx: int, url: str, title: str,
                      operation: str, target_element: Optional[str] = None,
                      confidence: float = 0.0, latency_ms: float = 0.0):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO session_actions (session_uuid, step_idx, url, title, operation, target_element, confidence, latency_ms, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_uuid, step_idx, url, title, operation, target_element, confidence, latency_ms, now))

    def end_session(self, session_uuid: str, status: str = "completed"):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            UPDATE sessions SET ended_at = ?, status = ? WHERE session_uuid = ?
            """, (now, status, session_uuid))

    def get_recent_actions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("""
            SELECT * FROM session_actions ORDER BY id DESC LIMIT ?
            """, (limit,)).fetchall()
            return [dict(r) for r in rows]

    # --- Scrapes Operations ---

    def record_scrape(self, url: str, title: str, file_path: str, word_count: int, profile_name: str):
        now = datetime.utcnow().isoformat()
        with self.get_connection() as conn:
            conn.execute("""
            INSERT INTO scrapes (url, title, file_path, word_count, profile_name, scraped_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (url, title, file_path, word_count, profile_name, now))

    def list_scrapes(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM scrapes ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
            return [dict(r) for r in rows]
