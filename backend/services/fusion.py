
def reciprocal_rank_fusion(
    vector_results: list[dict],
    bm25_results: list[dict],
    top_k: int = 10,
    k: int = 60
) -> list[dict]:
    fused_scores = {}
    result_lookup = {}

    def get_chunk_key(result: dict):
        return (result["document_id"], result["chunk_index"])

    # Add vector-search rankings.
    for rank, result in enumerate(vector_results, start=1):
        chunk_key = get_chunk_key(result)
        fused_scores[chunk_key] = (
            fused_scores.get(chunk_key, 0) + 1 / (k + rank)
        )
        result_lookup[chunk_key] = result.copy()

    # Add BM25 rankings.
    for rank, result in enumerate(bm25_results, start=1):
        chunk_key = get_chunk_key(result)
        fused_scores[chunk_key] = (
            fused_scores.get(chunk_key, 0) + 1 / (k + rank)
        )
        if chunk_key not in result_lookup:
            result_lookup[chunk_key] = result.copy()

    ranked_chunks = sorted(
        fused_scores.items(),
        key=lambda item: item[1],
        reverse=True
    )

    results = []
    content_lookup = {}

    for chunk_key, score in ranked_chunks:
        result = result_lookup[chunk_key].copy()

        normalized_content = " ".join(
            result.get("content", "").split()
        ).casefold()

        result["fusion_score"] = score
        result["duplicate_sources"] = []

        # Group identical non-empty content.
        if normalized_content:
            if normalized_content in content_lookup:
                primary_result = content_lookup[normalized_content]

                primary_result["duplicate_sources"].append({
                    "document_id": result["document_id"],
                    "document_filename": result.get("document_filename"),
                    "page_number": result.get("page_number"),
                    "chunk_index": result["chunk_index"],
                })
                continue

            content_lookup[normalized_content] = result

        # Keep only the requested number of unique results,
        # but continue scanning so their duplicate metadata is complete.
        if len(results) < top_k:
            results.append(result)

    return results
