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
            "YANDEX_PLACE": "https://yandex.example/test",
            "GOOGLE_PLACE": "https://google.example/test",
            "STYLIST_CONTACT_URL": "https://t.me/test_stylist",
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
        stylist_contact_url="https://t.me/test_stylist",
        default_map_url="https://maps.example/test",
        yandex_map_url="https://yandex.example/test",
        google_map_url="https://google.example/test",
        webhook_secret="test-secret",
        env="test",
    )
    assert settings.timezone_info.key == "Asia/Tbilisi"
