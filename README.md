# Property OS V2

A local-first, dark-interface real-estate sourcing workspace. Its primary workflow is matching manually entered client requirements against property opportunities captured from five broker WhatsApp groups. The first Broker Feed release adds local post capture, WhatsApp text-export import, rule-based extraction, local attachments and broker-post-to-lead matching.

## Non-negotiable operating policy

Property OS is being designed for **₹0 recurring software/service cost**. The core application does not require a subscription, paid API, paid AI service, paid cloud database, paid hosting or WhatsApp integration. It runs on hardware you control using open-source software.

No one can guarantee that an unrelated third-party service will remain free forever. For that reason, external messaging, maps, AI and other services are optional adapters only. Manual workflows must continue to work when every integration is disconnected.

“Free” does not mean that hardware, electricity, internet access, optional domain names, or third-party charges are magically free. Those are outside the application's software cost. The core app has no built-in paid dependency.

## Requirements

- macOS, Windows or Linux computer to host the application.
- Python 3.11 or newer recommended.
- A modern browser.
- For a team, all devices should be on the same trusted local network and able to reach the host computer.

## Run on macOS

1. Extract the project folder somewhere you can keep it, such as `~/PropertyOS`.
2. Open the folder in Finder.
3. Right-click `run.command` → Open. (The first launch may ask for permission.)
4. The script creates `.venv`, installs free Python packages and starts the server.
5. Open `http://127.0.0.1:8000`.
6. The first screen asks you to create the administrator account. Do not lose this password.

The first package installation needs internet access. After the dependencies are installed, the core application can run locally without internet access. Optional image/PDF OCR uses the macOS Vision framework through Swift; install the free Xcode Command Line Tools with `xcode-select --install` if they are not already present.

## Run from Terminal (macOS/Linux)

```bash
cd /path/to/property_os_v2
chmod +x run.command
./run.command
```

Windows users can run these commands from PowerShell:

```powershell
cd path\to\property_os_v2
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Small-team LAN mode

The default is intentionally private to the host computer (`127.0.0.1`). To let colleagues on the **same trusted local network** access the app:

```bash
PROPERTY_OS_HOST=0.0.0.0 ./run.command
```

Then share the host computer's private LAN address, for example `http://192.168.x.x:8000`. Use each teammate's separate account. Do not expose this initial build directly to the public internet. Public deployment requires HTTPS, hardened session handling, backups, rate limits, access-control review and a security pass.

The host computer must remain on and connected to the network while teammates use the application. No cloud hosting is required.

## Data location and backups

- Main database: `data/property_os.db`
- Local signing secret: `data/.secret_key`
- Backups: `data/backups/` for update snapshots; the general backup command currently writes `backups/`.

Use `backup.command` on macOS/Linux or run `python scripts/backup_db.py` with the project's virtual environment active. Keep a copy of the `data/` folder and backups somewhere safe. **Never delete `.secret_key` while keeping the database**: doing so invalidates active sessions (users can sign in again after the key is recreated).

The project includes CSV export for leads and properties. CSV is useful for portability, but it does not replace a full SQLite backup.

## Implemented in this foundation

- First-run administrator setup and local sign-in.
- Team accounts (admin can create manager and agent accounts).
- Manual lead creation with contact and requirement data.
- Contact reuse when an exact phone number already exists.
- Lead list, search, status and priority tracking.
- Manual residential and commercial property entry.
- Owner and source-broker contact capture.
- Property availability updates and verification timestamp.
- Client → property matching and property → client reverse matching.
- Broker Feed: five configurable group slots, manual message capture, WhatsApp `.txt` / `.zip` export import, basic field extraction, local media attachment linking and direct matching against active client requirements.
- Local image/PDF attachments linked to captured broker posts, with optional on-device macOS Vision OCR for images/PDFs when the free Swift command-line tools are installed.
- Automatic first-pass matching when a lead or property is created.
- Explainable compatibility reasons, shortlist/approve status.
- Manual follow-up task creation and completion.
- Dashboard summary and CSV exports.
- Local SQLite storage with foreign keys, WAL and busy timeout.

## Not yet implemented (planned, not falsely represented as complete)

- Full edit screens for all lead and property fields.
- Requirement version history and multiple concurrent requirements per lead in the UI.
- Full contacts/brokers directory and merge workflow.
- Builder projects and unit inventory screens.
- Site visit scheduling and feedback screens.
- Deal pipeline and commission ledger screens.
- Property candidate promotion and richer document/photo workflows; broker post media capture is implemented.
- Team assignment filters, granular role permissions and audit-log viewer.
- Automatic follow-up rules, configurable scoring UI and reverse-match opportunity inbox.
- Live monitoring of the five existing WhatsApp groups; current safe intake is manual capture or exported `.txt` / `.zip` chat import.
- WhatsApp adapter, message templates and conversation inbox.
- Database migration tooling and automated scheduled backups.

## API documentation

When the app is running, open `http://127.0.0.1:8000/api/docs` for the locally generated API reference. API docs are not exposed as a public service; they are part of the local app.

## Tech stack

- Python + FastAPI
- SQLAlchemy
- SQLite
- Vanilla JavaScript, HTML and CSS (no frontend build chain or paid UI kit)

This foundation deliberately avoids requiring React build tooling, remote fonts, CDNs or cloud services, so the UI itself can load without external network access.

## Broker Feed workflow

See [`docs/BROKER_FEED_PLAN.md`](docs/BROKER_FEED_PLAN.md) for the primary product workflow, how to import an exported group chat, current implementation scope and WhatsApp access limitations. The Broker Feed is separate from verified inventory: raw broker messages become candidates, are matched against manually entered demand, and require human verification before promotion to inventory.
