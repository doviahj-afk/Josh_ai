# Josh AI 🤖

An autonomous agent powered by the Gemini API, built around a **ReAct
loop** (Reason → Act → Observe) — the algorithm that lets it look things
up, run commands, do math reliably, and remember things across sessions,
instead of just replying from a single prompt.

This is a from-scratch, dependency-light version of the same idea as your
earlier Termux agent — rebuilt with strict API key validation up front so
the "key validation issue" problem surfaces immediately with a clear fix,
not buried three layers into a chat session.

**Termux note:** this talks to Gemini over plain REST with `requests`
(see `gemini_client.py`) instead of the official `google-generativeai`
SDK. The SDK pulls in `grpcio` and `cryptography`, which try to compile
native code for Android/aarch64 and need a Rust toolchain — that's a
common source of install failures on Termux. This version only needs
`requests`, which installs instantly.

## Project structure

```
josh_ai/
├── main.py                  # CLI entrypoint
├── app.py                   # Web entrypoint (Flask + Socket.IO)
├── agent.py                 # ReAct loop — shared by both entrypoints
├── config.py                # API key loading & validation
├── memory.py                # Working + long-term memory
├── gemini_client.py         # Plain REST client (no heavy SDK)
├── requirements.txt
├── templates/index.html     # Terminal-style chat UI
├── static/css/style.css
├── static/js/main.js
└── tools/
    ├── web_search.py
    ├── shell.py
    ├── files.py
    └── calculator.py
```

## How the algorithm works

On every message, Josh doesn't just answer — it runs a loop:

```
Thought:      what does the model think it should do next?
Action:       pick a tool (or "final_answer" to respond directly)
Action Input: input for that tool
Observation:  the tool's result, fed back in
   ... repeats up to 6 times ...
Action: final_answer  →  done
```

This means Josh only reaches for a tool when it decides it needs one —
simple questions get answered directly, while questions that need current
info, a calculation, or a file lookup trigger the relevant tool
automatically. Every step prints to the terminal, so the reasoning is
fully auditable, not a black box.

## Tools available out of the box

| Tool | What it does |
|---|---|
| `web_search` | Searches the web (DuckDuckGo HTML, no API key needed) |
| `shell` | Runs shell commands in a sandboxed folder, with a blocklist for destructive commands and a 20s timeout |
| `read_file` / `write_file` / `list_files` | File I/O confined to the sandbox directory — can't touch files elsewhere on your device |
| `calculate` | Safe arithmetic (parsed via Python's `ast`, never `eval()`) |
| `remember` | Saves a durable fact about you to long-term memory (`~/.josh_ai/memory.json`), recalled in future sessions |

## Two ways to run Josh AI

**Terminal (original):**
```bash
python main.py
```

**Web interface** — a browser-based terminal you chat with, same agent
and same memory underneath:
```bash
python app.py
```
Then open `http://localhost:5000`. Every Thought/Action/Observation step
streams to the page live as the agent works, collapsed into a "reasoning
(N steps)" toggle you can expand — so you see the agent thinking, then
the answer lands. The sidebar shows what Josh remembers about you
long-term, live-updated as it learns new facts.

Both entry points share `agent.py`, `memory.py`, and the sandboxed tools
— nothing is duplicated, the web app just gives the same agent a browser
front end instead of a terminal prompt.

To reach it from your phone's browser while it's running in Termux, use
`http://localhost:5000` if you're on the same device, or find your
device's local IP (`ip addr` in Termux) to reach it from another device
on the same network.

## Setup (Termux or any Linux machine)

```bash
pip install -r requirements.txt --break-system-packages
export GEMINI_API_KEY="your_key_here"
python main.py
```

This only installs `requests` — no compilation, no Rust, no build
failures. If you ever see a `maturin`/`cryptography`/`grpcio` build error
again, it means something in your environment is pulling in the heavy
SDK; this version of Josh AI shouldn't need it.

On startup, Josh makes one live test call to Gemini and tells you plainly
if the key is missing, malformed, revoked, rate-limited, or pointed at a
model that doesn't exist for your API version — before you're stuck
mid-conversation with a cryptic 400 error.

### Getting a Gemini API key

Free key: https://aistudio.google.com/apikey

Google is currently migrating Gemini API keys to a new **auth key** format
starting with `AQ.` (tied to a service account, more secure). The older
`AIza`-prefixed **standard keys** are being phased out: unrestricted
standard keys stopped working June 19, 2026, and all standard keys stop
working in September 2026. Any key you generate in AI Studio now will
default to the new `AQ.` format — that's expected and correct.

### Optional `.env` file

Instead of `export`, you can put this in a `.env` file next to `main.py`:
```
GEMINI_API_KEY=AQ.Ab...  (or an AIza... key if you're still on the old format)
JOSH_MODEL=gemini-2.5-flash
```

## A note on model names

Google retired `gemini-2.0-flash` and `gemini-2.0-flash-lite` on June 1,
2026 — they no longer have any free-tier quota at all (a `429` with
`limit: 0` on those specific models means exactly this, not a billing
problem). Josh AI defaults to `gemini-2.5-flash`. If Google ships a newer
recommended free-tier model later, just set `JOSH_MODEL` to it.

## Chat commands

- `/reset` — clear the current conversation (long-term facts are kept)
- `/facts` — list what Josh remembers about you long-term
- `/forget N` — delete fact number N
- `/exit` — quit

## Extending Josh

- **Add a tool**: write a function in `tools/`, register it in
  `tools/__init__.py`'s `TOOLS` dict with a one-line description. The
  model sees that description and decides when to call it — no other
  wiring needed.
- **Swap the model**: set `JOSH_MODEL` (e.g. `gemini-1.5-pro` for harder
  reasoning tasks, at higher latency/cost).
- **Autonomous mode**: `agent.py`'s `ask()` method is a plain function —
  wrap it in a loop that feeds it goals from a queue instead of typed
  input, and you have the fully autonomous version you were building
  toward, with the same safety rails (sandboxed shell, no arbitrary
  `eval`, path-confined file access) already in place.

## Notes on the sandbox

`shell`, `read_file`, `write_file`, and `list_files` are all confined to
`~/.josh_ai/sandbox/`. This isn't a security boundary against a
deliberately malicious model — it's a guard rail so an agent running
autonomously in Termux can't accidentally wipe files outside its own
workspace.
