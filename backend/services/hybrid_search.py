
from sqlalchemy.orm import Session

from backend.services.semantic_search import semantic_search
from backend.services.bm25_search import bm25_search
from backend.services.fusion import reciprocal_rank_fusion
from backend.services.reranker import rerank


def hybrid_search(
    query: str,
    db: Session,
    user_id: int,
    is_admin: bool = False,
    top_k: int = 10,
    min_similarity: float = 0.30
) -> list[dict]:

    vector_results = semantic_search(
        query=query,
        db=db,
        user_id=user_id,
        is_admin=is_admin,
        top_k=top_k,
        min_similarity=min_similarity
    )

    bm25_results = bm25_search(
        query=query,
        db=db,
        user_id=user_id,
        is_admin=is_admin,
        top_k=top_k
    )

    fused_results = reciprocal_rank_fusion(
        vector_results=vector_results,
        bm25_results=bm25_results,
        top_k=top_k
    )

    reranked_results = rerank(
        query=query,
        results=fused_results,
        top_k=top_k
    )

    return reranked_results
