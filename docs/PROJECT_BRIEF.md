
# Project Brief: Shishki Booking Bot

Use this document before running `prompts/STRATEGIST.md`.

Implementation note: this repository will be implemented by Codex. Claude Code
is not currently part of the workflow. If a future Standard/Strict bootstrap
mentions copying `.claude` settings, commands, or hooks, Codex should instead
produce the equivalent starter artifacts manually for this repository.

The goal is not to pre-design the system, but to give the Strategist enough context to choose the right solution shape, governance level, runtime tier, and model strategy without guessing.

---

## 1. Project

* **Project name:** Shishki Booking Bot
* **One-sentence summary:** Telegram bot for appointment booking, client notifications, manual admin bookings, and lightweight revenue/client tracking for one stylist.
* **Why this project exists:** Clients need a beautiful and clear way to book or confirm an appointment without confusing back-and-forth messages, while the stylist needs a lightweight system to manage bookings, notify clients about changes, track appointment status, record manual complex services, and see basic weekly revenue/client statistics.
* **What success looks like in v1:** A client opens the Telegram bot, books a simple service or receives confirmation for a manually created booking, gets a clear message with service, date, time, place, price, and change/cancel instructions, and receives reminders or change notifications automatically. The stylist receives booking updates, can create/change/cancel bookings, and can see weekly revenue plus basic client history.

---

## 1b. Problem Fit and Adoption Reality

* **Concrete operational pain:** Appointment booking currently depends on manual messaging, checking availability, confirming time, repeating the price/place, tracking status, reminding clients manually, and later remembering how much the client paid and what service was done. Complex services like coloring also need manual entry because duration and final price are not obvious to the client.
* **Current workaround:** Clients write directly in Telegram/Instagram or another channel. The stylist manually answers, checks availability, agrees on time, explains the price/place, remembers to remind the client, updates the schedule manually, and tracks revenue/client history outside the booking flow or from memory.
* **Why existing process is insufficient:** Manual booking is fine for consultation, but it is inefficient for confirmations, reminders, reschedules, cancellations, client history, and weekly earnings. A normal chat also does not reliably show booking status, total revenue, client spending, service history, materials, rent, or assistant costs.
* **First user / buyer / operator who feels the pain:** The stylist / service provider.
* **What would make v1 not worth adopting:** If the bot creates more manual work than direct messages, looks confusing to clients, shows wrong availability, allows double bookings, fails to notify clients about changes, or makes it hard for the stylist to update bookings and revenue.
* **Adoption proof metric:** At least 30–50% of standard haircut bookings come through the bot after launch, all client confirmations include date/time/place/price, no double bookings occur, fewer manual reminder messages are needed, and the stylist can view weekly revenue without separate manual calculation.
* **Claims that are out of bounds before evidence:** “Fully automates the salon”, “replaces communication with clients”, “handles all beauty services”, “AI booking assistant”, “autonomous sales agent”.
* **Work AI will not replace:** Human consultation for coloring, complex services, changing appearance, estimating time/cost for non-standard work, conflict handling, final responsibility for the schedule, and final financial/expense entries.

---

## 2. Users and Workflows

* **Primary users / operators:**

  * Clients who want to book, confirm, remember, cancel, or reschedule an appointment.
  * Stylist / business owner who manages availability, receives booking updates, creates manual bookings, edits bookings, and tracks revenue/client history.
  * Optional admin/operator if the stylist wants someone else to manage slots later.

* **Main workflow 1: Beautiful client self-booking for simple services**

  1. Client opens Telegram bot.
  2. Bot sends a short, polished greeting with clear buttons.
  3. Bot explains service options, duration, price, address/place, and what can be booked automatically.
  4. Bot shows available dates and time slots for simple services.
  5. Client selects a slot.
  6. Bot asks for final confirmation.
  7. Bot creates booking and locks the slot.
  8. Client receives a confirmation message with service, date, time, place/address, price, duration, and cancellation/change instructions.
  9. Stylist receives an admin notification about the new booking.

