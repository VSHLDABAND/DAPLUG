# Property OS V2 — Core Workflows and Rules

## Workflow A — Manually add a client lead

1. User clicks the persistent **Add New Lead** action.
2. User enters any available details; only the client name is mandatory in the first form.
3. Application normalizes phone digits and checks for an exact existing phone contact.
4. If the contact exists, the new lead links to it; otherwise, a new contact is created.
5. Application creates a lead and its current requirement in one database transaction.
6. Activity/audit event records who created it.
7. Matching engine searches currently available inventory.
8. User can inspect matches or return later. No message is sent automatically.

Incomplete requirements are allowed. Unknown preferences remain unknown.

## Workflow B — Manually add a property

1. User clicks **Add Property**.
2. User enters residential/commercial, sale/rent, type, location, INR price/monthly rent and any known characteristics.
3. Owner and sourcing broker contacts are created/reused when supplied.
4. New listing is stored with a unique property code and creator/assignee.
5. Reverse matching searches existing non-converted/non-lost lead requirements.
6. Compatible lead/property pairs are stored for review.
7. User verifies availability before approving a match for external sharing.

## Workflow C — Client-to-property matching

1. Choose a lead; retrieve its current requirement.
2. Consider only available properties with the same transaction type and category.
3. Enforce any explicit property type and strict preference gates.
4. Reject prices above the maximum stretch budget.
5. Score remaining listings only on comparable, supplied preference dimensions.
6. Return a normalized 0–100 compatibility score plus human-readable reasons.
7. User may shortlist, approve, reject or later mark sent.

Initial weights when the dimension is supplied and comparable:
- Location: 25
- Budget: 25
- Configuration: 20
- Area: 10
- Furnishing: 5
- Parking: 5
- Amenities: 10

The score is normalized across the weights actually evaluated. An unspecified preference is not counted as a failure. If no useful preference is supplied, return 50 with a warning that there is insufficient information to score reliably. The score is a heuristic, not a close probability.

## Workflow D — Property-to-client reverse matching

1. Choose an available listing.
2. Consider current requirements of leads not marked converted/lost.
3. Apply the same transaction/category gates and scoring function used in forward matching.
4. Return compatible clients and reasons.
5. User reviews and decides whether to contact them.

## Workflow E — Inventory freshness

- Only `available` listings enter current match results.
- User can change a property's status to on hold, under negotiation, sold, rented or archived.
- User can record a verification timestamp through Verify Now.
- A future freshness policy should configure a stale period and suppress or label outdated listings.

## Workflow F — Follow-up task

1. User creates a task manually, optionally linking it to a lead.
2. Task appears on the Tasks page and the dashboard action queue.
3. User marks it complete after acting.
4. Planned rules may suggest follow-ups after enquiry, property share, visit or negotiation, but do not silently contact clients.

## Workflow G — Team access

1. First-run setup creates the workspace administrator.
2. Admin creates individual manager/agent accounts.
3. Teammates sign in through a browser on the local host or trusted LAN.
4. The initial build has role labels and account separation, but fine-grained record permissions still need implementation before broader team rollout.
