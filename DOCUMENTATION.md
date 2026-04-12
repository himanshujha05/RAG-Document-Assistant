# Complete Project Documentation
# RAG Document Assistant — Everything Explained

> Written for someone who has never built an AI project before.
> Every term is explained. Every piece of code has a reason. Read top to bottom once and you'll understand the whole system.

---

## Table of Contents

1. [What Problem Does This Solve?](#1-what-problem-does-this-solve)
2. [What Is RAG? The Core Idea](#2-what-is-rag-the-core-idea)
3. [How a Request Actually Flows Through the System](#3-how-a-request-actually-flows-through-the-system)
4. [Every Term Defined](#4-every-term-defined)
5. [The Tech Stack — What Each Tool Is and Why](#5-the-tech-stack--what-each-tool-is-and-why)
6. [File-by-File Breakdown](#6-file-by-file-breakdown)
7. [The Two API Endpoints Explained](#7-the-two-api-endpoints-explained)
8. [How OpenAI Is Used (Two Different Ways)](#8-how-openai-is-used-two-different-ways)
9. [How ChromaDB Works Internally](#9-how-chromadb-works-internally)
10. [How PDF Parsing and Chunking Works](#10-how-pdf-parsing-and-chunking-works)
11. [How the Tests Work](#11-how-the-tests-work)
12. [How Docker Works in This Project](#12-how-docker-works-in-this-project)
13. [Environment Variables and Config](#13-environment-variables-and-config)
14. [What Happens When Something Goes Wrong](#14-what-happens-when-something-goes-wrong)
15. [The Full Picture — Everything Connected](#15-the-full-picture--everything-connected)
16. [What You Would Build Next](#16-what-you-would-build-next)

---

## 1. What Problem Does This Solve?

### The Problem with Just Asking GPT-4o

Imagine you have a 300-page legal contract. You want to know what the termination clause says.

You could copy-paste the whole document into ChatGPT. But:
- GPT-4o has a **context limit** — there's a maximum amount of text it can read at once (about 128,000 tokens, roughly 100,000 words). A long document can exceed this.
- Even if it fits, sending 300 pages every time you ask a question is **expensive** — you pay for every word you send to OpenAI.
- The model gets "distracted" by irrelevant content. If you want to know about the termination clause, sending 300 pages of unrelated content makes the answer worse.

### The Solution: Only Send What's Relevant

What if instead of sending the whole document, you could:
1. Find the 3-5 paragraphs most relevant to your question
2. Send only those to GPT-4o
3. GPT-4o answers based on just those paragraphs

That's exactly what this project does. And the technique is called **RAG**.

---

## 2. What Is RAG? The Core Idea

**RAG** stands for **Retrieval-Augmented Generation**.

Break it apart:
- **Retrieval** = finding relevant information from a database
- **Augmented** = adding that information to your question
- **Generation** = having the AI generate an answer

In plain English: **Search first, then ask the AI.**

### Without RAG:
```
You → "What is the termination clause?" → GPT-4o → Answer
         (GPT-4o uses only its training data, can hallucinate)
```

### With RAG:
```
You → "What is the termination clause?"
         ↓
     Search your document for relevant paragraphs
         ↓
     Found: "Section 12.3: Either party may terminate..."
         ↓
     Send to GPT-4o: "Using this text: [Section 12.3...], what is the termination clause?"
         ↓
     GPT-4o → Accurate answer grounded in your actual document
```

The AI is not guessing from memory. It's reading the real text and summarizing it for you.

---

## 3. How a Request Actually Flows Through the System

Here is the complete journey of a PDF upload and then a question — step by step.

### Part A: Uploading a PDF

```
Step 1: You send a PDF file to POST /upload

Step 2: FastAPI receives it, checks:
        - Is it actually a PDF? (content type check)
        - Is it under 20MB? (size check)
        - Is it not empty? (empty file check)

Step 3: pdf_service.py
        - Saves the file temporarily to disk (pypdf needs a file path)
        - pypdf reads every page and extracts all the text
        - The text is split into chunks of ~800 characters with 100-char overlap
        - Temporary file is deleted
        - A document_id is generated (a short hash/fingerprint of the file)

Step 4: vector_service.py
        - Takes all the text chunks
        - Sends them to OpenAI: "Convert these to embeddings"
        - OpenAI returns a list of vectors (one per chunk)
        - ChromaDB stores: the text, the vector, and the chunk ID — all linked to your document_id

Step 5: You receive back:
        { "document_id": "a3f9c2b1", "chunk_count": 47 }
        Save this document_id — you need it to ask questions
```

### Part B: Asking a Question

```
Step 1: You send POST /ask with your question and document_id

Step 2: FastAPI validates the request

Step 3: vector_service.py
        - Takes your question: "What is the termination clause?"
        - Sends it to OpenAI: "Convert this question to an embedding"
        - OpenAI returns a vector for your question
        - ChromaDB compares your question's vector to all stored chunk vectors
        - Returns the top 5 most similar chunks

Step 4: llm_service.py
        - Builds a prompt:
          "You are a document assistant.
           Context: [chunk1] [chunk2] [chunk3] [chunk4] [chunk5]
           Question: What is the termination clause?"
        - Sends this to GPT-4o
        - GPT-4o reads the context and generates an answer

Step 5: You receive back:
        {
          "answer": "According to Section 12.3, either party may...",
          "source_chunks": ["Section 12.3: Either party may terminate..."],
          "document_id": "a3f9c2b1"
        }
```

---

## 4. Every Term Defined

This section explains every technical word used in this project. Read this like a glossary.

---

### API (Application Programming Interface)
A way for two programs to talk to each other. Your frontend (or curl command) talks to this backend through an API. Think of it like a menu at a restaurant — it tells you what you can order (what requests you can make) and what you'll get back.

---

### Endpoint
A specific URL that does a specific thing. This project has three:
- `POST /upload` — upload a PDF
- `POST /ask` — ask a question
- `GET /health` — check if the server is running

"POST" and "GET" are HTTP methods — they tell the server what kind of action you're performing. GET = "give me something," POST = "here's some data, do something with it."

---

### FastAPI
A Python framework for building APIs. You write Python functions, add decorators like `@app.post("/upload")`, and FastAPI handles everything else — routing requests to the right function, validating input, generating documentation, etc.

FastAPI is called "Fast" for two reasons:
1. It's fast to develop with (less code than alternatives like Flask or Django)
2. It performs fast at runtime (uses Python's async capabilities)

---

### Pydantic
A Python library for data validation. You define what shape your data should be:
```python
class AskRequest(BaseModel):
    question: str
    document_id: str
```
If someone sends an empty question or forgets the document_id, Pydantic rejects it automatically before your code runs. This prevents bad data from reaching your business logic.

---

### LLM (Large Language Model)
A type of AI trained on huge amounts of text that can understand and generate human language. GPT-4o is an LLM. It's the "brain" that reads your document chunks and formulates an answer.

---

### GPT-4o
OpenAI's most capable model (as of 2024). The "o" stands for "omni" — it can handle text, images, and audio. We use it for text only in this project. It's what actually reads the retrieved document chunks and writes the answer.

---

### Token
The unit LLMs think in. A token is roughly 0.75 words. "Hello world" is 2 tokens. You pay OpenAI per token — for both input (the text you send) and output (the text it writes back). This is why we don't send the whole document — we only send the relevant chunks to keep costs low.

---

### Embedding
A way to convert text into numbers so a computer can measure meaning.

Specifically, an embedding is a **vector** (a list of numbers) that represents the meaning of a piece of text. OpenAI's `text-embedding-3-small` model converts text to a list of 1536 numbers.

Example (simplified):
```
"The dog ran fast"  →  [0.23, -0.87, 0.41, 0.02, ...]  (1536 numbers)
"The puppy sprinted" →  [0.25, -0.84, 0.39, 0.05, ...]  (1536 numbers, very similar!)
"Tax return deadline" → [0.91,  0.12, -0.67, 0.88, ...]  (1536 numbers, very different)
```

Similar meaning → similar numbers. This lets you search by meaning, not keywords.

---

### Vector
A list of numbers. An embedding IS a vector. In this project, every text chunk and every question gets converted into a vector of 1536 numbers. The database then does math on these vectors to find which ones are close to each other.

---

### Cosine Similarity
The math used to measure how similar two vectors are. It gives a score between -1 and 1:
- **1.0** = identical meaning
- **0.0** = completely unrelated
- **-1.0** = opposite meaning (rare in text)

When you ask a question, ChromaDB calculates the cosine similarity between your question's vector and every stored chunk's vector. The top 5 closest chunks are your "relevant" results.

---

### Vector Database
A database designed to store and search vectors efficiently. Unlike a normal database that searches by exact match ("find rows where name = 'John'"), a vector database searches by similarity ("find the 5 vectors closest to this one").

ChromaDB is the vector database in this project. It runs locally — no internet connection needed, data is stored in a folder on your machine (`./chroma_db/`).

---

### ChromaDB
An open-source vector database. It:
- Runs in-process (no separate server to start)
- Persists data to disk automatically
- Has built-in integration with OpenAI's embedding model
- Is easy to swap out for Pinecone (cloud) later

In this project, each document gets its own "collection" in ChromaDB — think of it like a separate table per document.

---

### Chunk
A piece of a larger document. Since we can't embed a whole 300-page PDF as one unit, we split it into chunks of ~800 characters. Each chunk gets its own embedding and is stored separately. When you search, you find relevant chunks, not the whole document.

---

### Chunk Overlap
When splitting text into chunks, we allow chunks to share 100 characters with their neighbors. This prevents losing meaning at boundaries.

Without overlap:
```
Chunk 1: "...the company was founded in 1995. The"
Chunk 2: "founders initially struggled with funding..."
```
The sentence "The founders initially struggled" gets split. If your question is about the founders, you might miss this context.

With 100-character overlap:
```
Chunk 1: "...the company was founded in 1995. The founders initially"
Chunk 2: "The founders initially struggled with funding..."
```
The sentence appears fully in at least one chunk.

---

### RecursiveCharacterTextSplitter
The LangChain tool used to split PDFs into chunks. It tries to split at natural boundaries in this order:
1. Double newlines (paragraph breaks) — best split point
2. Single newlines
3. Periods (sentence ends)
4. Spaces (word boundaries)
5. Individual characters (last resort)

It "recursively" tries each separator until chunks are within the target size. This preserves logical structure — paragraphs and sentences stay together when possible.

---

### LangChain
A Python library for building LLM applications. In this project, we use two things from it:
- `PyPDFLoader` — reads PDF files and extracts text page by page
- `RecursiveCharacterTextSplitter` — splits text into chunks intelligently

LangChain has hundreds of other tools (connectors to different LLMs, vector databases, memory systems) that become useful in later phases.

---

### pypdf
A pure-Python library that reads PDF files. It handles the low-level parsing of PDF format (which is actually quite complex — PDFs are not just text files). LangChain's `PyPDFLoader` uses pypdf under the hood.

---

### Document ID
A short string that uniquely identifies your uploaded document. It's generated by taking a SHA-256 hash of the filename + first 8KB of file content. Same file = same ID every time. You use this ID in every `/ask` request so the system knows which document's chunks to search.

---

### Hash / SHA-256
A mathematical function that takes any input and produces a fixed-length output (64 hex characters for SHA-256). Same input always gives the same output. Different inputs give completely different outputs. We use the first 16 characters as the document_id — collision probability is astronomically low.

---

### uvicorn
The web server that runs your FastAPI app. FastAPI is a framework (it defines how to write your app), uvicorn is the server (it actually listens for network connections and runs your app). You start the server with `uvicorn app.main:app --reload`.

---

### Docker
A tool that packages your application and all its dependencies into a container — a self-contained environment that runs the same on any machine. No more "it works on my machine" problems. You define your environment in a `Dockerfile`, run `docker-compose up`, and the app starts identically on your laptop, a server, or in the cloud.

---

### Docker Compose
A tool that runs multiple Docker containers together. In this project there's only one container (the API), but in future phases you might add a database container, a Redis container, etc. Compose starts them all with one command and wires up their network connections.

---

### Environment Variable
A value stored outside your code, in the operating system or a `.env` file. API keys, database URLs, and config settings should NEVER be hardcoded in code — if you push code to GitHub, anyone can see them. Instead, you store them as environment variables and load them at runtime.

```
# .env file (never committed to git)
OPENAI_API_KEY=sk-abc123...
```

---

### Pydantic Settings
The `pydantic-settings` library reads environment variables and exposes them as typed Python attributes. If a required variable is missing, the app crashes immediately with a clear error — instead of crashing later with a confusing `None` error.

---

### Middleware (CORS)
Code that runs on every request before it reaches your endpoint. CORS (Cross-Origin Resource Sharing) middleware handles a browser security rule that blocks web pages from calling APIs on different domains. With CORS middleware enabled, any frontend (a React app, a web page) can call your API.

---

### Pytest
Python's testing framework. You write functions that start with `test_`, and pytest automatically finds and runs them. It reports which tests passed and which failed.

---

### Mock / Patch
In tests, you don't want to actually call OpenAI (costs money, slow, needs a real key). `unittest.mock.patch` lets you replace a real function with a fake one for the duration of a test. The fake function returns whatever you tell it to, and your test verifies the code behaves correctly based on those fake responses.

---

### HTTP Status Codes
Numbers that tell the caller what happened:
- `200` — Success
- `400` — Bad request (your fault — you sent bad data)
- `404` — Not found (the resource you asked for doesn't exist)
- `413` — Payload too large (file exceeded size limit)
- `422` — Unprocessable entity (Pydantic validation failed)
- `500` — Internal server error (our fault — something broke in the code)

---

## 5. The Tech Stack — What Each Tool Is and Why

### Python
The language the entire backend is written in. Python is the dominant language in AI/ML because of its ecosystem — NumPy, PyTorch, LangChain, OpenAI SDK, and ChromaDB all have excellent Python libraries.

### FastAPI
Chosen over Flask (older, less features) and Django (overkill for an API-only service). FastAPI gives you:
- Automatic input validation via Pydantic
- Auto-generated Swagger UI at `/docs` (interactive browser testing)
- Async support (handles many requests at once efficiently)
- Type hints that make code self-documenting

### OpenAI API
Used for two separate things in this project:
1. **text-embedding-3-small** — converts text to vectors. Cheap ($0.02 per 1M tokens).
2. **GPT-4o** — reads context chunks and writes answers. More expensive but most accurate.

### ChromaDB
Chosen because it runs locally with zero setup — no account, no server, no cloud. Data persists in a folder (`./chroma_db/`). In Phase 3, it gets swapped for Pinecone (cloud-hosted, scales infinitely) with minimal code changes.

### LangChain
We only use two components from it: PDF loading and text splitting. LangChain provides battle-tested implementations of these — writing your own PDF parser from scratch would be a project in itself.

### Docker
Every modern production deployment uses containers. Having a working Dockerfile from day one shows production awareness. It also means anyone can clone this repo and run it in 2 commands without installing Python.

---

## 6. File-by-File Breakdown

### `app/config.py` — The Settings File
```python
class Settings(BaseSettings):
    openai_api_key: str          # Required. App won't start without this.
    chroma_persist_dir: str      # Where to save ChromaDB files. Default: ./chroma_db
    chunk_size: int              # Characters per chunk. Default: 800
    chunk_overlap: int           # Overlap between chunks. Default: 100
    max_retrieved_chunks: int    # How many chunks to retrieve per question. Default: 5
```
All other files import `settings` from here. There's one place to change config. No scattered `os.getenv()` calls.

---

### `app/models.py` — The Data Contracts
Defines what valid requests and responses look like.

`AskRequest` — what you send to `/ask`:
- `question`: a string, 1-1000 characters (prevents empty questions and massive inputs)
- `document_id`: a string, at least 1 character

`AskResponse` — what you get back from `/ask`:
- `answer`: the GPT-4o answer
- `source_chunks`: the actual document excerpts used
- `document_id`: echoed back for confirmation

`UploadResponse` — what you get back from `/upload`:
- `document_id`: use this in all future `/ask` calls
- `chunk_count`: how many chunks were stored
- `filename`: echoed back
- `message`: human-readable success message

---

### `app/services/pdf_service.py` — The PDF Parser
Two functions:

**`generate_document_id(filename, content)`**
Creates a stable ID by hashing the filename + first 8KB of content. Same file always gets same ID. Different files get different IDs.

**`parse_and_chunk_pdf(file_content, filename)`**
1. Writes bytes to a temp file (pypdf needs a path, not bytes)
2. Uses `PyPDFLoader` to extract text from every page
3. Deletes the temp file (cleanup)
4. Uses `RecursiveCharacterTextSplitter` to chunk the text
5. Strips whitespace from each chunk, removes empties
6. Returns `(document_id, [chunk1, chunk2, ...])`

---

### `app/services/vector_service.py` — The ChromaDB Manager
Three functions:

**`_collection(document_id)`**
Gets or creates a ChromaDB collection for this document. Each document has its own isolated collection.

**`store_chunks(document_id, chunks)`**
Sends all chunks to ChromaDB. ChromaDB calls OpenAI to embed them, then stores both the text and the vectors. Uses `upsert` — if chunks for this document already exist, they get replaced (not duplicated).

**`query_chunks(document_id, question)`**
Sends the question to ChromaDB. ChromaDB embeds the question, compares it to all stored chunk vectors, returns the top 5 most similar chunks as plain text strings.

---

### `app/services/llm_service.py` — The GPT-4o Caller
One main function:

**`ask_llm(question, context_chunks)`**
1. Joins the context chunks with separator lines
2. Builds a prompt: system message (role definition) + user message (context + question)
3. Calls GPT-4o with `temperature=0.0` (deterministic, no creativity — we want facts)
4. Returns the text answer

The system prompt explicitly tells GPT-4o: "Only use the provided context. Don't make things up." This is critical for accuracy.

---

### `app/main.py` — The Entry Point
Wires everything together. Defines the two main endpoints:

**`POST /upload`**
```
Receive file → validate → parse_and_chunk_pdf → store_chunks → return UploadResponse
```

**`POST /ask`**
```
Receive question + document_id → query_chunks → ask_llm → return AskResponse
```

Also has `GET /health` which just returns `{"status": "ok"}` — used by Docker health checks and monitoring systems to verify the server is alive.

---

## 7. The Two API Endpoints Explained

### POST /upload

**Purpose:** Take a PDF, extract its text, split it into chunks, embed each chunk, store in ChromaDB.

**Input:** A PDF file sent as `multipart/form-data` (the standard way browsers and curl send files).

**Validations performed:**
1. Content type must be `application/pdf`
2. File must not be empty
3. File must be under 20MB
4. PDF must contain extractable text (some PDFs are just scanned images — we can't read those yet)

**What it does internally:**
```
file bytes
    ↓
generate document_id (hash of filename + content)
    ↓
write to temp file → pypdf reads it → extract text → delete temp file
    ↓
split text into ~800-char chunks with 100-char overlap
    ↓
for each chunk: OpenAI converts it to a 1536-number vector
    ↓
ChromaDB stores: chunk text + vector + chunk_id
    ↓
return { document_id, chunk_count, filename, message }
```

**Output:**
```json
{
    "document_id": "a3f9c2b1d4e8f701",
    "chunk_count": 47,
    "filename": "contract.pdf",
    "message": "Successfully processed 47 chunks."
}
```

---

### POST /ask

**Purpose:** Answer a question about a previously uploaded document.

**Input:** JSON with `question` and `document_id`.

**What it does internally:**
```
question + document_id
    ↓
OpenAI converts question to a 1536-number vector
    ↓
ChromaDB finds 5 chunks with most similar vectors
    ↓
Build prompt: "Context: [5 chunks]\n\nQuestion: [question]"
    ↓
GPT-4o reads prompt and writes an answer
    ↓
return { answer, source_chunks, document_id }
```

**Why return source_chunks?**
This is called **grounding** — showing your work. Instead of just trusting the AI's answer, you can read the exact passages it used. If the answer seems wrong, you can check whether the right chunks were retrieved.

---

## 8. How OpenAI Is Used (Two Different Ways)

This is one of the most important things to understand. OpenAI is called **twice**, for completely different purposes.

### Call 1: Embeddings (text-embedding-3-small)

**When:** During upload (for each chunk) and during questions (for the question itself)

**What it does:** Converts text to a vector (list of 1536 numbers)

**Why 1536 numbers?** That's the dimensionality of this particular model. More dimensions = more nuance in representation. `text-embedding-3-small` is a balance of quality and cost.

**Cost:** Very cheap. ~$0.02 per 1 million tokens. A 50-page PDF might use 50,000 tokens = $0.001.

**It does NOT generate text.** It only converts text to numbers. It has no "intelligence" in the traditional sense — it's a mathematical transformation.

---

### Call 2: Chat Completion (GPT-4o)

**When:** During every `/ask` request

**What it does:** Reads the context chunks + question, writes a natural language answer

**Why GPT-4o and not something cheaper?** Accuracy. This is the model that actually "understands" your document and writes coherent answers. Cheaper models (GPT-3.5) tend to hallucinate or give worse answers on complex documents.

**Cost:** More expensive. GPT-4o is ~$5 per 1M input tokens, $15 per 1M output tokens. A single question with 5 chunks might use 2,000 tokens = $0.01.

**Key setting:** `temperature=0.0` — this makes GPT-4o deterministic. Temperature controls "creativity." At 0, the model always picks the highest-probability next word. At 1.0, it's more creative but less reliable. For a document assistant, you want facts, not creativity.

---

## 9. How ChromaDB Works Internally

### Collections
ChromaDB organizes data into collections (like tables in a regular database). In this project, each document gets its own collection, named `doc_{document_id}`.

This means:
- Searching document A never accidentally returns results from document B
- You can delete a document's data by deleting its collection
- Collections are created with `get_or_create_collection` — safe to call multiple times

### Storage
ChromaDB stores three things per chunk:
1. **id** — a unique string like `a3f9c2b1_chunk_0`
2. **document** — the original text of the chunk
3. **embedding** — the 1536-number vector (stored internally, you don't see it)

All of this is written to disk in the `./chroma_db/` folder.

### Querying
When you call `collection.query(query_texts=["your question"], n_results=5)`:
1. ChromaDB calls OpenAI to embed "your question" → gets a vector
2. Computes cosine similarity between that vector and every stored chunk's vector
3. Returns the 5 chunks with the highest similarity scores

The result includes the original text, so you can pass it directly to GPT-4o.

### Upsert vs Insert
We use `upsert` (update + insert) instead of plain `add`. If you upload the same PDF twice, upsert replaces the existing chunks instead of creating duplicates. This is idempotent — safe to call multiple times with the same data.

---

## 10. How PDF Parsing and Chunking Works

### Step 1: PDF Loading
`PyPDFLoader` opens the PDF and extracts text page by page. Each page becomes a LangChain `Document` object with two fields:
- `page_content`: the text on that page
- `metadata`: includes the page number

### Step 2: The Splitting Problem
A 50-page PDF might have 50,000 words. One big vector for all 50,000 words would be useless — the meaning would be too diluted to find specific topics.

We need small chunks that each cover one idea. But how small?
- Too small (100 chars): chunks lose context, a sentence gets cut in half
- Too large (5000 chars): too much noise in one chunk, similarity search gets confused
- **800 chars is the sweet spot** for most documents (~120-150 words)

### Step 3: RecursiveCharacterTextSplitter
This splitter is "recursive" because it tries separators in priority order:

```
Priority 1: Split at "\n\n" (paragraph breaks)
    → If any chunk is still > 800 chars, recurse:
Priority 2: Split at "\n" (line breaks)
    → If still > 800 chars, recurse:
Priority 3: Split at ". " (sentence ends)
    → If still > 800 chars, recurse:
Priority 4: Split at " " (word boundaries)
    → If still > 800 chars, recurse:
Priority 5: Split at "" (individual characters)
```

This preserves logical structure. A paragraph won't be split unless it's too long. A sentence won't be split unless it has to be.

### Step 4: Overlap
After splitting, adjacent chunks share 100 characters. This is implemented by the splitter — it "backs up" 100 characters before starting the next chunk. The cost is slightly more chunks and slightly more storage. The benefit is no lost context at boundaries.

---

## 11. How the Tests Work

### Why Test?
Every time you change code, there's a risk of breaking something that worked before. Tests catch these regressions automatically. Running `pytest` before any commit tells you immediately if you broke something.

### What We Test
**test_upload.py:**
- Rejecting non-PDF files (should return 400)
- Rejecting empty files (should return 400)
- Successful upload (should return 200 with correct fields)
- Health endpoint (should return 200)

**test_ask.py:**
- Successful question (should return 200 with answer and chunks)
- Question for nonexistent document (should return 404)
- Empty question (should return 422 from Pydantic validation)
- Missing document_id (should return 422 from Pydantic validation)

### Mocking — The Key Concept
Tests should not call real APIs. If they did:
- They would cost money (OpenAI charges per token)
- They would be slow (network calls take seconds)
- They would fail without an internet connection
- They would fail if OpenAI is down

Instead, we use `unittest.mock.patch` to replace the real functions with fakes:

```python
# Instead of actually calling OpenAI and ChromaDB:
with patch("app.main.parse_and_chunk_pdf", return_value=("abc123", ["chunk1", "chunk2"])):
    with patch("app.main.store_chunks"):
        # Now when the endpoint calls these functions, it gets our fake data
        response = client.post("/upload", ...)
```

The test verifies that the endpoint handles the *result* correctly — it doesn't test whether OpenAI works (that's OpenAI's responsibility).

### TestClient
FastAPI provides a `TestClient` that simulates HTTP requests without starting a real server. You call `client.post("/upload", ...)` and it runs your endpoint function directly, returning a fake `Response` object you can check.

---

## 12. How Docker Works in This Project

### The Problem Docker Solves
"It works on my machine" — a classic developer nightmare. Your code depends on:
- Python 3.12 specifically
- Specific versions of 15 libraries
- Specific OS-level dependencies

Docker packages all of this into a single image that runs identically everywhere.

### The Dockerfile Explained
```dockerfile
FROM python:3.12-slim
# Start from an official Python 3.12 image (slim = smaller size)

WORKDIR /app
# All commands run from /app inside the container

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Install dependencies FIRST, before copying code.
# Why? Docker caches layers. If requirements.txt didn't change,
# Docker reuses the cached "pip install" layer and skips it.
# This makes rebuilds much faster.

COPY app/ ./app/
# Copy your application code

EXPOSE 8000
# Document that the container listens on port 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
# The command that runs when the container starts
# --host 0.0.0.0 is important: it means "accept connections from outside the container"
# Without this, the server only accepts connections from inside the container
```

### docker-compose.yml Explained
```yaml
services:
  api:
    build: .                    # Build using the Dockerfile in this directory
    ports:
      - "8000:8000"             # Map host port 8000 to container port 8000
                                # Format: "host:container"
    env_file:
      - .env                    # Load environment variables from .env file
    volumes:
      - ./chroma_db:/app/chroma_db  # Mount local folder into container
                                    # Without this, ChromaDB data disappears on restart
```

### Running It
```bash
docker-compose up --build    # Build the image and start the container
docker-compose up            # Start without rebuilding (faster, uses cached image)
docker-compose down          # Stop and remove containers
```

---

## 13. Environment Variables and Config

### Why Not Hardcode Values?
```python
# NEVER do this:
client = OpenAI(api_key="sk-abc123...")

# Why? If you push this to GitHub, your API key is public.
# Anyone can find it and use your OpenAI account.
# OpenAI will charge YOU for their usage.
```

### The .env File Pattern
```
# .env (local only, never committed to git)
OPENAI_API_KEY=sk-your-real-key-here
CHROMA_PERSIST_DIR=./chroma_db
CHUNK_SIZE=800
CHUNK_OVERLAP=100
MAX_RETRIEVED_CHUNKS=5
```

```
# .env.example (committed to git — shows what variables are needed, but no real values)
OPENAI_API_KEY=sk-...
CHROMA_PERSIST_DIR=./chroma_db
CHUNK_SIZE=800
CHUNK_OVERLAP=100
MAX_RETRIEVED_CHUNKS=5
```

The `.gitignore` file lists `.env` so git never tracks it. `.env.example` is tracked — it tells other developers what variables they need to set up.

### How Config Is Loaded
```python
class Settings(BaseSettings):
    openai_api_key: str   # Required — no default value
    chunk_size: int = 800 # Optional — has a default

settings = Settings()     # Reads .env at import time
```

If `OPENAI_API_KEY` is not set, `Settings()` raises a `ValidationError` immediately when the app starts — not later when the first request comes in. Fail fast = easier debugging.

---

## 14. What Happens When Something Goes Wrong

### Validation Errors (422)
If a request doesn't match the Pydantic model:
```json
{
    "detail": [
        {
            "type": "string_too_short",
            "loc": ["body", "question"],
            "msg": "String should have at least 1 character",
            "input": ""
        }
    ]
}
```
FastAPI generates this automatically. Your code never even runs.

### Business Logic Errors (400, 404, 413)
These are raised manually with `HTTPException`:
```python
if file.content_type != "application/pdf":
    raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
```
FastAPI catches this and returns:
```json
{ "detail": "Only PDF files are accepted." }
```

### Document Not Found (404)
```python
if not relevant_chunks:
    raise HTTPException(
        status_code=404,
        detail=f"No document found with id '{body.document_id}'. Upload it first."
    )
```
This happens when `query_chunks` returns an empty list — either the document_id is wrong, or that collection doesn't exist in ChromaDB yet.

### Unhandled Errors (500)
If something unexpected breaks (network timeout to OpenAI, ChromaDB corruption, etc.), FastAPI returns a 500 with `{"detail": "Internal Server Error"}`. The full traceback is printed to the server logs (visible in your terminal), not exposed to the caller — for security.

---

## 15. The Full Picture — Everything Connected

Here's every component and how it connects to every other component:

```
                          ┌─────────────────────────────────┐
                          │           .env file             │
                          │  OPENAI_API_KEY=sk-...          │
                          └──────────────┬──────────────────┘
                                         │ read at startup
                                         ▼
                          ┌─────────────────────────────────┐
                          │         app/config.py           │
                          │  settings.openai_api_key        │
                          │  settings.chunk_size = 800      │
                          └──────┬──────────────────────────┘
                                 │ imported by all services
              ┌──────────────────┼──────────────────────┐
              ▼                  ▼                       ▼
    ┌──────────────────┐ ┌───────────────────┐ ┌─────────────────────┐
    │  pdf_service.py  │ │ vector_service.py │ │  llm_service.py     │
    │                  │ │                   │ │                     │
    │  PyPDFLoader     │ │  chromadb         │ │  OpenAI()           │
    │  TextSplitter    │ │  OpenAI embeddings│ │  gpt-4o             │
    │  → chunks[]      │ │  → store/query    │ │  → answer text      │
    └────────┬─────────┘ └────────┬──────────┘ └──────────┬──────────┘
             │                    │                        │
             └────────────────────┴────────────────────────┘
                                  │ all used by
                                  ▼
                     ┌────────────────────────┐
                     │      app/main.py        │
                     │                        │
                     │  POST /upload          │
                     │    pdf_service         │
                     │    → vector_service    │
                     │                        │
                     │  POST /ask             │
                     │    vector_service      │
                     │    → llm_service       │
                     └───────────┬────────────┘
                                 │ HTTP
                    ┌────────────┴────────────┐
                    │         YOU             │
                    │  curl / browser / app   │
                    └─────────────────────────┘

                    External Services:
                    ┌─────────────────────────────────────────┐
                    │            OpenAI API                   │
                    │  text-embedding-3-small (vectors)       │
                    │  gpt-4o (answers)                       │
                    └─────────────────────────────────────────┘
                    ┌─────────────────────────────────────────┐
                    │        ChromaDB (local disk)            │
                    │  ./chroma_db/  (persisted vectors)      │
                    └─────────────────────────────────────────┘
```

### Data Flow Summary

**Upload:**
```
PDF bytes → pdf_service (extract + chunk) → vector_service (embed + store in ChromaDB)
```

**Ask:**
```
Question → vector_service (embed + search ChromaDB) → top 5 chunks
                                                              ↓
                                                    llm_service (GPT-4o) → answer
```

---

## 16. What You Would Build Next

### Phase 2 — Reliability & Scale
- **API key authentication** — require callers to have a valid key (so strangers can't use your OpenAI credits)
- **Async upload processing** — for large PDFs, return immediately and process in background
- **Request logging middleware** — log every request with timing, so you can debug issues
- **Better error handling** — catch OpenAI rate limits and retry automatically

### Phase 3 — Cloud & Multi-Document
- **Pinecone** instead of ChromaDB — cloud-hosted vector DB that scales to billions of vectors
- **Multi-document support** — upload 50 PDFs, ask "which document mentions X?"
- **Conversation history** — remember previous questions in a session (right now each `/ask` is stateless)

### Phase 4 — Production Hardening
- **GitHub Actions CI/CD** — automatically run tests on every push, block merges if tests fail
- **Docker production config** — HTTPS, proper logging, health checks
- **Rate limiting** — prevent abuse (max 10 requests per minute per user)

### Phase 5 — Frontend
- A simple React or HTML/JS page where users can drag-drop PDFs and type questions
- Streaming responses — the answer appears word by word instead of all at once (GPT-4o supports this)

---

## Quick Reference Card

| Question | Answer |
|---|---|
| What does this app do? | Upload PDF, ask questions, get AI answers |
| What is RAG? | Search for relevant text first, then ask the AI |
| What is an embedding? | Text converted to numbers to measure meaning similarity |
| What is a vector database? | Database that searches by meaning, not keywords |
| Why split into chunks? | LLMs have context limits; smaller chunks = better search |
| What is chunk overlap? | Shared text at chunk boundaries to prevent split sentences |
| Why temperature=0? | Makes GPT-4o deterministic — factual, not creative |
| What is a document_id? | A hash fingerprint of the file — used to identify which document to search |
| Why mock in tests? | Avoid real API calls — tests run fast and free |
| What does Docker do? | Packages app + dependencies so it runs identically anywhere |
| Why .env file? | Keep API keys out of code and out of git history |

---

*Built with FastAPI · OpenAI · ChromaDB · LangChain · Docker*
