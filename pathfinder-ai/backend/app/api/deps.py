from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.cache import get_cache
from app.core.config import get_settings
from app.core.errors import RateLimited, Unauthorized
from app.core.security import COOKIE_NAME, decode_access_token
from app.db.models import User
from app.db.session import get_db
from app.knowledge.catalog import Catalog, get_catalog


def _token(request: Request) -> str | None:
    auth = request.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return request.cookies.get(COOKIE_NAME)


def current_user_optional(request: Request, db: Session = Depends(get_db)) -> User | None:
    token = _token(request)
    if not token:
        return None
    uid = decode_access_token(token)
    return db.get(User, uid) if uid else None


def current_user(user: User | None = Depends(current_user_optional)) -> User:
    if user is None:
        raise Unauthorized("Please sign in to continue.")
    return user


def catalog_dep() -> Catalog:
    return get_catalog()


def rate_limit(bucket: str, per_minute: int | None = None) -> Callable:
    def dep(request: Request, user: User | None = Depends(current_user_optional)) -> None:
        limit = per_minute or get_settings().rate_limit_ai_per_minute
        who = user.id if user else (request.client.host if request.client else "anon")
        if get_cache().hit(f"rl:{bucket}:{who}", 60) > limit:
            raise RateLimited("You're going a little fast. Please wait a minute and try again.")
    return dep
