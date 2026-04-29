# Vinyl

A small shared web app for tracking vinyl records you own and ones you want.
Backed by the Discogs database for search and metadata.

Designed for a household of two: one shared library, one shared wishlist,
single shared password. No user accounts.

## First-time setup (Windows / PowerShell)

From the project folder:

```powershell
# 1. Create a virtual environment
python -m venv .venv

# 2. Activate it
.\.venv\Scripts\Activate.ps1

# (If PowerShell complains about execution policy, run this once:
#  Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned)

# 3. Install dependencies
pip install -r requirements.txt

# 4. Copy the env template
Copy-Item .env.example .env

# 5. Generate a session secret and copy it to your clipboard
python -c "import secrets; print(secrets.token_urlsafe(32))"

# 6. Open .env and fill in:
#    - DISCOGS_TOKEN     (get one at https://www.discogs.com/settings/developers)
#    - APP_PASSWORD      (the shared password to access the app)
#    - SESSION_SECRET    (paste the output from step 5)
notepad .env
```

## Running

```powershell
.\run.ps1
```

Then open http://localhost:8000 in your browser. You'll be redirected to a
login page; enter the `APP_PASSWORD` you chose. The session cookie lasts a
year, so you log in once per device.

The first time you run it, `data/vinyl.db` is created automatically.

## Project layout

```
app/
  main.py        FastAPI routes
  auth.py        Shared-password auth middleware
  config.py      env loading
  db.py          SQLite setup + helpers
  discogs.py     Discogs API client
  models.py      simple data classes
  templates/     Jinja2 HTML templates
static/          CSS, images
data/            SQLite database (gitignored)
```

## Environment variables

| Variable             | Required | Notes                                                              |
| -------------------- | -------- | ------------------------------------------------------------------ |
| `DISCOGS_TOKEN`      | yes      | Personal access token from Discogs.                                |
| `DISCOGS_USER_AGENT` | no       | Identifies the app to Discogs. Default `VinylCollector/0.1`.       |
| `DISCOGS_CACHE_TTL`  | no       | Seconds to cache Discogs responses. Default `86400` (24 h).        |
| `APP_PASSWORD`       | yes      | Shared password to log in.                                         |
| `SESSION_SECRET`     | yes      | Used to sign session cookies. Min 32 chars, generate with `secrets.token_urlsafe(32)`. |
| `COOKIE_SECURE`      | no       | Set `true` in production (HTTPS only). Leave `false` for local dev. |

## Notes

- One shared library + wishlist, no user accounts. Designed for two people.
- All edits are last-write-wins.
- Library and wishlist data is stored locally in `data/vinyl.db`.
  To back up: just copy that file somewhere safe.
- Changing `SESSION_SECRET` invalidates all active sessions — a handy way to
  force-logout every device if you need to.