* **Main workflow 2: Reminder and change-notification flow**

  1. Booking is created manually or by the client.
  2. Bot schedules reminder 24 hours before appointment.
  3. Bot schedules second reminder a few hours before appointment.
  4. Client receives reminders automatically.
  5. If the stylist changes, cancels, or reschedules the booking, the client receives an automatic update with the new date/time/place/price/status.
  6. Optional: reminder contains “confirm / reschedule / cancel” buttons.

* **Main workflow 3: Admin booking management**

  1. Stylist opens admin menu in Telegram.
  2. Stylist can view today, tomorrow, week, and upcoming bookings.
  3. Stylist can inspect booking status and client details.
  4. Stylist can change booking date/time, service, price, duration, place, notes, or status.
  5. Stylist can cancel or reschedule a booking.
  6. Bot sends the client an automatic notification when relevant booking details change.

* **Main workflow 4: Manual complex-service booking**

  1. Client requests coloring or another complex service through chat/personal consultation.
  2. Stylist decides service duration, date/time, price, and any notes manually.
  3. Stylist creates the booking in the admin flow.
  4. Bot sends the client a clean confirmation message with service, date, time, place, and price.
  5. After the appointment, stylist can record final amount charged and basic costs such as materials, rent, assistant payment, or other expenses.

* **Main workflow 5: Revenue and client statistics**

  1. Stylist opens analytics/admin menu.
  2. Bot shows weekly revenue, completed bookings, cancellations, and optional estimated profit after recorded expenses.
  3. Stylist can open a client card and see visit history, services, total spent, last visit, and notes.
  4. Stylist can use this information for follow-up, planning, and basic business tracking.

---

## 3. Scope

* **In scope for v1:**

  * Telegram bot interface.
  * Polished welcome message and clear client menu.
  * Display of available dates and time slots.
  * 1-hour haircut slots.
  * Male haircut price: 100 GEL.
  * Female haircut price: 120 GEL.
  * Booking confirmation with service, date, time, place/address, duration, and price.
  * Prevention of double booking.
  * Automatic reminders 24 hours before and a few hours before service.
  * Automatic client notifications when a booking is changed, rescheduled, or cancelled by the stylist.
  * Admin notification when a new booking is created.
  * Admin workflow for adding/removing available slots.
  * Admin workflow for viewing booking status.
  * Admin workflow for changing, rescheduling, or cancelling a booking.
  * Manual admin booking creation for coloring / complex services.
  * Manual entry of service duration, price, final amount charged, notes, and basic costs.
  * Basic cost categories: materials/consumables, rent, assistant payment, other.
  * Weekly revenue summary.
  * Basic client statistics: visit history, total spent, services, last visit, notes.
  * Basic booking storage.
  * Basic logs/errors.

* **Out of scope / non-goals:**

  * Online payment.
  * AI consultation for coloring.
  * Automatic price estimation for coloring.
  * Multi-stylist scheduling.
  * Loyalty program.
  * Full CRM or marketing automation.
  * Instagram integration.
  * Full salon management system.
  * Dynamic service duration estimation.
  * Automatic calendar optimization.
  * Complex analytics dashboard beyond simple Telegram summaries.
  * Payroll, tax accounting, inventory management, or formal bookkeeping.

---

## 4. AI Scope

* **Where AI may be needed:** Not needed for v1. The product should be deterministic and rule-based.
* **Where AI is explicitly not wanted:** Booking availability, slot confirmation, pricing, reminder scheduling, cancellation rules, service duration, status changes, financial summaries, and client notifications should not depend on AI.
* **External agent skills planned:** none.
* **If external skills are planned, source and install scope:** none.
* **External skill capabilities expected:** none.
* **Possible retrieval / RAG need:** none for v1.
* **If retrieval is needed, is text-only likely sufficient or is multimodal evidence truly required:** not applicable.
* **If multimodal may be needed, which modalities and why:** not applicable.
* **Possible tool-use need:** Telegram Bot API, database, scheduler, admin allowlist, optional Google Calendar later, optional CSV export later.
* **Possible planning / agentic behavior need:** none for v1.

