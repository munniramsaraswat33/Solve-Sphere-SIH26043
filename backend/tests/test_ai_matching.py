import app
import os
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

import app
from ai.embeddings import cosine_similarity
from ai.matching_model import analyze_challenge, rank_students
from app.main import app as api_app
from app.models.auth import UserResponse, UserRole
from app.routes import matching as matching_routes
from app.utils.auth_dependencies import get_current_user


STUDENTS = [
    {
        "_id": "student-city",
        "name": "Aarav Sharma",
        "profile": {
            "skills": ["Python", "ML", "Data Analysis"],
            "interests": ["Smart city", "Traffic"],
            "experience": "Built a traffic forecasting project for urban mobility.",
            "college": "City Engineering College",
        },
    },
    {
        "_id": "student-environment",
        "name": "Meera Patel",
        "profile": {
            "skills": ["IoT", "GIS", "Optimization"],
            "interests": ["Environment", "Waste management"],
            "experience": "Designed an IoT route optimization prototype for waste collection.",
            "college": "Green Valley University",
        },
    },
    {
        "_id": "student-health",
        "name": "Fatima Khan",
        "profile": {
            "skills": ["Python", "Data Analysis"],
            "interests": ["Public health", "Healthcare"],
            "experience": "Analyzed patient records for a community clinic project.",
            "college": "North Medical Institute",
        },
    },
]

CHALLENGES = [
    {
        "title": "Urban Traffic Flow Prediction",
        "description": "Predict traffic congestion using city transport data and improve urban mobility.",
        "expected_outcome": "A traffic forecasting dashboard for city planners.",
        "required_skills": ["Python", "Machine Learning", "Data Analysis"],
    },
    {
        "title": "Smart Waste Collection",
        "description": "Use connected sensors and route optimization to improve waste collection and recycling.",
        "expected_outcome": "A map of efficient municipal waste collection routes.",
        "required_skills": ["IoT", "GIS", "Optimization"],
    },
]


def semantic_fixture_encoder(texts: list[str]) -> list[list[float]]:
    vectors = []
    for text in texts:
        normalized = text.lower()
        vectors.append(
            [
                float(any(term in normalized for term in ("traffic", "congestion", "urban", "mobility", "transport"))),
                float(any(term in normalized for term in ("waste", "environment", "recycling", "collection", "route"))),
                float(any(term in normalized for term in ("health", "clinic", "patient", "medical"))),
                float(any(term in normalized for term in ("python", "machine learning", " ml ", "data analysis", "iot", "gis", "optimization", "sensor"))),
            ]
        )
    return vectors


def test_challenge_analysis_extracts_domain_skills_keywords_and_summary() -> None:
    analysis = analyze_challenge(
        title="Urban Traffic Flow Prediction",
        description="Predict traffic congestion using Python, machine learning, and city transport data.",
        expected_outcome="A mobility dashboard for traffic planners.",
    )

    assert analysis["category"] == "Smart City"
    assert analysis["domain"] == "Urban infrastructure and mobility"
    assert {"Python", "Machine Learning"}.issubset(analysis["required_skills"])
    assert "traffic" in analysis["keywords"]
    assert analysis["difficulty"] in {"Beginner", "Intermediate", "Advanced"}
    assert analysis["summary"].startswith("Predict traffic congestion")


def test_matching_ranks_three_students_for_two_different_challenges() -> None:
    city_analysis = analyze_challenge(**CHALLENGES[0])
    environment_analysis = analyze_challenge(**CHALLENGES[1])

    city_matches = rank_students(city_analysis | CHALLENGES[0], STUDENTS, embedding_encoder=semantic_fixture_encoder)
    environment_matches = rank_students(
        environment_analysis | CHALLENGES[1],
        STUDENTS,
        embedding_encoder=semantic_fixture_encoder,
    )

    assert len(city_matches) == 3
    assert len(environment_matches) == 3
    assert city_matches[0]["student_name"] == "Aarav Sharma"
    assert environment_matches[0]["student_name"] == "Meera Patel"
    assert city_matches[0]["match_percentage"] > city_matches[-1]["match_percentage"]
    assert environment_matches[0]["match_percentage"] > environment_matches[-1]["match_percentage"]
    assert city_matches[0]["matched_skills"] == ["Python", "Machine Learning", "Data Analysis"]
    assert environment_matches[0]["missing_skills"] == []
    assert 0 <= city_matches[0]["domain_similarity"] <= 100
    assert "matches 3 of 3 required skills" in city_matches[0]["explanation"]


