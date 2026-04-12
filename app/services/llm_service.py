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
