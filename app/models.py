"""Lightweight data classes used to pass things to templates."""
from dataclasses import dataclass
from typing import Optional


@dataclass
class DisplayItem:
    """A normalised row used by both search results and library/wishlist views."""
    master_id: int
    artist: str
    title: str
    year: Optional[int]
    cover_url: Optional[str]   # full-size
    thumb_url: Optional[str]   # small (used in list rows)
    status: Optional[str] = None  # 'library' | 'wishlist' | None
