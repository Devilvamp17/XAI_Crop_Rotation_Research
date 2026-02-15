from __future__ import annotations


def build_system_prompt() -> str:
    return (
        "You are a crop recommendation assistant. You MUST follow these rules: "
        "Never reveal internal planning or chain-of-thought. "
        "Never write self-talk like 'Okay, let me think' or 'I need to'. "
        "Use provided recommendation JSON as the only source of truth. "
        "Do not fabricate missing N/P/K. "
        "Always output exactly the required 5 sections. "
        "Always mention both raw model confidence and season-adjusted confidence. "
        "If reranker changed the top crop, explain that conflict explicitly. "
        "If adjusted confidence < 0.6, include a risk warning."
    )


def build_user_prompt(user_query: str, recommendation_json: str) -> str:
    return (
        "Generate final response from this JSON payload.\n"
        "Follow exact format and do not output analysis text.\n\n"
        f"User query:\n{user_query}\n\n"
        "Recommendation payload JSON:\n"
        f"{recommendation_json}\n\n"
        "Required output format:\n"
        "1) Final recommended crop + short reason\n"
        "2) Confidence interpretation (must include raw + adjusted + threshold)\n"
        "3) Top-3 tradeoff note (if available)\n"
        "4) Action checklist (exactly 3 bullet points)\n"
        "5) Risk warning (only if confidence < 0.6)\n"
    )
