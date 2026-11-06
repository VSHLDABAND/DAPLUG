# Broker Feed & Property Sourcing Engine

## The product's primary job

Property OS is primarily a broker-network property sourcing system. The user manually enters buyer/tenant requirements. Property OS captures property posts from five WhatsApp broker groups, extracts structured details from text and media, compares each discovered property candidate against active requirements, and surfaces the best client matches with the original post and source-broker information.

A broker post is a **candidate**, not automatically verified inventory. The user should be able to contact the source broker, verify availability and terms, and only then promote the candidate into the verified Property Inventory.

## Intended pipeline

1. **Lead demand** — manually entered client profiles and one or more evolving requirements remain a first-class workflow.
2. **Group source registry** — keep five named WhatsApp group sources; preserve group name, sender, original timestamp and source reference.
3. **Message capture** — capture incoming text and media from an approved/consented source adapter. Keep the raw post unchanged for review.
4. **Property extraction** — use local parsing/OCR/vision to extract transaction type (rent/sale), category, type, city/locality, price, configuration, area, furnishing, parking, amenities, broker contact and availability hints. Unknown data remains unknown.
5. **Candidate normalization** — normalize amounts (₹, thousands, lakh, crore), locality aliases, configurations, property types and dates.
6. **Deduplication** — identify repeated forwards and near-duplicate listings without erasing the separate source-group evidence.
7. **Demand matching** — hard-filter incompatible transaction/category/mandatory criteria; rank the remaining candidates; expose score reasons and extraction confidence separately.
8. **Opportunity inbox** — show lead, match score, original message, attachments, group, sender and missing fields. Allow shortlist, contact, reject and mark reviewed.
9. **Verification & promotion** — do not treat an unverified broker post as available inventory. A human confirms details before promotion.
10. **Feedback** — capture rejected/shortlisted/contacted outcomes to improve configurable ranking; never silently relax mandatory lead constraints.

## Current first implementation in this source package

- Five local broker-group slots, initially named Broker Group 1–5 and editable by the user.
- Manual paste/capture of a broker message.
- Import of a WhatsApp exported `.txt` chat or `.zip` with media. The importer filters common non-property chatter and retains photo-only messages when a media filename is referenced in the exported chat; matching ZIP media is linked to the corresponding post.
- Local rule-based extraction for common Ahmedabad localities, property type, category, sale/rent, BHK, amount, area, furnishing, parking, amenities and Indian mobile numbers.
- Local attachment storage plus optional macOS Apple Vision OCR for images and PDFs when the free Swift command-line tools are installed. OCR text is fed back into parsing and matching; original attachments remain available.
- Missing requirement evidence lowers the compatibility score rather than being omitted from its denominator, preventing sparse posts from being ranked artificially high.
- Broker-post-to-lead matching against current requirements, separate from verified inventory.
- Match reasons, extraction confidence, review states, shortlist/contact/reject actions and reprocessing.
- Duplicate detection for repeated long messages within a group.

## How to bring posts into the local feed today

1. In WhatsApp, open one of the five broker groups and use **Export chat**.
2. Choose **Include media** when the export option is offered. Transfer the resulting ZIP to the Mac. A text-only export can be imported as `.txt`, but it will not contain the original image files.
3. In Property OS, open **Property Matching** or **WhatsApp Broker Feed**, select the matching source-group slot, and import the `.zip` or `.txt` file.
4. Property OS keeps likely property messages, links referenced images/PDFs, tries local OCR on macOS, extracts fields, and checks the candidates against all active manually created lead requirements.
5. Review the original post and broker details before contacting anyone. Treat extracted details as unverified until the source broker confirms availability and terms.

A new lead created after a chat export is imported is also matched against the already captured broker-post history, so you do not need to import the same chat again just because a client requirement was added later.

## Important current limitations

- **Live monitoring of existing WhatsApp groups is not implemented.** The `.txt` import and manual capture are the initial zero-subscription intake methods.
- ZIP export media is linked when the exported text references the exact media filename. Attachments can also be added to a captured post from the UI.
- macOS Vision OCR is optional and requires the free Swift command-line tools. If they are not installed, OCR reports `unavailable` and posts remain usable through manual review.
- The text parser is a first-pass rules engine. Its extracted fields and compatibility score are not proof that a listing is genuine or still available.

## WhatsApp access and safety decision

The standard WhatsApp Business Platform does not provide a general-purpose API to silently read arbitrary existing community groups. The newer Groups API is designed for groups created through that API and requires Official Business Account eligibility plus a very high messaging-limit threshold; its groups are invite-only and subject to small group-size limits. That does not solve access to five existing broker groups.

WhatsApp's current Messaging Guidelines explicitly include scraping data and use of unofficial clients among adversarial behaviours and say WhatsApp may suspend accounts for guideline violations. Therefore, Property OS must not silently rely on a WhatsApp Web scraper, reverse-engineered client, or third-party paid bridge as a required feature. Such approaches would expose the user's normal WhatsApp number and do not meet the lifetime-free/reliable requirement.

Future connector work must prefer a documented and authorized route, with group/admin consent where required. Keep the connector behind an optional adapter interface. The local broker feed, manual capture, export importer, matching and verified inventory must continue functioning without WhatsApp connectivity.

## Next development stages

1. Improve Gujarati/Hinglish/English property-post parsing and locality dictionaries from the user's real samples.
2. Add property candidate promotion to verified inventory and broker-contact workflow.
3. Add a local quick-capture workflow that reduces friction when manually forwarding/pasting a new group post.
4. Implement an approved/consented live ingestion adapter only if a compliant source is available; do not assume the official API can join the five existing groups.
