"""Environment-backed application settings."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from os import environ
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


class ConfigError(ValueError):
    """Raised when required configuration is missing or invalid."""


@dataclass(frozen=True, slots=True)
class Settings:
    bot_token: str
    admin_telegram_ids: tuple[int, ...]
    database_url: str
    timezone: str
    default_place: str
    stylist_contact_url: str
    default_map_url: str | None = None
    webhook_secret: str | None = None
    env: str = "local"

    @property
    def timezone_info(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


def load_settings(source: Mapping[str, str] | None = None) -> Settings:
    values = environ if source is None else source

    bot_token = _required(values, "BOT_TOKEN")
    admin_telegram_ids = _parse_admin_ids(_required(values, "ADMIN_TELEGRAM_IDS"))
    database_url = _required(values, "DATABASE_URL")
    timezone = _required(values, "TIMEZONE")
    _validate_timezone(timezone)
    default_place = _required(values, "DEFAULT_PLACE")
    stylist_contact_url = _required(values, "STYLIST_CONTACT_URL")

    return Settings(
        bot_token=bot_token,
        admin_telegram_ids=admin_telegram_ids,
        database_url=database_url,
        timezone=timezone,
        default_place=default_place,
        stylist_contact_url=stylist_contact_url,
        default_map_url=_optional(values, "DEFAULT_MAP_URL"),
        webhook_secret=_optional(values, "WEBHOOK_SECRET"),
        env=_optional(values, "ENV") or "local",
    )


def _required(values: Mapping[str, str], key: str) -> str:
    value = values.get(key, "").strip()
    if not value:
        raise ConfigError(f"Missing required setting: {key}")
    return value


def _optional(values: Mapping[str, str], key: str) -> str | None:
    value = values.get(key)
    if value is None:
        return None
    value = value.strip()
    return value or None


def _parse_admin_ids(raw_value: str) -> tuple[int, ...]:
    admin_ids: list[int] = []
    for chunk in raw_value.split(","):
        value = chunk.strip()
        if not value:
            continue
        try:
            admin_ids.append(int(value))
        except ValueError as exc:
            raise ConfigError("ADMIN_TELEGRAM_IDS must contain integers") from exc

    if not admin_ids:
        raise ConfigError("ADMIN_TELEGRAM_IDS must contain at least one admin ID")

    return tuple(admin_ids)


def _validate_timezone(timezone: str) -> None:
    try:
        ZoneInfo(timezone)
    except ZoneInfoNotFoundError as exc:
        raise ConfigError(f"Unknown timezone: {timezone}") from exc
