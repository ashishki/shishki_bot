# Project Tasks

Status: active
Mode: Standard
Last updated: 2026-06-23

This task graph is the forward contract for Codex. Keep tasks small enough for
one focused implementation session and update this file when scope changes.

## T01: Project Skeleton

Owner:      codex
Phase:      1
Type:       none
Depends-On: none
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Create the Python project skeleton, package metadata, app directories, config
  loading, and placeholder entrypoints for the Telegram bot.

Acceptance-Criteria:
  - id: AC-1
    description: "Repository contains `pyproject.toml`, `requirements.txt`, `requirements-dev.txt`, `app/`, and `tests/`."
    test: "test -f pyproject.toml && test -f requirements.txt && test -f requirements-dev.txt && test -d app && test -d tests"
  - id: AC-2
    description: "`app/config.py` defines settings for bot token, admin IDs, database URL, timezone, default place, and optional map URL without hardcoded secrets."
    test: "tests/test_config.py::test_settings_load_from_environment"
  - id: AC-3
    description: "`app/main.py` exposes a startable bot entrypoint without contacting Telegram during import."
    test: "tests/test_imports.py::test_app_imports_without_side_effects"

Files:
  - pyproject.toml
  - requirements.txt
  - requirements-dev.txt
  - app/main.py
  - app/config.py
  - tests/test_config.py
  - tests/test_imports.py

Context-Refs:
  - docs/ARCHITECTURE.md
  - docs/spec.md
  - docs/IMPLEMENTATION_CONTRACT.md

## T02: CI And Local Verification

Owner:      codex
Phase:      1
Type:       none
Depends-On: T01
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Configure local and GitHub Actions verification for lint, format, tests, and
  playbook integrity.

Acceptance-Criteria:
  - id: AC-1
    description: "CI installs dev dependencies and runs ruff check, ruff format --check, pytest, integrity check, and skill security gate."
    test: "python3 tools/integrity_check.py --root ."
  - id: AC-2
    description: "Local verification command is documented in README and CODEX_PROMPT."
    test: "python3 tools/integrity_check.py --root ."

Files:
  - .github/workflows/ci.yml
  - README.md
  - docs/CODEX_PROMPT.md

Context-Refs:
  - docs/ARCHITECTURE.md#tech-stack

## T03: First Smoke Tests

Owner:      codex
Phase:      1
Type:       none
Depends-On: T01 T02
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Add the first smoke tests for settings import, application import, and
  no-network import behavior so future feature tasks start from a verified
  skeleton.

Acceptance-Criteria:
  - id: AC-1
    description: "Settings can be loaded from test environment variables without reading `.env` or real secrets."
    test: "tests/test_config.py::test_settings_load_from_environment"
  - id: AC-2
    description: "Application modules import without contacting Telegram or opening a database connection."
    test: "tests/test_imports.py::test_app_imports_without_side_effects"
  - id: AC-3
    description: "The full smoke-test command runs successfully."
    test: "python -m pytest tests/test_config.py tests/test_imports.py -q"

Files:
  - tests/test_config.py
  - tests/test_imports.py
  - app/main.py
  - app/config.py

Context-Refs:
  - docs/spec.md#feature-8---operations-and-reliability
  - docs/IMPLEMENTATION_CONTRACT.md#mandatory-pre-task-protocol

## T04: Database Models And Migrations

Owner:      codex
Phase:      1
Type:       none
Depends-On: T03
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Add database models and persistence primitives for users, clients, slots,
  bookings, status history, notification logs, reminder logs, and booking
  expenses.

Acceptance-Criteria:
  - id: AC-1
    description: "Models represent users, clients, slots, bookings, status history, notification logs, reminder logs, and booking expenses."
    test: "tests/test_models.py::test_models_create_minimal_booking_graph"
  - id: AC-2
    description: "Booking status values are constrained to the statuses declared in architecture."
    test: "tests/test_models.py::test_booking_status_enum_matches_architecture"
  - id: AC-3
    description: "Local test database setup can create and drop all tables."
    test: "tests/test_models.py::test_metadata_create_all"

Files:
  - app/db/models.py
  - app/db/session.py
  - tests/test_models.py

Context-Refs:
  - docs/ARCHITECTURE.md#booking-statuses
  - docs/spec.md#feature-8---operations-and-reliability

## T05: Booking Service And Slot Locking

Owner:      codex
Phase:      2
Type:       none
Depends-On: T04
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Implement deterministic booking creation, slot availability checks, and
  double-booking prevention.

