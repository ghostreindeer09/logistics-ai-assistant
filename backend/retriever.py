"""
RAG Retriever & Answer Generation Module
Handles question answering using retrieved context and OpenAI LLM.
"""

import os
from typing import List

from openai import OpenAI
from dotenv import load_dotenv

from document_processor import retrieve_chunks
from guardrails import compute_composite_confidence, check_guardrails
from models import AskResponse, SourceChunk

load_dotenv()


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key == "your-openai-api-key-here":
        raise ValueError(
            "OpenAI API key not configured. Set OPENAI_API_KEY in your .env file."
        )
    return OpenAI(api_key=api_key)


SYSTEM_PROMPT = """You are a logistics document assistant. Your role is to answer questions ONLY based on the provided document context.

STRICT RULES:
1. Answer ONLY from the provided context. Do not use any external knowledge.
2. If the information is not in the context, say "This information is not found in the document."
3. Be precise and concise. Quote relevant parts of the document when possible.
4. Do not speculate, infer, or make assumptions beyond what the document explicitly states.
5. For numerical values (rates, weights, dates), provide the exact values from the document.
6. If asked about something ambiguous, mention all relevant pieces of information from the context.
"""


def build_context_prompt(question: str, chunks: List[dict]) -> str:
    """Build the prompt with retrieved context."""
    context_parts = []
    for i, chunk in enumerate(chunks):
        context_parts.append(f"[Source {i+1}] (Relevance: {chunk['similarity_score']:.2f})\n{chunk['text']}")

    context_str = "\n\n---\n\n".join(context_parts)

    return f"""Document Context:
{context_str}

Question: {question}

Based ONLY on the document context above, provide a clear and accurate answer. If the information is not present in the context, explicitly state that it is not found in the document."""


def answer_question(
    doc_id: str,
    question: str,
    top_k: int = 5,
    confidence_threshold: float = 0.45,
    model: str = "gpt-3.5-turbo",
    embedding_model: str = "all-MiniLM-L6-v2",
) -> AskResponse:
    """
    Full RAG pipeline: retrieve → generate → score → guardrail.
    """
    # Step 1: Retrieve relevant chunks
    chunks = retrieve_chunks(doc_id, question, top_k=top_k, embedding_model=embedding_model)

    if not chunks:
        return AskResponse(
            answer="⚠️ No relevant content found in the document for this question.",
            confidence_score=0.0,
            sources=[],
            guardrail_triggered=True,
            guardrail_message="No chunks were retrieved from the vector store.",
        )

    similarity_scores = [c["similarity_score"] for c in chunks]
    source_texts = [c["text"] for c in chunks]

    # Step 2: Generate answer using LLM
    try:
        client = get_openai_client()
        prompt = build_context_prompt(question, chunks)

        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.1,  # Low temperature for factual grounding
            max_tokens=500,
        )

        answer = response.choices[0].message.content.strip()

    except ValueError as e:
        # API key not set - provide a fallback extractive answer
        answer = _extractive_fallback(question, chunks)
    except Exception as e:
        print(f"[Retriever] LLM error: {e}")
        answer = _extractive_fallback(question, chunks)

    # Step 3: Compute confidence score
    confidence = compute_composite_confidence(
        similarity_scores=similarity_scores,
        answer=answer,
        source_texts=source_texts,
        chunks=chunks,
    )

    # Step 4: Apply guardrails
    triggered, guardrail_msg, final_answer = check_guardrails(
        answer=answer,
        confidence=confidence,
        similarity_scores=similarity_scores,
        threshold=confidence_threshold,
    )

    # Build source chunks for response
    source_chunks = [
        SourceChunk(
            text=c["text"],
            chunk_index=c["chunk_index"],
            similarity_score=c["similarity_score"],
        )
        for c in chunks
    ]

    return AskResponse(
        answer=final_answer,
        confidence_score=confidence,
        sources=source_chunks,
        guardrail_triggered=triggered,
        guardrail_message=guardrail_msg,
    )


def _extractive_fallback(question: str, chunks: List[dict]) -> str:
    """
    Fallback answer when LLM is unavailable.
    Returns the most relevant chunk as the answer.
    """
    if not chunks:
        return "No relevant information found."

    best_chunk = chunks[0]
    text = best_chunk["text"]

    # Try to find the most relevant sentence
    sentences = [s.strip() for s in text.split('.') if s.strip()]
    question_lower = question.lower()

    # Simple keyword matching to find best sentence
    q_words = set(question_lower.split())
    scored_sentences = []
    for sent in sentences:
        sent_words = set(sent.lower().split())
        overlap = len(q_words & sent_words)
        scored_sentences.append((overlap, sent))

    scored_sentences.sort(reverse=True, key=lambda x: x[0])

    if scored_sentences and scored_sentences[0][0] > 0:
        # Return top 3 most relevant sentences
        top = scored_sentences[:3]
        return ". ".join(s for _, s in top) + "."
    else:
        # Return the beginning of the most relevant chunk
        return text[:500] + ("..." if len(text) > 500 else "")
