EVALUATION_DATASET = [
    {
        "query": "Which technologies are used to build NexusAI?",
        "expected_chunks": [(7, 0)],
    },
    {
        "query": "Which backend features are implemented in NexusAI, including authentication, PDF extraction, embeddings, and reranking?",
        "expected_chunks": [(7, 1)],
    },
    {
        "query": "How does NexusAI combine semantic and keyword search?",
        "expected_chunks": [(10, 0)],
    },
    {
        "query": "What is reciprocal rank fusion used for in NexusAI?",
        "expected_chunks": [(10, 0)],
    },
    {
        "query": "How does NexusAI retrieve information from Word documents?",
        "expected_chunks": [(11, 0)],
    },
    {
        "query": "What does NexusAI use PostgreSQL and pgvector for?",
        "expected_chunks": [(7, 0), (7, 1)],
    },
    {
        "query": "What is the purpose of cross-encoder reranking?",
        "expected_chunks": [(7, 0), (7, 1)],
    },
    {
        "query": "Which backend features are implemented, including user authentication and role-based authorization?",
        "expected_chunks": [(7, 1)],
    },
    {
        "query": "How does NexusAI enforce user authentication and role-based authorization?",
        "expected_chunks": [(7, 1)],
    },
    {
        "query": "What does NexusAI do with document chunks and embeddings?",
        "expected_chunks": [(8, 0)],
    },
]