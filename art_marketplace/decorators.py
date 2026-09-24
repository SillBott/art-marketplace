from functools import wraps
from flask import abort
from flask_login import current_user


def role_required(*roles):
    """Restrict a view to users whose .role is in `roles`."""
    def decorator(fn):
        @wraps(fn)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated:
                abort(401)
            if current_user.role not in roles:
                abort(403)
            return fn(*args, **kwargs)
        return wrapped
    return decorator


def artist_required(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        if not current_user.is_authenticated or current_user.artist_profile is None:
            abort(403)
        return fn(*args, **kwargs)
    return wrapped
