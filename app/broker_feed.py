"""Local broker-post parsing helpers for Property OS.

The parser deliberately avoids remote AI/API calls. Unknown fields stay unknown and
are surfaced for human review rather than being invented.
"""
from __future__ import annotations

import re
from typing import Any


LOCALITIES = [
    "South Bopal", "Prahlad Nagar", "Prahladnagar", "Science City", "Science Park",
    "SG Highway", "S G Highway", "S.G. Highway", "Sindhubhavan Extension", "Sindhubhavan Road",
    "Sindhubhavan", "Navrangpura", "Chandkheda", "Vastrapur", "Bodakdev", "Satellite",
    "Thaltej", "Gota", "Motera", "Maninagar", "Nikol", "Shilaj", "Shela", "Bopal",
    "Ghuma", "Ambli", "Shyamal", "Jodhpur", "Paldi", "Sola Bhagwat", "Sola",
    "Iscon Ambli", "Iscon", "Gandhinagar", "Sanand", "Ahmedabad", "Mithakhali",
    "Ashram Road", "CG Road", "C.G. Road", "C G Road", "Shivranjani", "Anand Nagar",
    "Anandnagar", "Radio Mirchi Road", "Ramdevnagar", "Ramdev Nagar", "Prernatirth",
    "Manekbaug", "Makarba", "Changodar", "Gurukul", "Naranpura", "Ambawadi",
    "Ambavadi", "Jivraj Park", "Vejalpur", "New Ranip", "Ranip", "Chandlodia",
    "Kudasan", "Vaishnodevi", "Juhapura", "Vasna", "Sarkhej", "Tragad", "Thol",
    "Pipli", "Dholera", "Chankyapuri", "Chanakyapuri", "Bakeri City", "Jodhpur Cross Road",
    "Sola Bhagwat Vidyapith", "Rajpath Rangoli", "Karnavati Club", "Vayana Village",
    "Shilaj Canal Road", "Sola Road", "100 Feet Road", "100 Ft Road", "Judges Bungalow",
]

COMMERCIAL_TYPES = {
    "office": ("commercial", "office"),
    "shop": ("commercial", "shop"),
    "showroom": ("commercial", "showroom"),
    "warehouse": ("commercial", "warehouse"),
    "godown": ("commercial", "warehouse"),
    "industrial": ("commercial", "industrial"),
    "industrials": ("commercial", "industrial"),
    "factory": ("commercial", "industrial"),
    "offices": ("commercial", "office"),
    "shops": ("commercial", "shop"),
    "showrooms": ("commercial", "showroom"),
    "godown": ("commercial", "warehouse"),
    "godaun": ("commercial", "warehouse"),
    "godowns": ("commercial", "warehouse"),
    "godauns": ("commercial", "warehouse"),
    "cafe": ("commercial", "shop"),
    "restaurant": ("commercial", "shop"),
    "hotel": ("commercial", "hotel"),
    "retail": ("commercial", "shop"),
}
RESIDENTIAL_TYPES = {
    "flat": ("residential", "apartment"),
    "apartment": ("residential", "apartment"),
    "villa": ("residential", "villa"),
    "bungalow": ("residential", "bungalow"),
    "row house": ("residential", "row_house"),
    "plot": ("residential", "plot"),
    "land": ("residential", "plot"),
    "penthouse": ("residential", "penthouse"),
    "flats": ("residential", "apartment"),
    "apartments": ("residential", "apartment"),
    "plots": ("residential", "plot"),
    "villas": ("residential", "villa"),
    "bungalows": ("residential", "bungalow"),
    "tenement": ("residential", "row_house"),
    "tenament": ("residential", "row_house"),
    "tenements": ("residential", "row_house"),
    "tenaments": ("residential", "row_house"),
}


