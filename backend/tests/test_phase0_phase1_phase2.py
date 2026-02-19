from app.phase0_identity_lock.policy import build_search_policy
from app.phase1_semantic_pipeline.embeddings import normalize_similarity_to_score
from app.phase2_transparency_ux.accessibility import haversine_km


def test_local_first_default_policy():
    policy = build_search_policy(
        include_chains=None,
        open_now=False,
        walking_distance=False,
        walking_threshold_minutes=None,
    )
    assert policy.include_chains is False


def test_similarity_score_range():
    assert normalize_similarity_to_score(-1.0) == 0
    assert normalize_similarity_to_score(1.0) == 100


def test_haversine_distance_positive():
    distance = haversine_km(44.9778, -93.265, 44.98, -93.26)
    assert distance > 0
