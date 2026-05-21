import re


COMPLIANCE_TERMS = {
    "policy",
    "compliance",
    "security",
    "access",
    "authentication",
    "authorization",
    "data",
    "risk",
    "incident",
    "report",
    "control",
    "nist",
    "vendor",
    "system",
    "assessment",
    "employee",
    "customer",
}

BLOCKED_PATTERNS = [
    r"ignore (all )?(previous|system|developer) instructions",
    r"reveal (your )?(prompt|system message|secrets)",
    r"bypass (policy|guardrails|security)",
]


def validate_policy_question(question: str) -> tuple[bool, str]:
    clean = question.strip()
    if len(clean) < 3:
        return False, "Ask a complete compliance or policy question."
    if len(clean) > 2000:
        return False, "Question is too long. Keep it under 2,000 characters."
    lowered = clean.lower()
    for pattern in BLOCKED_PATTERNS:
        if re.search(pattern, lowered):
            return False, "The question appears to be trying to bypass system instructions."
    tokens = set(re.findall(r"[a-zA-Z]{3,}", lowered))
    if tokens and tokens.isdisjoint(COMPLIANCE_TERMS) and "can i" not in lowered and "should i" not in lowered:
        return False, "Ask a question related to company policy, security, access, data handling, or compliance."
    return True, "ok"
