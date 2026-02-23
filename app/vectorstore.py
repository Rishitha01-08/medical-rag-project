from sentence_transformers import SentenceTransformer
import chromadb
import os

# Load embedding model
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")

# Initialize ChromaDB client
chroma_client = chromadb.Client()

# Create or get collection
collection = chroma_client.get_or_create_collection(
    name="medical_docs"
)

def load_documents():
    """
    Load medical documents into vector database
    """
    file_path = "data/raw/medical.txt"

    if not os.path.exists(file_path):
        raise FileNotFoundError("medical.txt not found")

    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()

    documents = [text]

    metadatas = [{
        "source": "Harrison's Internal Medicine",
        "section": "Hypertension",
        "page": "1221"
    }]

    ids = ["doc_1"]

    embeddings = embedding_model.encode(documents).tolist()

    collection.add(
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas,
        ids=ids
    )

    print("✅ Documents loaded into vector database")

def query_documents(query: str, k: int = 2):
    """
    Retrieve relevant medical context
    """
    query_embedding = embedding_model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_embedding,
        n_results=k
    )

    return results
