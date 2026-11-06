from types import SimpleNamespace
from app.matching import calculate_match


def req(**overrides):
    values = dict(transaction_type="sale", category="residential", property_type="apartment",
                  preferred_locations=["South Bopal"], min_budget=6_000_000, max_budget=7_500_000,
                  stretch_budget=8_000_000, configuration="3 BHK", min_area_sqft=None,
                  max_area_sqft=None, furnishing=None, parking_required=None, amenities=[],
                  strict_location=False, strict_configuration=False)
    values.update(overrides)
    return SimpleNamespace(**values)


def prop(**overrides):
    values = dict(status="available", transaction_type="sale", category="residential",
                  property_type="apartment", locality="South Bopal", city="Ahmedabad",
                  price=7_200_000, bhk="3 BHK", area_sqft=1600, furnishing=None,
                  parking=True, amenities=[])
    values.update(overrides)
    return SimpleNamespace(**values)


def test_exact_match_is_high_score():
    result = calculate_match(req(), prop())
    assert result is not None
    assert result[0] == 100
    assert "Preferred location matches" in result[1]


def test_strict_location_excludes_other_locality():
    assert calculate_match(req(strict_location=True), prop(locality="Maninagar")) is None


def test_budget_above_stretch_excluded():
    assert calculate_match(req(), prop(price=8_500_000)) is None


def test_unavailable_property_excluded():
    assert calculate_match(req(), prop(status="sold")) is None


def test_unknown_preferences_do_not_reduce_score():
    sparse = req(preferred_locations=[], min_budget=None, max_budget=None, stretch_budget=None,
                 configuration=None, property_type=None)
    result = calculate_match(sparse, prop())
    assert result == (50, ["Not enough preferences supplied to score reliably; review manually"])
