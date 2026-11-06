from app.broker_feed import (
    classify_broker_message,
    parse_broker_post,
    split_property_entries,
)


def test_requirement_post_is_not_property_supply():
    raw = (
        "URGENT REQUIREMENT – 3 BHK ON RENT\n"
        "Preferred Areas: Science City | Thaltej | Sola\n"
        "Budget: ₹40K – ₹55K\nFor family"
    )
    parsed = parse_broker_post(raw)
    assert classify_broker_message(raw) == "demand"
    assert parsed["message_intent"] == "demand"
    assert parsed["transaction_type"] is None
    assert parsed["price"] is None
    assert parsed["configuration"] is None


def test_property_offer_is_supply_and_extracts_fields():
    raw = (
        "3BHK FLAT FOR RENT\nFULLY FURNISHED\n"
        "LOCATION: JODHPUR NEAR STAR BAZAR\nRENT: 35K"
    )
    parsed = parse_broker_post(raw)
    assert parsed["message_intent"] == "supply"
    assert parsed["transaction_type"] == "rent"
    assert parsed["configuration"] == "3 BHK"
    assert parsed["price"] == 35000
    assert parsed["locality"] == "Jodhpur"


def test_mixed_supply_and_requirement_is_review_only():
    raw = (
        "AVAILABLE FOR RENT\n"
        "3 BHK flat in Satellite, rent 35k\n\n"
        "URGENT REQUIREMENT ON RENT\n"
        "2 BHK in Shela, budget 25k"
    )
    assert classify_broker_message(raw) == "mixed"
    parsed = parse_broker_post(raw)
    assert parsed["message_intent"] == "mixed"
    assert parsed["transaction_type"] is None


def test_numbered_multi_property_inventory_splits_into_entries():
    raw = (
        "EXCLUSIVE RENTAL OPTION\n\n"
        "1) South Bopal\n3 BHK furnished bungalow\nRent: 40k\n\n"
        "2) Bodakdev\n4 BHK semi furnished bungalow\nRent: 70k\n\n"
        "3) Science City\n4 BHK furnished bungalow\nRent: 70k"
    )
    entries = split_property_entries(raw)
    assert len(entries) == 3
    parsed = [parse_broker_post(entry) for entry in entries]
    assert all(p["message_intent"] == "supply" for p in parsed)
    assert [p["locality"] for p in parsed] == ["South Bopal", "Bodakdev", "Science City"]
    assert [p["price"] for p in parsed] == [40000, 70000, 70000]


def test_sparkle_inventory_splits_and_supports_half_bhk():
    raw = (
        "EXCLUSIVE FLATS AVAILABLE ON SALE — SATELLITE\n"
        "✨ Ratnaakar 3\n3 BHK | Fully Furnished\n2610 Sq.Ft.\nPrice: 3.25 Cr.\n\n"
        "✨ 3rd Eye Blessing\n2.5 BHK | Furnished\n1700 Sq.Ft.\nPrice: 1.15 Cr."
    )
    entries = split_property_entries(raw)
    assert len(entries) == 2
    parsed = [parse_broker_post(entry) for entry in entries]
    assert parsed[1]["configuration"] == "2.5 BHK"
    assert parsed[1]["price"] == 11_500_000


def test_sale_or_rent_ambiguous_listing_is_not_auto_matched():
    parsed = parse_broker_post(
        "Exclusive bungalow for sale / rent in South Bopal, 4 BHK, price 3.5 Cr / rent 70k"
    )
    assert parsed["message_intent"] == "mixed"
    assert parsed["transaction_type"] is None
    assert parsed["price"] is None


def test_per_square_foot_rent_is_not_treated_as_monthly_rent():
    parsed = parse_broker_post(
        "3550 Sqft Office on Rent. Rent: 45 rs per sqft."
    )
    assert parsed["transaction_type"] == "rent"
    assert parsed["area_sqft"] == 3550
    assert parsed["price"] is None


def test_mixed_bulk_message_splits_supply_from_requirement_section():
    raw = """AVAILABLE FOR RENT
👉 2 BHK Flat on Rent Fully Furnished
🔹 35000
🔹 Only Family
🔹 Satellite

👉 3 BHK Bungalow on Rent
📍 Thaltej
Rent 80000

🔺 Urgent Requirement On Rent
3 BHK Flat
Budget 60000
Preferred Area Prahladnagar
"""
    entries = split_property_entries(raw)
    assert len(entries) == 3
    parsed = [parse_broker_post(entry) for entry in entries]
    assert [item["message_intent"] for item in parsed] == ["supply", "supply", "demand"]
    assert all(item["transaction_type"] == "rent" for item in parsed[:2])
    assert parsed[2]["transaction_type"] is None


def test_urgent_require_typo_and_riq_heading_are_demand():
    assert classify_broker_message("Urgent Require on Rent 3 BHK flat") == "demand"
    assert classify_broker_message("RIQ ON RENT SHOP Gurukul") == "demand"


def test_diamond_detail_bullets_do_not_become_fake_property_segments():
    raw = """AVAILABLE FOR RENT
👉 3 BHK Flat on Rent
🔹 Fully Furnished
🔹 35000
🔹 Only Family
🔹 Satellite
"""
    entries = split_property_entries(raw)
    assert len(entries) == 1
    parsed = parse_broker_post(entries[0])
    assert parsed["message_intent"] == "supply"
    assert parsed["configuration"] == "3 BHK"
