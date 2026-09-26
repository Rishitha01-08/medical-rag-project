# Offline evaluation

Run `MOCK_MODE=true python -m evaluation.run_evaluation`. The small JSONL set and corpus are synthetic educational examples. Recall@k, Precision@k, MRR and nDCG measure retrieval against expected synthetic chunk identifiers. Citation support and groundedness are deterministic citation-integrity proxies, not judgments of medical correctness. Latencies are local process observations and not production benchmarks. The command writes `evaluation/reports/mock-evaluation.json`; reports are ignored by Git and should be generated locally.
