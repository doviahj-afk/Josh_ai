"""
Josh AI — Agent core
====================
Implements a ReAct loop (Reason + Act): on each turn the model is asked to
either think-and-call-a-tool, or give a final answer. The result of a tool
call is fed back in as an "Observation" and the loop continues until the
model is confident enough to answer, or a step limit is hit.

This is the "powerful algorithm" — it's what lets Josh go beyond a single
LLM reply and actually look things up, run commands, do arithmetic
reliably, and remember things across sessions, while staying auditable:
every step is printed, so you can see exactly why it did what it did.
"""

import re
import time

from gemini_client import generate_content, GeminiError
from config import DEFAULT_MODEL
from memory import Memory
from tools import TOOLS, tool_manifest

MAX_STEPS = 6
RETRY_ATTEMPTS = 3

SYSTEM_PROMPT_TEMPLATE = """You are Josh AI, an autonomous assistant built by Joshua.
You reason step by step and use tools when they'll make your answer more
accurate, then give a clear final answer in plain language.

Available tools:
{tool_manifest}

You also have a special action "remember" — use it to save a durable fact
about the user for future sessions (input: the fact as a short sentence).

Respond using EXACTLY this format, one block per step:

Thought: <your reasoning about what to do next>
Action: <one of: {tool_names}, remember, or final_answer>
Action Input: <the input for that action>

When you have enough information, use:

Thought: <final reasoning>
Action: final_answer
Action Input: <your complete answer to the user, written for them directly>

Rules:
- Only take ONE action per step.
- Never invent an Observation yourself — wait for it to be provided.
- Use tools only when they add real value; for simple conversational replies,
  go straight to final_answer.
- Be concise. Do not pad Thought steps with filler.
{memory_context}
Conversation so far:
{transcript}
"""

STEP_PATTERN = re.compile(
    r"Thought:\s*(?P<thought>.*?)\s*Action:\s*(?P<action>.*?)\s*Action Input:\s*(?P<input>.*)",
    re.DOTALL,
)


class JoshAI:
    def __init__(self, api_key: str, verbose: bool = True, on_step=None):
        self.api_key = api_key
        self.model_name = DEFAULT_MODEL
        self.memory = Memory()
        self.verbose = verbose
        self.on_step = on_step  # optional callback(label: str, text: str) for UIs

    def _log(self, label, text):
        if self.on_step:
            self.on_step(label, text)
        if self.verbose:
            print(f"\033[2m[{label}]\033[0m {text}")

    def _call_model(self, prompt: str) -> str:
        last_error = None
        for attempt in range(1, RETRY_ATTEMPTS + 1):
            try:
                return generate_content(self.api_key, self.model_name, prompt)
            except GeminiError as exc:
                last_error = exc
                if exc.status_code in (400, 403):
                    # Not transient — retrying won't help a bad key or permission issue.
                    raise RuntimeError(f"Gemini API error ({exc.status_code}): {exc.message}")
                wait = 2 ** attempt
                self._log("retry", f"Gemini call failed ({exc}); retrying in {wait}s...")
                time.sleep(wait)
        raise RuntimeError(f"Gemini API call failed after {RETRY_ATTEMPTS} attempts: {last_error}")

    def _build_prompt(self, scratchpad: str) -> str:
        return SYSTEM_PROMPT_TEMPLATE.format(
            tool_manifest=tool_manifest(),
            tool_names=", ".join(TOOLS.keys()),
            memory_context=self.memory.context_block(),
            transcript=self.memory.transcript(),
        ) + "\n" + scratchpad

    def ask(self, user_message: str) -> str:
        self.memory.add_turn("user", user_message)
        scratchpad = ""

        for step in range(1, MAX_STEPS + 1):
            prompt = self._build_prompt(scratchpad)
            raw = self._call_model(prompt)

            match = STEP_PATTERN.search(raw)
            if not match:
                # Model didn't follow the format — treat the raw text as the final answer.
                self.memory.add_turn("assistant", raw)
                return raw

            thought = match.group("thought").strip()
            action = match.group("action").strip()
            action_input = match.group("input").strip()

            self._log("thought", thought)
            self._log("action", f"{action} -> {action_input!r}")

            if action == "final_answer":
                self.memory.add_turn("assistant", action_input)
                return action_input

            if action == "remember":
                self.memory.remember_fact(action_input)
                observation = f"Saved to long-term memory: {action_input}"
            elif action in TOOLS:
                observation = TOOLS[action]["run"](action_input)
            else:
                observation = f"Unknown action '{action}'. Choose one of: {', '.join(TOOLS.keys())}, remember, final_answer."

            self._log("observation", observation[:300])
            scratchpad += (
                f"Thought: {thought}\nAction: {action}\nAction Input: {action_input}\n"
                f"Observation: {observation}\n"
            )

        # Step limit reached without a final_answer — degrade gracefully.
        fallback = "I wasn't able to settle on a confident answer in time — could you rephrase or narrow the question?"
        self.memory.add_turn("assistant", fallback)
        return fallback
