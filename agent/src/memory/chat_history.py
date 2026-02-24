"""Redis-backed persistent chat history store.

Stores chat messages (role + content) per user as a Redis list,
keyed by a hash of their auth token. Falls back to an in-memory
dict when Redis is unavailable (same pattern as MemoryStore).

Each key has a 7-day TTL so old conversations are automatically cleaned up.
"""

from __future__ import annotations

import hashlib
import json
import logging
logger = logging.getLogger("agentforge.memory.chat_history")

# 7 days in seconds
CHAT_TTL_SECONDS = 7 * 24 * 60 * 60


def _chat_key(auth_token: str) -> str:
    """Hash the auth token to create a stable, non-reversible chat history key."""
    return f"agentforge:chat:{hashlib.sha256(auth_token.encode()).hexdigest()[:16]}"


class ChatHistoryStore:
    """Persistent chat history store backed by Redis.

    Each user (identified by auth token hash) has a Redis list of
    JSON-encoded messages with role and content fields.
    """

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._fallback: dict[str, list[dict[str, str]]] = {}

    @property
    def is_persistent(self) -> bool:
        return self._redis is not None

    async def append_message(self, auth_token: str, role: str, content: str) -> None:
        """Append a message to the user's chat history."""
        key = _chat_key(auth_token)
        message = json.dumps({"role": role, "content": content})

        if self._redis:
            try:
                await self._redis.rpush(key, message)
                await self._redis.expire(key, CHAT_TTL_SECONDS)
                return
            except Exception as e:
                logger.warning("Redis append failed, using fallback: %s", e)

        self._fallback.setdefault(key, []).append({"role": role, "content": content})

    async def get_history(self, auth_token: str) -> list[dict[str, str]]:
        """Get the full chat history for a user."""
        key = _chat_key(auth_token)

        if self._redis:
            try:
                raw_messages = await self._redis.lrange(key, 0, -1)
                # Refresh TTL on read
                if raw_messages:
                    await self._redis.expire(key, CHAT_TTL_SECONDS)
                return [
                    json.loads(m if isinstance(m, str) else m.decode())
                    for m in raw_messages
                ]
            except Exception as e:
                logger.warning("Redis get_history failed, using fallback: %s", e)

        return list(self._fallback.get(key, []))

    async def clear_history(self, auth_token: str) -> None:
        """Clear the entire chat history for a user."""
        key = _chat_key(auth_token)

        if self._redis:
            try:
                await self._redis.delete(key)
                return
            except Exception as e:
                logger.warning("Redis clear_history failed, using fallback: %s", e)

        self._fallback.pop(key, None)
