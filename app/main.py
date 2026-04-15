from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import (
    AskRequest,
    AskResponse,
    DocumentInfo,
    ExtractRequest,
    ExtractResponse,
    ListDocumentsResponse,
    SummarizeRequest,
    SummarizeResponse,
    UploadResponse,
)
from app.services.llm_service import ask_llm, extract_document_info, summarize_document
from app.services.pdf_service import parse_and_chunk_pdf
from app.services.vector_service import (
    delete_document,
    get_all_chunks,
    list_documents,
    query_chunks,
    store_chunks,
)

app = FastAPI(
    title="RAG Document Assistant",
    description="Upload PDFs and ask questions about them using GPT-4o.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_BYTES = 20 * 1024 * 1024  # 20 MB


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/upload", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)) -> UploadResponse:
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    content = await file.read()

    if len(content) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="File exceeds 20 MB limit.")

    if len(content) == 0:
        raise HTTPException(status_code=400, detail="Uploaded file is empty.")

    document_id, chunks = parse_and_chunk_pdf(content, file.filename or "upload.pdf")

    if not chunks:
        raise HTTPException(status_code=422, detail="Could not extract text from PDF.")

    store_chunks(document_id, chunks)

    return UploadResponse(
        document_id=document_id,
        chunk_count=len(chunks),
        filename=file.filename or "upload.pdf",
        message=f"Successfully processed {len(chunks)} chunks.",
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(body: AskRequest) -> AskResponse:
    relevant_chunks = query_chunks(body.document_id, body.question)

    if not relevant_chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{body.document_id}'. Upload it first.",
        )

    answer = ask_llm(body.question, relevant_chunks)

    return AskResponse(
        answer=answer,
        source_chunks=relevant_chunks,
        document_id=body.document_id,
    )


@app.get("/documents", response_model=ListDocumentsResponse)
def list_all_documents() -> ListDocumentsResponse:
    """List every uploaded document and how many chunks each has."""
    docs = list_documents()
    return ListDocumentsResponse(
        documents=[DocumentInfo(**d) for d in docs],
        total=len(docs),
    )


@app.delete("/document/{document_id}")
def remove_document(document_id: str) -> dict:
    """Permanently delete a document and all its stored embeddings."""
    deleted = delete_document(document_id)
    if not deleted:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{document_id}'.",
        )
    return {"deleted": True, "document_id": document_id}


@app.post("/summarize", response_model=SummarizeResponse)
def summarize(body: SummarizeRequest) -> SummarizeResponse:
    """Generate a concise summary of an entire uploaded document."""
    chunks = get_all_chunks(body.document_id)
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{body.document_id}'. Upload it first.",
        )
    summary = summarize_document(chunks)
    return SummarizeResponse(
        document_id=body.document_id,
        summary=summary,
        chunks_used=len(chunks),
    )


@app.post("/extract", response_model=ExtractResponse)
def extract(body: ExtractRequest) -> ExtractResponse:
    """Extract key points, named entities, and main topics from a document."""
    chunks = get_all_chunks(body.document_id)
    if not chunks:
        raise HTTPException(
            status_code=404,
            detail=f"No document found with id '{body.document_id}'. Upload it first.",
        )
    result = extract_document_info(chunks)
    return ExtractResponse(
        document_id=body.document_id,
        key_points=result.get("key_points", []),
        entities=result.get("entities", []),
        topics=result.get("topics", []),
    )
