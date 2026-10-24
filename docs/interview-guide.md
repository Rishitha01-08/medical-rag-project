# Interview guide: Medical RAG project

This guide describes the code in this repository as it is implemented. Be honest about the distinction between the original offline demo, the current local retrieval stack, and the parts that still require hosted credentials/deployment.

## Problem statement

Medical education content is large and fragmented. A user may ask a plain-language question but need an answer that points back to where its evidence came from. A general LLM can produce fluent but unsupported text. This project explores a RAG pipeline over supplied educational textbook extracts, with citations, a limited safety layer, and abstention when evidence is missing. Its novelty is the end-to-end combination of dense and lexical retrieval, inspectable source excerpts, explicit completeness checks, and a cautious educational boundary—not a new medical model or a clinically validated product.

## 30-second explanation

I built an educational medical-information RAG application with FastAPI. It chunks supplied text, embeds each chunk locally with FastEmbed, indexes vectors in Qdrant, and indexes text in SQLite FTS5 for BM25. The API combines dense and lexical retrieval with Reciprocal Rank Fusion, then returns an answer with source excerpts and citation IDs. It has safety boundaries and abstains when evidence is insufficient. It is a demo, not a clinical decision system.

## Two-minute architecture answer

The nine supplied inputs in this workspace are text extracts, not PDFs. The ingestion script preserves line breaks, emits at-most 180-word chunks with 30-word overlap, and writes local JSONL plus an audit. It found 110,891 chunks; one extract has 67,528 replacement characters and there are no source page numbers. FastEmbed BGE-small creates 384-dimensional vectors. Qdrant handles semantic nearest-neighbor retrieval and SQLite FTS5 handles BM25 exact-term search. Reciprocal Rank Fusion combines their ranks. A deterministic lexical-overlap reranker is optional. The API validates the request, applies limited safety rules, passes bounded evidence to mock or configured Gemini/OpenAI generation, and validates citation IDs. Mock mode is default and only returns evidence excerpts. The full indexes are not yet verified on this machine, so `/ready` must pass before claiming the app answers from all books. There is no produced RAGAS score, deployed endpoint, or clinical validation.

## File-by-file map

| File | Interview explanation |
|---|---|
| `app/main.py` | Creates the FastAPI app, registers routes, serves the browser UI, and attaches request IDs and privacy-conscious request logging. |
| `app/config.py` | Reads and validates environment settings; secrets are never embedded in source. |
| `app/api/routes_qa.py` | Defines the question endpoint, invokes orchestration, and returns a controlled service-unavailable response on backend failure. |
| `app/api/routes_health.py` | Separates process health from readiness; readiness checks both search indexes. |
| `app/services/ingestion_service.py` | Chunks structured educational documents and attaches source metadata. |
| `scripts/ingest_text_corpus.py` | Converts the supplied plain text corpus into local JSONL chunks. |
| `app/services/vector_store_service.py` | Loads FastEmbed, creates stable Qdrant points, writes batches, and performs dense nearest-neighbor queries. |
| `app/services/lexical_index_service.py` | Builds and queries a persistent SQLite FTS5 text index using BM25 ranking. |
| `scripts/index_vector_store.py` | Orchestrates vector embedding/upserts and rebuilds the lexical index from JSONL sources. |
| `app/services/retrieval_service.py` | Chooses dense, lexical, hybrid, and optional reranked retrieval; normalizes only a few explicit demo typos. |
| `app/retrieval/fusion.py` | Implements Reciprocal Rank Fusion and deduplicates by chunk ID. |
| `app/services/generation_service.py` | Selects deterministic mock or configured LLM provider. |
| `app/services/grounding_service.py` | Checks that response citations point to evidence in the retrieved set; this is an integrity check, not a truth check. |
| `app/services/safety_service.py` | Handles known safety-sensitive patterns and prompt-injection-like inputs; deterministic rules are not complete clinical safeguards. |
| `app/services/account_service.py` | Stores local SQLite or configured PostgreSQL accounts, hashed session tokens, and opt-in Fernet-encrypted chat history. |
| `app/services/index_manifest.py` | Reads the local index completion manifest used by readiness checks. |
| `evaluation/run_evaluation.py` | Runs deterministic retrieval and abstention proxies against small synthetic cases. |
| `evaluation/run_ragas.py` | Optionally calls a Gemini judge through RAGAS for faithfulness and context-utilization estimates. |
| `evaluation/jury-scorecard.md` | Structures independent human review and blocking safety findings. |

