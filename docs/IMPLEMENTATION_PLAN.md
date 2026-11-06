# Property OS V2 — Implementation Plan

## Build sequence

### Milestone 0 — Foundation (current)
- Repo layout, local run scripts and dependency constraints.
- FastAPI + SQLAlchemy + SQLite foundation.
- First-run admin account and individual team users.
- Dark responsive navigation and dashboard shell.
- Manual lead entry, list/search/status, contact de-duplication on exact normalized phone.
- Manual residential/commercial sale/rent property entry and availability status.
- Two-way matching and first-pass automatic matching on lead/property creation.
- Task creation/completion, CSV exports, local backup script.

**Exit checks:** setup/login; create lead; create property; see match from either direction; add/complete task; export; backup.

### Milestone 1 — Data management completeness
- Full lead edit and requirement edit; multi-requirement history.
- Property detail/edit, attachments, price history and verification workflow.
- Contact/broker directory, duplicate suggestions and merge review.
- Search/filter/sort/pagination and saved views.
- Database migration framework (Alembic), backup/restore UI and audit viewer.

### Milestone 2 — Daily brokerage operations
- Assignment and permission matrix.
- Task reminders and configurable workflow rules.
- Site visits with feedback and rescheduling.
- Deal pipeline, negotiation timeline and loss reasons.
- Commission tracking (expected/agreed/invoiced/received).

### Milestone 3 — Inventory intelligence
- Reverse match opportunity inbox and notifications within the local app.
- Configurable match weights and mandatory filters.
- Listing freshness, stale listing rules and source confidence.
- Location aliases/locality adjacency managed manually (no paid maps service).
- Match feedback analysis and score calibration.

### Milestone 4 — Communication adapters
- Manual call/WhatsApp log and reusable copyable templates.
- Optional WhatsApp Cloud API adapter only after current price/policy verification.
- Consent/opt-out, message-template compliance, delivery status and error handling.
- Integration can be disabled without affecting the database or manual workflows.

### Milestone 5 — Advanced assistance and reporting
- Local-only natural-language search/lead requirement extraction (optional model, if practical on owned hardware).
- Conversation summaries from messages imported/received with consent.
- Business analytics, pipeline and inventory reporting.
- Import wizard and data quality reports.

## Engineering standards

- Keep business logic separate from route handlers and UI.
- Validate enums, budgets, dates and cross-field requirements.
- Add automated tests for every hard filter and scoring factor.
- Treat match scores as explainable heuristics, not close probabilities.
- No external network call in normal core workflows.
- No external fonts or JavaScript CDNs.
- Add structured logs and an audit event for important actions.
- Use backups before migrations and before bulk imports.
- Test with synthetic data; never mix test records into the user's live database.

## Definition of done for each feature

1. Works manually without integrations.
2. Validates input and handles empty/error states.
3. Updates the database transactionally.
4. Records actor and timestamps.
5. Can be exported/backed up.
6. Has a basic automated test.
7. Is represented accurately in the interface (no fake or static data presented as live).