---

## 5. Deterministic Candidates

List the parts that probably should stay deterministic unless the Strategist proves otherwise.

* **Validation / policy checks:**

  * Slot must exist.
  * Slot must be available.
  * Slot duration is 1 hour.
  * Male haircut price is 100 GEL.
  * Female haircut price is 120 GEL.
  * Coloring cannot be self-booked automatically in v1.
  * Coloring and complex services can be created manually by the stylist with custom duration and price.
  * User cannot book an already reserved slot.
  * Booking must have Telegram user ID or manually entered client reference, date, time, status, service, price, place, and created timestamp.
  * Booking status must be one of the declared status values.
  * Booking changes must be logged.
  * Client notification must be sent when date, time, place, price, status, or cancellation changes.

* **Routing / decision rules:**

  * “Haircut” → show available slots.
  * “Coloring” → redirect to personal account.
  * “Other service” → redirect to personal account.
  * “My booking” → show active booking details.
  * “Cancel/change appointment” → show instructions or button flow.
  * Admin “today / week” → show relevant bookings.
  * Admin “manual booking” → create booking and optionally notify client.
  * Admin “change/cancel/reschedule” → update booking and notify client.
  * Admin “stats” → show weekly revenue and client statistics.
  * Unknown input → show main menu again.

* **Calculations / transformations:**

  * Appointment end time = start time + 1 hour.
  * Reminder 1 = appointment time minus 24 hours.
  * Reminder 2 = appointment time minus 2–3 hours.
  * Date/time formatting for client messages.
  * Weekly revenue = sum of completed booking final amounts in selected week.
  * Basic profit estimate = completed booking final amounts minus recorded expenses.
  * Client total spent = sum of completed booking final amounts for that client.
  * Expense total = materials + rent + assistant payment + other recorded expenses.

* **Retries / idempotency / audit triggers:**

  * Booking creation must be idempotent.
  * Reminder sending should not duplicate messages after restart.
  * Failed reminder should be retried.
  * Every booking status change should be logged.
  * Every client notification for a booking change should be logged.
  * Manual admin edits should record who changed what and when.

---

## 6. Human Approval Boundaries

* **What actions must require human approval:**

  * Coloring booking.
  * Any service with unknown duration or unknown price.
  * Manual override of booked slots.
  * Cancelling or rescheduling an existing booking.
  * Changing final price, place, or status after confirmation.
  * Sending custom non-template messages to clients.
  * Dispute/conflict handling.
  * Same-day schedule exceptions if not configured.
  * Any future pricing changes.

* **What can be automated safely:**

  * Showing available haircut slots.
  * Creating haircut bookings for available slots.
  * Sending fixed price and duration.
  * Sending reminders.
  * Sending standard confirmation messages.
  * Sending standard change/cancel/reschedule notifications after admin action.
  * Showing weekly revenue and client history from stored records.
  * Redirecting complex service requests to personal account.
  * Basic cancellation/reschedule instructions.

* **Why these boundaries matter:** Haircut is standardized and low-risk: fixed time and fixed price. Coloring is variable and can require consultation, visual assessment, different timing, different materials, and different pricing. Automating coloring too early may create bad expectations and operational mistakes.

---

## 7. Risk and Error Cost

* **What is expensive if the system is wrong:**

  * Double booking.
  * Wrong appointment time.
  * Wrong price communication.
  * Booking complex service as a simple haircut.
  * Sending reminders to the wrong person.
  * Failing to notify client after reschedule/cancellation.
  * Wrong weekly revenue or client spending totals.
  * Lost manual booking or expense data.
  * Losing bookings after restart.

* **What is expensive if the system is slow:**

  * Client may drop off and write manually.
  * Available slot selection becomes annoying.
  * User loses trust in the bot.

