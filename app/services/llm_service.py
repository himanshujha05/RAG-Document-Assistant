from openai import OpenAI

from app.config import settings

_client: OpenAI | None = None

SYSTEM_PROMPT = """You are a document assistant. Answer questions using ONLY the context provided below.
If the answer is not in the context, say "I don't have enough information in this document to answer that."
Be concise and accurate."""


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def ask_llm(question: str, context_chunks: list[str]) -> str:
    """Send question + retrieved context to GPT-4o and return its answer."""
    if not context_chunks:
        return "No relevant content found in the document for your question."

    context = "\n\n---\n\n".join(context_chunks)
    user_message = f"Context:\n{context}\n\nQuestion: {question}"

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
        temperature=0.0,
        max_tokens=1024,
    )

    return response.choices[0].message.content or "No response generated."


_SUMMARIZE_SYSTEM = """You are a document summarizer. Given chunks of text from a document,
write a clear, concise summary covering the main ideas. Use 3-5 sentences. Do not add information
that is not in the provided text."""

_EXTRACT_SYSTEM = """You are an information extractor. Given chunks of text from a document,
extract the following and return them as valid JSON with exactly these keys:
- "key_points": list of 5-8 important facts or statements (strings)
- "entities": list of notable names, organizations, places, or products mentioned (strings, deduplicated)
- "topics": list of 3-6 main subject areas or themes covered (strings)

Return ONLY the JSON object, no markdown fences, no explanation."""


def summarize_document(chunks: list[str]) -> str:
    """Summarize all chunks of a document into a short paragraph."""
    if not chunks:
        return "No content available to summarize."

    # Sample evenly across the document so large docs don't exceed token limits
    MAX_CHUNKS = 20
    if len(chunks) > MAX_CHUNKS:
        step = len(chunks) // MAX_CHUNKS
        sampled = chunks[::step][:MAX_CHUNKS]
    else:
        sampled = chunks

    context = "\n\n---\n\n".join(sampled)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _SUMMARIZE_SYSTEM},
            {"role": "user", "content": f"Document text:\n{context}"},
        ],
        temperature=0.0,
        max_tokens=512,
    )

    return response.choices[0].message.content or "Could not generate summary."


def extract_document_info(chunks: list[str]) -> dict:
    """Extract key points, entities, and topics from document chunks."""
    import json

    if not chunks:
        return {"key_points": [], "entities": [], "topics": []}

    MAX_CHUNKS = 20
    if len(chunks) > MAX_CHUNKS:
        step = len(chunks) // MAX_CHUNKS
        sampled = chunks[::step][:MAX_CHUNKS]
    else:
        sampled = chunks

    context = "\n\n---\n\n".join(sampled)

    response = _get_client().chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": _EXTRACT_SYSTEM},
            {"role": "user", "content": f"Document text:\n{context}"},
        ],
        temperature=0.0,
        max_tokens=1024,
    )

    raw = response.choices[0].message.content or "{}"
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"key_points": [], "entities": [], "topics": [], "raw": raw}
