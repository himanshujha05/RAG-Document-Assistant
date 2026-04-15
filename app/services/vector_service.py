import chromadb
from chromadb.utils import embedding_functions

from app.config import settings

# Module-level singletons — created once, reused on every request
_client: chromadb.PersistentClient | None = None
_embed_fn: embedding_functions.OpenAIEmbeddingFunction | None = None


def _get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return _client


def _get_embed_fn() -> embedding_functions.OpenAIEmbeddingFunction:
    global _embed_fn
    if _embed_fn is None:
        _embed_fn = embedding_functions.OpenAIEmbeddingFunction(
            api_key=settings.openai_api_key,
            model_name="text-embedding-3-small",
        )
    return _embed_fn


def _collection(document_id: str) -> chromadb.Collection:
    """Each document gets its own ChromaDB collection."""
    return _get_client().get_or_create_collection(
        name=f"doc_{document_id}",
        embedding_function=_get_embed_fn(),
    )


def store_chunks(document_id: str, chunks: list[str]) -> None:
    """Embed and persist all chunks for a document."""
    collection = _collection(document_id)
    ids = [f"{document_id}_chunk_{i}" for i in range(len(chunks))]
    collection.upsert(documents=chunks, ids=ids)


def query_chunks(document_id: str, question: str) -> list[str]:
    """Return the top-k most relevant chunks for a question."""
    collection = _collection(document_id)
    results = collection.query(
        query_texts=[question],
        n_results=min(settings.max_retrieved_chunks, collection.count()),
    )
    documents = results.get("documents", [[]])[0]
    return [doc for doc in documents if doc]


def get_all_chunks(document_id: str) -> list[str]:
    """Return every stored chunk for a document (used for summarization)."""
    collection = _collection(document_id)
    count = collection.count()
    if count == 0:
        return []
    results = collection.get()
    return [doc for doc in (results.get("documents") or []) if doc]


def list_documents() -> list[dict]:
    """Return all document collections with their chunk counts."""
    client = _get_client()
    collections = client.list_collections()
    documents = []
    for col in collections:
        if col.name.startswith("doc_"):
            document_id = col.name[4:]  # strip "doc_" prefix
            full_col = client.get_collection(
                name=col.name,
                embedding_function=_get_embed_fn(),
            )
            documents.append({"document_id": document_id, "chunk_count": full_col.count()})
    return documents


def delete_document(document_id: str) -> bool:
    """Delete a document's collection. Returns False if it didn't exist."""
    client = _get_client()
    collection_name = f"doc_{document_id}"
    try:
        client.delete_collection(name=collection_name)
        return True
    except Exception:
        return False
