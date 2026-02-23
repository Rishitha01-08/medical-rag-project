from app.vectorstore import query_documents
from transformers import pipeline

# Load LLM
llm = pipeline(
    "text-generation",
    model="google/gemma-2b",
    max_new_tokens=200
)

def generate_answer(question: str):
    retrieved = query_documents(question)

    context = retrieved["documents"][0][0]
    metadata = retrieved["metadatas"][0][0]

    prompt = f"""
You are a medical assistant.
Answer ONLY using the context below.
Cite the source clearly.

Context:
{context}

Question:
{question}

Answer (include citation):
"""

    response = llm(prompt)[0]["generated_text"]

    return {
        "answer": response,
        "citation": metadata,
        "context_used": context
    }
