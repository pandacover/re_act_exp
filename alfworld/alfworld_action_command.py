#!/usr/bin/env python3
"""External command for Ollama/tool use: query in, one ALFWorld action out."""

from __future__ import annotations

import argparse
import json
import re
import sys

import requests

DEFAULT_MODEL = "qwen3.5:0.8b"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"

ACTION_PREFIXES = (
    "go to ",
    "open ",
    "close ",
    "take ",
    "put ",
    "look",
    "inventory",
    "examine ",
    "use ",
    "heat ",
    "cool ",
    "clean ",
    "slice ",
    "toggle ",
)

ACTION_LABEL_RE = re.compile(
    r"^\s*(?:action|command|next action|next command|answer)\s*[:\-]\s*",
    re.IGNORECASE,
)


def _clean_action_line(line: str) -> str:
    line = ACTION_LABEL_RE.sub("", line).strip()
    line = re.sub(r"^[`\-\*\d\.\)\s]+", "", line).strip()
    line = line.strip('"\'`').strip()
    return line.lower()


def normalize_action(text: str) -> str:
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
    for candidate in candidates:
        if action_looks_valid(candidate):
            return candidate
    return candidates[0] if candidates else ""


def action_looks_valid(action: str) -> bool:
    if not action or len(action) > 120:
        return False
    return any(action == p.strip() or action.startswith(p) for p in ACTION_PREFIXES)


def build_prompt(query: str, strict: bool = False) -> str:
    prompt = f"""{query}

You are controlling a text-game environment. These are simulated actions, not real-world actions.
Valid actions include examples like:
go to ...
open ...
close ...
take ...
put ...
look
inventory

Choose the next best action.
Output only the action command.
No explanation.
No reasoning.
No markdown."""
    if strict:
        prompt += "\n\nYour previous output was invalid. Return exactly one ALFWorld command, nothing else."
    return prompt


def call_ollama(model: str, prompt: str, url: str) -> str:
    response = requests.post(
        url,
        json={
            "model": model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0, "num_predict": 32},
        },
        timeout=120,
    )
    response.raise_for_status()
    return response.json().get("response", "")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Accept a task/observation query and print exactly one ALFWorld action."
    )
    parser.add_argument("query", nargs="*", help="Task/observation query. If omitted, reads stdin.")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    args = parser.parse_args()

    query = " ".join(args.query).strip()
    if not query:
        query = sys.stdin.read().strip()

    if not query:
        print("look")
        return 0

    for strict in (False, True):
        raw = call_ollama(args.model, build_prompt(query, strict), args.ollama_url)
        action = normalize_action(raw)
        if action_looks_valid(action):
            print(action)
            return 0

    print("look")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
