from datetime import datetime, timezone
from sqlalchemy.orm import Session, joinedload
from .models import Lead, Requirement, Property, Match


def _num(v):
    return float(v) if v is not None else None


def _normalise_property_type(value: str | None) -> str | None:
    if not value:
        return None
    key = " ".join(value.strip().lower().replace("_", " ").split())
    aliases = {
        "flat": "apartment", "flats": "apartment", "residential flat": "apartment",
        "office space": "office", "offices": "office", "shop/showroom": "shop",
        "showroom": "showroom", "row house": "row house", "rowhouse": "row house",
        "villa": "villa", "bungalow": "bungalow", "penthouse": "penthouse",
    }
    return aliases.get(key, key)


def calculate_match(req: Requirement, prop: Property) -> tuple[int, list[str]] | None:
    """Return an explainable 0-100 score, or None for a hard-filter failure.

    Unknown listing fields are scored as *unverified evidence* rather than omitted
    from the denominator. This avoids a sparse broker message receiving an inflated
    100/100 just because only one field happened to be extracted.
    """
    if getattr(prop, "status", "available") != "available":
        return None
    if prop.transaction_type != req.transaction_type:
        return None

    prop_category = getattr(prop, "category", None)
    if prop_category and req.category and prop_category != req.category:
        return None

    wanted_type = _normalise_property_type(getattr(req, "property_type", None))
    actual_type = _normalise_property_type(getattr(prop, "property_type", None))
    if wanted_type and wanted_type not in ("any", "all") and actual_type and wanted_type != actual_type:
        return None

    earned = 0.0
    possible = 0.0
    reasons: list[str] = []

    def add(weight: float, fraction: float, reason: str):
        nonlocal earned, possible
        earned += weight * max(0.0, min(1.0, fraction))
        possible += weight
        reasons.append(reason)

    # Weights total 100 across all specified requirements. Missing candidate data
    # earns zero for that dimension and is clearly called out in the explanation.
    desired = [str(x).strip().lower() for x in (req.preferred_locations or []) if str(x).strip()]
    actual_location = " ".join(str(x) for x in [getattr(prop, "locality", None), getattr(prop, "city", None)] if x).lower()
    if desired:
        location_hit = bool(actual_location) and any(d in actual_location or actual_location in d for d in desired)
        if req.strict_location and not location_hit:
            return None
        fraction = 1.0 if location_hit else (0.25 if actual_location else 0.0)
        explanation = "Preferred location matches" if location_hit else ("Different locality; review distance" if actual_location else "Location not stated in broker post")
        add(25, fraction, explanation)

    low, high, stretch = _num(req.min_budget), _num(req.max_budget), _num(req.stretch_budget)
    price = _num(getattr(prop, "price", None))
    if low is not None or high is not None or stretch is not None:
        if price is None:
            add(25, 0.0, "Price not stated; confirm with source broker")
        elif high is not None and price > high:
            if stretch is not None and price <= stretch:
                add(25, 0.55, "Above target budget but within stretch budget")
            else:
                return None
        elif (low is None or price >= low) and (high is None or price <= high):
            add(25, 1.0, "Price is within budget")
        else:
            add(25, 0.82, "Price is below the stated minimum budget")

    if req.configuration:
        wanted_config = " ".join(str(req.configuration).lower().split()).replace("bhk", " bhk").strip()
        actual_config = " ".join(str(getattr(prop, "bhk", None) or "").lower().split()).replace("bhk", " bhk").strip()
        if not actual_config:
            if req.strict_configuration:
                return None
            add(20, 0.0, "Configuration not stated in broker post")
        elif wanted_config == actual_config:
            add(20, 1.0, "Configuration matches")
        elif req.strict_configuration:
            return None
        else:
            add(20, 0.25, "Configuration differs; review manually")

    if req.property_type and str(req.property_type).lower() not in ("any", "all"):
        if not actual_type:
            add(8, 0.0, "Property type not stated in broker post")
        else:
            add(8, 1.0, "Property type matches")

    min_area, max_area = _num(req.min_area_sqft), _num(req.max_area_sqft)
    if min_area is not None or max_area is not None:
        area = _num(getattr(prop, "area_sqft", None))
        if area is None:
            add(10, 0.0, "Area not stated in broker post")
        elif (min_area is None or area >= min_area) and (max_area is None or area <= max_area):
            add(10, 1.0, "Area is within requested range")
        else:
            bound = min_area if min_area is not None and area < min_area else max_area
            deviation = abs(area - bound) / max(bound, 1)
            add(10, 0.65 if deviation <= 0.10 else 0.25,
                "Area is close to requested range" if deviation <= 0.10 else "Area differs from requested range")

    if req.furnishing:
        actual_furnishing = getattr(prop, "furnishing", None)
        if not actual_furnishing:
            add(4, 0.0, "Furnishing not stated in broker post")
        else:
            same = str(req.furnishing).lower() == str(actual_furnishing).lower()
            add(4, 1.0 if same else 0.35, "Furnishing matches" if same else "Furnishing differs")

    if req.parking_required is True:
        parking = getattr(prop, "parking", None)
        if parking is None:
            add(4, 0.0, "Parking availability not stated")
        else:
            add(4, 1.0 if parking else 0.0, "Parking available" if parking else "Parking requirement not met")

    wanted_amenities = {str(x).strip().lower() for x in (req.amenities or []) if str(x).strip()}
    if wanted_amenities:
        available_amenities = {str(x).strip().lower() for x in (getattr(prop, "amenities", None) or []) if str(x).strip()}
        overlap = len(wanted_amenities & available_amenities)
        add(4, overlap / len(wanted_amenities), f"{overlap} of {len(wanted_amenities)} requested amenities listed")

    if not prop_category:
        reasons.append("Property category not clear; verify manually")
    if possible == 0:
        return 50, ["Not enough preferences supplied to score reliably; review manually", *reasons]
    return min(100, max(0, int(round(earned / possible * 100)))), reasons


