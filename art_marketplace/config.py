import os

BASE_DIR = os.path.abspath(os.path.dirname(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # On Vercel the filesystem is read-only except /tmp, and /tmp is wiped
    # between invocations, so SQLite there is only good for quick demos.
    # For real use, set DATABASE_URL to a hosted Postgres (e.g. Neon,
    # Vercel Postgres, Supabase) in your Vercel project's environment vars.
    _default_sqlite = f"sqlite:///{os.path.join(BASE_DIR, 'app.db')}"
    if os.environ.get("VERCEL"):
        _default_sqlite = "sqlite:////tmp/app.db"

    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", _default_sqlite)
    # Some hosts give postgres:// but SQLAlchemy 2.x wants postgresql://
    if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgres://", "postgresql://", 1
        )
    # Force the psycopg v3 driver explicitly — psycopg2's prebuilt wheel
    # isn't ABI-compatible with newer Python builds, so leaving driver
    # selection to SQLAlchemy's default is unreliable.
    if SQLALCHEMY_DATABASE_URI.startswith("postgresql://"):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace(
            "postgresql://", "postgresql+psycopg://", 1
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Uploaded files. On Vercel this must point at /tmp (ephemeral!) — see
    # README for wiring up persistent storage (e.g. S3/Cloudinary) instead.
    if os.environ.get("VERCEL"):
        UPLOAD_FOLDER = "/tmp/uploads"
    else:
        UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

    ARTWORK_UPLOAD_SUBDIR = "artworks"
    SLIP_UPLOAD_SUBDIR = "slips"
    SETTINGS_UPLOAD_SUBDIR = "settings"
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB per request
    ALLOWED_IMAGE_EXT = {"png", "jpg", "jpeg", "webp"}

    ITEMS_PER_PAGE = 12

    # Portion of a sale that goes to the artist (rest is platform commission)
    DEFAULT_ARTIST_SHARE = 0.80