## Important concepts to explain

- **RAG:** retrieve relevant evidence at request time and ground the response in it. This keeps the source corpus replaceable and makes evidence inspectable; it does not guarantee correctness.
- **Chunking:** splits long documents into retrieval units. This version uses 180-word windows and 30-word overlap while preserving line breaks and detecting explicit chapter/section headings. It is still a fixed-window baseline, not a clinically optimized segmentation strategy.
- **Embedding:** maps text to a vector so semantically similar passages can be close by cosine distance. Here BGE-small is 384-dimensional and runs locally through FastEmbed. This replaced the earlier deterministic token-vector fallback.
- **Vector database:** Qdrant stores and searches embedding vectors with metadata. Local embedded Qdrant is for one local process; a server deployment needs durable storage and access controls.
- **BM25:** lexical search ranks exact word matches using term frequency, inverse document frequency, and length normalization. FTS5 provides the persistent keyword index.
- **Hybrid retrieval:** combines vector similarity and lexical ranking so paraphrases and exact technical terms both have a path to retrieval.
- **RRF:** adds `1 / (k + rank)` from each list. A result ranked highly by multiple retrievers rises without requiring their scores to share a scale.
- **Reranking:** reorders a shortlist. The project's simple token-overlap reranker is not a learned cross-encoder.
- **Grounding:** attaching source excerpts and checking citation IDs improves inspectability. It does not prove the excerpt supports every sentence.
- **Abstention:** returning an insufficient-evidence response when the corpus cannot support an answer is safer than inventing details.
- **RAGAS:** judge-model estimates can examine faithfulness/context utilization. Scores depend on the judge, and a small synthetic evaluation set cannot establish clinical quality.
- **Human jury review:** reviewers independently inspect the same question, evidence, answer, citations, clarity, and safety. A critical unsafe claim is a failure even if numerical averages look good.

## Likely interviewer questions

1. **Why RAG instead of fine-tuning?** The factual source content can be updated without retraining; retrieved evidence can be shown. Fine-tuning does not automatically provide current facts or citations.
2. **Why both Qdrant and FTS5?** Vector search helps semantic similarity, while BM25 finds exact terms and names; their results are complementary.
3. **Why use RRF?** It combines rank positions and avoids directly mixing uncalibrated scores.
4. **Why 180 words and 30-word overlap?** It is an initial baseline intended to keep passage context manageable while preserving some boundary context. It should be tuned using a labeled retrieval benchmark; it is not universally optimal.
5. **Why FastEmbed and BGE-small?** A compact local embedding path avoids per-chunk hosted embedding calls and uses a 384-dimensional vector; model choice should be validated on the task corpus.
6. **How are chunk IDs stable?** A SHA-256 digest includes document identity, chunk position, and content, allowing stable references for an unchanged source/chunking configuration.
7. **What does `--recreate` do?** Deletes the configured Qdrant collection and rebuilds it; use only when intentionally replacing the indexed collection.
8. **How is an answer grounded?** The generator receives retrieved excerpts and citation IDs; a grounding layer rejects citation IDs outside the retrieved set. This checks provenance wiring, not factual entailment.
9. **How do you measure retrieval?** With labeled expected chunk IDs and metrics such as Recall@k, Precision@k, MRR, and nDCG. The checked-in set is small/synthetic; the Hack-A-Cure corpus needs expert-reviewed queries and labels.
10. **What does RAGAS add?** It uses an evaluator model to estimate properties such as faithfulness and context utilization. Its scores are not ground truth and can cost money or be rate-limited.
11. **How do you use the human jury?** Reviewers score the same saved outputs with a rubric, note unsafe or unsupported claims, and block release on critical safety defects.
12. **What are the biggest limits?** Corpus rights and curation, no clinical validation, simple word-based chunks, limited safety patterns, prototype SQLite accounts, no full production identity/rate-limit/monitoring solution, and no deployed URL yet.
13. **Is it ready for patient use?** No. It is an educational prototype and must not be used for diagnosis, treatment decisions, triage, or emergency care.

## Interview honesty checklist

Say that the project includes a real embedding/vector retrieval path in its current branch, but distinguish local implementation from a hosted production deployment. Do not claim a public endpoint, RAGAS score, clinical validation, jury review, or benchmark improvement until that result is produced and documented. Never describe a mock answer as a real LLM response.
