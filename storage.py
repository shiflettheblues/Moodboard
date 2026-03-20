import os
import sqlite3
from datetime import datetime

import config


def _get_db():
    """Get a database connection, creating the data directory and tables if needed."""
    os.makedirs(config.DATA_DIR, exist_ok=True)
    os.makedirs(config.IMAGES_DIR, exist_ok=True)
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    _ensure_tables(conn)
    return conn


def _ensure_tables(conn):
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS boards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            board_id INTEGER NOT NULL,
            added_by TEXT NOT NULL,
            item_type TEXT NOT NULL,
            content TEXT NOT NULL,
            image_path TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (board_id) REFERENCES boards(id)
        );
    """)
    conn.commit()


def get_or_create_active_board(phone):
    """Return the currently active board, creating a default one if none exists."""
    conn = _get_db()
    row = conn.execute("SELECT * FROM boards WHERE is_active = 1 ORDER BY created_at DESC LIMIT 1").fetchone()
    if row:
        conn.close()
        return dict(row)

    # Auto-create a board named with today's date
    name = f"Board {datetime.now().strftime('%b %d')}"
    conn.execute("UPDATE boards SET is_active = 0")
    conn.execute(
        "INSERT INTO boards (name, created_by, is_active) VALUES (?, ?, 1)",
        (name, phone),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM boards WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    result = dict(row)
    conn.close()
    return result


def create_new_board(phone, name):
    """Create a new board and make it active, deactivating all others."""
    conn = _get_db()
    conn.execute("UPDATE boards SET is_active = 0")
    conn.execute(
        "INSERT INTO boards (name, created_by, is_active) VALUES (?, ?, 1)",
        (name, phone),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM boards WHERE is_active = 1 ORDER BY id DESC LIMIT 1").fetchone()
    result = dict(row)
    conn.close()
    return result


def add_item(board_id, phone, item_type, content, image_path=None):
    """Add an item (image, text, or instagram) to a board."""
    conn = _get_db()
    conn.execute(
        "INSERT INTO items (board_id, added_by, item_type, content, image_path) VALUES (?, ?, ?, ?, ?)",
        (board_id, phone, item_type, content, image_path),
    )
    conn.commit()
    count = conn.execute("SELECT COUNT(*) as c FROM items WHERE board_id = ?", (board_id,)).fetchone()["c"]
    conn.close()
    return count


def get_board_items(board_id):
    """Get all items for a board, ordered by when they were added."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT * FROM items WHERE board_id = ? ORDER BY added_at ASC", (board_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def list_boards():
    """List all boards with their item counts."""
    conn = _get_db()
    rows = conn.execute("""
        SELECT b.*, COUNT(i.id) as item_count
        FROM boards b
        LEFT JOIN items i ON b.id = i.board_id
        GROUP BY b.id
        ORDER BY b.created_at DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def switch_board(name):
    """Switch active board by name (case-insensitive partial match)."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM boards WHERE LOWER(name) LIKE ? ORDER BY created_at DESC LIMIT 1",
        (f"%{name.lower()}%",),
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("UPDATE boards SET is_active = 0")
    conn.execute("UPDATE boards SET is_active = 1 WHERE id = ?", (row["id"],))
    conn.commit()
    result = dict(row)
    conn.close()
    return result


def delete_last_item(board_id):
    """Delete the most recently added item from a board."""
    conn = _get_db()
    row = conn.execute(
        "SELECT * FROM items WHERE board_id = ? ORDER BY added_at DESC LIMIT 1", (board_id,)
    ).fetchone()
    if not row:
        conn.close()
        return None
    conn.execute("DELETE FROM items WHERE id = ?", (row["id"],))
    conn.commit()
    result = dict(row)
    conn.close()
    return result


def clear_board(board_id):
    """Remove all items from a board."""
    conn = _get_db()
    count = conn.execute("SELECT COUNT(*) as c FROM items WHERE board_id = ?", (board_id,)).fetchone()["c"]
    conn.execute("DELETE FROM items WHERE board_id = ?", (board_id,))
    conn.commit()
    conn.close()
    return count


def get_board_status(board_id):
    """Get status info for a board: item count and breakdown by type."""
    conn = _get_db()
    rows = conn.execute(
        "SELECT item_type, COUNT(*) as c FROM items WHERE board_id = ? GROUP BY item_type",
        (board_id,),
    ).fetchall()
    conn.close()
    return {r["item_type"]: r["c"] for r in rows}
