import re
from collections import Counter
from collections.abc import Callable
from typing import Any

from ai.embeddings import cosine_similarity, encode_texts

CATEGORY_TERMS: dict[str, tuple[str, ...]] = {
    "Smart City": ("traffic", "transport", "road", "urban", "mobility", "congestion", "city", "public service"),
    "Environment": ("environment", "waste", "recycling", "water", "pollution", "climate", "energy", "conservation"),
    "Education": ("education", "student", "school", "learning", "teacher", "classroom", "literacy", "curriculum"),
    "Healthcare": ("health", "hospital", "patient", "medical", "diagnosis", "clinic", "disease", "wellness"),
    "Agriculture": ("agriculture", "crop", "farm", "farmer", "soil", "irrigation", "livestock", "harvest"),
    "Governance": ("government", "governance", "citizen", "public service", "municipal", "beneficiary", "civic"),
}

DOMAIN_BY_CATEGORY = {
    "Smart City": "Urban infrastructure and mobility",
    "Environment": "Environmental sustainability",
    "Education": "Education and learning",
    "Healthcare": "Healthcare and public health",
    "Agriculture": "Agriculture and food systems",
    "Governance": "Public services and governance",
    "Other": "Cross-domain social innovation",
}

SKILL_TERMS = {
    "Python": ("python",),
    "JavaScript": ("javascript", " js "),
    "React": ("react",),
    "Machine Learning": ("machine learning", " ml ", "deep learning"),
    "Natural Language Processing": ("natural language processing", "nlp", "text classification"),
    "Computer Vision": ("computer vision", "image recognition", "object detection"),
    "Data Analysis": ("data analysis", "data analytics", "analytics", "data visualization"),
    "SQL": ("sql", "database query"),
    "IoT": ("iot", "internet of things", "sensor network", "sensors"),
    "GIS": ("gis", "geospatial", "geographic information", "mapping"),
    "Optimization": ("optimization", "optimisation", "route planning"),
    "Cloud Computing": ("cloud", "aws", "azure", "gcp"),
    "UI/UX": ("ui/ux", "user experience", "user interface", "accessibility", "usability"),
    "Mobile Development": ("mobile app", "android", "ios application"),
    "Cybersecurity": ("cybersecurity", "cyber security", "encryption", "security audit"),
    "API Development": ("api", "rest api", "web service"),
}

SKILL_ALIASES = {
    "ml": "machine learning",
    "deep learning": "machine learning",
    "ai": "machine learning",
    "data analytics": "data analysis",
    "analytics": "data analysis",
    "js": "javascript",
    "reactjs": "react",
    "internet of things": "iot",
    "user experience": "ui ux",
    "user interface": "ui ux",
    "ui ux": "ui ux",
    "computer vision": "computer vision",
}

STOP_WORDS = {
    "about", "across", "after", "also", "among", "and", "are", "been", "being", "between",
    "build", "can", "could", "develop", "for", "from", "have", "into", "into", "its", "make",
    "need", "our", "should", "solution", "solutions", "such", "that", "their", "them", "there",
    "this", "through", "using", "which", "with", "will", "would", "your", "the", "a", "an", "to", "of", "in", "on", "is", "by", "as", "or",
}


def _normalized_text(text: str) -> str:
    return f" {re.sub(r'[^a-z0-9]+', ' ', text.lower()).strip()} "


def _extract_keywords(text: str, limit: int = 10) -> list[str]:
    words = [word for word in re.findall(r"[a-zA-Z][a-zA-Z0-9+#.-]{2,}", text.lower()) if word not in STOP_WORDS]
    counts = Counter(words)
    first_position = {word: words.index(word) for word in counts}
    return sorted(counts, key=lambda word: (-counts[word], first_position[word]))[:limit]


def _extract_skills(text: str) -> list[str]:
    normalized = _normalized_text(text)
    found = []
    for skill, terms in SKILL_TERMS.items():
        if any(_normalized_text(term) in normalized for term in terms):
            found.append(skill)
    return found


def _summarize(text: str, word_limit: int = 42) -> str:
    words = text.split()
    if len(words) <= word_limit:
        return text
    return f"{' '.join(words[:word_limit]).rstrip('.,;:')}..."


