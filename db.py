import sqlite3
import json
from models import UserProfile
from config import DB_PATH
import os

def get_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                tg_id INTEGER PRIMARY KEY,
                username TEXT,
                display_name TEXT,
                avatar_url TEXT,
                bio TEXT,
                games TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

def save_profile(profile: UserProfile):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO users (tg_id, username, display_name, avatar_url, bio, games)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (profile.tg_id, profile.username, profile.display_name,
              profile.avatar_url, profile.bio, json.dumps(profile.games or [])))
        conn.commit()

def get_profile(tg_id: int):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM users WHERE tg_id = ?", (tg_id,)).fetchone()
        if row:
            return UserProfile(
                tg_id=row["tg_id"],
                username=row["username"],
                display_name=row["display_name"],
                avatar_url=row["avatar_url"],
                bio=row["bio"],
                games=json.loads(row["games"] or "[]")
            )
        return None

def delete_profile(tg_id: int):
    with get_db() as conn:
        conn.execute("DELETE FROM users WHERE tg_id = ?", (tg_id,))
        conn.commit()