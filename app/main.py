from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from app.models import AskRequest, AskResponse, UploadResponse
from app.services.llm_service import ask_llm
from app.services.pdf_service import parse_and_chunk_pdf
from app.services.vector_service import query_chunks, store_chunks

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
