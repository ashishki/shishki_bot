"""Telegram bot entrypoint.

Importing this module must not create network clients, connect to Telegram, or
open a database connection.
"""

from __future__ import annotations

import asyncio

from app.bot.handlers.admin import build_admin_router
from app.config import Settings, load_settings


async def run(settings: Settings | None = None) -> None:
    """Start the bot runtime.

    The Telegram framework import is intentionally deferred so tests and other
    modules can import app.main without network-capable objects being created.
    """

    active_settings = settings or load_settings()

    try:
        from aiogram import Bot, Dispatcher
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "aiogram is required to start the bot; install requirements.txt"
        ) from exc

    bot = Bot(token=active_settings.bot_token)
    dispatcher = Dispatcher()
    dispatcher.include_router(build_admin_router(active_settings))
    await dispatcher.start_polling(bot)


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
