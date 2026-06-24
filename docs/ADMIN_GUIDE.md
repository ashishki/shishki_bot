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

- Today
- This week
- Manual booking
- Change booking
- Cancel booking
- Revenue
- Clients
- Бонусы

The code also provides tested service/admin wrapper behavior for:

- Creating manual complex bookings with custom service, duration, price, place,
  and notes.
- Rescheduling bookings and logging/sending client notifications.
- Cancelling bookings and logging/sending client notifications.
- Updating client-visible booking details with required notification logging.
- Completing bookings with final amount and recorded expenses.
- Viewing weekly gross/net revenue from completed bookings only.
- Viewing client cards and visit history from completed bookings only.
- Viewing referral progress on client cards.
- Viewing referral bonuses and marking a cosmetics/styling bonus as awarded.

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
