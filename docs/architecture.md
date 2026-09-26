# Architecture

## Components and request flow

FastAPI routes validate input through Pydantic schemas, the safety service classifies it, the retrieval service loads the synthetic sample plus ignored local JSONL chunks, then chooses dense-style token-vector, BM25, RRF hybrid, or hybrid plus a deterministic overlap reranker. Mock generation is the default and summarizes only retrieved text; optional provider adapters are used only when mock mode is explicitly disabled. Grounding verifies that claim source IDs point to retrieved chunk IDs. Responses include citations, disclaimer, safety state, retrieval count, and local timings.

## Ingestion and chunking

JSONL documents preserve document ID, title, source, URL/page/section metadata. Chunk IDs hash document ID, chunk position, and normalized chunk text; chunk content hashes are also recorded. Chunk size/overlap are configurable; empty and duplicate chunk text is removed. CLI dry-run previews output without writing. The API ingestion endpoint writes to ignored `data/local/documents.jsonl`.

## Retrieval design

BM25 provides lexical relevance for exact terms. Dense retrieval currently means a dependency-free token-frequency cosine similarity fallback, not pretrained semantic embeddings. Reciprocal Rank Fusion adds `1/(k + rank)` across result lists and deduplicates on chunk ID while preserving source ranks. The lightweight reranker sorts by query-token overlap. Configured relevance filtering is applied after ranking. These are demonstrative offline components, not a production search service.

## Generation and grounding

`Provider` defines the generation boundary. Mock generation is the default; optional OpenAI-compatible and Gemini JSON-mode adapters are selected only when mock mode is disabled and the matching environment key is present. They pass question and evidence as data, request structured JSON, and retry malformed structured output once. No real provider call is made in tests or CI. Citation support is the fraction of claims containing a retrieved ID. Unsupported responses abstain. This mechanical check does not establish claim truth or medical validity.

## Failure handling and scaling

Malformed requests receive FastAPI validation errors, unexpected errors receive a generic response, and every response receives an `X-Request-ID`. The local JSONL store is suitable only for a small single-process demonstration. A deployment could add durable transactional storage, Qdrant, measured embeddings, a cross-encoder, provider adapters with structured-output retry, authentication, distributed rate limiting, secret management, and monitoring after threat modeling and validation.
