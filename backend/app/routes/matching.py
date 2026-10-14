from fastapi import APIRouter, Depends, HTTPException
from pymongo.errors import PyMongoError

from ai.embeddings import EmbeddingModelError
from ai.matching_model import analyze_challenge
from app.database.client import MongoDBNotConfigured
from app.models.auth import UserResponse
from app.models.matching import (
    ChallengeAnalysisRequest,
    ChallengeAnalysisResponse,
    StudentMatchesRequest,
    StudentMatchesResponse,
)
from app.services.ai_matching import StudentDirectoryUnavailable, match_challenge_to_students
from app.utils.auth_dependencies import get_current_user

router = APIRouter(prefix="/matching", tags=["AI matching"])


@router.post("/analyze", response_model=ChallengeAnalysisResponse)
async def analyze_challenge_endpoint(
    request: ChallengeAnalysisRequest,
    _: UserResponse = Depends(get_current_user),
) -> ChallengeAnalysisResponse:
    return ChallengeAnalysisResponse(**analyze_challenge(
        title=request.title,
        description=request.description,
        expected_outcome=request.expected_outcome,
        required_skills=request.required_skills,
    ))


@router.post("/students", response_model=StudentMatchesResponse)
async def match_students_endpoint(
    request: StudentMatchesRequest,
    _: UserResponse = Depends(get_current_user),
) -> StudentMatchesResponse:
    analysis = analyze_challenge(
        title=request.title,
        description=request.description,
        expected_outcome=request.expected_outcome,
        required_skills=request.required_skills,
    )
    challenge = {
        **analysis,
        "description": request.description,
        "expected_outcome": request.expected_outcome,
    }
    try:
        matches = await match_challenge_to_students(challenge, request.limit)
    except StudentDirectoryUnavailable as error:
        raise HTTPException(status_code=503, detail="Student directory is not available") from error
    except EmbeddingModelError as error:
        raise HTTPException(status_code=503, detail="AI embedding model is not available") from error
    except PyMongoError as error:
        raise HTTPException(status_code=503, detail="Student directory is not available") from error
    except MongoDBNotConfigured as error:
        raise HTTPException(status_code=503, detail="Student directory is not available") from error

    return StudentMatchesResponse(challenge_analysis=analysis, matches=matches)