from types import SimpleNamespace

from app.broker_feed import parse_broker_post, split_whatsapp_export
from app.matching import calculate_match


def requirement(**overrides):
    values = dict(
        transaction_type="rent", category="residential", property_type="apartment",
        preferred_locations=["South Bopal"], min_budget=25000, max_budget=35000,
        stretch_budget=None, configuration="3 BHK", min_area_sqft=None,
        max_area_sqft=None, furnishing=None, parking_required=None, amenities=[],
        strict_location=True, strict_configuration=True,
    )
    values.update(overrides)
    return SimpleNamespace(**values)


def candidate(parsed):
    return SimpleNamespace(
        status="available", transaction_type=parsed["transaction_type"],
        category=parsed["category"], property_type=parsed["property_type"],
        locality=parsed["locality"], city=parsed["city"], price=parsed["price"],
        bhk=parsed["configuration"], area_sqft=parsed["area_sqft"],
        furnishing=parsed["furnishing"], parking=parsed["parking"],
        amenities=parsed["amenities"],
    )


def test_extracts_common_ahmedabad_rental_post():
    text = "FOR RENT 3 BHK flat in South Bopal. Rent ₹32,000 per month. 1650 sqft. Parking available."
    parsed = parse_broker_post(text)
    assert parsed["transaction_type"] == "rent"
    assert parsed["category"] == "residential"
    assert parsed["property_type"] == "apartment"
    assert parsed["locality"] == "South Bopal"
    assert parsed["price"] == 32000
    assert parsed["configuration"] == "3 BHK"
    assert parsed["area_sqft"] == 1650
    assert parsed["parking"] is True
    assert parsed["confidence"] >= 85


def test_extracts_sale_price_in_lakhs_and_commercial_office():
    parsed = parse_broker_post("Commercial office for sale on SG Highway, 1200 sq ft, price 1.25 Cr")
    assert parsed["transaction_type"] == "sale"
    assert parsed["category"] == "commercial"
    assert parsed["property_type"] == "office"
    assert parsed["price"] == 12_500_000
    assert parsed["area_sqft"] == 1200


def test_unknown_details_are_not_invented():
    parsed = parse_broker_post("Available property, contact 9876543210")
    assert parsed["transaction_type"] is None
    assert parsed["price"] is None
    assert parsed["locality"] is None
    assert parsed["configuration"] is None


def test_feed_candidate_matches_manual_lead_requirements():
    parsed = parse_broker_post("FOR RENT 3 BHK flat in South Bopal. Rent ₹32,000 per month. 1650 sqft.")
    result = calculate_match(requirement(), candidate(parsed))
    assert result is not None
    assert result[0] == 100
    assert "Price is within budget" in result[1]


def test_strict_requirement_rejects_candidate_without_location():
    parsed = parse_broker_post("FOR RENT 3 BHK flat. Rent ₹32,000 per month.")
    assert calculate_match(requirement(), candidate(parsed)) is None


def test_whatsapp_export_splits_multiline_messages_and_senders():
    export = (
        "05/11/26, 10:35 am - Rahul Broker: FOR RENT 3 BHK flat in South Bopal\n"
        "Rent ₹32,000 per month\n1650 sqft\n"
        "05/11/26, 10:36 am - Neha: hello everyone\n"
    )
    rows = split_whatsapp_export(export)
    assert len(rows) == 2
    assert rows[0]["sender"] == "Rahul Broker"
    assert "1650 sqft" in rows[0]["text"]
    assert rows[1]["sender"] == "Neha"


def test_sparse_broker_message_does_not_receive_inflated_match_score():
    parsed = parse_broker_post("For rent, rent 32k per month")
    req = requirement(strict_location=False, strict_configuration=False)
    result = calculate_match(req, candidate(parsed))
    assert result is not None
    assert result[0] < 50
    assert "Location not stated in broker post" in result[1]
    assert "Configuration not stated in broker post" in result[1]


def test_extracts_compact_hinglish_style_listing_and_lakh_price():
    parsed = parse_broker_post("2BHK flat on rent at Satellite Ahmedabad 32k pm, 1100 sqft")
    assert parsed["transaction_type"] == "rent"
    assert parsed["configuration"] == "2 BHK"
    assert parsed["locality"] == "Satellite"
    assert parsed["price"] == 32000
    assert parsed["area_sqft"] == 1100


def test_photo_only_export_message_is_splittable():
    export = "05/11/26, 11:15 am - Broker: IMG-20261105-WA0001.jpg (file attached)\n"
    rows = split_whatsapp_export(export)
    assert len(rows) == 1
    assert "IMG-20261105-WA0001.jpg" in rows[0]["text"]


def test_extracts_indian_phone_with_space_separator():
    parsed = parse_broker_post("For rent 2 BHK flat Satellite 30k. Call 98765 43210")
    assert parsed["phone_numbers"] == ["9876543210"]
