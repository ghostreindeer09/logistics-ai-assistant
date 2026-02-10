"""
Guardrails & Confidence Scoring Module
Implements hallucination guardrails and multi-signal confidence scoring.
"""

import re
from typing import List, Tuple, Optional


# ── Confidence Scoring ──────────────────────────────────────────────

def compute_retrieval_confidence(similarity_scores: List[float]) -> float:
    """
    Compute retrieval confidence based on the similarity scores of top-k chunks.
    
    Signals:
    1. Top-1 similarity (primary signal)
    2. Score gap between top-1 and top-2 (distinctiveness)
    3. Mean similarity of all retrieved chunks (overall relevance)
    """
    if not similarity_scores:
        return 0.0

    top_score = similarity_scores[0]
    mean_score = sum(similarity_scores) / len(similarity_scores)

    # Signal 1: Top retrieval score (weight: 0.5)
    top_signal = min(1.0, max(0.0, top_score))

    # Signal 2: Score gap - larger gap means more focused retrieval (weight: 0.2)
    if len(similarity_scores) > 1:
        gap = similarity_scores[0] - similarity_scores[1]
        gap_signal = min(1.0, gap * 5)  # Scale gap
    else:
        gap_signal = 0.5

    # Signal 3: Mean relevance (weight: 0.3)
    mean_signal = min(1.0, max(0.0, mean_score))

    confidence = (0.5 * top_signal) + (0.2 * gap_signal) + (0.3 * mean_signal)
    return round(min(1.0, max(0.0, confidence)), 4)


def compute_answer_coverage(answer: str, source_texts: List[str]) -> float:
    """
    Measure how well the answer is grounded in the source texts.
    Checks what fraction of significant words in the answer appear in sources.
    """
    if not answer or not source_texts:
        return 0.0

    # Normalize
    answer_lower = answer.lower()
    combined_sources = " ".join(source_texts).lower()

    # Extract significant words (>3 chars, not common stopwords)
    stopwords = {
        "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
        "her", "was", "one", "our", "out", "has", "have", "been", "from",
        "they", "this", "that", "with", "will", "would", "there", "their",
        "what", "about", "which", "when", "make", "than", "them", "some",
        "time", "very", "your", "just", "know", "take", "come", "could",
        "into", "year", "also", "back", "after", "only", "most", "other",
        "over", "such", "does", "should", "being", "found", "based",
        "document", "information", "please", "note", "mentioned", "according",
    }

    words = re.findall(r'\b[a-z]{4,}\b', answer_lower)
    sig_words = [w for w in words if w not in stopwords]

    if not sig_words:
        return 0.5  # Can't measure, neutral confidence

    covered = sum(1 for w in sig_words if w in combined_sources)
    coverage = covered / len(sig_words)

    return round(coverage, 4)


def compute_chunk_agreement(chunks: List[dict], answer: str) -> float:
    """
    Measure agreement across retrieved chunks.
    Higher agreement = multiple chunks corroborate the same info = more confidence.
    """
    if not chunks or not answer:
        return 0.0

    answer_lower = answer.lower()
    key_terms = set(re.findall(r'\b[a-z]{4,}\b', answer_lower))

    if not key_terms:
        return 0.5

    # Count how many chunks contain each key term
    chunk_texts = [c["text"].lower() for c in chunks]
    term_chunk_counts = []

    for term in key_terms:
        count = sum(1 for ct in chunk_texts if term in ct)
        term_chunk_counts.append(count / len(chunk_texts))

    avg_agreement = sum(term_chunk_counts) / len(term_chunk_counts)
    return round(avg_agreement, 4)


def compute_composite_confidence(
    similarity_scores: List[float],
    answer: str,
    source_texts: List[str],
    chunks: List[dict],
) -> float:
    """
    Compute a composite confidence score from multiple signals:
    - Retrieval similarity (40%)
    - Answer coverage (35%)
    - Chunk agreement (25%)
    """
    retrieval_conf = compute_retrieval_confidence(similarity_scores)
    coverage_conf = compute_answer_coverage(answer, source_texts)
    agreement_conf = compute_chunk_agreement(chunks, answer)

    composite = (0.40 * retrieval_conf) + (0.35 * coverage_conf) + (0.25 * agreement_conf)
    return round(min(1.0, max(0.0, composite)), 4)


# ── Guardrails ──────────────────────────────────────────────────────

HALLUCINATION_PHRASES = [
    "as an ai",
    "i don't have access",
    "i cannot determine",
    "based on my training",
    "as a language model",
    "i'm not sure",
    "general knowledge",
    "typically in logistics",
    "usually",
    "in my experience",
    "commonly",
]


def check_guardrails(
    answer: str,
    confidence: float,
    similarity_scores: List[float],
    threshold: float = 0.45,
) -> Tuple[bool, Optional[str], str]:
    """
    Apply guardrails to the answer.
    
    Returns: (triggered: bool, guardrail_message: str | None, final_answer: str)
    
    Guardrails applied:
    1. Low confidence threshold - refuse if confidence is too low
    2. Low retrieval similarity - refuse if best chunk is not relevant enough
    3. Hallucination phrase detection - detect signs of fabrication
    4. Empty/non-answer detection
    """
    # Guardrail 1: Overall confidence threshold
    if confidence < threshold:
        return (
            True,
            f"Confidence score ({confidence:.2f}) is below the threshold ({threshold:.2f}). "
            f"The answer may not be reliably grounded in the document.",
            "⚠️ Not found in document — The system could not find a confident answer "
            "to this question in the uploaded document. The information may not be present, "
            "or the question may need to be rephrased."
        )

    # Guardrail 2: Low retrieval similarity
    if similarity_scores and similarity_scores[0] < 0.25:
        return (
            True,
            f"Top retrieval similarity ({similarity_scores[0]:.2f}) is very low. "
            f"No relevant content was found in the document.",
            "⚠️ Not found in document — No relevant content was found that matches "
            "your question. The information may not be present in this document."
        )

    # Guardrail 3: Hallucination phrase detection
    answer_lower = answer.lower()
    for phrase in HALLUCINATION_PHRASES:
        if phrase in answer_lower:
            return (
                True,
                f"Potential hallucination detected: answer contains phrase '{phrase}'. "
                f"The response may not be grounded in the document.",
                f"⚠️ The answer may not be fully grounded in the document. "
                f"Please verify: {answer}"
            )

    # Guardrail 4: Empty or non-answer detection
    if len(answer.strip()) < 10:
        return (
            True,
            "Answer is too short or empty — likely no relevant information found.",
            "⚠️ Not found in document — Could not generate a meaningful answer."
        )

    # All guardrails passed
    return (False, None, answer)
