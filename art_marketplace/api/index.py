import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app import app, db  # noqa: E402

# Vercel's filesystem is ephemeral outside /tmp; make sure tables exist
# on cold start when using the default sqlite fallback. When DATABASE_URL
# points at a real Postgres, run `flask --app app init-db` once instead.
with app.app_context():
    try:
        db.create_all()
    except Exception:
        pass

# Vercel's Python runtime looks for a WSGI callable named `app`
