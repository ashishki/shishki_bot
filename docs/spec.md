# Product Spec - shishki_bot

Version: 1.0
Last updated: 2026-07-06
Status: Phase 1 bootstrap

## Overview

`shishki_bot` is a Telegram bot for one stylist. It supports client booking for
simple services, admin-managed manual bookings for complex services, reminders,
change notifications, and lightweight business statistics.

## User Roles

| Role | Capabilities |
|------|--------------|
| Client | Book simple service, view active booking, receive confirmation/reminders/change notifications, request cancel/reschedule path. |
| Stylist admin | Manage slots, receive booking updates, create/edit/cancel bookings, record final amounts/expenses, view revenue and client history. |

## Feature 1 - Client Main Menu

Description: The client receives a clear Telegram menu with primary service
choices, active booking access, referral bonus access, and stylist information.

Acceptance criteria:

1. Client can open `/start` and see concise welcome text plus buttons.
2. Welcome text is short, avoids service price/duration detail, and points the
   client to service choice buttons.
3. Menu includes haircut, coloring, consultation, my booking, referral, and
   about master options.
4. About master, no-active-booking, and service redirect screens keep useful
   service/main-menu navigation available.
5. Unknown input returns the main menu without creating a booking.

Out of scope for v1: multilingual copy and rich media onboarding.

## Feature 2 - Simple Haircut Booking

Description: Clients can self-book a male or female haircut into available
slots.

Acceptance criteria:

1. Bot asks for haircut type before showing only available future slots.
2. Client must confirm before booking is created.
3. Booking stores client, service, date/time, duration, place, price, status, and created timestamp.
4. Slot cannot be double-booked under concurrent attempts.
5. Client receives confirmation with service, date, time, place, map links,
   salon entrance hint/photo, duration, price, and change/cancel instructions.
6. Stylist admin receives a notification after confirmed self-booking, client
   reschedule, and client cancellation; the notification includes client
   identity/chat when available, and delivery success/failure is logged.
7. One Telegram client cannot hold more than 2 active haircut bookings on the
   same date.
8. Male haircut self-booking is 100 GEL; female haircut self-booking is 120 GEL.

Out of scope for v1: online payment and automatic deposits.

## Feature 3 - Complex Service Redirect and Manual Booking

Description: Coloring and consultations require personal chat. Coloring can then
be created manually by admin once duration and complexity are clear.

Acceptance criteria:

1. Client choosing coloring receives consultation copy and stylist contact link.
2. Client cannot self-book coloring directly.
3. Client choosing consultation receives stylist contact link without creating a booking.
4. Coloring and consultation redirect screens keep buttons for other service
   choices and the main menu.
5. Admin can create a manual booking with custom service, duration, date/time,
   price, place, and notes using either client ID or Telegram username.
6. Admin can create common manual bookings through a button flow: client,
   service, duration, date, time, and final confirmation.
7. Admin can send client a confirmation with salon entrance photo for a manual
   booking when the client has a Telegram identity and the service has a known
   client-visible price.
8. Manual bookings block all overlapping self-booking slots for their full
   duration, not only the starting slot.

Out of scope for v1: AI price/time estimation from photos or descriptions.

## Feature 4 - Admin Booking Management

Description: Stylist can manage the schedule from Telegram admin menu.

Acceptance criteria:

1. Admin-only menu is restricted to allowlisted Telegram IDs.
2. Admin can open `/admin` and see a dashboard with today/upcoming bookings,
   client counts, free slots, weekly metrics, and quick controls.
3. Admin can reschedule, cancel, change service, change duration, change price, change place, and update notes.
4. Booking changes create status/change history records.
5. Relevant changes send client notifications or log delivery failure.
6. Admin can create/reopen a single hour or working day from Telegram.
7. Admin can use button-driven working-time controls with date selection,
   presets, per-hour actions, and confirmation before schedule changes.
8. Admin can close one free slot or the remaining free slots in a day without
   changing occupied active bookings.
9. Admin can open client list/cards and see per-client visit, spend, current
   booking, history, and referral metrics.
10. Admin can create a booking from the dashboard or client card through
    guided buttons without memorizing the `/book` format.

Out of scope for v1: web admin panel and multi-admin permissions beyond a simple allowlist.

## Feature 5 - Reminders and Notifications

Description: The bot sends appointment confirmations, reminders, and change
notifications.

Acceptance criteria:

1. Reminder schedule is derived from booking time.
2. Reminders are sent 24 hours before and a few hours before the appointment.
3. Reminder sending is restart-safe by reading pending reminders from database.
4. Duplicate reminders are prevented by delivery logs.
5. Reschedule/cancel/change notifications include the updated appointment details.
6. Client reminder messages do not include appointment price.

Out of scope for v1: SMS/email notifications.

## Feature 6 - Completion, Revenue, and Expenses

Description: Admin can mark appointments completed and record actual payment and
basic costs.

Acceptance criteria:

1. Admin can mark booking completed.
2. Admin can record final amount charged.
3. Admin can record materials/consumables, rent, assistant payment, and other expenses.
4. Weekly revenue sums completed booking final amounts only.
5. Estimated net subtracts recorded expenses from completed booking final amounts.

Out of scope for v1: formal accounting, tax reports, payroll, inventory.

## Feature 7 - Client History

Description: Admin can view basic client history and spending.

Acceptance criteria:

1. Client card shows display name or Telegram username when available.
2. Client card shows visit count, total spent, last visit, services summary, and notes.
3. Total spent uses completed booking final amounts only.
4. Client history includes manual and self-booked appointments.

Out of scope for v1: marketing automation, loyalty program, segmentation.

## Feature 8 - Operations and Reliability

Description: The app should be safe to deploy and recover from restart.

Acceptance criteria:

1. Secrets are read from environment variables.
2. Bot restart does not lose bookings or pending reminder state.
3. Local tests do not send real Telegram messages.
4. CI runs formatting/lint/tests once the project skeleton exists.
5. Production deployment has documented backup and rollback notes before real client use.

Out of scope for v1: high availability and multi-region deployment.

## Feature 9 - Referral Program

Description: Clients can share a personal Telegram deep link. The bot records
new clients who first enter through that link and qualifies the referral after
the referred client's appointment is completed. Admin-approved manual credits
can also count toward bonus progress without creating fake referred clients.

Acceptance criteria:

1. Client can request a personal referral link from the bot.
2. `/start ref_<code>` records the referrer for a new client before booking.
3. Self-referrals and clients with existing bookings are ignored.
4. A referral becomes qualified only after a completed booking.
5. Every 3 credited units, from qualified referrals plus approved manual
   credits, creates an admin-visible pending bonus.
6. Admin receives a one-time reminder for a newly earned bonus.
7. Client cards show referral code/progress, pending referred clients, pending
   bonuses, manual credits, and awarded bonuses.

Reward positioning: professional hair cosmetics, either care or styling,
instead of a haircut discount.

Out of scope for this iteration: payment/refund logic, public leaderboards, and
automatic product inventory management.
