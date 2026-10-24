"""Print retrieval rankings for a question without logging full question text."""

import argparse

from app.services.retrieval_service import search


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    args = parser.parse_args()
    for mode in ("dense", "bm25", "hybrid", "hybrid_rerank"):
        print(
            mode,
            [
                (item["chunk_id"], round(item.get("score", 0), 4))
                for item in search(args.question, mode)
            ],
        )


if __name__ == "__main__":
    main()
