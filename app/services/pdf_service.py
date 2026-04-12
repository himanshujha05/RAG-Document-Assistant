import hashlib
import tempfile
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

from app.config import settings


def generate_document_id(filename: str, content: bytes) -> str:
    """Stable ID based on filename + first 8KB of content."""
    fingerprint = filename.encode() + content[:8192]
    return hashlib.sha256(fingerprint).hexdigest()[:16]


def parse_and_chunk_pdf(file_content: bytes, filename: str) -> tuple[str, list[str]]:
    """
    Parse a PDF and split it into overlapping text chunks.

    Returns:
        document_id: stable hex ID for this document
        chunks: list of text strings ready for embedding
    """
    document_id = generate_document_id(filename, file_content)

    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(file_content)
        tmp_path = Path(tmp.name)

    try:
        loader = PyPDFLoader(str(tmp_path))
        pages = loader.load()
    finally:
        tmp_path.unlink(missing_ok=True)

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    docs = splitter.split_documents(pages)
    chunks = [doc.page_content.strip() for doc in docs if doc.page_content.strip()]

    return document_id, chunks
