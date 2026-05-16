#!/usr/bin/env python3
"""Tiny Windows-compatible ALFWorld-style text environment.

This is NOT the official ALFWorld benchmark. It is a pure-Python simulator
for testing whether a small model can follow the action -> observation loop
before fighting ALFWorld/TextWorld/Jericho install issues.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class MiniWorldState:
    room: str = "living room"
    apple_location: str = "table"  # table, inventory, fridge
    fridge_open: bool = False
    done: bool = False


class MiniALFWorldEnv:
    """Small subset of the ALFWorld API used by run_alfworld_agent.py."""

    goal = "put the apple in the fridge"

    def __init__(self) -> None:
        self.state = MiniWorldState()

    def reset(self):
        self.state = MiniWorldState()
        return [self._observation("You are in the living room.")], self._infos()

    def step(self, actions: list[str]):
        action = actions[0].strip().lower() if actions else "look"
        feedback = self._apply(action)
        score = 1.0 if self.state.done else 0.0
        return [feedback], [score], [self.state.done], self._infos()

    def _apply(self, action: str) -> str:
        s = self.state

        if action == "look":
            return self._observation("You look around.")

        if action == "inventory":
            if s.apple_location == "inventory":
                return "You are carrying an apple."
            return "You are carrying nothing."

        if action == "go to kitchen":
            s.room = "kitchen"
            return self._observation("You go to the kitchen.")

        if action in {"go to living room", "go to livingroom"}:
            s.room = "living room"
            return self._observation("You go to the living room.")

        if action == "open fridge":
            if s.room != "kitchen":
                return "You do not see a fridge here."
            if s.fridge_open:
                return "The fridge is already open."
            s.fridge_open = True
            return self._observation("You open the fridge.")

        if action == "close fridge":
            if s.room != "kitchen":
                return "You do not see a fridge here."
            s.fridge_open = False
            return self._observation("You close the fridge.")

        if action == "take apple":
            if s.room != "kitchen" or s.apple_location != "table":
                return "You cannot take the apple."
            s.apple_location = "inventory"
            return "You pick up the apple."

        if action in {"put apple in fridge", "put apple into fridge"}:
            if s.apple_location != "inventory":
                return "You are not holding the apple."
            if not s.fridge_open:
                return "The fridge is closed."
            s.apple_location = "fridge"
            s.done = True
            return "You put the apple in the fridge. Task complete."

        if action.startswith("examine "):
            return self._observation(f"You examine the {action.removeprefix('examine ')}.")

        return f"Nothing happens. Invalid or unsupported command: {action}"

    def _observation(self, prefix: str) -> str:
        s = self.state
        parts = [prefix]
        if s.room == "kitchen":
            visible = []
            if s.apple_location == "table":
                visible.append("an apple on the table")
            visible.append("a fridge")
            fridge_state = "open" if s.fridge_open else "closed"
            parts.append(f"You see {', '.join(visible)}. The fridge is {fridge_state}.")
        elif s.room == "living room":
            parts.append("You see a sofa and a doorway to the kitchen.")
        return " ".join(parts)

    def _infos(self):
        return {
            "goal": [self.goal],
            "admissible_commands": [self._admissible_commands()],
        }

    def _admissible_commands(self) -> list[str]:
        s = self.state
        commands = ["look", "inventory"]
        if s.room != "kitchen":
            commands.append("go to kitchen")
        if s.room != "living room":
            commands.append("go to living room")
        if s.room == "kitchen":
            commands.extend(["open fridge", "close fridge", "examine fridge"])
            if s.apple_location == "table":
                commands.extend(["take apple", "examine apple"])
            if s.apple_location == "inventory" and s.fridge_open:
                commands.append("put apple in fridge")
        return commands