def analyze_challenge(
    *,
    title: str,
    description: str,
    expected_outcome: str | None = None,
    required_skills: list[str] | None = None,
) -> dict[str, Any]:
    full_text = " ".join(part for part in (title, description, expected_outcome or "") if part).strip()
    normalized = _normalized_text(full_text)

    category_scores = {
        category: sum(normalized.count(f" {term} ") for term in terms)
        for category, terms in CATEGORY_TERMS.items()
    }
    winning_category = max(category_scores, key=category_scores.get)
    category = winning_category if category_scores[winning_category] else "Other"

    extracted_skills = _extract_skills(full_text)
    known_skill_keys = {_canonical_skill(skill) for skill in extracted_skills}
    for skill in required_skills or []:
        normalized_skill = skill.strip()
        canonical_skill = _canonical_skill(normalized_skill)
        if normalized_skill and canonical_skill not in known_skill_keys:
            extracted_skills.append(normalized_skill)
            known_skill_keys.add(canonical_skill)

    complexity_terms = (
        "real-time", "real time", "large-scale", "large scale", "predictive", "optimization",
        "optimize", "optimise", "integrate", "integration", "scalable", "distributed", "automate",
    )
    complexity_count = sum(term in full_text.lower() for term in complexity_terms)
    if complexity_count >= 2 or len(full_text.split()) > 180:
        difficulty = "Advanced"
    elif len(full_text.split()) < 35 and complexity_count == 0:
        difficulty = "Beginner"
    else:
        difficulty = "Intermediate"

    return {
        "title": title.strip(),
        "category": category,
        "domain": DOMAIN_BY_CATEGORY[category],
        "required_skills": extracted_skills,
        "keywords": _extract_keywords(full_text),
        "difficulty": difficulty,
        "summary": _summarize(description.strip()),
    }


def _canonical_skill(skill: str) -> str:
    normalized = re.sub(r"[^a-z0-9/ +]+", "", skill.lower()).strip()
    return SKILL_ALIASES.get(normalized, normalized)


def _as_text(value: Any) -> str:
    if isinstance(value, list):
        return " ".join(str(item) for item in value if item)
    return str(value or "")


def _student_text(student: dict[str, Any]) -> str:
    profile = student.get("profile") or {}
    return " ".join(
        part
        for part in (
            _as_text(profile.get("skills")),
            _as_text(profile.get("interests")),
            _as_text(profile.get("experience")),
            _as_text(profile.get("branch")),
            _as_text(profile.get("college")),
        )
        if part
    )


def rank_students(
    challenge: dict[str, Any],
    students: list[dict[str, Any]],
    *,
    embedding_encoder: Callable[[list[str]], list[list[float]]] = encode_texts,
) -> list[dict[str, Any]]:
    if not students:
        return []

    required_skills = challenge.get("required_skills") or []
    challenge_description = " ".join(
        part
        for part in (
            challenge.get("title", ""),
            challenge.get("description", ""),
            challenge.get("summary", ""),
            challenge.get("expected_outcome", ""),
        )
        if part
    )
    domain_text = " ".join(
        part for part in (challenge.get("domain", ""), challenge.get("category", ""), _as_text(challenge.get("keywords"))) if part
    )

    student_texts = [_student_text(student) for student in students]
    student_interests = [_as_text((student.get("profile") or {}).get("interests")) for student in students]
    student_experience = [_as_text((student.get("profile") or {}).get("experience")) for student in students]
    texts_to_encode = [challenge_description, domain_text]
    for profile_text, interests_text, experience_text in zip(student_texts, student_interests, student_experience):
        texts_to_encode.extend([profile_text, interests_text, experience_text or profile_text])
    vectors = embedding_encoder(texts_to_encode)

    challenge_vector = vectors[0]
    domain_vector = vectors[1]
    matches = []
    for index, student in enumerate(students):
        profile_vector, interests_vector, experience_vector = vectors[2 + index * 3:5 + index * 3]
        profile = student.get("profile") or {}
        student_skills = profile.get("skills") or []
        student_skill_map = {_canonical_skill(skill): skill for skill in student_skills}
        matched_skills = []
        missing_skills = []
        for required_skill in required_skills:
            canonical = _canonical_skill(required_skill)
            if canonical in student_skill_map:
                matched_skills.append(required_skill)
            else:
                missing_skills.append(required_skill)

        skills_similarity = len(matched_skills) / len(required_skills) if required_skills else 0.5
        description_similarity = cosine_similarity(challenge_vector, profile_vector)
        domain_similarity = cosine_similarity(domain_vector, interests_vector) if student_interests[index] else 0.0
        experience_similarity = (
            cosine_similarity(challenge_vector, experience_vector)
            if student_experience[index]
            else 0.0
        )
        overall = (
            description_similarity * 0.45
            + skills_similarity * 0.30
            + domain_similarity * 0.15
            + experience_similarity * 0.10
        )

        if required_skills:
            skill_detail = f"matches {len(matched_skills)} of {len(required_skills)} required skills"
        else:
            skill_detail = "no required skills were supplied, so skills were neutral in the score"
        interest_detail = (
            f"domain/interests align {domain_similarity:.0%}"
            if student_interests[index]
            else "no interests are recorded"
        )
        experience_detail = (
            f"experience aligns {experience_similarity:.0%}"
            if student_experience[index]
            else "no experience is recorded"
        )
        explanation = (
            f"Profile meaning aligns {description_similarity:.0%} with the challenge; {skill_detail}; "
            f"{interest_detail}; {experience_detail}."
        )
        matches.append(
            {
                "student_id": str(student.get("_id", "")),
                "student_name": str(student.get("name", "Student")),
                "match_percentage": round(overall * 100),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills,
                "domain_similarity": round(domain_similarity * 100),
                "explanation": explanation,
            }
        )

    return sorted(matches, key=lambda match: match["match_percentage"], reverse=True)