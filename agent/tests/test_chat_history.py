"""Tests for the ChatHistoryStore."""

import pytest

from src.memory.chat_history import ChatHistoryStore, _chat_key


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


class TestChatKey:
    def test_key_is_hashed(self):
        key = _chat_key("secret-token")
        assert "secret-token" not in key
        assert key.startswith("agentforge:chat:")

    def test_key_is_deterministic(self):
        assert _chat_key("token-a") == _chat_key("token-a")
        assert _chat_key("token-a") != _chat_key("token-b")

    def test_key_differs_from_prefs_key(self):
        from src.memory.store import _user_key

        chat = _chat_key("same-token")
        prefs = _user_key("same-token")
        assert chat != prefs
        assert "chat" in chat
        assert "prefs" in prefs
