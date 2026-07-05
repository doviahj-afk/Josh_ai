"""
Josh AI — CLI
=============
    python main.py

Commands inside the chat:
  /reset      clear the current conversation (long-term memory is kept)
  /facts      show what Josh remembers about you long-term
  /forget N   remove fact number N
  /exit       quit
"""

import sys

from config import bootstrap_or_exit
from agent import JoshAI


BANNER = r"""
   ╦╔═╗╔═╗╦ ╦  ╔═╗╦
   ║║ ║╚═╗╠═╣  ╠═╣║
  ╚╝╚═╝╚═╝╩ ╩  ╩ ╩╩
  Gemini-powered agent · ReAct loop · Ctrl+C to quit
"""


def main():
    print(BANNER)
    api_key = bootstrap_or_exit()
    josh = JoshAI(api_key=api_key, verbose=True)

    print("Josh AI is ready. Type a message, or /exit to quit.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye.")
            break

        if not user_input:
            continue

        if user_input == "/exit":
            print("Goodbye.")
            break

        if user_input == "/reset":
            josh.memory.reset()
            print("[josh-ai] Conversation cleared.\n")
            continue

        if user_input == "/facts":
            facts = josh.memory.facts
            if not facts:
                print("[josh-ai] No long-term facts stored yet.\n")
            else:
                for i, fact in enumerate(facts):
                    print(f"  {i}. {fact}")
                print()
            continue

        if user_input.startswith("/forget"):
            parts = user_input.split()
            if len(parts) == 2 and parts[1].isdigit():
                removed = josh.memory.forget_fact(int(parts[1]))
                print(f"[josh-ai] Forgot: {removed}\n" if removed else "[josh-ai] No such fact.\n")
            else:
                print("[josh-ai] Usage: /forget <index> (see /facts for indices)\n")
            continue

        answer = josh.ask(user_input)
        print(f"\nJosh: {answer}\n")


if __name__ == "__main__":
    sys.exit(main())
