"""FastAPI app: routes for the three pages and their htmx endpoints."""
import json
import logging
from pathlib import Path
from typing import Optional

import httpx
from fastapi import FastAPI, Form, Query, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from . import db, discogs
from .config import settings
from .models import DisplayItem


logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)


# ---------- app setup ----------

settings.validate()
db.init_db()

app = FastAPI(title="Vinyl")

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount(
    "/static",
    StaticFiles(directory=str(BASE_DIR.parent / "static")),
    name="static",
)


# ---------- helpers ----------

def _row_to_display_item(row) -> DisplayItem:
    return DisplayItem(
        master_id=row["discogs_master_id"],
        artist=row["artist"],
        title=row["title"],
        year=row["year"],
        cover_url=row["cover_url"],
        thumb_url=row["thumb_url"],
        status=row["status"],
    )


def _search_result_to_display_item(r: dict, status: Optional[str]) -> DisplayItem:
    artist, title = discogs.split_search_title(r.get("title", ""))
    year_raw = r.get("year")
    try:
        year = int(year_raw) if year_raw else None
    except (TypeError, ValueError):
        year = None
    return DisplayItem(
        master_id=r.get("id") or r.get("master_id") or 0,
        artist=artist,
        title=title,
        year=year,
        cover_url=r.get("cover_image"),
        thumb_url=r.get("thumb") or r.get("cover_image"),
        status=status,
    )


# ---------- pages ----------

@app.get("/", response_class=HTMLResponse)
async def home():
    return RedirectResponse("/search")


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request):
    return templates.TemplateResponse(
        request,
        "search.html",
        {"active": "search", "fields": discogs.SEARCH_FIELDS},
    )


@app.get("/library", response_class=HTMLResponse)
async def library_page(request: Request, view: str = Query("list")):
    rows = db.list_items("library")
    items = [_row_to_display_item(r) for r in rows]
    return templates.TemplateResponse(
        request,
        "library.html",
        {
            "active": "library",
            "items": items,
            "view": view if view in ("list", "grid") else "list",
            "page_kind": "library",
        },
    )


@app.get("/wishlist", response_class=HTMLResponse)
async def wishlist_page(request: Request, view: str = Query("list")):
    rows = db.list_items("wishlist")
    items = [_row_to_display_item(r) for r in rows]
    return templates.TemplateResponse(
        request,
        "wishlist.html",
        {
            "active": "wishlist",
            "items": items,
            "view": view if view in ("list", "grid") else "list",
            "page_kind": "wishlist",
        },
    )


# ---------- htmx endpoints ----------

@app.post("/search/results", response_class=HTMLResponse)
async def search_results(
    request: Request,
    q: str = Form(...),
    field: str = Form("general"),
):
    try:
        results = await discogs.search(q, field=field)
    except httpx.HTTPStatusError as e:
        return HTMLResponse(
            f"<p class='text-red-600 p-4'>Discogs error {e.response.status_code}. "
            f"Try again in a minute.</p>"
        )
    except httpx.HTTPError as e:
        return HTMLResponse(
            f"<p class='text-red-600 p-4'>Network error: {e}</p>"
        )

    master_ids = [r.get("id") for r in results if r.get("id")]
    statuses = db.get_statuses_for_master_ids(master_ids)

    items = [
        _search_result_to_display_item(r, statuses.get(r.get("id")))
        for r in results
    ]

    return templates.TemplateResponse(
        request,
        "_result_list.html",
        {
            "items": items,
            "page_kind": "search",
            "empty_msg": "No results. Try a different search.",
        },
    )


@app.get("/detail/{master_id}", response_class=HTMLResponse)
async def detail(request: Request, master_id: int):
    """Return the detail panel for a given master.

    For items already in DB we could skip the network call, but Discogs gives
    us richer detail (e.g. notes) than what we store, so fetch fresh.
    Cache makes subsequent calls cheap anyway.
    """
    existing = db.get_item_by_master_id(master_id)
    existing_status = existing["status"] if existing else None

    try:
        detail = await discogs.get_master_with_tracklist(master_id)
    except httpx.HTTPError as e:
        return HTMLResponse(
            f"<div class='p-4 text-red-600'>Couldn't load details: {e}</div>"
        )

    return templates.TemplateResponse(
        request,
        "_detail_modal.html",
        {
            "d": detail,
            "existing_status": existing_status,
        },
    )


@app.post("/items/{master_id}/add", response_class=HTMLResponse)
async def add_item(request: Request, master_id: int, status: str = Form(...)):
    """Add an item to library or wishlist by master_id.

    Fetches metadata from Discogs (cached) so the DB is self-sufficient.
    """
    if status not in ("library", "wishlist"):
        return HTMLResponse("Invalid status", status_code=400)

    try:
        detail = await discogs.get_master_with_tracklist(master_id)
    except httpx.HTTPError as e:
        return HTMLResponse(f"<div class='text-red-600'>Discogs error: {e}</div>")

    db.upsert_item(
        master_id=master_id,
        status=status,
        artist=detail["artist"],
        title=detail["title"],
        year=detail["year"],
        cover_url=detail["cover_url"],
        thumb_url=detail["thumb_url"],
        tracklist_json=json.dumps(detail["tracklist"]),
        genres_json=json.dumps(detail["genres"]),
        styles_json=json.dumps(detail["styles"]),
    )

    # Return a small confirmation that swaps into the modal
    return templates.TemplateResponse(
        request,
        "_added_confirm.html",
        {
            "status": status,
        },
    )


@app.post("/items/{master_id}/move", response_class=HTMLResponse)
async def move_item(master_id: int, status: str = Form(...)):
    if status not in ("library", "wishlist"):
        return HTMLResponse("Invalid status", status_code=400)
    db.update_status(master_id, status)
    # htmx will redirect via HX-Redirect header to refresh the page
    return HTMLResponse(
        "",
        headers={"HX-Redirect": f"/{status}"},
    )


@app.post("/items/{master_id}/delete", response_class=HTMLResponse)
async def delete_item_route(master_id: int, redirect_to: str = Form("library")):
    db.delete_item(master_id)
    target = redirect_to if redirect_to in ("library", "wishlist", "search") else "library"
    return HTMLResponse(
        "",
        headers={"HX-Redirect": f"/{target}"},
    )
