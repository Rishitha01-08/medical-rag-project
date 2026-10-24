"""Citation integrity and deterministic response support checks."""


def citation_support(claim_source_ids, retrieved):
    valid = {item["chunk_id"] for item in retrieved}
    if not claim_source_ids:
        return 0.0
    return sum(bool(set(ids)) and set(ids).issubset(valid) for ids in claim_source_ids) / len(
        claim_source_ids
    )


def citations_for(retrieved):
    return [
        {
            "source_id": d["chunk_id"],
            "title": d.get("title", "Educational sample"),
            "source": d.get("source"),
            "source_url": d.get("source_url"),
            "page_number": d.get("page_number"),
            "section": d.get("section"),
            "excerpt": d.get("content", "")[:240],
        }
        for d in retrieved
    ]
