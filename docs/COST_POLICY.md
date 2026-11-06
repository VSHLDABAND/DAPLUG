# Property OS V2 — Lifetime-Free Operating Policy

## Target

The application's core functionality must remain usable for ₹0 in recurring software and service charges.

## Allowed by default

- Open-source software installed on hardware owned/controlled by the brokerage.
- Python, FastAPI, SQLAlchemy, SQLite and browser-native HTML/CSS/JavaScript.
- Local file storage and local database backups.
- Manual entry, manual search, manual matching, manual follow-ups and CSV exports.
- Local-network access without paid cloud hosting.
- Optional local AI only if the model runs on owned hardware and uses no metered API.

## Not allowed as a core dependency

- Paid API keys or usage-based AI services.
- Paid SaaS CRM, managed database or cloud hosting.
- Paid automation tools or workflow platforms.
- Paid map/geocoding, enrichment, scraping or property-data subscriptions.
- Any mandatory WhatsApp, SMS, email, telephony or social-platform integration.
- CDN, analytics or hosted font dependencies that stop the UI working offline.

## Third-party boundary

WhatsApp, messaging, maps and other external platforms control their own pricing, terms, permissions, quotas and availability. Property OS cannot promise those providers will remain free for the lifetime of this project. Integrations must be adapters that can be disabled or replaced, with manual operation still available.

## Cost visibility

Before adding any dependency, document:
1. Is it open-source and self-hostable?
2. Does it require an account or API key?
3. Is any usage billed or capped?
4. Does it send business/customer data outside the local machine?
5. What happens to the workflow if the service disappears or starts charging?

Reject it as a required dependency if it violates the core free/local-first requirements. Clearly label any optional cost or limitation before implementation.

## Practical caveat

The user still needs a computer, electricity and a network to run a multi-device local application. The application has no mandatory subscription or recurring hosted-service cost, but this does not mean every operating expense of the business is zero.