Acceptance-Criteria:
  - id: AC-1
    description: "A confirmed haircut booking can be created for an available slot with default 90 GEL price and 1 hour duration."
    test: "tests/test_booking_service.py::test_create_haircut_booking"
  - id: AC-2
    description: "Two bookings cannot reserve the same slot."
    test: "tests/test_booking_service.py::test_prevent_double_booking"
  - id: AC-3
    description: "Coloring cannot be self-booked through the simple booking path."
    test: "tests/test_booking_service.py::test_coloring_not_self_bookable"

Files:
  - app/services/booking.py
  - tests/test_booking_service.py

Context-Refs:
  - docs/spec.md#feature-2---simple-haircut-booking

Transaction-Contract: |
  Booking service functions participate in a caller-owned SQLAlchemy Session
  transaction. They lock the slot, create the booking, and flush. Callers must
  commit or roll back the session boundary.

## T06: Message Templates And Notification Service

Owner:      codex
Phase:      2
Type:       none
Depends-On: T04 T05
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Add reusable client/admin message templates and a notification service that
  logs sent or failed notification attempts.

Acceptance-Criteria:
  - id: AC-1
    description: "Booking confirmation includes service, date, time, place, duration, price, and change/cancel instructions."
    test: "tests/test_notifications.py::test_confirmation_message_contains_required_fields"
  - id: AC-2
    description: "Reschedule and cancellation notifications include updated appointment details."
    test: "tests/test_notifications.py::test_change_notifications_contain_required_fields"
  - id: AC-3
    description: "Notification service records delivery success or failure."
    test: "tests/test_notifications.py::test_notification_delivery_is_logged"

Files:
  - app/bot/messages.py
  - app/services/notifications.py
  - tests/test_notifications.py

Context-Refs:
  - docs/spec.md#feature-5---reminders-and-notifications
  - docs/IMPLEMENTATION_CONTRACT.md#client-notification-integrity

## T07: Admin Authorization And Menus

Owner:      codex
Phase:      2
Type:       none
Depends-On: T01
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Implement admin allowlist checks and menu handlers for schedule and business
  operations without exposing admin actions to clients.

Acceptance-Criteria:
  - id: AC-1
    description: "Only allowlisted Telegram IDs can access admin handlers."
    test: "tests/test_admin_auth.py::test_admin_allowlist_required"
  - id: AC-2
    description: "Admin menu exposes today, this week, manual booking, change booking, cancel booking, revenue, and clients actions."
    test: "tests/test_admin_auth.py::test_admin_menu_actions"

Files:
  - app/bot/handlers/admin.py
  - app/bot/keyboards.py
  - app/main.py
  - tests/test_admin_auth.py

Context-Refs:
  - docs/IMPLEMENTATION_CONTRACT.md#admin-authorization

## T08: Client Booking Handlers

Owner:      codex
Phase:      3
Type:       none
Depends-On: T05 T06
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Implement Telegram client handlers for start menu, simple haircut booking,
  complex service redirect, active booking view, and reschedule/cancel path.

Acceptance-Criteria:
  - id: AC-1
    description: "`/start` returns welcome copy and the declared client menu."
    test: "tests/test_client_handlers.py::test_start_menu"
  - id: AC-2
    description: "Client can confirm a simple haircut booking from an available slot."
    test: "tests/test_client_handlers.py::test_client_haircut_booking_flow"
  - id: AC-3
    description: "Complex service selection returns consultation redirect and creates no booking."
    test: "tests/test_client_handlers.py::test_complex_service_redirect"

Files:
  - app/bot/handlers/client.py
  - app/bot/keyboards.py
  - app/config.py
  - app/main.py
  - tests/test_client_handlers.py
  - tests/test_config.py

Context-Refs:
  - docs/spec.md#feature-1---client-main-menu
  - docs/spec.md#feature-3---complex-service-redirect-and-manual-booking

## T09: Admin Manual Booking And Edits

Owner:      codex
Phase:      3
Type:       none
Depends-On: T05 T06 T07
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Implement admin-created bookings and admin edits for reschedule, cancellation,
  service, price, duration, place, and notes.

Acceptance-Criteria:
  - id: AC-1
    description: "Admin can create a manual complex-service booking with custom duration and price."
    test: "tests/test_admin_booking.py::test_admin_manual_booking"
  - id: AC-2
    description: "Admin reschedule updates booking, writes status history, and triggers client notification."
    test: "tests/test_admin_booking.py::test_admin_reschedule_notifies_client"
  - id: AC-3
    description: "Admin cancellation updates status history and triggers client notification."
    test: "tests/test_admin_booking.py::test_admin_cancel_notifies_client"

