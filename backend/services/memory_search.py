
import numpy as np
from sqlalchemy.orm import Session

from backend.models import UserMemory
from backend.services.embedding import generate_embedding


def search_memory(
    db: Session,
    user_id: int,
    query: str,
    top_k: int = 5,
    min_similarity: float = 0.40,
    duplicate_similarity: float = 0.92,
) -> list[dict]:

    if top_k <= 0:
        return []

    query_embedding = generate_embedding(query)
    distance = UserMemory.embedding.cosine_distance(query_embedding)

    results = (
        db.query(UserMemory, distance.label("distance"))
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.embedding.isnot(None),
        )
        .order_by(distance)
        .limit(top_k * 3)
        .all()
    )

    selected = []

    for memory, distance_value in results:
        similarity = 1 - float(distance_value)

        if similarity < min_similarity:
            continue

        candidate_embedding = np.asarray(memory.embedding, dtype=float)
        is_duplicate = False

        for item in selected:
            existing_embedding = item["embedding"]

            denominator = (
                np.linalg.norm(candidate_embedding)
                * np.linalg.norm(existing_embedding)
            )

            if denominator == 0:
                continue

            pair_similarity = float(
                np.dot(candidate_embedding, existing_embedding)
                / denominator
            )

            if pair_similarity >= duplicate_similarity:
                is_duplicate = True
                break

        if is_duplicate:
            continue

        selected.append({
            "memory_id": memory.id,
            "memory": memory.memory,
            "similarity": similarity,
            "embedding": candidate_embedding,
        })

        if len(selected) >= top_k:
            break

    return [
        {
            "memory_id": item["memory_id"],
            "memory": item["memory"],
            "similarity": item["similarity"],
        }
        for item in selected
    ]
