from app.config import Settings, load_settings


def test_settings_load_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("BOT_TOKEN", "real-env-token-should-not-be-used")
    monkeypatch.setenv("ADMIN_TELEGRAM_IDS", "999")

    settings = load_settings(
        {
            "BOT_TOKEN": "test-token",
            "ADMIN_TELEGRAM_IDS": "123, 456",
            "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
            "TIMEZONE": "Asia/Tbilisi",
            "DEFAULT_PLACE": "Test studio",
            "DEFAULT_MAP_URL": "https://maps.example/test",
            "WEBHOOK_SECRET": "test-secret",
            "ENV": "test",
        }
    )

    assert settings == Settings(
        bot_token="test-token",
        admin_telegram_ids=(123, 456),
        database_url="sqlite+aiosqlite:///:memory:",
        timezone="Asia/Tbilisi",
        default_place="Test studio",
        default_map_url="https://maps.example/test",
        webhook_secret="test-secret",
        env="test",
    )
    assert settings.timezone_info.key == "Asia/Tbilisi"
