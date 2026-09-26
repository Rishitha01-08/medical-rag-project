# ADR 002: Hybrid ranking with reciprocal-rank fusion

- **Status:** Accepted
- **Context:** Keyword retrieval alone misses semantic paraphrases; raw dense and lexical scores have different scales.
- **Decision:** Demonstrate BM25 and a local token-vector fallback, combine ranks with RRF, then optionally use a deterministic overlap reranker.
- **Alternatives:** BM25 only, embedding cosine only, score normalization and weighted sum, learned reranker.
- **Trade-offs:** Simple and deterministic; token-vector similarity is not semantic, RRF discards score magnitude, overlap reranking is weak.
- **Consequences:** The ablation runner measures only a synthetic retrieval proxy. A real embedding/reranker should be added only with reproducible offline tests and rights-cleared data.
