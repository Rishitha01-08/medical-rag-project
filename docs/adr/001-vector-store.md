# ADR 001: Local JSONL store for offline demo

- **Status:** Accepted
- **Context:** The prototype downloaded embedding models and initialized a vector database at import time, making tests network dependent.
- **Decision:** Use synthetic JSONL plus ignored local JSONL chunks for deterministic mock operation; keep vector-store environment names reserved.
- **Alternatives:** Chroma, Qdrant, hosted vector database, in-memory-only fixtures.
- **Trade-offs:** Easy offline setup and inspection; no transactional writes, scale, semantic embedding, or multi-process guarantees.
- **Consequences:** Qdrant migration needs an adapter, persistence/concurrency design, and operational security review.
