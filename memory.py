"""
Josh AI — Memory
================
Two tiers, kept deliberately simple:
  - Working memory: the current conversation (list of {role, content}).
  - Long-term memory: small facts Josh chooses to remember across sessions
    ("remember that Joshua prefers Termux over Colab"), stored as plain
    strings in a JSON file.
"""

import json
import os
from datetime import datetime

from config import MEMORY_FILE


class Memory:
    def __init__(self, max_turns=30):
        self.max_turns = max_turns
        self.history = []          # [{role, content}]
        self.facts = []            # [str]
        self._load()

    def _load(self):
        if os.path.exists(MEMORY_FILE):
            try:
                with open(MEMORY_FILE) as f:
                    data = json.load(f)
                self.facts = data.get("facts", [])
            except (json.JSONDecodeError, OSError):
                self.facts = []

    def _save(self):
        os.makedirs(os.path.dirname(MEMORY_FILE), exist_ok=True)
        with open(MEMORY_FILE, "w") as f:
            json.dump({"facts": self.facts, "updated": datetime.utcnow().isoformat()}, f, indent=2)

    def add_turn(self, role, content):
        self.history.append({"role": role, "content": content})
        # Keep the working window bounded so prompts don't grow unbounded.
        if len(self.history) > self.max_turns:
            self.history = self.history[-self.max_turns:]

    def remember_fact(self, fact: str):
        fact = fact.strip()
        if fact and fact not in self.facts:
            self.facts.append(fact)
            self._save()

    def forget_fact(self, index: int):
        if 0 <= index < len(self.facts):
            removed = self.facts.pop(index)
            self._save()
            return removed
        return None

    def context_block(self):
        """Rendered block of long-term facts to prepend to the system prompt."""
        if not self.facts:
            return ""
        bullet_list = "\n".join(f"- {f}" for f in self.facts)
        return f"\nThings you remember about the user from past sessions:\n{bullet_list}\n"

    def transcript(self):
        """History formatted as plain text for the prompt."""
        lines = []
        for turn in self.history:
            speaker = "User" if turn["role"] == "user" else "Josh"
            lines.append(f"{speaker}: {turn['content']}")
        return "\n".join(lines)

    def reset(self):
        self.history = []
