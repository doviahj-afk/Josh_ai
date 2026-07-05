"""
Josh AI — Web frontend
======================
Wraps the same JoshAI agent used by the CLI (main.py) in a browser chat
interface. Each user message runs the agent's ReAct loop in a background
task; every Thought/Action/Observation step streams to the browser live
over WebSocket as it happens, then the final answer arrives.

Run:
    pip install -r requirements.txt --break-system-packages
    export GEMINI_API_KEY="your_key_here"
    python app.py

Then open http://localhost:5000
"""

import os

from flask import Flask, render_template
from flask_socketio import SocketIO

from config import bootstrap_or_exit, DEFAULT_MODEL
from agent import JoshAI

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "josh-ai-dev")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

# Single shared agent instance — this is a personal assistant for one user,
# not a multi-tenant service, so one JoshAI (and one memory file) is fine.
_api_key = None
_josh = None


def get_josh():
    global _josh
    if _josh is None:
        _josh = JoshAI(api_key=_api_key, verbose=True)
    return _josh


@app.route("/")
def index():
    return render_template("index.html", model=DEFAULT_MODEL)


@socketio.on("connect")
def on_connect():
    josh = get_josh()
    socketio.emit("facts_update", {"facts": josh.memory.facts})


@socketio.on("user_message")
def on_user_message(data):
    message = (data or {}).get("message", "").strip()
    if not message:
        return

    josh = get_josh()

    def on_step(label, text):
        socketio.emit("agent_step", {"label": label, "text": text})
        socketio.sleep(0)  # yield so the step reaches the browser immediately

    josh.on_step = on_step

    def run():
        try:
            answer = josh.ask(message)
            socketio.emit("agent_reply", {"answer": answer})
            socketio.emit("facts_update", {"facts": josh.memory.facts})
        except Exception as exc:
            socketio.emit("agent_error", {"error": str(exc)})

    socketio.start_background_task(run)


@socketio.on("reset_conversation")
def on_reset():
    josh = get_josh()
    josh.memory.reset()
    socketio.emit("conversation_reset")


if __name__ == "__main__":
    _api_key = bootstrap_or_exit()
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host="0.0.0.0", port=port, debug=True, use_reloader=False)
