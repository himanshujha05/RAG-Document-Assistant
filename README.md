# RAG Document Assistant

Upload any PDF. Ask questions about it in plain English. Get accurate answers — powered by GPT-4o.

---

## What Is This?

Imagine you have a 200-page research paper. You don't want to read the whole thing. You just want to ask:

> "What methodology did they use?" or "What were the key findings?"

This app does exactly that. You upload a PDF, and it lets you have a conversation with it.

It's built using a technique called **RAG (Retrieval-Augmented Generation)** — a pattern used in real production AI systems at companies like Notion, Cursor, and Perplexity.

---

## How It Works — The Big Picture

```
You upload a PDF
       │
       ▼
  Text is extracted and split into small chunks
       │
       ▼
  Each chunk is converted into a vector (a list of numbers
  that represents its meaning) and stored in a database
       │
       ▼
  You ask a question
       │
       ▼
  Your question is also converted into a vector
       │
       ▼
  The database finds the chunks most similar to your question
       │
       ▼
  Those chunks + your question are sent to GPT-4o
       │
       ▼
  GPT-4o reads only the relevant parts and gives you an answer
```

This approach is smarter than just feeding the whole document to GPT-4o because:
- GPT-4o has a context limit (can't read 500 pages at once)
- It's cheaper (you only send the relevant parts)
- It's more accurate (less irrelevant noise in the prompt)

---

## Key Concepts Explained Simply

### What is a Vector / Embedding?
A vector is a way to represent text as numbers so a computer can measure how "similar" two pieces of text are. For example, "dog" and "puppy" would have vectors close to each other. "Dog" and "tax return" would be far apart. OpenAI's embedding model converts your text chunks into these vectors.

### What is a Vector Database (ChromaDB)?
A normal database searches by exact keywords. A vector database searches by *meaning*. You ask "what's the revenue?" and it finds chunks that talk about income, earnings, and profits — even if they never say the word "revenue." ChromaDB stores your vectors on disk locally.

### What is RAG?
RAG = Retrieval-Augmented Generation. Instead of asking GPT-4o to answer from memory (which can hallucinate), you *retrieve* relevant facts first and *augment* the prompt with them before *generating* an answer. The model is grounded in your actual document.

### What is Chunking?
PDFs can be thousands of words. We can't embed the whole thing as one piece — the meaning gets too diluted. So we split it into overlapping chunks of ~800 characters. The overlap (100 characters) ensures a sentence that falls at a boundary still appears fully in at least one chunk.

---

## Tech Stack

| Layer | Tool | Why |
|---|---|---|
| API Framework | FastAPI (Python) | Fast, modern, auto-generates docs |
| LLM | GPT-4o | Best reasoning, grounded answers |
| Embeddings | text-embedding-3-small | Cheap, accurate, 1536 dimensions |
| Vector DB | ChromaDB | Local-first, no cloud account needed |
| PDF Parsing | LangChain + pypdf | Battle-tested PDF text extraction |
| Containerization | Docker | Runs the same on any machine |
| CI/CD | GitHub Actions | Auto-tests every push |

---

## Project Structure

```
rag-document-assistant/
├── app/
│   ├── main.py              ← API endpoints (/upload, /ask, /health)
│   ├── config.py            ← Reads environment variables (.env)
│   ├── models.py            ← Request/response data shapes
│   └── services/
│       ├── pdf_service.py   ← PDF parsing and text chunking
│       ├── vector_service.py← ChromaDB: store and query embeddings
│       └── llm_service.py   ← GPT-4o: builds prompt and gets answer
├── tests/
│   ├── test_upload.py       ← Tests for the /upload endpoint
│   └── test_ask.py          ← Tests for the /ask endpoint
├── Dockerfile               ← Containerizes the app
├── docker-compose.yml       ← Runs the app with one command
├── requirements.txt         ← Python dependencies
└── .env.example             ← Template for your API key
```

Each file has one job. `main.py` handles HTTP. `pdf_service.py` handles parsing. `vector_service.py` handles the database. `llm_service.py` handles GPT-4o. They don't know about each other — `main.py` wires them together.

---

## API Endpoints

### `POST /upload`
Upload a PDF file. Returns a `document_id` you use for all future questions.

**Request:** `multipart/form-data` with a `.pdf` file

**Response:**
```json
{
  "document_id": "a3f9c2b1d4e8",
  "chunk_count": 47,
  "filename": "research-paper.pdf",
  "message": "Successfully processed 47 chunks."
}
```

---

### `POST /ask`
Ask a question about an uploaded document.

**Request:**
```json
{
  "question": "What are the main conclusions?",
  "document_id": "a3f9c2b1d4e8"
}
```

**Response:**
```json
{
  "answer": "The paper concludes that...",
  "source_chunks": ["...relevant passage 1...", "...relevant passage 2..."],
  "document_id": "a3f9c2b1d4e8"
}
```

The `source_chunks` field shows exactly which parts of the document GPT-4o used to form its answer. This makes the system auditable — you can verify the answer is grounded in real text.

---

### `GET /health`
Check if the server is running.

```json
{ "status": "ok" }
```

---

## Getting Started

### Prerequisites
- Python 3.12+
- An [OpenAI API key](https://platform.openai.com/api-keys)
- Docker (optional, for containerized run)

### Local Setup

```bash
# 1. Clone the repo
git clone https://github.com/your-username/rag-document-assistant.git
cd rag-document-assistant

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Add your API key
cp .env.example .env
# Open .env and set OPENAI_API_KEY=sk-...

# 5. Run the server
uvicorn app.main:app --reload
```

Open `http://localhost:8000/docs` — you'll see the full interactive API explorer.

### Docker Setup

```bash
cp .env.example .env
# Set your OPENAI_API_KEY in .env

docker-compose up --build
```

Same result, no Python setup needed.

---

## Running Tests

```bash
pytest tests/ -v
```

Tests mock all external calls (OpenAI, ChromaDB) so they run instantly without an API key. You should see 8 tests pass.

---

## Try It — Step by Step

```bash
# Step 1: Upload a PDF
curl -X POST http://localhost:8000/upload \
  -F "file=@/path/to/your-document.pdf"

# Output: {"document_id": "a3f9c2b1d4e8", "chunk_count": 47, ...}

# Step 2: Ask a question using the document_id from step 1
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is this document about?",
    "document_id": "a3f9c2b1d4e8"
  }'
```

Or use the browser UI at `http://localhost:8000/docs` — no curl needed.

---

## What's Coming Next

| Phase | What Gets Added |
|---|---|
| Phase 2 | API key authentication, async PDF processing, error handling middleware |
| Phase 3 | Pinecone cloud vector DB, multi-document support, conversation history |
| Phase 4 | GitHub Actions CI/CD pipeline, production Docker hardening |
| Phase 5 | Simple frontend UI |

---

## Why This Project Matters (for Recruiters / Reviewers)

This project demonstrates:

- **RAG architecture** — the dominant pattern for production AI applications
- **Clean service layer design** — each concern is isolated and independently testable
- **Input validation** — Pydantic models reject bad data before it reaches business logic
- **Immutable data patterns** — services return new objects, never mutate inputs
- **Test coverage** — endpoints tested with mocks, no real API calls needed in CI
- **Containerization** — runs identically in dev and production via Docker
- **Environment-based config** — no hardcoded secrets anywhere in the codebase