# The same WhatsApp groups contain both property supply (offers) and broker demand
# (requirements). Demand posts must never be treated as available properties.
_DEMAND_HEADING = re.compile(
    r"^\s*[\W_]*(?:(?:urgent|immediate|hot)\s+)?"
    r"(?:requirement|required|require|riq(?:rment)?|looking\s+for|wanted|need(?:ed)?\s+for)\b",
    re.I,
)
_DEMAND_RE = re.compile(
    r"\b(?:requirements?|required|require|riq(?:rment)?|looking\s+for|looking\s+to\s+(?:buy|rent|lease)|"
    r"searching\s+for|search\s+for|want\s+to\s+(?:buy|rent)|need\s+(?:a|an|on|for|to)|"
    r"urgent\s+requirement|any\s+(?:suitable\s+)?options?|suitable\s+options\s+required|"
    r"property\s+required|flat\s+required|office\s+required|shop\s+required|"
    r"client\s+(?:is\s+)?looking|if\s+you\s+have\s+any\s+option|options\s+required)\b",
    re.I,
)
_SUPPLY_RE = re.compile(
    r"\b(?:available(?:\s+for)?|availability|for\s+rent|on\s+rent|to\s+let|for\s+sale|on\s+sale|"
    r"exclusive\s+(?:rental|properties)|hot\s+property|property\s+available|rent\s+inventory|"
    r"asking\s+price|sale\s+price|sell\s+price|rent\s*[:=\-]|price\s*[:=\-]|"
    r"selling|\brent\b|\bsale\b|\bleased\b|\blease\b)",
    re.I,
)


def classify_broker_message(raw_text: str) -> str:
    """Classify a group message as supply, demand, mixed, or unknown.

    High-precision behaviour is intentional: demand/ambiguous messages are never
    automatically matched as available properties.
    """
    text = (raw_text or "").strip()
    if not text:
        return "unknown"
    lines = [line.strip().strip("*_~` ") for line in text.splitlines() if line.strip()]
    heading = " ".join(lines[:3])[:350] if lines else text[:350]
    has_demand = bool(_DEMAND_RE.search(text))
    has_supply = bool(_SUPPLY_RE.search(text))

    # A requirement-led message such as "URGENT REQUIREMENT – 3 BHK ON RENT"
    # is demand, even though it contains the word rent.
    if _DEMAND_HEADING.search(heading):
        return "demand"
    if has_demand and has_supply:
        return "mixed"
    if has_demand:
        return "demand"
    if has_supply:
        return "supply"
    return "unknown"


def split_property_entries(raw_text: str) -> list[str]:
    """Split a WhatsApp post into safer sub-entries before intent classification.

    Important: some broker messages contain several available properties followed
    by one or more client requirements. The old implementation classified the
    entire message first and therefore hid every property in a mixed post. This
    version adds a demand-section boundary and avoids treating every 🔹 detail
    bullet (price, locality, furnishing, parking) as a separate property.

    Prefix context (for example "EXCLUSIVE RENTAL OPTION") is retained for
    property segments, but is deliberately not copied into a demand segment.
    """
    text = (raw_text or "").strip()
    if not text:
        return []
    lines = text.splitlines()

    numbered = re.compile(
        r"^\s*[*_`~]*(?:\(\s*)?\d{1,2}\s*(?:\)|[.)](?=\s|[*_`~🔹🔸])|\ufe0f?\u20e3)\s*",
        re.I,
    )
    arrow_property = re.compile(
        r"^\s*👉\s*[*_`~]*(?:(?:available\s+(?:for\s+)?(?:rent|sale))|"
        r"(?:[1-6](?:\.5)?\s*bhk)|flat|apartment|bungalow|villa|office|shop|showroom|"
        r"warehouse|godown|plot|land|penthouse|tenement)\b",
        re.I,
    )
    sparkle_header = re.compile(r"^\s*✨\s*[*_`~]*\S", re.I)

    # Find the first explicit demand heading. Once a requirement section starts,
    # do not split its internal bullets into fake property entries.
    demand_index = next((i for i, line in enumerate(lines) if _DEMAND_HEADING.match(line)), None)

    marker_kinds: dict[int, str] = {}
    for i, line in enumerate(lines):
        if demand_index is not None and i > demand_index:
            continue
        if numbered.match(line):
            marker_kinds[i] = "listing"
        elif arrow_property.match(line):
            marker_kinds[i] = "listing"
        elif sparkle_header.match(line):
            marker_kinds[i] = "listing"

    if demand_index is not None:
        marker_kinds[demand_index] = "demand"

    indexes = sorted(marker_kinds)
    if len(indexes) < 2:
        return [text]

    prefix = "\n".join(lines[:indexes[0]]).strip()
    result: list[str] = []
    for pos, start in enumerate(indexes):
        end = indexes[pos + 1] if pos + 1 < len(indexes) else len(lines)
        block = "\n".join(lines[start:end]).strip()
        if not block:
            continue
        # Apply shared listing context only to supply-side segments. Never let an
        # "AVAILABLE FOR RENT" prefix contaminate a later buyer requirement.
        if marker_kinds[start] == "listing" and prefix:
            block = prefix + "\n" + block
        result.append(block)

    # When text precedes the first marker, preserve it as its own reviewable unit.
    # This matters when a message begins with prose and only later lists entries.
    if prefix and result:
        first_kind = marker_kinds[indexes[0]]
        if first_kind == "demand":
            result.insert(0, prefix)

    return result or [text]

