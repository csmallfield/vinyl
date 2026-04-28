"""SQLite layer. Plain stdlib sqlite3, no ORM.

Schema is created on first run. Two tables:
- items:          one row per album in library or wishlist
- discogs_cache:  raw JSON responses keyed by URL, with TTL
"""
import sqlite3
import time
from contextlib import contextmanager
from typing import Iterable, Optional

from .config import settings


SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    discogs_master_id   INTEGER NOT NULL UNIQUE,
    status              TEXT NOT NULL CHECK (status IN ('library', 'wishlist')),
    artist              TEXT NOT NULL,
    title               TEXT NOT NULL,
    year                INTEGER,
    cover_url           TEXT,
    thumb_url           TEXT,
    tracklist_json      TEXT,           -- JSON array of {position, title, duration}
    genres_json         TEXT,           -- JSON array of strings
    styles_json         TEXT,
    notes               TEXT,
    added_at            INTEGER NOT NULL    -- unix epoch seconds
);

CREATE INDEX IF NOT EXISTS idx_items_status ON items(status);
CREATE INDEX IF NOT EXISTS idx_items_added_at ON items(added_at);

CREATE TABLE IF NOT EXISTS discogs_cache (
    url         TEXT PRIMARY KEY,
    body        TEXT NOT NULL,        -- raw JSON string
    fetched_at  INTEGER NOT NULL
);
"""


def init_db() -> None:
    """Create tables if they don't exist. Safe to call repeatedly."""
    settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)


@contextmanager
def connect():
    """Yield a sqlite3 connection with sensible defaults."""
    conn = sqlite3.connect(settings.DB_PATH, isolation_level=None)  # autocommit
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")  # better for concurrent reads
    try:
        yield conn
    finally:
        conn.close()


# ---------- items ----------

def list_items(status: str) -> list[sqlite3.Row]:
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM items WHERE status = ? ORDER BY added_at DESC",
            (status,),
        )
        return cur.fetchall()


def get_item_by_master_id(master_id: int) -> Optional[sqlite3.Row]:
    with connect() as conn:
        cur = conn.execute(
            "SELECT * FROM items WHERE discogs_master_id = ?", (master_id,)
        )
        return cur.fetchone()


def get_statuses_for_master_ids(master_ids: Iterable[int]) -> dict[int, str]:
    """Return {master_id: status} for any of the given IDs already in the DB.
    Used to badge search results.
    """
    ids = [int(i) for i in master_ids if i]
    if not ids:
        return {}
    placeholders = ",".join("?" * len(ids))
    with connect() as conn:
        cur = conn.execute(
            f"SELECT discogs_master_id, status FROM items "
            f"WHERE discogs_master_id IN ({placeholders})",
            ids,
        )
        return {row["discogs_master_id"]: row["status"] for row in cur.fetchall()}


def upsert_item(
    *,
    master_id: int,
    status: str,
    artist: str,
    title: str,
    year: Optional[int],
    cover_url: Optional[str],
    thumb_url: Optional[str],
    tracklist_json: Optional[str],
    genres_json: Optional[str],
    styles_json: Optional[str],
) -> None:
    """Insert or update by master_id. Used by add and move."""
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO items (
                discogs_master_id, status, artist, title, year,
                cover_url, thumb_url, tracklist_json, genres_json, styles_json,
                added_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(discogs_master_id) DO UPDATE SET
                status         = excluded.status,
                artist         = excluded.artist,
                title          = excluded.title,
                year           = excluded.year,
                cover_url      = excluded.cover_url,
                thumb_url      = excluded.thumb_url,
                tracklist_json = excluded.tracklist_json,
                genres_json    = excluded.genres_json,
                styles_json    = excluded.styles_json
            """,
            (
                master_id, status, artist, title, year,
                cover_url, thumb_url, tracklist_json, genres_json, styles_json,
                now,
            ),
        )


def update_status(master_id: int, status: str) -> None:
    with connect() as conn:
        conn.execute(
            "UPDATE items SET status = ? WHERE discogs_master_id = ?",
            (status, master_id),
        )


def delete_item(master_id: int) -> None:
    with connect() as conn:
        conn.execute(
            "DELETE FROM items WHERE discogs_master_id = ?", (master_id,)
        )


# ---------- discogs_cache ----------

def cache_get(url: str, max_age: int) -> Optional[str]:
    cutoff = int(time.time()) - max_age
    with connect() as conn:
        cur = conn.execute(
            "SELECT body FROM discogs_cache WHERE url = ? AND fetched_at >= ?",
            (url, cutoff),
        )
        row = cur.fetchone()
        return row["body"] if row else None


def cache_set(url: str, body: str) -> None:
    now = int(time.time())
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO discogs_cache (url, body, fetched_at)
            VALUES (?, ?, ?)
            ON CONFLICT(url) DO UPDATE SET
                body = excluded.body,
                fetched_at = excluded.fetched_at
            """,
            (url, body, now),
        )