* **What is expensive if the system is inconsistent / variable:**

  * Different clients receive different rules or prices.
  * Confusion about whether coloring can be booked automatically.
  * Missed reminders.
  * Client receives outdated appointment details after admin edits.
  * Admin stats do not match stored completed bookings.
  * Operational distrust from the stylist.

* **Blast radius if it fails badly:** Low to medium. Main risk is schedule confusion, lost revenue, and client dissatisfaction. No high-risk regulated decisions.

* **Audit / explainability needs:** Basic logs of booking creation, cancellation, reschedule, status changes, admin edits, client notifications, reminder scheduling, reminder delivery, final amount updates, and expense updates.

---

## 8. Data

* **Primary data sources:**

  * Telegram user profile: Telegram user ID, username, first name if available.
  * Client profile: Telegram identity when available, display name, notes, visit history, total spent.
  * Booking data: date, time, service type, planned price, final amount charged, duration, place, status.
  * Slot data: available slots, booked slots, blocked slots.
  * Reminder data: reminder schedule, delivery status.
  * Notification data: confirmation/change/cancel/reminder delivery log.
  * Expense data per completed booking: materials/consumables, rent, assistant payment, other.
  * Admin configuration: working days, available hours, stylist account link, reminder timing.
  * Business configuration: default place/address, map link, default service prices, default duration.

* **Approximate data volume:** Low. Expected tens to hundreds of bookings per month.

* **Does data change frequently:** Yes. Availability and bookings can change daily.

* **Sensitive / regulated data present:** Low sensitivity. Personal contact data and appointment data are present. No medical, financial, or regulated data expected.

* **Retention / deletion expectations:** Keep booking history, client history, and basic financial records for operational reference. Allow deletion/anonymization if requested. Do not store unnecessary personal information.

---

## 8b. Continuity and Evidence

* **Which decisions are likely to be revisited later:**

  * Whether to add Google Calendar sync.
  * Whether to add cancellation/reschedule buttons.
  * Whether to add admin panel.
  * Whether to support multiple services.
  * Whether manual complex-service bookings should stay Telegram-only or move to a web admin panel.
  * Whether financial tracking should remain basic or become real accounting/export.
  * Whether to add CSV/Google Sheets export.
  * Whether to add payments/deposits.
  * Whether to add multilingual support.
  * Whether to add Instagram link or web booking page.

* **What prior evidence or proof will future agents need to find quickly:**

  * Haircut prices: 100 GEL male, 120 GEL female.
  * Haircut duration: 1 hour.
  * Client chooses male or female haircut before date selection.
  * Coloring requires personal consultation.
  * Coloring and complex services can be entered manually by the stylist.
  * Client confirmations must include service, date, time, place, and price.
  * Client must be notified when a booking is changed, rescheduled, or cancelled.
  * Stylist needs weekly revenue and client spending/service history.
  * Reminder timing: 24 hours before and a few hours before.
  * Telegram bot is the primary interface.
  * Codex is the implementation agent for this repository; Claude Code is not currently available.

* **Will work span multiple sessions / agents / weeks:** Yes, likely across multiple development sessions.

* **Any existing docs, ADRs, audits, or notes that should become retrieval anchors:**

  * This `PROJECT_BRIEF.md`.
  * Future `ARCHITECTURE.md`.
  * Future `DECISIONS.md`.
  * Future `BOT_COPY.md`.
  * Future `ADMIN_GUIDE.md`.
  * Future `CLIENT_MESSAGES.md`.
  * Future `FINANCE_REPORTS.md`.

---

## 9. Integrations

* **External APIs / services:**

  * Telegram Bot API.
  * Optional later: Google Calendar API.
  * Optional later: CSV / Google Sheets export.
  * Optional later: external notification/logging service.

* **Databases / storage:**

  * v1 simple option: SQLite.
  * Better production option: PostgreSQL.
  * For very small deployment: SQLite with backups may be enough.
  * Redis can be added later if background jobs need more reliability.

* **Auth / identity provider:**

  * Client identity through Telegram user ID.
  * Admin identity through allowlisted Telegram user IDs.