def refresh_matches(db: Session, lead_id: int) -> list[Match]:
    lead = db.query(Lead).options(joinedload(Lead.requirement)).filter(Lead.id == lead_id).first()
    if not lead or not lead.requirement:
        return []
    req = lead.requirement
    props = db.query(Property).filter(
        Property.status == "available",
        Property.transaction_type == req.transaction_type,
        Property.category == req.category,
    ).all()
    seen = set()
    for prop in props:
        result = calculate_match(req, prop)
        if result is None:
            continue
        score, reasons = result
        match = db.query(Match).filter_by(requirement_id=req.id, property_id=prop.id).first()
        if match is None:
            match = Match(requirement_id=req.id, property_id=prop.id, score=score, reasons=reasons, status="new")
            db.add(match)
        else:
            match.score = score
            match.reasons = reasons
            match.calculated_at = datetime.now(timezone.utc)
        seen.add(prop.id)
    db.flush()
    results = db.query(Match).options(joinedload(Match.property)).filter(Match.requirement_id == req.id).all()
    return sorted([m for m in results if m.property and m.property.status == "available"], key=lambda m: m.score, reverse=True)


def refresh_matches_for_property(db: Session, property_id: int) -> list[Match]:
    """Reverse matching: a new/updated listing discovers existing client demand."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop or prop.status != "available":
        return []
    requirements = db.query(Requirement).join(Lead).filter(
        Lead.status.notin_(["converted", "lost"]),
        Requirement.transaction_type == prop.transaction_type,
        Requirement.category == prop.category,
    ).all()
    for req in requirements:
        result = calculate_match(req, prop)
        if result is None:
            continue
        score, reasons = result
        match = db.query(Match).filter_by(requirement_id=req.id, property_id=prop.id).first()
        if match is None:
            match = Match(requirement_id=req.id, property_id=prop.id, score=score, reasons=reasons, status="new")
            db.add(match)
        else:
            match.score = score
            match.reasons = reasons
            match.calculated_at = datetime.now(timezone.utc)
    db.flush()
    return db.query(Match).filter(Match.property_id == prop.id).order_by(Match.score.desc()).all()
