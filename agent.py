import argparse
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

from menu_policy import action_looks_valid, normalize_action, pick_fallback_action

ALFWORLD_PATH = "absolute_path_to_alfworld"
DEFAULT_MODEL = "qwen3.5:0.8b"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MAX_STEPS = 30


def platform_path(path: str) -> str:
    if os.name != "nt" and len(path) > 2 and path[1:3] == ":/":
        drive = path[0].lower()
        rest = path[3:]
        return f"/mnt/{drive}/{rest}"
    return path


def run_alfworld_command(*args: str) -> dict:
    result = subprocess.run(
        [
            "python",
            f"{platform_path(ALFWORLD_PATH)}/mini_alfworld_command.py",
            *args,
        ],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"ALFWORLD command failed with exit code {result.returncode}.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        )

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "ALFWORLD command did not return valid JSON.\n"
            f"STDOUT:\n{result.stdout}\n"
            f"STDERR:\n{result.stderr}"
        ) from exc


def build_prompt(
    task: str, observation: str, admissible: list[str], strict: bool = False
) -> str:
    menu = "\n".join(f"- {cmd}" for cmd in admissible)
    prompt = f"""Task: {task}
Observation: {observation}

Choose the single best next action from this exact menu:
{menu}

Output only one command from the menu.
No explanation.
No markdown.
No extra text."""
    if strict:
        prompt += "\n\nYour previous answer was invalid. Copy exactly one command from the menu."
    return prompt


def call_ollama(model: str, prompt: str, url: str) -> str:
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0, "num_predict": 32},
    }
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("response", "")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama request failed: {exc}") from exc


def choose_action(
    model: str, task: str, observation: str, admissible: list[str], url: str
) -> tuple[str, list[str]]:
    raw_outputs: list[str] = []
    for strict in (False, True):
        raw = call_ollama(
            model, build_prompt(task, observation, admissible, strict), url
        )
        raw_outputs.append(raw)
        action = normalize_action(raw, admissible)
        if action_looks_valid(action, admissible):
            return action, raw_outputs
    return pick_fallback_action(admissible), raw_outputs


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Menu-based ALFWorld action runner. No model tool calls."
    )
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--max-steps", type=int, default=DEFAULT_MAX_STEPS)
    parser.add_argument(
        "--no-reset",
        action="store_true",
        help="Continue from current persisted env state instead of reset",
    )
    args = parser.parse_args()

    data = run_alfworld_command("status" if args.no_reset else "reset")
    task = data["task"]
    observation = data["observation"]
    done = bool(data.get("done"))
    success = bool(data.get("success"))

    print(f"TASK: {task}")
    print(f"START: {observation}")

    for step_number in range(1, args.max_steps + 1):
        if done:
            break

        admissible = [str(cmd) for cmd in data.get("admissible_commands", [])]
        action, raw_outputs = choose_action(
            args.model, task, observation, admissible, args.ollama_url
        )
        data = run_alfworld_command("step", action)
        observation = data["observation"]
        done = bool(data.get("done"))
        success = bool(data.get("success"))

        print(f"\nSTEP {step_number}")
        print(f"ADMISSIBLE: {admissible}")
        print(f"RAW MODEL: {raw_outputs[-1].strip()!r}")
        print(f"ACTION: {action}")
        print(f"OBSERVATION: {observation}")
        print(f"DONE: {done} SUCCESS: {success}")

    final = run_alfworld_command("status")
    print("\nFINAL STATUS:")
    print(json.dumps(final, indent=2))
    return 0 if final.get("success") else 1


if __name__ == "__main__":
    sys.exit(main())
