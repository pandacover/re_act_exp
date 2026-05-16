#!/usr/bin/env python3
"""Stateful callable command for the mini ALFWorld-style environment.

Use this from any external agent/project:
  python mini_alfworld_command.py reset
  python mini_alfworld_command.py step "take apple"
  python mini_alfworld_command.py status

State is persisted in .mini_alfworld_state.json by default.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from mini_alfworld_env import MiniALFWorldEnv, MiniWorldState

DEFAULT_STATE_FILE = ".mini_alfworld_state.json"


def env_to_dict(env: MiniALFWorldEnv) -> dict[str, Any]:
    return {
        "room": env.state.room,
        "apple_location": env.state.apple_location,
        "fridge_open": env.state.fridge_open,
        "done": env.state.done,
    }


def env_from_file(path: Path) -> MiniALFWorldEnv:
    env = MiniALFWorldEnv()
    if not path.exists():
        return env
    data = json.loads(path.read_text(encoding="utf-8"))
    env.state = MiniWorldState(
        room=data.get("room", "living room"),
        apple_location=data.get("apple_location", "table"),
        fridge_open=bool(data.get("fridge_open", False)),
        done=bool(data.get("done", False)),
    )
    return env


def save_env(env: MiniALFWorldEnv, path: Path) -> None:
    path.write_text(json.dumps(env_to_dict(env), indent=2), encoding="utf-8")


def emit(payload: dict[str, Any]) -> int:
    print(json.dumps(payload, indent=2))
    return 0


def current_observation(env: MiniALFWorldEnv) -> str:
    return env._observation("Current state.")  # intentionally using mini env's formatter


def main() -> int:
    parser = argparse.ArgumentParser(description="Callable mini ALFWorld environment command")
    parser.add_argument("command", choices=("reset", "step", "status", "admissible"))
    parser.add_argument("action", nargs="?", help="Action for step, e.g. 'take apple'")
    parser.add_argument("--state-file", default=DEFAULT_STATE_FILE)
    args = parser.parse_args()

    state_path = Path(args.state_file)

    if args.command == "reset":
        env = MiniALFWorldEnv()
        obs, infos = env.reset()
        save_env(env, state_path)
        return emit({
            "ok": True,
            "command": "reset",
            "task": infos["goal"][0],
            "observation": obs[0],
            "admissible_commands": infos["admissible_commands"][0],
            "done": False,
            "success": False,
        })

    env = env_from_file(state_path)

    if args.command == "status":
        infos = env._infos()
        return emit({
            "ok": True,
            "command": "status",
            "task": infos["goal"][0],
            "observation": current_observation(env),
            "admissible_commands": infos["admissible_commands"][0],
            "done": env.state.done,
            "success": env.state.done,
            "state": env_to_dict(env),
        })

    if args.command == "admissible":
        return emit({
            "ok": True,
            "command": "admissible",
            "admissible_commands": env._admissible_commands(),
            "done": env.state.done,
        })

    if args.command == "step":
        if not args.action:
            return emit({"ok": False, "error": "step requires an action string"})
        obs, scores, dones, infos = env.step([args.action])
        save_env(env, state_path)
        return emit({
            "ok": True,
            "command": "step",
            "action": args.action,
            "task": infos["goal"][0],
            "observation": obs[0],
            "admissible_commands": infos["admissible_commands"][0],
            "score": scores[0],
            "done": dones[0],
            "success": bool(dones[0] and scores[0] > 0),
        })

    return emit({"ok": False, "error": "unknown command"})


if __name__ == "__main__":
    raise SystemExit(main())
