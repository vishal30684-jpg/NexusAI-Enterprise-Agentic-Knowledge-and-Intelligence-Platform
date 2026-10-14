from sqlalchemy.orm import Session

from backend.models import UserMemory
from backend.services.embedding import generate_embedding



def save_memory(
    db: Session,
    user_id: int,
    memory_text: str,
    embedding: list[float],
    duplicate_distance: float = 0.20
) -> UserMemory:

    existing_memory = (
        db.query(UserMemory)
        .filter(
            UserMemory.user_id == user_id,
            UserMemory.embedding.isnot(None),
            UserMemory.embedding.cosine_distance(embedding)
            <= duplicate_distance
        )
        .order_by(
            UserMemory.embedding.cosine_distance(embedding)
        )
        .first()
    )

    if existing_memory:
        return existing_memory

    memory = UserMemory(
        user_id=user_id,
        memory=memory_text,
        embedding=embedding
    )

    db.add(memory)
    db.commit()
    db.refresh(memory)

    return memory




def save_extracted_memories(
    db: Session,
    user_id: int,
    memories: list[str]
) -> list[UserMemory]:

    saved_memories = []
    seen_texts = set()

    for memory_text in memories:
        memory_text = memory_text.strip()

        if not memory_text:
            continue

        # Normalize capitalization and whitespace.
        normalized_text = " ".join(memory_text.lower().split())

        # Skip duplicates within the current extraction batch.
        if normalized_text in seen_texts:
            continue

        seen_texts.add(normalized_text)

        # Skip exact-text duplicates already stored for this user.
        existing_memory = (
            db.query(UserMemory)
            .filter(
                UserMemory.user_id == user_id,
                UserMemory.memory == memory_text,
            )
            .first()
        )

        if existing_memory:
            saved_memories.append(existing_memory)
            continue

        embedding = generate_embedding(memory_text)

        memory = save_memory(
            db=db,
            user_id=user_id,
            memory_text=memory_text,
            embedding=embedding,
        )

        saved_memories.append(memory)

    return saved_memories



def build_memory_context(memories: list[dict]) -> str:
    if not memories:
        return ""

    context_parts = []

    for index, memory in enumerate(memories, start=1):
        context_parts.append(
            f"[MEMORY {index}]\n"
            f"{memory['memory']}\n"
        )

    return "\n".join(context_parts)