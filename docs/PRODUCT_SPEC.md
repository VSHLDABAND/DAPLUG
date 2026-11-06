# Property OS V2 — Product Specification

**Product type:** Local-first real-estate CRM, inventory and matching workspace  
**Primary users:** Small brokerage team  
**Initial market:** Residential and commercial property; sale and rental  
**Visual direction:** Professional dark desktop-first interface, responsive for tablets  
**Cost policy:** ₹0 recurring cost for the core application; no paid dependency

## 1. Product objective

Create one source of truth for the brokerage's contacts, leads, active requirements, property inventory, matches, follow-up tasks, site visits, deals and commissions. Reduce repetitive manual searching and data re-entry while preserving full manual control.

The application is not a public property portal. It is an internal operating workspace for the brokerage team.

## 2. Non-negotiable product principles

1. **Manual-first, automation-assisted:** every core workflow remains possible manually. Automation proposes or performs only configured actions.
2. **Local-first:** all core records live in a database controlled by the brokerage. No cloud service is required for normal operations.
3. **Zero recurring cost:** no subscription, paid API, paid AI inference, hosted database, managed hosting or mandatory third-party service.
4. **Human control:** sending client communications, deleting records, merging contacts, changing deal outcomes and other consequential actions require a user action or an explicit rule.
5. **Explainable matching:** every match shows the reasons, hard-filter decisions and the data used.
6. **Data portability:** open CSV export plus a complete database backup path.
7. **Small-team ready:** individual user accounts, role model, assignment and audit history. Team use starts on a trusted LAN.
8. **Truthful availability:** stale or unverified listings must be flagged; a property is not assumed available indefinitely.

## 3. User roles

| Role | Initial permissions | Planned permissions |
|---|---|---|
| Admin | First-run setup, create team accounts, use all modules | Configure scoring, roles, exports, backup and workspace settings |
| Manager | Access workspace records | Assign leads, review activity, manage inventory and team pipeline |
| Agent | Access workspace records | Manage assigned clients, properties, activities and visits |

The first foundation implements sign-in and user creation. Fine-grained per-record permissions and row-level visibility are not yet implemented. Do not expose the initial build publicly.

## 4. Core modules and detailed screens

### 4.1 Overview / Command Centre

Purpose: tell the user what needs attention rather than only showing vanity metrics.

Components:
- KPI cards: active leads, available listings, new matches, open/overdue tasks.
- Recently added leads.
- Action queue of open tasks.
- Future: hot leads, inventory freshness alerts, recent match discoveries, visits today, negotiation pipeline, expected/received commission.

Primary actions: add lead, add property, create task, open matching centre.

### 4.2 Leads & Clients

Lead list columns: client, lead ID, requirement summary, source, assigned agent, priority, stage, next action.

Lead creation is permanently manual and must be reachable from the global action button. The form is grouped into:
- Contact: name, primary phone, alternate phone (planned), email, company.
- Lead classification: buyer, tenant, investor, owner; transaction sale/rent; source; lead stage; priority.
- Requirement: category, property type, city, one or more localities, budget floor/ceiling/stretch, configuration, area, furnishing, parking, amenities, strict preferences, timeline.
- Qualification: seriousness, decision maker, finance readiness, expected transaction date (planned).
- Internal: assigned agent, tags, notes, consent/contact preference (planned).

A lead may be saved with incomplete information. Missing data is represented as unknown, not treated as a negative match. A lead can eventually have multiple dated requirements; updating a requirement must preserve the older version.

Lead detail screen (planned): profile header; tabs for requirements, matches, activity, messages, visits, deals and notes; complete timeline; status and next-action controls.

### 4.3 Contacts & Brokers

Canonical contact records can represent clients, owners, landlords, builders, brokers, channel partners and vendors. One person may be related to multiple leads and listings. Dedupe candidates by normalized phone/email, but merging must be reviewable and reversible through audit history.

### 4.4 Property Inventory

Separate the listing from the person who owns or sourced it.

Fields: property ID, title, sale/rent, residential/commercial, property type, city, locality, address, map coordinate (planned), price or monthly rent, configuration, area and area basis, furnishing, floor, parking, amenities, status, owner, sourcing broker, source type, internal commission, verification timestamp, documents/media (planned), notes and assigned user.

Status lifecycle: draft → available → on hold → under negotiation → sold/rented → archived. Only available listings enter new matches. Sold/rented/archived listings stay in history.

Listing freshness: retain last verified timestamp and verification outcome. A configurable stale threshold should mark a listing as needing verification; stale data should lower confidence or block outgoing suggestions according to workspace settings.

Property detail (planned): full data, photos/documents, source and owner, price history, verification history, matching clients, visits, negotiations and audit trail.

### 4.5 Builder Projects

Project is a parent record, with project units/configuration inventory below it. Fields include developer, RERA number, location, category, project status, possession, configuration, price range, unit count, area, amenities, floor plans, booking terms and channel partner commission. Do not duplicate project inventory as unrelated independent listings; individual units may be materialized as listings when required.

### 4.6 Matching Centre

