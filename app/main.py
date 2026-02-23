from fastapi import FastAPI
from app.vectorstore import load_documents
from app.rag import generate_answer

app = FastAPI(
    title="Explainable Medical RAG API",
    version="1.0"
)

@app.on_event("startup")
def startup_event():
    load_documents()

@app.get("/health")
def health():
    return {"status": "running"}

@app.post("/ask")
def ask(question: str):
    return generate_answer(question)
