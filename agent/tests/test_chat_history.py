"""Tests for the ChatHistoryStore."""

import base64
import json

import pytest

from src.memory.chat_history import ChatHistoryStore, _chat_key, _extract_user_id


def _make_jwt(payload: dict) -> str:
    """Build a fake JWT (header.payload.signature) with the given payload."""
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()
    return f"{header}.{body}.fake-signature"


AUTH_TOKEN = "test-token-123"
OTHER_TOKEN = "other-user-456"


@pytest.fixture
def store():
    return ChatHistoryStore()


class TestChatHistoryStore:
    async def test_empty_history(self, store):
        result = await store.get_history(AUTH_TOKEN)
        assert result == []

    async def test_append_and_get(self, store):
        await store.append_message(AUTH_TOKEN, "user", "Hello")
        await store.append_message(AUTH_TOKEN, "agent", "Hi there!")
        history = await store.get_history(AUTH_TOKEN)
        assert len(history) == 2
        assert history[0] == {"role": "user", "content": "Hello"}
        assert history[1] == {"role": "agent", "content": "Hi there!"}

    async def test_append_preserves_order(self, store):
        messages = [
            ("user", "First"),
            ("agent", "Response 1"),
            ("user", "Second"),
            ("agent", "Response 2"),
        ]
        for role, content in messages:
            await store.append_message(AUTH_TOKEN, role, content)

        history = await store.get_history(AUTH_TOKEN)
        assert len(history) == 4
        for i, (role, content) in enumerate(messages):
            assert history[i]["role"] == role
            assert history[i]["content"] == content

    async def test_clear_history(self, store):
        await store.append_message(AUTH_TOKEN, "user", "Hello")
        await store.append_message(AUTH_TOKEN, "agent", "Hi!")
        await store.clear_history(AUTH_TOKEN)
        history = await store.get_history(AUTH_TOKEN)
        assert history == []

    async def test_clear_empty_history(self, store):
        # Should not raise
        await store.clear_history(AUTH_TOKEN)

    async def test_user_isolation(self, store):
        await store.append_message(AUTH_TOKEN, "user", "User A message")
        await store.append_message(OTHER_TOKEN, "user", "User B message")

        history_a = await store.get_history(AUTH_TOKEN)
        history_b = await store.get_history(OTHER_TOKEN)

        assert len(history_a) == 1
        assert history_a[0]["content"] == "User A message"
        assert len(history_b) == 1
        assert history_b[0]["content"] == "User B message"

    async def test_clear_only_affects_target_user(self, store):
        await store.append_message(AUTH_TOKEN, "user", "User A message")
        await store.append_message(OTHER_TOKEN, "user", "User B message")

        await store.clear_history(AUTH_TOKEN)

        assert await store.get_history(AUTH_TOKEN) == []
        assert len(await store.get_history(OTHER_TOKEN)) == 1

    def test_is_persistent_without_redis(self, store):
        assert not store.is_persistent

    async def test_special_characters_in_content(self, store):
        content = 'He said "hello" & used <html> tags\nwith newlines'
        await store.append_message(AUTH_TOKEN, "user", content)
        history = await store.get_history(AUTH_TOKEN)
        assert history[0]["content"] == content


class TestExtractUserId:
    def test_extracts_id_from_jwt(self):
        jwt = _make_jwt({"id": "user-abc-123"})
        assert _extract_user_id(jwt) == "user-abc-123"

    def test_different_jwts_same_user_id(self):
        """Two JWTs with the same user ID should return the same value."""
        jwt1 = _make_jwt({"id": "user-abc-123", "iat": 1000})
        jwt2 = _make_jwt({"id": "user-abc-123", "iat": 2000})
        assert _extract_user_id(jwt1) == _extract_user_id(jwt2)

    def test_fallback_for_non_jwt(self):
        """Non-JWT strings should fall back to the raw value."""
        assert _extract_user_id("plain-session-id") == "plain-session-id"

    def test_fallback_for_missing_id_field(self):
        jwt = _make_jwt({"sub": "no-id-field"})
        # Missing 'id' key → fallback to raw token
        assert _extract_user_id(jwt) == jwt


class TestChatKey:
    def test_key_is_hashed(self):
        key = _chat_key("secret-token")
        assert "secret-token" not in key
        assert key.startswith("agentforge:chat:")

    def test_key_is_deterministic(self):
        assert _chat_key("token-a") == _chat_key("token-a")
        assert _chat_key("token-a") != _chat_key("token-b")

    def test_key_stable_across_jwt_reissues(self):
        """Different JWTs for the same user should produce the same chat key."""
        jwt1 = _make_jwt({"id": "user-xyz", "iat": 1000})
        jwt2 = _make_jwt({"id": "user-xyz", "iat": 9999})
        assert _chat_key(jwt1) == _chat_key(jwt2)

    def test_key_differs_between_users(self):
        jwt_a = _make_jwt({"id": "user-a"})
        jwt_b = _make_jwt({"id": "user-b"})
        assert _chat_key(jwt_a) != _chat_key(jwt_b)

    def test_key_differs_from_prefs_key(self):
        from src.memory.store import _user_key

        chat = _chat_key("same-token")
        prefs = _user_key("same-token")
        assert chat != prefs
        assert "chat" in chat
        assert "prefs" in prefs