def test_cosine_similarity_uses_vector_direction() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_missing_student_interests_are_not_inferred_from_other_profile_data() -> None:
    student_without_interests = {
        "_id": "student-no-interests",
        "name": "Rohan Das",
        "profile": {"skills": ["Python"], "interests": [], "experience": "Built a city traffic analysis tool."},
    }
    challenge = analyze_challenge(**CHALLENGES[0]) | CHALLENGES[0]

    match = rank_students(
        challenge,
        [student_without_interests],
        embedding_encoder=semantic_fixture_encoder,
    )[0]

    assert match["domain_similarity"] == 0
    assert "no interests are recorded" in match["explanation"]


@pytest.mark.skipif(
    os.getenv("SOLVE_SPHERE_REAL_EMBEDDINGS") != "1",
    reason="Set SOLVE_SPHERE_REAL_EMBEDDINGS=1 to run the downloaded model integration test",
)
def test_real_sentence_transformer_ranks_three_students_for_two_challenges() -> None:
    ranked_names = []
    for challenge_request in CHALLENGES:
        analysis = analyze_challenge(**challenge_request)
        matches = rank_students(analysis | challenge_request, STUDENTS)
        ranked_names.append(matches[0]["student_name"])
        assert len(matches) == 3
        assert all("aligns" in match["explanation"] for match in matches)

    assert ranked_names == ["Aarav Sharma", "Meera Patel"]


@pytest.fixture(autouse=True)
def clear_auth_overrides():
    api_app.dependency_overrides.clear()
    yield
    api_app.dependency_overrides.clear()


def test_challenge_analysis_api_returns_extracted_fields() -> None:
    api_app.dependency_overrides[get_current_user] = lambda: UserResponse(
        id="owner-id",
        name="City Office",
        email="owner@example.com",
        role=UserRole.PROBLEM_OWNER,
        created_at=datetime.now(timezone.utc),
    )

    with TestClient(api_app) as client:
        response = client.post(
            "/api/matching/analyze",
            json={
                "title": "Urban Traffic Flow Prediction",
                "description": "Predict traffic congestion using Python and machine learning for city roads.",
                "required_skills": [],
            },
        )

    assert response.status_code == 200
    assert response.json()["category"] == "Smart City"
    assert response.json()["domain"] == "Urban infrastructure and mobility"
    assert "Machine Learning" in response.json()["required_skills"]


def test_student_matching_api_returns_explainable_results(monkeypatch) -> None:
    api_app.dependency_overrides[get_current_user] = lambda: UserResponse(
        id="owner-id",
        name="City Office",
        email="owner@example.com",
        role=UserRole.PROBLEM_OWNER,
        created_at=datetime.now(timezone.utc),
    )
    expected_match = {
        "student_id": "student-city",
        "student_name": "Aarav Sharma",
        "match_percentage": 91,
        "matched_skills": ["Python", "Machine Learning"],
        "missing_skills": ["Data Analysis"],
        "domain_similarity": 86,
        "explanation": "Profile meaning aligns 90% with the challenge; matches 2 of 3 required skills; domain/interests align 86%; experience aligns 80%.",
    }
    match_mock = AsyncMock(return_value=[expected_match])
    monkeypatch.setattr(matching_routes, "match_challenge_to_students", match_mock)

    with TestClient(api_app) as client:
        response = client.post(
            "/api/matching/students",
            json={
                "title": "Urban Traffic Flow Prediction",
                "description": "Predict traffic congestion using Python and machine learning for city roads.",
                "required_skills": ["Python", "Machine Learning", "Data Analysis"],
                "limit": 10,
            },
        )

    assert response.status_code == 200
    assert response.json()["challenge_analysis"]["category"] == "Smart City"
    assert response.json()["matches"][0] == expected_match
    assert match_mock.await_args.args[1] == 10
