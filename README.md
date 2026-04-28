# Vinyl

A small shared web app for tracking vinyl records you own and ones you want.
Backed by the Discogs database for search and metadata.

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

# 4. Copy the env template and fill in your Discogs token
Copy-Item .env.example .env
notepad .env   # paste your token, save, close
```

## Running

```powershell
.\run.ps1
```

Then open http://localhost:8000 in your browser.

The first time you run it, `data/vinyl.db` is created automatically.

## Project layout

```
app/
  main.py        FastAPI routes
  config.py      env loading
  db.py          SQLite setup + helpers
  discogs.py     Discogs API client
  models.py      simple data classes
  templates/     Jinja2 HTML templates
static/          CSS, images
data/            SQLite database (gitignored)
```

## Notes

- One shared library + wishlist, no user accounts. Designed for two people.
- All edits are last-write-wins.
- Library and wishlist data is stored locally in `data/vinyl.db`.
  To back up: just copy that file somewhere safe.
