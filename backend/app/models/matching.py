from pydantic import BaseModel, Field


class ChallengeAnalysisRequest(BaseModel):
    title: str = Field(min_length=5, max_length=160)
    description: str = Field(min_length=20, max_length=10000)
    expected_outcome: str | None = Field(default=None, max_length=3000)
    required_skills: list[str] = Field(default_factory=list, max_length=50)


class ChallengeAnalysisResponse(BaseModel):
    title: str
    category: str
    domain: str
    required_skills: list[str]
    keywords: list[str]
    difficulty: str
    summary: str


class StudentMatchesRequest(ChallengeAnalysisRequest):
    limit: int = Field(default=20, ge=1, le=100)


class StudentMatch(BaseModel):
    student_id: str
    student_name: str
    match_percentage: int = Field(ge=0, le=100)
    matched_skills: list[str]
    missing_skills: list[str]
    domain_similarity: int = Field(ge=0, le=100)
    explanation: str


class StudentMatchesResponse(BaseModel):
    challenge_analysis: ChallengeAnalysisResponse
    matches: list[StudentMatch]