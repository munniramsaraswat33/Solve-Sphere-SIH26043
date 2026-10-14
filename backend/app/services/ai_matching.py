from typing import Any

from pymongo.errors import PyMongoError
from starlette.concurrency import run_in_threadpool

from ai.embeddings import EmbeddingModelError
from ai.matching_model import analyze_challenge, rank_students
from app.database.client import MongoDBNotConfigured, get_database
from app.models.matching import ChallengeAnalysisRequest


class StudentDirectoryUnavailable(RuntimeError):
    """Raised when the student directory cannot be queried."""


def analyze_challenge_request(request: ChallengeAnalysisRequest) -> dict[str, Any]:
    return analyze_challenge(
        title=request.title,
        description=request.description,
        expected_outcome=request.expected_outcome,
        required_skills=request.required_skills,
    )


async def match_challenge_to_students(
    challenge: dict[str, Any],
    limit: int,
) -> list[dict[str, Any]]:
    try:
        cursor = get_database()["users"].find(
            {"role": "student", "is_active": True},
            {"name": 1, "profile": 1},
        ).limit(limit)
        students = await cursor.to_list(length=limit)
    except (MongoDBNotConfigured, PyMongoError) as error:
        raise StudentDirectoryUnavailable from error

    return await run_in_threadpool(rank_students, challenge, students)


__all__ = ["EmbeddingModelError", "analyze_challenge_request", "match_challenge_to_students"]