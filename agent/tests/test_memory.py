"""Tests for persistent memory store and preference tools."""

import pytest

from src.memory.store import MemoryStore, _user_key
from src.tools.preferences import (
    delete_user_preference,
    get_user_preferences,
    save_user_preference,
)


AUTH_TOKEN = "test-token-123"
OTHER_TOKEN = "other-user-456"


@pytest.fixture
def store():
    return MemoryStore()


@pytest.fixture
def pref_config(store):
    return {
        "configurable": {
            "memory": store,
            "auth_token": AUTH_TOKEN,
        }
    }


# === MemoryStore ===


class TestMemoryStore:
    async def test_get_nonexistent_key(self, store):
        result = await store.get(AUTH_TOKEN, "nonexistent")
        assert result is None

    async def test_set_and_get(self, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        result = await store.get(AUTH_TOKEN, "currency")
        assert result == "USD"

    async def test_overwrite_value(self, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        await store.set(AUTH_TOKEN, "currency", "EUR")
        result = await store.get(AUTH_TOKEN, "currency")
        assert result == "EUR"

    async def test_delete_key(self, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        await store.delete(AUTH_TOKEN, "currency")
        result = await store.get(AUTH_TOKEN, "currency")
        assert result is None

    async def test_delete_nonexistent_key(self, store):
        # Should not raise
        await store.delete(AUTH_TOKEN, "nonexistent")

    async def test_get_all_empty(self, store):
        result = await store.get_all(AUTH_TOKEN)
        assert result == {}

    async def test_get_all_with_values(self, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        await store.set(AUTH_TOKEN, "risk", "high")
        result = await store.get_all(AUTH_TOKEN)
        assert result == {"currency": "USD", "risk": "high"}

    async def test_user_isolation(self, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        await store.set(OTHER_TOKEN, "currency", "EUR")
        assert await store.get(AUTH_TOKEN, "currency") == "USD"
        assert await store.get(OTHER_TOKEN, "currency") == "EUR"

    def test_is_persistent_without_redis(self, store):
        assert not store.is_persistent

    def test_user_key_is_hashed(self):
        key = _user_key("secret-token")
        assert "secret-token" not in key
        assert key.startswith("agentforge:prefs:")

    def test_user_key_is_deterministic(self):
        assert _user_key("token-a") == _user_key("token-a")
        assert _user_key("token-a") != _user_key("token-b")


# === Preference Tools ===


class TestGetUserPreferences:
    async def test_no_preferences(self, pref_config):
        result = await get_user_preferences.ainvoke({}, config=pref_config)
        assert "No preferences saved" in result

    async def test_get_specific_key(self, pref_config, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        result = await get_user_preferences.ainvoke(
            {"key": "currency"}, config=pref_config
        )
        assert "USD" in result

    async def test_get_missing_key(self, pref_config):
        result = await get_user_preferences.ainvoke(
            {"key": "nonexistent"}, config=pref_config
        )
        assert "No preference saved" in result

    async def test_get_all_preferences(self, pref_config, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        await store.set(AUTH_TOKEN, "risk", "moderate")
        result = await get_user_preferences.ainvoke({}, config=pref_config)
        assert "currency" in result
        assert "USD" in result
        assert "risk" in result
        assert "moderate" in result


class TestSaveUserPreference:
    async def test_save_preference(self, pref_config, store):
        result = await save_user_preference.ainvoke(
            {"key": "currency", "value": "EUR"}, config=pref_config
        )
        assert "saved" in result.lower()
        assert await store.get(AUTH_TOKEN, "currency") == "EUR"

    async def test_overwrite_preference(self, pref_config, store):
        await save_user_preference.ainvoke(
            {"key": "currency", "value": "USD"}, config=pref_config
        )
        await save_user_preference.ainvoke(
            {"key": "currency", "value": "EUR"}, config=pref_config
        )
        assert await store.get(AUTH_TOKEN, "currency") == "EUR"


class TestDeleteUserPreference:
    async def test_delete_preference(self, pref_config, store):
        await store.set(AUTH_TOKEN, "currency", "USD")
        result = await delete_user_preference.ainvoke(
            {"key": "currency"}, config=pref_config
        )
        assert "deleted" in result.lower()
        assert await store.get(AUTH_TOKEN, "currency") is None

    async def test_delete_nonexistent(self, pref_config):
        # Should not raise
        result = await delete_user_preference.ainvoke(
            {"key": "nonexistent"}, config=pref_config
        )
        assert "deleted" in result.lower()
