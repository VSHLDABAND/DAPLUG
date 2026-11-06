# Property OS V2 — Screen Inventory

This document describes the intended screen hierarchy and controls. Items labelled **Live in foundation** are implemented now; items labelled **Planned** are product specification, not shipped functionality.

## Global shell — Live in foundation

- Fixed left sidebar with workspace, operations and insights groups.
- Top bar with current location, section search and global Add New Lead action.
- Professional dark palette, responsive navigation and modal forms.
- User identity, role label and sign-out.
- Local-workspace indicator.

## 1. Overview — Live in foundation (first pass)

**Header:** greeting, description, Add Property and Add New Lead.

**KPI row:** active leads, available listings, new matches, open follow-ups.

**Lower workspace:** recent leads table and action queue. Empty states guide the user to create the first record.

**Planned:** hot lead queue, stale inventory warning, recent reverse matches, today's visits, lead-source funnel, deal pipeline, commission snapshot and team activity.

## 2. Leads & Clients — Live in foundation (first pass)

**Header actions:** add lead, export CSV.

**Toolbar:** status filter, lead-type filter, current-section search.

**Table:** client identity and lead code, requirement summary, source, assigned user, priority, editable status, Find Matches action.

**Manual Add Lead modal sections:**
1. Contact information — name, phone, email, company.
2. Lead classification — lead type, sale/rent, residential/commercial, status, priority, source.
3. Requirement — property type, city, localities, configuration, min/max/stretch INR budget, area range, furnishing, parking, amenities, timeline and strictness checkboxes.
4. Internal — notes and requirement notes.

**Planned detail page:** Overview, Requirements, Matches, Activity, Messages, Visits, Deals and Notes tabs; requirement version timeline; full edit controls; assignment; tags; qualification; consent and preferred contact window.

## 3. Property Inventory — Live in foundation (first pass)

**Header actions:** add property, export CSV.

**Toolbar:** availability and category filters; section search.

**Table:** listing title and code, category/type, locality/city, price, configuration/area, editable availability, verification state and Verify Now control.

**Manual Add Property modal sections:**
1. Listing details — title, transaction, category, type, city, locality, address, price, configuration, area, furnishing, floor, parking and amenities.
2. Sourcing/ownership — source type, availability, owner name/phone, source broker name/phone, expected commission.
3. Internal information — private notes.

**Planned detail page:** Photos/videos, documents, map, owner/broker profile, verification evidence, price history, expiry, matching clients, visits, deal history and activity timeline.

## 4. Matching Centre — Live in foundation

**Mode A — Client → Properties:** select a lead, run/re-run matching, inspect score/reasons, shortlist or approve.

**Mode B — Property → Clients:** select an available listing, run reverse matching against current lead requirements, inspect score/reasons, shortlist or approve.

The first-pass matching engine also calculates a first set automatically when a new lead or listing is created.

**Planned:** all-opportunities inbox, saved searches, comparison view, score-weight editor, listing-confidence indicator, stale listing rules, rejection reasons, manual score override, notification rules and match conversion analytics.

## 5. Follow-ups & Tasks — Live in foundation (first pass)

Create a task with title, due date/time, priority, optional linked lead and description. Filter all/open/completed; mark open tasks complete. Dashboard surfaces a short action queue.

**Planned:** due-today/overdue/upcoming/assigned-to-me views, task assignment, property/deal/visit links, recurring rules, reminders and SLA reporting.

## 6. Builder Projects — Planned

Project list with developer, project name, category, locality, RERA number, possession and status. Project detail contains unit/configuration inventory, price ranges, availability, plans, amenities and channel-partner commission terms.

## 7. Deals & Negotiations — Planned

Kanban and list views by stage. Deal detail includes client, property, offer history, negotiation notes, expected closure, agreed value, documents, next task and commission ledger.

## 8. Analytics & Reports — Planned

Date-range selector, actual-vs-estimated labels and export. Lead funnel, source conversion, locality demand, inventory aging, matching performance, visit conversion, agent activity and collected commission.

## 9. Team — Live in foundation (basic)

Admin creates agent/manager accounts; team list shows role and active state. Planned: invitation/reset workflow, deactivate/reactivate, record ownership, assignment and role-permission matrix.

## 10. Settings — Live in foundation (basic)

Shows CSV export links, local data policy, zero-cost policy and optional integration boundary. Planned: configurable match weights, stale thresholds, backup/restore, database location, audit viewer, status dictionaries and import options.
