import re

from sqlalchemy.orm import Session

from backend.models import Document, DocumentChunk, DocumentPermission
from rank_bm25 import BM25Okapi



STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by",
    "for", "from", "how", "in", "is", "it", "of", "on",
    "or", "that", "the", "this", "to", "was", "were",
    "what", "which", "with"
}


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"\b\w+\b", text.lower())
    return [token for token in tokens if token not in STOP_WORDS]



def bm25_search(
    query: str,
    db: Session,
    user_id: int,
    is_admin: bool = False,
    top_k: int = 5,
    min_score: float = 0.0
) -> list[dict]:

    query_builder = (
        db.query(
            DocumentChunk,
            Document.filename
        )
        .join(
            Document,
            Document.id == DocumentChunk.document_id
        )
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

    rows = query_builder.all()
  

    if not rows:
        return []

    documents = [chunk.content for chunk, _ in rows]

    tokenized_documents = [
        tokenize(document)
        for document in documents
    ]

    bm25 = BM25Okapi(
        tokenized_documents,
        epsilon=0.25,
    )

    query_tokens = tokenize(query)

    scores = bm25.get_scores(query_tokens)
    
    ranked_indices = [
        index
        for index in sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True
        )
        if min_score <= 0.0 or scores[index] >= min_score
    ][:top_k]

    results = []

    for index in ranked_indices:
        chunk, filename = rows[index]

        results.append({
            "document_id": chunk.document_id,
            "document_filename": filename,
            "page_number": chunk.page_number,
            "chunk_index": chunk.chunk_index,
            "bm25_score": float(scores[index]),
            "content": chunk.content
        })

    return results