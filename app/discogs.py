"""Discogs API client. Async, with optional SQLite-backed caching."""
import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx

from .config import settings
from . import db

log = logging.getLogger(__name__)

BASE_URL = "https://api.discogs.com"


def _headers() -> dict:
    return {
        "Authorization": f"Discogs token={settings.DISCOGS_TOKEN}",
        "User-Agent": settings.DISCOGS_USER_AGENT,
    }


# Maps user-friendly search field names to Discogs query params.
# 'general' uses the catch-all 'q' param; the others narrow the field.
SEARCH_FIELDS = {
    "general": "q",
    "artist": "artist",
    "album": "release_title",
    "label": "label",
    "year": "year",
    "genre": "genre",
}


async def _get(client: httpx.AsyncClient, url: str, *, use_cache: bool = True) -> dict:
    """GET a Discogs URL, with caching and basic error handling."""
    if use_cache:
        cached = db.cache_get(url, settings.DISCOGS_CACHE_TTL)
        if cached is not None:
            log.debug("cache hit: %s", url)
            return json.loads(cached)

    log.debug("fetching: %s", url)
    r = await client.get(url, headers=_headers(), timeout=10.0)
    r.raise_for_status()
    body = r.text
    if use_cache:
        db.cache_set(url, body)
    return json.loads(body)


async def search(query: str, field: str = "general", per_page: int = 30) -> list[dict]:
    """Search master releases. Returns the list of result dicts."""
    if not query.strip():
        return []

    field_key = SEARCH_FIELDS.get(field, "q")
    params: dict = {
        "type": "master",
        "per_page": per_page,
    }
    params[field_key] = query.strip()

    url = f"{BASE_URL}/database/search?{urlencode(params)}"

    async with httpx.AsyncClient() as client:
        data = await _get(client, url)
    return data.get("results", [])


async def get_master_with_tracklist(master_id: int) -> dict:
    """Fetch a master and its main release tracklist.

    Returns a flattened dict with the fields we care about, normalising
    Discogs' inconsistencies (e.g. cover URL field naming).
    """
    master_url = f"{BASE_URL}/masters/{master_id}"
    async with httpx.AsyncClient() as client:
        master = await _get(client, master_url)

        artists = ", ".join(a.get("name", "") for a in master.get("artists", []))
        images = master.get("images") or []
        cover_url = images[0]["uri"] if images else None
        thumb_url = images[0].get("uri150") if images else None

        tracklist: list[dict] = []
        main_release_id = master.get("main_release")
        if main_release_id:
            release_url = f"{BASE_URL}/releases/{main_release_id}"
            try:
                release = await _get(client, release_url)
                for t in release.get("tracklist", []):
                    tracklist.append({
                        "position": t.get("position", ""),
                        "title": t.get("title", ""),
                        "duration": t.get("duration", ""),
                    })
            except httpx.HTTPError as e:
                log.warning("failed to fetch tracklist for master %s: %s", master_id, e)

    return {
        "master_id": master_id,
        "artist": artists,
        "title": master.get("title", ""),
        "year": master.get("year"),
        "cover_url": cover_url,
        "thumb_url": thumb_url,
        "tracklist": tracklist,
        "genres": master.get("genres", []),
        "styles": master.get("styles", []),
        "notes": master.get("notes", ""),
    }


def split_search_title(title: str) -> tuple[str, str]:
    """Discogs search results give 'Artist - Album' as a single string.
    Split on the first ' - '. Imperfect but good enough for display.
    """
    if " - " in title:
        artist, album = title.split(" - ", 1)
        return artist.strip(), album.strip()
    return "", title.strip()