* **Webhooks / messaging / queues:**

  * Telegram webhook or long polling.
  * Background scheduler for reminders.
  * Optional queue for reminders if deployed beyond simple MVP.

---

## 10. Constraints

* **Preferred stack:**

  * Python.
  * aiogram or python-telegram-bot.
  * SQLite or PostgreSQL.
  * SQLAlchemy / SQLModel / async SQLAlchemy.
  * APScheduler, Celery, Dramatiq, or simple persistent scheduler depending on deployment.
  * Docker for deployment.

* **Deployment target:**

  * Small VPS, Render, Railway, Fly.io, or similar simple container hosting.
  * Managed Postgres if using PostgreSQL.
  * For MVP, one small server/container is enough.

* **Budget constraints:** Low. Prefer simple infrastructure with minimal monthly cost.

* **Latency / throughput expectations:** Low throughput. Bot should respond within 1–2 seconds for common actions.

* **Compliance requirements:** Basic privacy hygiene. Do not overcollect personal data. Protect bot token and admin credentials.

* **Network / security restrictions:** Telegram bot token must be stored in environment variables. Admin commands must be restricted to allowlisted Telegram IDs.

* **Development workflow constraint:** All implementation work is expected to be done by Codex in this repository. Do not assume Claude Code is installed or available. Claude-specific `.claude` settings, commands, and hooks should not be required for v1.

---

## 11. Runtime and Operations

* **Should runtime stay simple (managed service / container) if possible:** Yes.
* **Any need for shell, package, or toolchain mutation at runtime:** No.
* **Any need for privileged actions or long-lived isolated workers:** No privileged actions. Long-lived process may be needed for polling/scheduler, unless using webhooks and external cron/worker.
* **Recovery / rollback expectations:**

  * Bot restart should not lose bookings.
  * Reminder jobs should survive restart or be recalculated from database.
  * Client notifications for reschedules/cancellations should be recoverable and logged.
  * Backups should exist for booking data.
  * Deployment should allow quick rollback to previous working version.

---

## 12. Model and Cost Expectations

Only fill what you know. The Strategist should still make the final recommendation.

* **Cost sensitivity:** high.
* **Latency sensitivity:** medium.
* **Expected request / task volume:** Low at launch. Tens to hundreds of user interactions per month, plus admin interactions for manual bookings and statistics.
* **If AI is used, should the system prefer smaller / cheaper models by default:** Yes, but AI is not needed for v1.
* **Any required capabilities:** Function calling / structured output not required for v1.
* **Preview-model tolerance:** none.
* **Per-run / per-task budget:** Ideally near zero. Telegram + hosting/database only.
* **Monthly project budget or budget ceiling:** Unknown, but should be kept minimal.
* **Who approves budget overruns:** Project owner / stylist.
* **Should budget overruns warn, block, or require approval:** Require approval.
* **Expected attribution needs:** Per booking, per user, per workflow.
* **Allowed model escalation path:** None for v1.
* **Maximum acceptable retries / tool calls / parallel agents:** Not applicable for AI. For bot operations: limited retries for failed reminder delivery.
* **Expected workload classes:** User-facing booking workflow, deterministic scheduling, notifications, admin configuration, manual booking management, financial summaries, client history summaries.
* **Prompt caching likely useful:** no.
* **Batch or async lane acceptable for any workload:** yes, reminders can be async/background.
* **Dynamic routing or cascades expected:** no.
* **If routing/cascades are expected, what quality floor must hold:** not applicable.
* **What cost metric matters most:** monthly ceiling.

---

## 13. Success Metrics

* **Business success metric:** Number and share of standard haircut bookings created through the bot, plus weekly revenue visible to the stylist without separate manual calculation.
* **Quality metric:** Zero double bookings; correct service, date, time, place, and price shown in 100% of booking confirmations and change notifications.
* **Latency metric:** Bot responds to slot selection and confirmation within 1–2 seconds under normal load.
* **Cost metric:** Minimal fixed monthly infrastructure cost.
* **Operational metric:** 95%+ of reminders/change notifications successfully sent; bookings survive bot restart; admin can update slots/bookings without code changes; completed bookings can be included in weekly revenue and client history.

