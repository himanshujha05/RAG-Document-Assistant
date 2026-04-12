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
