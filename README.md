# Explainable Medical RAG Q&A System

A Retrieval-Augmented Generation (RAG) based Medical Question Answering system
that provides citation-backed, explainable answers using verified medical texts.

## Features
- Medical Q&A using RAG (not pure LLM)
- Vector search using ChromaDB
- Sentence-Transformer embeddings
- Explainable answers with citations
- FastAPI backend with Swagger docs
- Ready for RAGAS evaluation

## Tech Stack
- Python
- FastAPI
- Sentence Transformers
- ChromaDB
- HuggingFace Transformers

## Run Instructions
```bash
uvicorn app.main:app --reload
