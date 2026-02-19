from app.services.distance_service import compute_travel_minutes, haversine_km


def test_haversine_zero_distance():
    assert haversine_km(44.0, -93.0, 44.0, -93.0) == 0


def test_compute_travel_minutes_monotonicity():
    walking, driving, fastest = compute_travel_minutes(2.0)
    assert walking > driving
    assert fastest == driving
