# Code walkthrough for the technical interview

This follows the path one question takes through the project. It describes the current code; it is not a claim that the indexes are already complete or that the system is clinically validated.

## 1. App startup: `app/main.py`

- Imports FastAPI, response helpers, route modules, settings, logging, and account initialization.
- `configure_logging(settings.log_level)` sets structured app logging.
- `FastAPI(...)` creates the OpenAPI application with a safety-oriented description.
- `include_router(...)` mounts health, accounts, ingestion, and question endpoints.
- The startup hook initializes the account schema in SQLite or PostgreSQL.
- `/` returns the static chat HTML file.
- The request-validation handler avoids reflecting user input into error responses.
- Middleware generates/sanitizes a request ID, measures elapsed time, catches unexpected exceptions, and logs route/status/latency without logging the question text.

## 2. A question enters: `app/api/routes_qa.py`

- `Question` from `app/schemas/qa.py` validates the request body, including question length and retrieval mode.
- The route reads the HttpOnly session cookie and checks whether the account opted in to history.
- If history is enabled, it verifies the encryption key before any request can be saved.
- `answer_question(question, retrieval_mode)` owns the answer workflow.
- If enabled, the route saves the final response through `account_service`; otherwise nothing is saved.
- Exceptions return a generic 503 message so internal paths or provider details are not shown to users.

## 3. Safety and orchestration: `app/services/qa_service.py`

- Starts a timer for observability.
- Checks emergency-like language first and returns an immediate emergency-services message with no citations.
- Checks dosage/treatment requests and abstains from medical instructions.
- Checks a limited set of prompt-injection patterns.
- Calls `search_detailed` for evidence.
- Trims total retrieved evidence to `MAX_CONTEXT_CHARS` so prompts and costs are bounded.
- Gets the configured mock, Gemini, or OpenAI-compatible generation provider.
- Calls `provider.generate(question, hits)` to produce a structured answer and claims.
- `citation_support` verifies that cited IDs exist in the retrieved hits. The check doesn't prove the source logically supports a statement.
- If there is no evidence, a citation mismatch, or an unsupported claim status, the service returns the safe insufficient-evidence message and no citations.
- Adds timing, retrieval count, and model label; detailed ranks are included only when the development debug setting is enabled.

## 4. Retrieval: `app/services/retrieval_service.py`

- Normalizes only a few explicitly listed common typos; it does not autocorrect medical terms or infer a diagnosis.
- Confirms the requested mode is one of dense, BM25, hybrid, or hybrid-rerank.
- Requires both index stores to match the local manifest before full-corpus search.
- Dense mode embeds the question and queries Qdrant. BM25 mode searches SQLite FTS5. Hybrid mode queries both and fuses ranks with `app/retrieval/fusion.py`.
- Hybrid-rerank applies a simple token-overlap reranker to a short candidate list. This is not a transformer cross-encoder.
- Filters suspicious retrieved instructions and returns a bounded number of hits.
- If the supplied local source files exist while indexes are incomplete, it fails instead of quietly using the small synthetic sample corpus.

## 5. Ingestion and indexing

- `scripts/ingest_text_corpus.py` reads each `.txt`, normalizes Unicode/spacing, preserves line boundaries, emits 180-word chunks with 30-word overlap, and writes JSONL metadata and a quality audit.
- `scripts/index_vector_store.py` reads unique chunk IDs, embeds text with FastEmbed's BGE-small model, creates Qdrant points, rebuilds SQLite FTS5, compares exact counts, then writes `data/local/index_manifest.json`.
- `app/services/index_manifest.py`, `vector_store_service.py`, `lexical_index_service.py`, and `/ready` enforce the completion check.
- The source text, chunks, local databases, embeddings, and manifest are ignored by Git. Verify dataset redistribution terms before sending source content to a cloud index or LLM.

## 6. Account/history path

- `routes_accounts.py` validates email/password shapes and provides signup, login, logout, account, history preference, and delete endpoints.
- `account_service.py` hashes passwords with scrypt and stores only a hash of each random session token. SQLite is local/single-instance; `DATABASE_URL` selects PostgreSQL.
- History is opt-in and disabled by default. Fernet encrypts the stored conversation payload, and disabling history deletes saved rows.
- The browser builds elements with `textContent` rather than injecting saved question strings as HTML. Users can open saved conversations from the history panel.
- This remains starter code: no verified email, reset flow, distributed throttling, or production privacy review.

## 7. Evaluation and claims

- `evaluation/run_evaluation.py` uses a small synthetic set to check ranking proxies such as Recall@k, MRR, and nDCG.
- `evaluation/run_ragas.py` requires complete indexes and a Gemini key; it estimates faithfulness and context utilization with an LLM judge.
- Human review should inspect answer correctness, passage relevance, citations, clarity, and safety using `evaluation/jury-scorecard.md`.
- No RAGAS number, medical accuracy, clinical validation, deployed URL, or hackathon leaderboard result exists until actually run and recorded.

## Interview-safe explanation of “what is new?”

The project contribution is a working prototype pipeline and user experience: textbook text ingestion with traceable chunk IDs, hybrid dense + BM25 retrieval, rank fusion, evidence display, citation integrity checks, safe abstention, corpus-index readiness, and optional account/history flows. These are engineering choices and integration work. Do not claim a novel algorithm, validated medical assistant, or improved RAGAS score without measured evidence.
