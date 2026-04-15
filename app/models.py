from pydantic import BaseModel, Field


class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000)
    document_id: str = Field(..., min_length=1)


class AskResponse(BaseModel):
    answer: str
    source_chunks: list[str]
    document_id: str


class UploadResponse(BaseModel):
    document_id: str
    chunk_count: int
    filename: str
    message: str


# --- /documents ---

class DocumentInfo(BaseModel):
    document_id: str
    chunk_count: int


class ListDocumentsResponse(BaseModel):
    documents: list[DocumentInfo]
    total: int


# --- /summarize ---

class SummarizeRequest(BaseModel):
    document_id: str = Field(..., min_length=1)


class SummarizeResponse(BaseModel):
    document_id: str
    summary: str
    chunks_used: int


# --- /extract ---

class ExtractRequest(BaseModel):
    document_id: str = Field(..., min_length=1)


class ExtractResponse(BaseModel):
    document_id: str
    key_points: list[str]
    entities: list[str]
    topics: list[str]
