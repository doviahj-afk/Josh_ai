"""
Sandboxed shell tool.
Runs commands inside the Josh AI sandbox directory only, with a timeout and
a blocklist for obviously destructive or system-altering commands. This is
NOT a security boundary against a malicious model — it's a guard rail
against the agent nuking the user's phone by accident.
"""

import subprocess
import shlex

from config import SANDBOX_DIR

BLOCKED_PATTERNS = [
    "rm -rf /", "rm -rf ~", ":(){:|:&};:", "mkfs", "dd if=", "> /dev/sda",
    "chmod -R 777 /", "chown -R", "reboot", "shutdown", "poweroff",
    "termux-reboot", "pkg uninstall", "apt remove", "curl | sh", "wget | sh",
]

TIMEOUT_SECONDS = 20


def run_shell(command: str) -> str:
    command = (command or "").strip()
    if not command:
        return "Error: empty command."

    lowered = command.lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern in lowered:
            return f"Blocked: command matches a disallowed pattern ({pattern!r}). Refusing to run it."

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=SANDBOX_DIR,
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
        )
        output = (result.stdout or "") + (result.stderr or "")
        output = output.strip()
        if not output:
            output = f"(command exited with code {result.returncode}, no output)"
        # Keep tool output bounded so it doesn't blow out the context window.
        return output[:4000]
    except subprocess.TimeoutExpired:
        return f"Command timed out after {TIMEOUT_SECONDS}s."
    except Exception as exc:
        return f"Error running command: {exc}"
