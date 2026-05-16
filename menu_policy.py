import json
import re

ACTION_PREFIXES = (
    "go to ",
    "open ",
    "close ",
    "take ",
    "put ",
    "look",
    "inventory",
    "examine ",
)

ACTION_LABEL_RE = re.compile(
    r"^\s*(?:action|command|next action|next command|answer)\s*[:\-]\s*",
    re.IGNORECASE,
)


def _clean_action_line(line: str) -> str:
    line = ACTION_LABEL_RE.sub("", line).strip()
    line = re.sub(r"^[`\-*\d\.)\s]+", "", line).strip()
    return line.strip('"\'`').strip().lower()


def normalize_action(text: str, admissible: list[str] | None = None) -> str:
    """Extract exactly one command from messy model output."""
    if not text or not text.strip():
        return ""

    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            for key in ("action", "command", "next_action"):
                if key in parsed:
                    return _clean_action_line(str(parsed[key]))
    except Exception:
        pass

    candidates = [_clean_action_line(line) for line in text.splitlines() if line.strip()]
    if not candidates:
        return ""

    if admissible:
        admissible_set = {a.lower() for a in admissible}
        for candidate in candidates:
            if candidate in admissible_set:
                return candidate

    for candidate in candidates:
        if any(candidate == prefix.strip() or candidate.startswith(prefix) for prefix in ACTION_PREFIXES):
            return candidate

    return candidates[0]


def action_looks_valid(action: str, admissible: list[str] | None = None) -> bool:
    if not action or len(action) > 120:
        return False
    if admissible is not None:
        return action in {a.lower() for a in admissible}
    return any(action == prefix.strip() or action.startswith(prefix) for prefix in ACTION_PREFIXES)


def pick_fallback_action(admissible: list[str] | None) -> str:
    """Deterministic fallback when the model rambles or picks an invalid command."""
    if not admissible:
        return "look"

    normalized = [a.lower() for a in admissible if isinstance(a, str) and a.strip()]
    for prefix in ("put ", "take ", "open ", "go to ", "examine ", "inventory", "look"):
        for action in normalized:
            if action == prefix.strip() or action.startswith(prefix):
                return action
    return normalized[0] if normalized else "look"
