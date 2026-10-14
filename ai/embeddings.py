import math
import os
from functools import lru_cache
from typing import Any

DEFAULT_EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class EmbeddingModelError(RuntimeError):
    """Raised when the configured sentence embedding model cannot be loaded."""


@lru_cache(maxsize=1)
def get_embedding_model() -> Any:
    try:
        from sentence_transformers import SentenceTransformer

        model_name = os.getenv("AI_EMBEDDING_MODEL", DEFAULT_EMBEDDING_MODEL).strip()
        return SentenceTransformer(model_name or DEFAULT_EMBEDDING_MODEL)
    except Exception as error:
        raise EmbeddingModelError("The sentence embedding model could not be loaded") from error


def encode_texts(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return vectors.tolist()


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0

    dot_product = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0

    return max(0.0, min(1.0, dot_product / (left_norm * right_norm)))