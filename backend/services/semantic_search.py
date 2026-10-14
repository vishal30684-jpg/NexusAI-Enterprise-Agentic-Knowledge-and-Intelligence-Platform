
from backend.models import Document, DocumentChunk, DocumentPermission
from sqlalchemy.orm import Session


from backend.services.embedding import generate_embedding


def semantic_search(
    query: str,
    db: Session,
    user_id: int,
    is_admin: bool = False,
    top_k: int = 5,
    min_similarity: float = 0.40
):
    query_embedding = generate_embedding(query)

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    query_builder = (
        db.query(
            DocumentChunk,
            Document.filename,
            distance.label("distance")
        )
        .join(Document, Document.id == DocumentChunk.document_id)
        .filter(DocumentChunk.embedding.isnot(None))
    )

    if not is_admin:
        query_builder = query_builder.filter(
            (Document.uploaded_by == user_id)
            |
            (
                db.query(DocumentPermission.id)
                .filter(
                    DocumentPermission.document_id == Document.id,
                    DocumentPermission.user_id == user_id
                )
                .exists()
            )
        )

    results = (
        query_builder
        .order_by(distance)
        .limit(top_k)
        .all()
    )

    return [
       {
        "document_id": chunk.document_id,
        "document_filename": filename,
        "page_number": chunk.page_number,
        "chunk_index": chunk.chunk_index,
        "similarity": 1 - distance_value,
        "content": chunk.content
      }
      for chunk, filename, distance_value in results
      if (1 - distance_value) >= min_similarity
    ]