def _find_price(text: str) -> float | None:
    """Extract a total asking price/rent, not a per-square-foot/yard rate."""
    unit_rate_re = re.compile(
        r"^\s*(?:(?:₹|rs\.?)\s*)?(?:/|-)?\s*(?:per\s*)?(?:sq\.?\s*(?:ft|feet|yd|yard)|sqft|sqrft|sqyd|square\s*(?:feet|yards)|var|vaar)\b",
        re.I,
    )

    def convert(raw: str, unit: str | None) -> float | None:
        try:
            amount = float(raw.replace(",", ""))
        except (TypeError, ValueError):
            return None
        unit = (unit or "").lower()
        if unit in {"crore", "crores", "cr"}:
            amount *= 10_000_000
        elif unit in {"lakh", "lakhs", "lac", "lacs", "l"}:
            amount *= 100_000
        elif unit in {"k", "thousand"}:
            amount *= 1_000
        return amount if amount > 0 else None

    patterns = [
        # Explicit asking/sale price is preferred over ancillary rent/yield.
        r"\b(?:asking\s+price|sale\s+price|sell\s+price|price)\s*[:=\-]?\s*(?:₹|INR\s*|Rs\.?\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k|thousand)?\b",
        r"\b(?:monthly\s+)?rent\s*[:=\-_]?\s*(?:₹|INR\s*|Rs\.?\s*)?([0-9][0-9,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k|thousand)?\b",
        r"(?:₹|\bINR\b|\bRs\.?\s*)\s*([0-9][0-9,]*(?:\.\d+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k|thousand)?\b",
        r"\b([0-9]+(?:\.[0-9]+)?)\s*(crores?|cr|lakhs?|lacs?|lac|l|k|thousand)\b",
        r"\b(?:rent|price|asking|budget)\s*[:=\-]?\s*([0-9][0-9,]{3,})\b",
        r"\b([0-9][0-9,]{3,})\s*/-\b",
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE):
            raw = match.group(1)
            unit = match.group(2) if len(match.groups()) > 1 else None
            # Unit rates are not comparable with a client's total budget.
            tail = text[match.end():match.end() + 45]
            # Never interpret a bedroom count immediately after "Rent" as the price.
            if re.match(r"\s*(?:bhk|b\.h\.k|bed(?:room)?s?)\b", tail, re.I):
                continue
            if unit_rate_re.match(tail):
                continue
            prefix = text[max(0, match.start() - 18):match.start()]
            if re.search(r"\brate\s*[:=]?\s*$", prefix, re.I) and re.search(r"\b(?:sq\.?\s*(?:ft|yd)|sqft|sqyd)\b", tail, re.I):
                continue
            amount = convert(raw, unit)
            if amount is not None:
                return amount
    return None