Files:
  - app/db/models.py
  - app/services/booking.py
  - app/bot/messages.py
  - app/bot/handlers/admin.py
  - tests/test_admin_booking.py

Context-Refs:
  - docs/spec.md#feature-4---admin-booking-management
  - docs/IMPLEMENTATION_CONTRACT.md#booking-integrity
  - docs/IMPLEMENTATION_CONTRACT.md#client-notification-integrity
  - docs/IMPLEMENTATION_CONTRACT.md#admin-authorization

## T10: Reminder Scheduler

Owner:      codex
Phase:      3
Type:       none
Depends-On: T04 T06
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Add restart-safe reminder scheduling and duplicate-send prevention.

Acceptance-Criteria:
  - id: AC-1
    description: "Reminder times are calculated as 24 hours before and a few hours before appointment time."
    test: "tests/test_reminders.py::test_reminder_times"
  - id: AC-2
    description: "Pending reminders can be reconstructed from database state after restart."
    test: "tests/test_reminders.py::test_recover_pending_reminders"
  - id: AC-3
    description: "A reminder with an existing success log is not sent twice."
    test: "tests/test_reminders.py::test_no_duplicate_reminders"

Files:
  - app/scheduler.py
  - app/services/reminders.py
  - tests/test_reminders.py

Context-Refs:
  - docs/spec.md#feature-5---reminders-and-notifications

## T11: Completion, Expenses, And Revenue

Owner:      codex
Phase:      4
Type:       none
Depends-On: T04 T09
Status:     [x] complete
Completed:  2026-06-23

Objective: |
  Implement booking completion, final amount entry, expense entry, weekly revenue
  summary, and estimated net calculation.

Acceptance-Criteria:
  - id: AC-1
    description: "Completed booking can store final amount and expense rows."
    test: "tests/test_finance.py::test_complete_booking_with_expenses"
  - id: AC-2
    description: "Weekly gross revenue sums completed booking final amounts only."
    test: "tests/test_finance.py::test_weekly_gross_revenue"
  - id: AC-3
    description: "Estimated net subtracts materials, rent, assistant, and other expenses."
    test: "tests/test_finance.py::test_weekly_net_revenue"

Files:
  - app/services/finance.py
  - app/bot/handlers/admin.py
  - tests/test_finance.py

Context-Refs:
  - docs/spec.md#feature-6---completion-revenue-and-expenses
  - docs/IMPLEMENTATION_CONTRACT.md#financial-calculations

## T12: Client History

Owner:      codex
Phase:      4
Type:       none
Depends-On: T04 T11

Objective: |
  Implement client card and visit history summaries for admin use.

Acceptance-Criteria:
  - id: AC-1
    description: "Client card shows visit count, total spent, last visit, services summary, and notes."
    test: "tests/test_client_history.py::test_client_card_summary"
  - id: AC-2
    description: "Client total spent includes completed manual and self-booked appointments only."
    test: "tests/test_client_history.py::test_client_total_spent"

Files:
  - app/services/clients.py
  - app/bot/handlers/admin.py
  - tests/test_client_history.py

Context-Refs:
  - docs/spec.md#feature-7---client-history

## T13: Deployment And Operator Guide

Owner:      codex
Phase:      5
Type:       none
Depends-On: T02 T10 T11 T12

Objective: |
  Add deployment artifacts and operator docs for local setup, environment
  variables, admin use, backup, rollback, and safe operation.

Acceptance-Criteria:
  - id: AC-1
    description: "README documents setup, env vars, local verification, and bot startup."
    test: "python3 tools/integrity_check.py --root ."
  - id: AC-2
    description: "Operator guide documents admin commands, backup, rollback, and no-real-client-test rule."
    test: "python3 tools/integrity_check.py --root ."
  - id: AC-3
    description: "Dockerfile or deployment notes exist for the selected target."
    test: "test -f Dockerfile -o -f docs/DEPLOYMENT.md"

Files:
  - README.md
  - docs/ADMIN_GUIDE.md
  - docs/DEPLOYMENT.md
  - Dockerfile

Context-Refs:
  - docs/ARCHITECTURE.md#runtime-model
  - docs/spec.md#feature-8---operations-and-reliability
