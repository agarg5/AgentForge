"""Redis-backed persistent memory store for user preferences.

Stores key-value preferences per user, keyed by a hash of their auth token.
Falls back to an in-memory dict when Redis is unavailable (dev/testing).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Protocol

logger = logging.getLogger("agentforge.memory")


class RedisLike(Protocol):
    """Minimal protocol for Redis client compatibility."""

    async def hget(self, name: str, key: str) -> bytes | None: ...
    async def hset(self, name: str, key: str, value: str) -> int: ...
    async def hdel(self, name: str, *keys: str) -> int: ...
    async def hgetall(self, name: str) -> dict[bytes, bytes]: ...


def _user_key(auth_token: str) -> str:
    """Hash the auth token to create a stable, non-reversible user key."""
    return f"agentforge:prefs:{hashlib.sha256(auth_token.encode()).hexdigest()[:16]}"


class MemoryStore:
    """Persistent user preference store backed by Redis.

    Each user (identified by auth token hash) has a Redis hash map
    of key-value preferences. Keys and values are strings.
    """

    def __init__(self, redis_client: RedisLike | None = None):
        self._redis = redis_client
        self._fallback: dict[str, dict[str, str]] = {}

    @property
    def is_persistent(self) -> bool:
        return self._redis is not None

    async def get(self, auth_token: str, key: str) -> str | None:
        """Get a single preference value."""
        user_key = _user_key(auth_token)

        if self._redis:
            try:
                val = await self._redis.hget(user_key, key)
                return val.decode() if val else None
            except Exception as e:
                logger.warning("Redis get failed, using fallback: %s", e)

        return self._fallback.get(user_key, {}).get(key)

    async def set(self, auth_token: str, key: str, value: str) -> None:
        """Set a single preference value."""
        user_key = _user_key(auth_token)

        if self._redis:
            try:
                await self._redis.hset(user_key, key, value)
                return
            except Exception as e:
                logger.warning("Redis set failed, using fallback: %s", e)

        self._fallback.setdefault(user_key, {})[key] = value

    async def delete(self, auth_token: str, key: str) -> None:
        """Delete a single preference."""
        user_key = _user_key(auth_token)

        if self._redis:
            try:
                await self._redis.hdel(user_key, key)
                return
            except Exception as e:
                logger.warning("Redis delete failed, using fallback: %s", e)

        self._fallback.get(user_key, {}).pop(key, None)

    async def get_all(self, auth_token: str) -> dict[str, str]:
        """Get all preferences for a user."""
        user_key = _user_key(auth_token)

        if self._redis:
            try:
                raw = await self._redis.hgetall(user_key)
                return {k.decode(): v.decode() for k, v in raw.items()}
            except Exception as e:
                logger.warning("Redis getall failed, using fallback: %s", e)

        return dict(self._fallback.get(user_key, {}))
