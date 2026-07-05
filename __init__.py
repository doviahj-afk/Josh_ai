"""
Josh AI — Tool registry
=======================
Every tool is a plain dict: {"description": str, "run": callable(str) -> str}.
The agent's ReAct loop picks a tool by name and calls run(input) on it.
Add a new tool by writing a module in this package and registering it below.
"""

from tools.web_search import web_search
from tools.shell import run_shell
from tools.files import read_file, write_file, list_files
from tools.calculator import calculate

TOOLS = {
    "web_search": {
        "description": "Search the web for current information. Input: a search query string.",
        "run": web_search,
    },
    "shell": {
        "description": (
            "Run a shell command in a sandboxed working directory. Use for file "
            "operations, running scripts, checking system state. Dangerous commands "
            "are blocked. Input: the command string."
        ),
        "run": run_shell,
    },
    "read_file": {
        "description": "Read a text file from the sandbox directory. Input: filename.",
        "run": read_file,
    },
    "write_file": {
        "description": "Write text to a file in the sandbox directory. Input: 'filename|||content'.",
        "run": write_file,
    },
    "list_files": {
        "description": "List files currently in the sandbox directory. Input: ignored, pass ''.",
        "run": list_files,
    },
    "calculate": {
        "description": "Evaluate a math expression safely. Input: an arithmetic expression string.",
        "run": calculate,
    },
}


def tool_manifest():
    """Human/LLM-readable list of tools and what they do, for the system prompt."""
    lines = []
    for name, spec in TOOLS.items():
        lines.append(f"- {name}: {spec['description']}")
    return "\n".join(lines)
