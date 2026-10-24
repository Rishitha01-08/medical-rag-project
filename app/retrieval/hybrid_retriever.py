"""Dense and lexical retrieval composition."""

from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.dense_retriever import DenseRetriever
from app.retrieval.fusion import reciprocal_rank_fusion


def retrieve(documents, query, mode="hybrid", dense_k=5, bm25_k=5):
    dense = DenseRetriever(documents).search(query, dense_k)
    bm25 = BM25Retriever(documents).search(query, bm25_k)
    if mode == "dense":
        return dense
    if mode == "bm25":
        return bm25
    if mode not in {"hybrid", "hybrid_rerank"}:
        raise ValueError("Unsupported retrieval mode")
    return reciprocal_rank_fusion({"dense": dense, "bm25": bm25})
