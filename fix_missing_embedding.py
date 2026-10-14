
from backend.database import SessionLocal
from backend.models import UserMemory
from backend.services.embedding import generate_embedding

db = SessionLocal()

try:
    memory = (
        db.query(UserMemory)
        .filter(
            UserMemory.id == 1,
            UserMemory.user_id == 3,
        )
        .first()
    )

    if memory is None:
        print("Memory ID 1 was not found for user 3.")
    elif memory.embedding is not None:
        print("Memory already has an embedding.")
    else:
        memory.embedding = generate_embedding(memory.memory)
        db.commit()
        print("Embedding generated and saved for memory ID 1.")

except Exception:
    db.rollback()
    raise

finally:
    db.close()