Two primary workflows:
- Client → Properties: choose a requirement; score available listings.
- Property → Clients: choose a listing; find active client requirements.

A third view should show new, reviewed, shortlisted, approved, sent and rejected opportunities.

Matching algorithm design:
1. Mandatory gates: sale/rent, residential/commercial, explicit property type, strict location and strict configuration, plus price above absolute stretch ceiling.
2. Soft score: location, budget fit, configuration, area, furnishing, parking and amenities.
3. Reliability: listing freshness, verification status, source reliability and data completeness are distinct from compatibility.
4. Explanation: return reasons and mismatches, not only a number.
5. Human feedback: users can shortlist, approve, reject or mark already contacted.
6. Recalculation: new lead and new listing trigger first-pass matching; user can request recalculation.

Initial score weights are provisional and should be calibrated with real brokerage outcomes. Avoid presenting a score as a probability of closing.

### 4.7 Communication / WhatsApp

Communication is an adapter, not the database. Planned capability: inbox, incoming enquiry capture, message-to-contact association, conversation summaries, templates, approved property sharing, delivery status and reply classification.

Manual note/call logging and copyable message templates must remain available if WhatsApp is disconnected. Official WhatsApp API access, pricing, template policies and availability can change. Do not promise lifetime-free messaging; never make the system depend on it.

### 4.8 Follow-ups & Tasks

Tasks can link to a lead, property, deal or visit. Fields: title, description, due time, priority, status, assignee, creator and completion timestamp. Views: today, overdue, upcoming, completed, assigned to me. Rules may suggest tasks; users retain manual creation and edits.

### 4.9 Site Visits

Link a lead and one property per visit. Track requested/scheduled/confirmed/completed/cancelled/no-show, date/time, meeting point, contact, attendees, feedback and next step. A client visiting multiple listings creates separate visit records.

### 4.10 Deals & Negotiations

A deal links one lead and one property (or a project unit). Stages: interest, visit, offer, negotiation, token/booking, documentation, closed-won, closed-lost. Keep asking price, offer, agreed value, expected close, closure date and loss reason. Never overwrite original listing price with final transaction price.

### 4.11 Commission Ledger

Track expected, agreed, invoiced and received amounts separately, with split/partner share, due date, received date and status. Reports must distinguish pipeline forecast from actual collected income.

### 4.12 Analytics & Reports

Lead source conversion, time-to-first-response, requirements by locality/budget, inventory aging, match approval/response rates, visits-to-deals conversion, agent pipeline, commission expected vs received. Always identify date range, sample size and whether values are estimates or actuals.

### 4.13 Settings & Data

Users, roles, matching weights, stale listing threshold, status vocabularies, export, backup/restore, local network host guidance, optional integrations and audit history.

## 5. Global interaction model

- Persistent sidebar and global Add New Lead action.
- Search within current module; filters and sorting.
- Keyboard shortcut `N` opens manual lead form; `Ctrl/Cmd + K` focuses search.
- Fast-add forms with optional fields; detailed profile editing on separate screens.
- Toast feedback and explicit empty/error states.
- Every automation action is visible in an activity log.
- Destructive actions require confirmation and should archive by default rather than hard-delete.

## 6. Data quality and business rules

- Normalize phone numbers and retain the entered display value.
- A contact may have multiple leads; a lead may have multiple requirements over time.
- Budgets are stored as INR numeric values, never as ambiguous text. Rental budgets/prices are monthly unless a future lease-period field states otherwise.
- Areas store numeric square feet and identify carpet/built-up/super-built-up basis in the full schema.
- Unknown information is null/unknown, not false.
- Matches are unique per requirement + property and retain user review status.
- Property status change to unavailable suppresses it from active matching.
- Do not auto-send recommendations during initial rollout.
- Record creator, editor and timestamps for important mutations.

## 7. Deployment and lifetime-free constraints

Primary deployment is one host computer on a trusted local network. That host runs the API and local database. Teammates use a browser to reach the host's private LAN address. No public cloud is required. The host must remain powered on for team access.

Open-source stack: Python, FastAPI, SQLAlchemy, SQLite, HTML, CSS and vanilla JavaScript. Avoid remote fonts, CDN scripts, external analytics, telemetry and hosted database dependencies. Local optional AI can be evaluated later only if it runs on owned hardware and does not require a paid API.

Security before public or internet exposure: HTTPS, secure cookie configuration, CSRF strategy, brute-force protection, permission matrix, audit review, backup/restore testing, secrets management and dependency review.

## 8. Acceptance criteria for the first usable release

- A user can create the workspace administrator without a third-party account.
- Admin can create separate team logins.
- A user can manually create a lead with a partial or complete requirement.
- A user can manually create residential/commercial sale/rental inventory.
- New lead triggers client-to-property matching; new listing triggers property-to-client matching.
- Match results explain compatibility and exclude unavailable inventory.
- User can shortlist/approve a match manually.
- User can create and complete a follow-up task.
- User can export leads/properties to CSV and back up the SQLite database.
- All core screens load without an internet connection after installation.