def parse_broker_post(raw_text: str) -> dict[str, Any]:
    """Extract conservative structured fields from a broker message."""
    text = (raw_text or "").strip()
    lower = re.sub(r"\s+", " ", text.lower())
    message_intent = classify_broker_message(text)
    result: dict[str, Any] = {
        "message_intent": message_intent,
        "transaction_type": None,
        "category": None,
        "property_type": None,
        "city": None,
        "locality": None,
        "price": _find_price(text),
        "configuration": None,
        "area_sqft": None,
        "furnishing": None,
        "parking": None,
        "amenities": [],
        "phone_numbers": [],
        "title": None,
        "confidence": 0,
        "extraction_notes": [],
    }

    # Keep demand and ambiguous messages out of the property-supply matching
    # pipeline. Their original text can still be retained for human review.
    if message_intent != "supply":
        result["price"] = None
        result["phone_numbers"] = list(dict.fromkeys(
            m.group(1) + m.group(2)
            for m in re.finditer(r"(?<!\d)(?:\+?91[ -]?)?([6-9]\d{4})[ -]?(\d{5})(?!\d)", text)
        ))
        if message_intent == "demand":
            result["extraction_notes"].append("This is a broker requirement/demand post, not an available property listing.")
        elif message_intent == "mixed":
            result["extraction_notes"].append("This message mixes property offers and requirements; manual separation is required before matching.")
        else:
            result["extraction_notes"].append("No clear property-offer signal was found; review the original message.")
        result["title"] = "Broker requirement — not property supply" if message_intent == "demand" else "Broker message — review required"
        return result

    rent_action = re.search(
        r"\b(?:for rent|on rent|to[- ]?let|exclusive rental|rental option|rent inventory|"
        r"rent\s*[:=_-]?\s*(?:₹|rs\.?\s*|[0-9]))", lower
    )
    sale_action = re.search(
        r"\b(?:for sale|on sale|sale price|asking price|sell price|resale|selling|sale in)\b", lower
    )
    preleased_sale = bool(re.search(r"\b(?:pre[- ]?leased|prelease|leased to|lease income)\b", lower) and sale_action)
    if rent_action and sale_action and not preleased_sale:
        result["message_intent"] = "mixed"
        result["transaction_type"] = None
        result["category"] = None
        result["property_type"] = None
        result["city"] = None
        result["locality"] = None
        result["price"] = None
        result["configuration"] = None
        result["area_sqft"] = None
        result["furnishing"] = None
        result["parking"] = None
        result["amenities"] = []
        result["confidence"] = 0
        result["extraction_notes"].append("The post mentions both sale and rental terms; confirm the transaction type before matching.")
        result["title"] = "Broker post — transaction type unclear"
        return result
    if preleased_sale or sale_action:
        result["transaction_type"] = "sale"
    elif rent_action or re.search(r"\b(rent|rental|to[- ]?let|lease|monthly rent|per month|pm)\b", lower):
        result["transaction_type"] = "rent"
    elif re.search(r"\b(for sale|sale|sell|selling|resale|asking price)\b", lower):
        result["transaction_type"] = "sale"

    for key, value in COMMERCIAL_TYPES.items():
        if re.search(rf"\b{re.escape(key)}\b", lower):
            result["category"], result["property_type"] = value
            break
    if result["property_type"] is None:
        for key, value in RESIDENTIAL_TYPES.items():
            if re.search(rf"\b{re.escape(key)}\b", lower):
                result["category"], result["property_type"] = value
                break
    if re.search(r"\bcommercial\b", lower) and re.search(r"\b(plot|land|plots)\b", lower):
        result["category"], result["property_type"] = "commercial", "plot"

    # BHK itself is strong evidence of residential supply.
    bhk = re.search(r"\b([1-6](?:\.5)?\+?)\s*(?:bhk|b\.h\.k\.?|bed(?:room)?s?)\b", lower)
    if bhk:
        result["configuration"] = f"{bhk.group(1)} BHK"
        result["category"] = result["category"] or "residential"
        result["property_type"] = result["property_type"] or "apartment"

    area = re.search(r"\b([0-9][0-9,]*(?:\.\d+)?)\s*(?:sq\.?\s*ft|sqft|sqrft|square feet)\b", lower)
    if area:
        result["area_sqft"] = float(area.group(1).replace(",", ""))
    else:
        area_yards = re.search(r"\b([0-9][0-9,]*(?:\.\d+)?)\s*(?:sq\.?\s*(?:yd|yard)s?|sqyd|square yards?|var|vaar)\b", lower)
        if area_yards:
            # Store a consistent square-foot equivalent for matching/display.
            result["area_sqft"] = float(area_yards.group(1).replace(",", "")) * 9

    if "semi furnished" in lower or "semi-furnished" in lower:
        result["furnishing"] = "semi-furnished"
    elif re.search(r"\bfurnished\b", lower):
        result["furnishing"] = "furnished"
    elif re.search(r"\bunfurnished\b", lower):
        result["furnishing"] = "unfurnished"

    if re.search(r"\b(no parking|without parking)\b", lower):
        result["parking"] = False
    elif re.search(r"\b(parking|car park|covered parking)\b", lower):
        result["parking"] = True

    amenity_terms = ["lift", "gym", "security", "swimming pool", "pool", "garden",
                     "power backup", "clubhouse", "visitor parking", "balcony"]
    result["amenities"] = [x for x in amenity_terms if x in lower]

    for locality in sorted(LOCALITIES, key=len, reverse=True):
        if re.search(rf"(?<![a-z]){re.escape(locality.lower())}(?![a-z])", lower):
            if locality.lower() in {"ahmedabad", "gandhinagar", "sanand"}:
                result["city"] = locality.title()
                result["locality"] = None
            else:
                result["locality"] = "SG Highway" if locality == "S G Highway" else locality
                result["city"] = "Ahmedabad"
            break

    phones = []
    for match in re.finditer(r"(?<!\d)(?:\+?91[ -]?)?([6-9]\d{4})[ -]?(\d{5})(?!\d)", text):
        phones.append(match.group(1) + match.group(2))
    result["phone_numbers"] = list(dict.fromkeys(phones))

    # Build a useful review label; this is not treated as a verified title.
    title_parts = []
    if result["configuration"]: title_parts.append(result["configuration"])
    if result["property_type"]: title_parts.append(result["property_type"].replace("_", " ").title())
    if result["locality"]: title_parts.extend(["in", result["locality"]])
    result["title"] = " ".join(title_parts) or "Broker property post — details to verify"

    checks = [
        result["transaction_type"] is not None,
        result["category"] is not None,
        result["property_type"] is not None,
        result["locality"] is not None,
        result["price"] is not None,
        result["configuration"] is not None or result["category"] == "commercial",
        result["area_sqft"] is not None,
    ]
    result["confidence"] = round(sum(checks) / len(checks) * 100)
    if result["transaction_type"] is None:
        result["extraction_notes"].append("Sale or rent is not clear from the message.")
    if result["price"] is None:
        result["extraction_notes"].append("Price is not clear; ask the source broker.")
    if result["locality"] is None:
        result["extraction_notes"].append("Locality is not recognised; review the original message.")
    if not result["property_type"]:
        result["extraction_notes"].append("Property type is not clear from the message.")
    return result


def split_whatsapp_export(text: str) -> list[dict[str, str]]:
    """Split common Android/iOS WhatsApp .txt export formats into messages."""
    patterns = [
        re.compile(r"^\u200e?(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)\s+-\s+(.*)$", re.I),
        re.compile(r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?\s?(?:AM|PM)?)\]\s+(.*)$", re.I),
    ]
    messages: list[dict[str, str]] = []
    current: dict[str, str] | None = None
    for line in (text or "").replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        match = next((p.match(line) for p in patterns if p.match(line)), None)
        if match:
            if current:
                current["text"] = current["text"].strip()
                if current["text"]: messages.append(current)
            date_text, time_text, tail = match.groups()
            sender, separator, body = tail.partition(": ")
            if not separator:
                sender, body = "", tail
            current = {"date": date_text, "time": time_text, "sender": sender.strip(), "text": body}
        elif current:
            current["text"] += "\n" + line
    if current:
        current["text"] = current["text"].strip()
        if current["text"]: messages.append(current)
    # Ignore WhatsApp's system-level encryption notice and empty records.
    return [m for m in messages if "messages and calls are end-to-end encrypted" not in m["text"].lower()]
