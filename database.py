import sqlite3
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

DB_NAME = "posts_queue.db"

def init_db() -> None:
    """Initializes the SQLite database and creates the posts table if it doesn't exist."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticker TEXT NOT NULL,
                post_text TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                published_at TIMESTAMP
            )
        """)
        conn.commit()
    print("💾 Database initialized successfully.")


def save_draft(ticker: str, post_text: str) -> int:
    """Saves a new AI draft into the database with PENDING status. Returns the draft ID."""
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO posts (ticker, post_text, status, created_at)
            VALUES (?, ?, 'PENDING', ?)
            """,
            (ticker, post_text, datetime.now(timezone.utc).isoformat())
        )
        conn.commit()
        return cursor.lastrowid


def update_post_status(post_id: int, status: str) -> None:
    """Updates post status (e.g., 'APPROVED', 'REJECTED', 'PUBLISHED')."""
    published_at = datetime.now(timezone.utc).isoformat() if status == "PUBLISHED" else None
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE posts 
            SET status = ?, published_at = COALESCE(?, published_at)
            WHERE id = ?
            """,
            (status, published_at, post_id)
        )
        conn.commit()


def get_pending_published_posts() -> List[Dict[str, Any]]:
    """Retrieves all APPROVED posts ready to be dispatched to social media."""
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, ticker, post_text FROM posts WHERE status = 'APPROVED' ORDER BY id ASC"
        )
        rows = cursor.fetchall()
        return [dict(row) for row in rows]


if __name__ == "__main__":
    init_db()