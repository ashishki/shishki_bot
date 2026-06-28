# Admin Guide

Version: 1.0
Last updated: 2026-06-23

This guide is for the stylist/admin operating `shishki_bot`.

## Access

- Admin actions are available only to Telegram IDs listed in
  `ADMIN_TELEGRAM_IDS`.
- Keep `ADMIN_TELEGRAM_IDS` narrow. Do not add temporary or unknown users.
- Client users must not receive admin callback payloads or admin commands.

## Admin Menu

The admin menu exposes:

- Записи
- Клиенты
- Метрики
- Создать запись
- Закрыть время
- Сегодня
- Бонусы

The code also provides tested service/admin wrapper behavior for:

- Opening `/admin` as a dashboard with today/upcoming bookings, free slots,
  client counts, weekly revenue, and pending bonuses.
- Creating manual complex bookings with custom service, duration, price, place,
  and notes.
- Rescheduling bookings and logging/sending client notifications.
- Cancelling bookings and logging/sending client notifications.
- Updating client-visible booking details with required notification logging.
- Completing bookings with final amount and recorded expenses.
- Viewing weekly gross/net revenue from completed bookings only.
- Viewing client cards, visit history, and per-client metrics from completed
  bookings only.
- Viewing referral progress on client cards.
- Viewing referral bonuses and marking a cosmetics/styling bonus as awarded.
- Closing one free slot or the rest of a day from Telegram admin commands.

## Manual Booking

Use this when a client writes directly about coloring, consultation, or another
non-standard service and you want to reserve time so it disappears from client
self-booking.

1. Ask the client to press `/start` in the bot at least once, or ask them to
   press `Окрашивание` / `Консультация`. This creates their client card.
2. Open `/admin` -> `Клиенты` and copy either `ID клиента` or the Telegram
   username from the card.
3. Send an admin command:

```text
/book <client_id|@username> <YYYY-MM-DD> <HH:MM> <minutes> <price> <service>
```

Example:

```text
/book @client 2026-06-28 15:00 180 250 Окрашивание
```

The command creates a confirmed booking, sends/logs a confirmation to the
client when the client has Telegram identity, and blocks all overlapping
client-visible slots for the duration of that booking.

The username form works only for clients who already have a bot client card.
Use numeric client ID when a Telegram username is missing or has changed.

## Closing Slots

Use this when you want to hide one free hour or close the rest of the day.
The commands do not close slots that already have an active booking.

```text
/close <YYYY-MM-DD> <HH:MM>
/close_day <YYYY-MM-DD> <HH:MM>
```

Examples:

```text
/close 2026-07-04 16:00
/close_day 2026-07-04 16:00
```

Open `/admin` -> `Ближайшие даты` -> a date to see the command hint with the
selected date.

## Referral Bonuses

Clients can request a personal referral link from the bot. When a new client
enters through that link, the source is recorded. The referral is counted only
after the referred client's booking is completed.

Every 3 qualified referrals creates a pending bonus for professional hair
cosmetics: care or styling. The scheduler sends the admin a one-time Telegram
reminder for a newly pending bonus. Open `/admin` -> `Бонусы` to see pending
bonuses, contact/open the client card if needed, and press `Выдано` after the
product is given.

## Safe Operation Rules

- Do not test with real clients or real production Telegram chats.
- Local and CI tests use fake senders and synthetic data only.
- Never put real bot tokens, admin IDs, client data, database dumps, or
  production `.env` files in git.
- Client-visible booking changes must be sent or logged as failed
  notifications.
- Revenue and client spending must use completed bookings and recorded final
  amounts only.
- Referral rewards must be marked awarded only after the cosmetics/styling
  product is actually given.

## Backup

Before real client use, configure the production database provider backup
feature or a daily `pg_dump` job.

`pg_dump` and `psql` require a libpq-compatible PostgreSQL URL such as
`postgresql://user:pass@host/db`. Do not pass the application async SQLAlchemy
URL shape `postgresql+asyncpg://...` directly to those tools.

Minimum PostgreSQL backup command shape:

```bash
export DATABASE_BACKUP_URL="postgresql://user:pass@host/db"
pg_dump "$DATABASE_BACKUP_URL" > "backups/shishki_bot_$(date +%Y%m%d_%H%M%S).sql"
```

Store backups outside the application container and restrict access to the same
people allowed to manage production secrets.

## Rollback

Rollback means restoring the last known-good application version and, only when
needed, restoring the database from a verified backup.

1. Stop the bot process.
2. Deploy the previous known-good commit or image.
3. Run the verification command from `README.md`.
4. Start the bot.
5. Check that `/admin` works only for allowlisted admin IDs.

Database rollback must be a deliberate operator action. Do not overwrite
production data without first saving a fresh backup and confirming the exact
restore point.

## Incident Notes

If reminders, notifications, bookings, or revenue look wrong:

- Stop the bot if it could continue making incorrect changes.
- Save current logs and a database backup.
- Record the commit SHA, environment, and exact admin action that triggered the
  issue.
- Fix through a normal reviewed commit; do not patch production manually unless
  a human explicitly approves the change and rollback note.
