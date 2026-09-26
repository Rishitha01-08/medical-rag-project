# Interview guide

## 30-second explanation

I upgraded a small medical question-answering prototype into an offline-first FastAPI RAG demo. It ingests synthetic educational text, compares BM25 with a deterministic token-vector fallback, fuses rankings with Reciprocal Rank Fusion, checks citation IDs, and abstains when evidence is missing. The application defaults to a deterministic mock generator and is not clinical software.

## 60-second explanation

The API validates questions, applies deterministic safety rules, retrieves from a tiny synthetic corpus with BM25, token-vector similarity, or hybrid RRF, and can apply a lexical reranker. A deterministic mock provider is the default; optional OpenAI-compatible and Gemini adapters request structured JSON only when configured outside mock mode. A grounding layer validates citations against retrieved chunk IDs and the API includes a disclaimer, safety metadata, and request ID. Tests and evaluation run offline in mock mode. The main trade-off is reproducibility and transparency over semantic quality: local dense retrieval is only token-vector cosine, not pretrained embeddings.

## Two-minute architecture explanation

Documents enter as JSONL with source metadata. Ingestion splits text into overlapping chunks, removes duplicates, hashes content and chunk identity, and stores local output under an ignored path. Retrieval exposes four modes: token-vector cosine as a deterministic dense-style baseline, BM25 for lexical matching, RRF across both ranked lists, and hybrid results followed by a deterministic overlap reranker. The mock generator produces an evidence excerpt and structured claim whose IDs are checked against retrieved chunks. Safety rules intercept emergency-like, diagnosis/prescription-related, and direct injection-like requests. If evidence is missing or citation verification fails, the service abstains. Offline evaluation compares ranking metrics and abstention behavior against a synthetic labeled set. These metrics do not measure clinical correctness.

## Concepts to explain

- **RAG vs fine-tuning:** retrieval updates the evidence collection without changing model weights and can expose source material; fine-tuning changes model behavior but is not a substitute for fresh source retrieval.
- **Hybrid retrieval:** lexical matching helps exact names/terms while vector-style similarity may help related vocabulary. Here the vector-style implementation is only token overlap and does not demonstrate semantic embeddings.
- **BM25:** a lexical ranking formula using term frequency, inverse document frequency, and document-length normalization.
- **Embeddings:** vectors representing text for similarity search; this repository does not currently generate pretrained embeddings.
- **Vector database:** a system that indexes vectors and metadata for similarity retrieval. The current local JSONL implementation does not use one.
- **RRF:** combines ranked lists using reciprocal rank contributions, so the systems need not share calibrated score scales.
- **Reranking:** scores a smaller candidate set more carefully; this project's fallback is query-token overlap, not a cross-encoder.
- **Hallucination risk:** reduced through evidence-limited mock output, citation-ID validation, and abstention; never eliminated or clinically evaluated.
- **Citations:** final citation IDs must identify retrieved chunks, with excerpts and preserved source metadata.
- **Safe abstention:** return an insufficient-evidence response instead of filling gaps with a guess.
- **Safety limits:** high-level educational response only; no diagnosis, medication, dosage, treatment, or emergency triage.
- **Testing:** unit tests validate ranking, chunking, IDs, safety, and grounding; integration tests call FastAPI with mock dependencies.
- **Metrics:** Recall@k/Precision@k measure retrieval overlap; MRR and nDCG reward earlier relevant ranks. Proxies are synthetic and not measures of clinical quality.
- **Docker/CI:** the image installs Python dependencies and runs the API; CI formats, lints, type-checks, tests, and evaluates with mock mode.
- **Cloud path:** replace local JSONL with secured durable storage, add a real vector adapter and embedding service, enforce identity/rate controls, and instrument deployment before exposure.
- **Cost/scaling:** no API cost in mock mode. Real-provider cost and throughput are unknown and depend on model, corpus, and usage; batch embeddings and cache carefully only after measurement.
- **Bottlenecks:** current linear scan, local JSONL reads, simplistic similarity, and no concurrency-safe writes are unsuitable for large corpora.
- **Security:** keep secrets external, minimize logs, limit ingestion, treat corpus text as untrusted, and avoid real health data.
- **Failure cases:** unsupported evidence, bad chunking, metadata loss, keyword mismatch, injection variants, malformed real-provider output, local write contention, and corpus poisoning.

## Likely technical interview questions

1. **Why use RAG?** It makes source material replaceable and citations inspectable without model retraining.
2. **What does BM25 do?** Ranks documents by lexical term matches with frequency and length adjustments.
3. **What is an embedding?** A numeric representation intended to encode text similarity; none is generated here.
4. **Why hybrid retrieval?** It can combine exact-term retrieval with vector similarity; current dense-style matching is only a baseline.
5. **Why RRF?** It combines ranks without requiring calibrated score scales.
6. **What does RRF compute?** A sum of `1/(k + rank)` contributions for each result list.
7. **Why rerank?** Reassess a smaller candidate set after broad retrieval; current implementation uses overlap only.
8. **How are citations checked?** Returned source IDs are checked against chunk IDs in the retrieved candidate set.
9. **Does that prove factual correctness?** No. It validates reference integrity only.
10. **When does the app abstain?** When retrieval is empty or generated claim support is invalid; safety-sensitive requests have separate safe behavior.
11. **How does it handle emergency wording?** It directs the user to local emergency services or urgent qualified care without diagnosing.
12. **Does it recommend medication?** No; those requests receive a limitation message.
13. **How is prompt injection handled?** Narrow deterministic phrase detection on user inputs and an instruction boundary for retrieved data. It is not complete protection.
14. **Why not fine-tune?** Fine-tuning would not keep a changing evidence corpus current and would not by itself provide citations.
15. **What is chunk overlap for?** To reduce loss of context at boundaries; too much overlap increases duplicate retrieval.
16. **How are chunk IDs made stable?** A digest incorporates document ID, chunk position, and chunk text.
17. **What is the local persistence trade-off?** Simple and inspectable but not transactional, concurrent-safe, or scalable.
18. **Why mock generation?** Deterministic, network-free tests with no credentials or usage costs.
19. **Is a real provider implemented?** Optional OpenAI-compatible and Gemini adapters exist; their runtime use requires credentials and network, neither used by tests or CI.
20. **How are secrets managed?** Environment variables, ignored `.env`, and placeholders only in `.env.example`.
21. **What does the request ID do?** Correlates a response with privacy-aware endpoint/status/latency logs.
22. **What does recall@k measure?** Relevant expected chunks retrieved within the first k results.
23. **What does MRR measure?** Reciprocal rank of the first relevant result averaged across questions.
24. **What does nDCG measure?** Ranking quality with a logarithmic penalty for lower ranked relevant results.
25. **Are evaluation values clinical benchmarks?** No; synthetic deterministic retrieval proxies only.
26. **How is the API tested offline?** FastAPI TestClient, deterministic corpus, mock mode, and no provider calls.
27. **What is a key deployment gap?** Authentication, distributed rate limiting, robust storage, and production monitoring are absent.
28. **How would you scale retrieval?** Add measured embeddings and indexed vector/lexical stores, then evaluate latency and recall on rights-cleared data.
29. **How would you improve reranking?** Add a validated cross-encoder behind an interface and compare against the same reproducible test set.
30. **What does the system promise medically?** Educational retrieval only; no clinical accuracy, validation, or treatment suitability is claimed.

Provider-specific behavior, semantic retrieval quality, cost, and performance depend on actual model, dataset, and provider configuration; this repository has not measured them.
