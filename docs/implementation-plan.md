# Implementation plan

## Starting point

The repository is a small FastAPI prototype. `app.main` exposes `/health` and `/ask`; `app.vectorstore` loads one text file into an in-memory Chroma collection using a Sentence Transformers model; and `app.rag` constructs a Hugging Face text-generation pipeline at import time. The existing `data/raw/medical.txt` is empty. The only evaluation file is a placeholder print statement. There are no tests, CI, Docker, typed settings, or meaningful documentation. This design requires downloads at startup and treats a medical textbook citation as source metadata without a bundled source document.

## Target design

Build an offline-first FastAPI service with typed environment configuration, request IDs, a safe mock provider, synthetic sample corpus, deterministic chunking, local JSONL persistence, dense and BM25 retrievers, reciprocal-rank fusion, a deterministic reranker, safety classification, evidence validation, and citations that can only refer to retrieved chunks. Add optional OpenAI-compatible and Gemini structured-output adapters, but never call them during implementation, tests, CI, or evaluation. Add deterministic tests, evaluation tooling, developer commands, Docker, CI, and honest setup/security/architecture/interview documentation.

## Stages

1. **Foundation and security:** ensure secret/local-data ignore rules, placeholder-only `.env.example`, typed validated settings, structured logging, request IDs, schemas, and the plan itself.
2. **Ingestion and retrieval:** add safe synthetic JSONL data; deterministic chunking and IDs; local storage; dense and BM25 interfaces; RRF, deduplication, deterministic reranking, and thresholding.
3. **Question answering and API:** add mock generation, strict evidence prompt/interface, safety and prompt-injection controls, grounding/citation validation, abstention, health/readiness, ask and protected ingestion endpoints.
4. **Evaluation and quality:** deterministic metrics and four retrieval modes; meaningful unit/integration tests; lint/format/type/coverage configuration and offline CI.
5. **Delivery and documentation:** Docker/Compose/Makefile; architecture, security, evaluation, ADRs, interview guide, and recruiter-ready README aligned to actual behavior.
6. **Quality gate and delivery:** run checks and offline API/evaluation smoke checks; inspect secret-safe diff and ignore behavior; commit logically; push the specified branch; create a draft-free PR targeting main without merging.

## Constraints and trade-offs

- No credentials, patient data, copyrighted corpus, model weights, generated caches, or local database files are committed. `.env` is not read or printed. `.env.example` contains only variable names, harmless defaults, and blank credential placeholders.
- All checks use mock mode and must work offline. Dense retrieval uses a deterministic local lexical/vector-like fallback when no embedding service is configured; no pretrained model is downloaded.
- Medical answers are educational only. Emergency-like inputs receive emergency-services guidance; unsupported claims abstain; retrieved content is untrusted data.
- Evaluation numbers are generated locally from the included synthetic corpus and questions. They are deterministic proxy measurements, not clinical or model-quality claims.
- Real-provider adapters exist but require credentials and network at runtime and were not called or externally tested. External Qdrant, production authentication, distributed rate limiting, and clinical validation remain outside scope and are stated plainly.
