from sentence_transformers import CrossEncoder


MODEL_NAME = "cross-encoder/ms-marco-MiniLM-L-6-v2"

model = CrossEncoder(MODEL_NAME)


def rerank(
    query: str,
    results: list[dict],
    top_k: int = 5
) -> list[dict]:

    if not results:
        return []

    pairs = [
        (query, result["content"])
        for result in results
    ]

    scores = model.predict(pairs)

    reranked_results = []

    for result, score in zip(results, scores):
        result_copy = result.copy()
        result_copy["rerank_score"] = float(score)
        reranked_results.append(result_copy)

    reranked_results.sort(
        key=lambda result: result["rerank_score"],
        reverse=True
    )

    return reranked_results[:top_k]