# Deterministic Case Study

Purpose: make `shishki_bot` the counterexample to premature AI adoption.
The correct v1 solution is a deterministic Telegram workflow with database
transactions, reminders, operator controls, and tests.

## Why Not AI

| Workflow | Correct Owner | Why |
| --- | --- | --- |
| Slot availability | Deterministic code | A slot is either free, booked, blocked, or in the past. |
| Booking creation | Database transaction | Double-booking prevention needs locking, not generation. |
| Prices and duration | Config/admin rules | Haircut prices and one-hour duration are business rules. |
| Coloring and complex services | Stylist | Duration, price, and suitability require human consultation. |
| Reminders | Scheduler | Delivery time must be predictable and restart-safe. |
| Revenue and client history | Database queries | Totals must reconcile to stored completed bookings and expenses. |
| Client/admin messages | Templates | Users need consistent wording, not creative variation. |

## First Proof Metrics

- 30-50% of standard haircut bookings move through the bot after launch.
- Zero double bookings in normal operation.
- Confirmation messages always include service, date, time, place, and price.
- Reminder messages are sent without timezone shift.
- Weekly revenue matches completed bookings and recorded expenses.
- Admin can operate the schedule without editing the database manually.

## Operator Checks

Before relying on a deployment, the operator should verify:

- environment variables are present and do not contain placeholder secrets;
- database schema is initialized and backed up;
- admin allowlist contains only intended Telegram IDs;
- booking, reminder, finance, admin, and client-handler tests pass;
- a dry-run booking, reschedule, cancellation, and reminder path work locally;
- rollback is possible from the current database backup.

## Future AI Boundary

Future AI can be considered only as an optional draft or analytics aid after v1
is stable. It must not own:

- booking availability;
- pricing;
- service duration;
- cancellation/reschedule decisions;
- client-facing commitments;
- financial totals;
- admin authorization.

Any future AI experiment needs a separate project brief, eval plan, privacy
review, cost budget, and human approval boundary before implementation.
