from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    openai_api_key: str
    chroma_persist_dir: str = "./chroma_db"
    chunk_size: int = 800
    chunk_overlap: int = 100
    max_retrieved_chunks: int = 5

    class Config:
        env_file = ".env"


settings = Settings()
