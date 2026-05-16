#!/usr/bin/env python3
"""Minimal ALFWorld + Ollama action-only runner."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from typing import Any

import requests
import yaml

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "qwen3.5:0.8b"
MAX_STEPS = 30

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
TASK_LINE_RE = re.compile(r"(?:your task is to|task)\s*:?\s*(.+)", re.IGNORECASE)


def find_base_config() -> Path:
    import alfworld

    root = Path(alfworld.__file__).resolve().parent
    candidates = [
        root / "agents" / "config" / "base_config.yaml",
        root / "config" / "base_config.yaml",
        root.parent / "alfworld" / "agents" / "config" / "base_config.yaml",
    ]
    for path in candidates:
        if path.exists():
            return path
    raise FileNotFoundError("Could not find ALFWorld base_config.yaml inside the installed package")


def load_env(backend: str, split: str, config_path: str | None):
    if backend == "mini":
        from mini_alfworld_env import MiniALFWorldEnv

        return MiniALFWorldEnv(), "mini_alfworld_env.py"

    import alfworld.agents.environment as environment

    cfg_path = Path(config_path) if config_path else find_base_config()
    with cfg_path.open("r", encoding="utf-8") as f:
        config = yaml.safe_load(f)

    config.setdefault("env", {})["type"] = config.get("env", {}).get("type", "AlfredTWEnv")
    config["env"]["batch_size"] = 1
    config["env"]["domain_randomization"] = False
    config["env"]["regen_game_files"] = False
    # Some ALFWorld/TextWorld installs expose admissible commands when this flag exists.
    # Older installs ignore unknown config keys.
    config["env"]["get_admissible_commands"] = True

    env_cls = getattr(environment, config["env"]["type"])
    env = env_cls(config, train_eval=split).init_env(batch_size=1)
    return env, str(cfg_path)


def _clean_action_line(line: str) -> str:
    line = ACTION_LABEL_RE.sub("", line).strip()
    line = re.sub(r"^[`\-\*\d\.\)\s]+", "", line).strip()
    line = line.strip('"\'`').strip()
    return line.lower()


def normalize_action(text: str, admissible: list[str] | None = None) -> str:
    """Extract one ALFWorld command from messy small-model output."""
    if not text or not text.strip():
        return ""

    # Reasoning-enabled small models may emit long traces in <think> blocks.
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.IGNORECASE | re.DOTALL)

    # Accept JSON-ish outputs: {"action": "take apple"}.
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
        if any(candidate == p.strip() or candidate.startswith(p) for p in ACTION_PREFIXES):
            return candidate

    return candidates[0]


def action_looks_valid(action: str, admissible: list[str] | None = None) -> bool:
    if not action or len(action) > 120:
        return False
    if admissible and action in {a.lower() for a in admissible}:
        return True
    return any(action == p.strip() or action.startswith(p) for p in ACTION_PREFIXES)


def pick_fallback_action(admissible: list[str] | None) -> str:
    """Choose a deterministic fallback when the model refuses or rambles."""
    if not admissible:
        return "look"

    normalized = [a.lower() for a in admissible if isinstance(a, str) and a.strip()]
    for prefix in ("take ", "open ", "go to ", "put ", "examine ", "inventory", "look"):
        for action in normalized:
            if action == prefix.strip() or action.startswith(prefix):
                return action
    return normalized[0] if normalized else "look"


def first_item(x: Any) -> Any:
    return x[0] if isinstance(x, (list, tuple)) else x


def extract_task(infos: dict[str, Any], observation: str) -> str:
    """Prefer an actual goal string over ALFWorld metadata like gamefile paths."""
    for key in ("goal", "task", "task_desc", "objective", "mission", "extra.goal", "extra.task_desc"):
        value = infos.get(key) if isinstance(infos, dict) else None
        if value is None:
            continue
        candidate = str(first_item(value)).strip()
        if candidate and not candidate.endswith((".tw-pddl", ".ulx", ".json")) and "/" not in candidate:
            return candidate

    for line in observation.splitlines():
        match = TASK_LINE_RE.search(line)
        if match:
            return match.group(1).strip()

    return observation


def build_prompt(task: str, observation: str, strict: bool = False, admissible: list[str] | None = None) -> str:
    base = f"""Task: {task}
Observation: {observation}

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
        extra = "\n\nYour previous output was invalid. Return exactly one ALFWorld command, nothing else."
        if admissible:
            extra += "\nIf unsure, choose one of these valid commands:\n" + "\n".join(admissible[:30])
        return base + extra
    return base


def call_ollama(model: str, prompt: str, url: str = OLLAMA_URL) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 32},
    }
    r = requests.post(url, json=payload, timeout=120)
    r.raise_for_status()
    return r.json().get("response", "")


def choose_action(model: str, task: str, observation: str, admissible: list[str] | None, url: str) -> tuple[str, list[str]]:
    raw_outputs: list[str] = []
    for strict in (False, True):
        raw = call_ollama(model, build_prompt(task, observation, strict, admissible), url)
        raw_outputs.append(raw)
        action = normalize_action(raw, admissible)
        if action_looks_valid(action, admissible):
            return action, raw_outputs
    return pick_fallback_action(admissible), raw_outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one ALFWorld task with an Ollama action-only agent")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-steps", type=int, default=MAX_STEPS)
    parser.add_argument("--backend", choices=("mini", "alfworld"), default="mini", help="mini runs natively on Windows; alfworld uses official ALFWorld")
    parser.add_argument("--split", default="eval_out_of_distribution", help="ALFWorld split/train_eval value; ignored by --backend mini")
    parser.add_argument("--config", default=None, help="Optional path to ALFWorld base_config.yaml")
    parser.add_argument("--ollama-url", default=OLLAMA_URL)
    parser.add_argument("--log", default="alfworld_run.log")
    args = parser.parse_args()

    env, cfg_path = load_env(args.backend, args.split, args.config)
    obs, infos = env.reset()
    observation = str(first_item(obs))
    task = extract_task(infos, observation)

    log_path = Path(args.log)
    with log_path.open("w", encoding="utf-8") as log:
        log.write(json.dumps({"event": "start", "backend": args.backend, "model": args.model, "config": cfg_path, "split": args.split, "task": task}) + "\n")

        done = False
        success = False
        for step in range(1, args.max_steps + 1):
            admissible = None
            cmds = infos.get("admissible_commands") if isinstance(infos, dict) else None
            if cmds:
                admissible = [str(cmd) for cmd in list(first_item(cmds))]

            action, raw_outputs = choose_action(args.model, task, observation, admissible, args.ollama_url)
            next_obs, scores, dones, infos = env.step([action])
            feedback = str(first_item(next_obs))
            done = bool(first_item(dones))
            success = bool(done and float(first_item(scores)) > 0)

            print(f"\nSTEP {step}")
            print(f"TASK:\n{task}")
            print(f"OBSERVATION:\n{observation}")
            print(f"MODEL ACTION: {action}")
            print(f"ENV FEEDBACK:\n{feedback}")
            print(f"DONE: {done} SUCCESS: {success}")

            log.write(json.dumps({
                "step": step,
                "task": task,
                "observation": observation,
                "admissible_commands": admissible,
                "raw_model_outputs": raw_outputs,
                "action": action,
                "feedback": feedback,
                "done": done,
                "success": success,
                "time": time.time(),
            }) + "\n")
            log.flush()

            observation = feedback
            if done:
                break

    print(f"\nLog written to {log_path.resolve()}")
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
