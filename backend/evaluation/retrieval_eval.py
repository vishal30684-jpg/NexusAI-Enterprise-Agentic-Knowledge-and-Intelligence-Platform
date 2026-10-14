
from backend.database import SessionLocal
from backend.services.hybrid_search import hybrid_search
from backend.evaluation.dataset import EVALUATION_DATASET


def evaluate_retrieval(k: int = 5) -> None:
    db = SessionLocal()

    total_hit = 0
    total_reciprocal_rank = 0.0
    total_precision = 0.0
    total_recall = 0.0

    try:
        for item in EVALUATION_DATASET:
            query = item["query"]
            expected_chunks = set(item["expected_chunks"])

            results = hybrid_search(
                query=query,
                db=db,
                user_id=3,
                is_admin=True,
                top_k=10,
                min_similarity=0.30,
            )

            top_k_results = results[:k]

            retrieved_chunks = [
                (result["document_id"], result["chunk_index"])
                for result in top_k_results
            ]

            # Find relevant chunks in the top-k results.
            relevant_chunks = (
                set(retrieved_chunks) & expected_chunks
            )

            hit = bool(relevant_chunks)
            total_hit += int(hit)

            # Mean Reciprocal Rank.
            reciprocal_rank = 0.0

            for rank, chunk in enumerate(
                retrieved_chunks, start=1
            ):
                if chunk in expected_chunks:
                    reciprocal_rank = 1.0 / rank
                    break

            total_reciprocal_rank += reciprocal_rank

            # Precision@k: relevant retrieved / retrieved results.
            precision = len(relevant_chunks) / k
            total_precision += precision

            # Recall@k: relevant retrieved / all expected chunks.
            recall = (
                len(relevant_chunks) / len(expected_chunks)
                if expected_chunks
                else 0.0
            )
            total_recall += recall

            print("\n" + "=" * 70)
            print("Question:", query)
            print("Expected chunks:", sorted(expected_chunks))
            print("Retrieved chunks:", retrieved_chunks)
            print(f"Hit@{k}: {int(hit)}")
            print(f"Reciprocal Rank: {reciprocal_rank:.4f}")
            print(f"Precision@{k}: {precision:.4f}")
            print(f"Recall@{k}: {recall:.4f}")

        count = len(EVALUATION_DATASET)

        if count == 0:
            print("Evaluation dataset is empty.")
            return

        print("\n" + "=" * 70)
        print("RETRIEVAL EVALUATION SUMMARY")
        print(f"Number of questions: {count}")
        print(f"Hit@{k}: {total_hit / count:.4f}")
        print(f"MRR: {total_reciprocal_rank / count:.4f}")
        print(f"Precision@{k}: {total_precision / count:.4f}")
        print(f"Recall@{k}: {total_recall / count:.4f}")

    finally:
        db.close()


if __name__ == "__main__":
    evaluate_retrieval(k=5)