---

# Suggested v1 Product Behavior

## Client main menu

Buttons:

* Book a haircut
* Coloring / complex service
* My booking
* Reschedule / cancel
* Contact stylist

## Welcome message

Hi! Here you can book an appointment.

Haircut duration: 1 hour.
Male haircut price: 100 GEL.
Female haircut price: 120 GEL.

Choose an available date and time below.

For coloring or complex services, please write to me personally, because time and price depend on the case.

## Booking confirmation message

You are booked.

Service: haircut
Date: {date}
Time: {time}
Place: {place}
Duration: 1 hour
Price: {100_or_120_GEL}

I will send you a reminder 24 hours before the appointment and again a few hours before.

If you need to change or cancel the appointment, use the bot menu or write to me.

## Admin new booking notification

New booking.

Client: {client_name}
Service: {service}
Date: {date}
Time: {time}
Place: {place}
Price: {price}
Status: confirmed

## Client reschedule notification

Your appointment has been changed.

Service: {service}
New date: {date}
New time: {time}
Place: {place}
Price: {price}

## Client cancellation notification

Your appointment has been cancelled.

Service: {service}
Date: {date}
Time: {time}

If you want to choose a new time, open the bot menu.

## Coloring redirect message

Coloring requires a personal consultation, because the time and price depend on your hair, current color, desired result, and technique.

Please write to me here: {stylist_account_link}

I will help you choose the right option and book the correct amount of time.

After we agree on the details, I will send you a confirmation here in the bot.

## Reminder 24 hours before

Reminder: your haircut is tomorrow.

Date: {date}
Time: {time}
Place: {place}
Price: {100_or_120_GEL}

## Reminder a few hours before

Reminder: your haircut is today at {time}.

Place: {place}
Price: {100_or_120_GEL}.

## Admin menu

Buttons:

* Today
* This week
* New manual booking
* Change booking
* Cancel booking
* Revenue
* Clients

## Weekly revenue summary

Week: {week_start} - {week_end}

Completed bookings: {completed_count}
Gross revenue: {gross_revenue} GEL
Recorded expenses: {expenses_total} GEL
Estimated net: {net_revenue} GEL

Breakdown:

* Haircuts: {haircut_total} GEL
* Coloring / complex services: {complex_total} GEL
* Other: {other_total} GEL

## Client card summary

Client: {client_name}
Total spent: {total_spent} GEL
Visits: {visit_count}
Last visit: {last_visit_date}
Services: {service_summary}
Notes: {notes}

---

# Suggested v1 Engineering Tasks

1. Initialize bot project structure.
2. Add Telegram bot framework.
3. Add config via environment variables.
4. Add database models:

   * User
   * Client
   * Slot
   * Booking
   * BookingStatusHistory
   * BookingNotificationLog
   * BookingExpense
   * ReminderLog
5. Add client booking flow.
6. Add deterministic slot locking to prevent double booking.
7. Add admin allowlist.
8. Add admin slot management commands.
9. Add admin booking list views: today, tomorrow, week, upcoming.
10. Add admin manual booking creation for coloring and complex services.
11. Add admin booking edit flow: reschedule, cancel, change service, change price, change duration, change place, update notes.
12. Add automatic client notifications after admin-created booking, reschedule, cancellation, and relevant booking edits.
13. Add reminder scheduler.
14. Add restart-safe reminder recovery from database.
15. Add booking completion flow with final amount charged and basic expense entry.
16. Add weekly revenue summary.
17. Add client card/history summary.
18. Add basic tests for booking, double-booking prevention, redirects, admin edits, client notifications, reminder calculation, and revenue/client-stat calculations.
19. Add Dockerfile and deployment instructions.
20. Add README with setup, env vars, admin commands, client messages, and operating rules.
