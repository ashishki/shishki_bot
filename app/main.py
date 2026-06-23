"""Telegram bot entrypoint.

Importing this module must not create network clients, connect to Telegram, or
open a database connection.
"""

from __future__ import annotations

import asyncio

from app.bot.handlers.admin import build_admin_router
from app.bot.handlers.client import build_client_router
from app.config import Settings, load_settings
from app.db.session import create_database_engine, create_session_factory
from app.scheduler import start_reminder_scheduler


async def run(settings: Settings | None = None) -> None:
    """Start the bot runtime.

    The Telegram framework import is intentionally deferred so tests and other
    modules can import app.main without network-capable objects being created.
    """

    active_settings = settings or load_settings()

    try:
        from aiogram import Bot, Dispatcher
        from aiogram.client.default import DefaultBotProperties
    except ImportError as exc:  # pragma: no cover - exercised only without deps
        raise RuntimeError(
            "aiogram is required to start the bot; install requirements.txt"
        ) from exc

    engine = create_database_engine(active_settings.database_url)
    session_factory = create_session_factory(engine)

    bot = Bot(
        token=active_settings.bot_token,
        default=DefaultBotProperties(parse_mode="HTML"),
    )
    dispatcher = Dispatcher()
    dispatcher.include_router(
        build_admin_router(
            active_settings,
            async_session_factory=session_factory,
        )
    )
    dispatcher.include_router(
        build_client_router(
            active_settings,
            async_session_factory=session_factory,
        )
    )
    reminder_scheduler = start_reminder_scheduler(
        active_settings,
        bot=bot,
        loop=asyncio.get_running_loop(),
    )
    try:
        await dispatcher.start_polling(bot)
    finally:
        reminder_scheduler.shutdown(wait=False)
        await engine.dispose()


def main() -> None:
    asyncio.run(run())


if __name__ == "__main__":
    main()
