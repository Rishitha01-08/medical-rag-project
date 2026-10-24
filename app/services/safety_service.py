"""Deterministic request safety and privacy classification."""

import re

EMERGENCY = re.compile(
    r"\b(chest pain|can't breathe|cannot breathe|trouble breathing|suicid|overdose|unconscious|severe bleeding)\b",
    re.I,
)
INJECTION = re.compile(
    r"ignore (all )?(previous|prior) instructions|reveal (the )?system prompt|ignore (your )?safety|follow these instructions",
    re.I,
)
SENSITIVE = re.compile(
    r"\b(diagnos|prescri|dosage|dose|treatment plan|what medicine|which medication)\w*\b", re.I
)
AMBIGUOUS = re.compile(r"\b(it|this|that|they)\b", re.I)


def classify(question, evidence_available=False):
    if INJECTION.search(question):
        return "prompt-injection-attempt"
    if EMERGENCY.search(question):
        return "safety-sensitive"
    if SENSITIVE.search(question):
        return "safety-sensitive"
    if " and " in question.lower() or "also" in question.lower():
        return "multi-part"
    if len(question.split()) < 3 or AMBIGUOUS.search(question):
        return "ambiguous"
    if not evidence_available:
        return "unsupported"
    return "factual"


def contains_untrusted_instruction(content):
    """Reject retrieved chunks that contain common direct prompt-injection text."""
    return bool(INJECTION.search(content))
