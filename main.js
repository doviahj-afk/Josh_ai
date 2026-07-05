// Josh AI — terminal frontend logic

const socket = io();

const logEl = document.getElementById("log");
const bootStatus = document.getElementById("boot-status");
const connState = document.getElementById("conn-state");
const factsList = document.getElementById("facts-list");
const form = document.getElementById("input-form");
const field = document.getElementById("input-field");
const resetBtn = document.getElementById("reset-btn");

let currentTrace = null; // {steps: [], containerEl}
let stepCount = 0;

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function scrollToBottom() {
  logEl.scrollTop = logEl.scrollHeight;
}

function appendMessage(role, text, isError = false) {
  const wrap = document.createElement("div");
  wrap.className = `msg msg--${role}` + (isError ? " msg--error" : "");
  wrap.innerHTML = `<div class="msg__prompt"></div><div class="msg__text">${escapeHtml(text)}</div>`;
  logEl.appendChild(wrap);
  scrollToBottom();
  return wrap;
}

function startTrace() {
  stepCount = 0;
  const container = document.createElement("div");
  container.className = "trace";

  const thinking = document.createElement("div");
  thinking.className = "thinking";
  thinking.innerHTML = `thinking<span class="cursor">_</span>`;
  container.appendChild(thinking);

  logEl.appendChild(container);
  scrollToBottom();

  currentTrace = { containerEl: container, thinkingEl: thinking, bodyEl: null, toggleEl: null };
}

function addTraceStep(label, text) {
  if (!currentTrace) startTrace();
  stepCount += 1;

  if (!currentTrace.bodyEl) {
    // First real step: replace the "thinking..." line with a collapsible trace.
    const toggle = document.createElement("button");
    toggle.className = "trace__toggle";
    toggle.type = "button";
    toggle.textContent = `reasoning (${stepCount} step)`;
    toggle.addEventListener("click", () => {
      body.classList.toggle("trace__body--open");
    });

    const body = document.createElement("div");
    body.className = "trace__body";

    currentTrace.containerEl.innerHTML = "";
    currentTrace.containerEl.appendChild(toggle);
    currentTrace.containerEl.appendChild(body);
    currentTrace.toggleEl = toggle;
    currentTrace.bodyEl = body;
  } else {
    currentTrace.toggleEl.textContent = `reasoning (${stepCount} steps)`;
  }

  const stepEl = document.createElement("div");
  stepEl.className = "trace__step";
  stepEl.innerHTML = `<span class="label">${escapeHtml(label)}</span>${escapeHtml(text)}`;
  currentTrace.bodyEl.appendChild(stepEl);
  scrollToBottom();
}

function endTrace() {
  currentTrace = null;
}

// ---------------- Socket events ----------------

socket.on("connect", () => {
  connState.textContent = "connected";
  connState.classList.add("live");
  bootStatus.innerHTML = `ready<span class="cursor">_</span>`;
});

socket.on("disconnect", () => {
  connState.textContent = "disconnected";
  connState.classList.remove("live");
});

socket.on("agent_step", (data) => {
  addTraceStep(data.label, data.text);
});

socket.on("agent_reply", (data) => {
  endTrace();
  appendMessage("josh", data.answer);
});

socket.on("agent_error", (data) => {
  endTrace();
  appendMessage("josh", `error: ${data.error}`, true);
});

socket.on("facts_update", (data) => {
  const facts = data.facts || [];
  factsList.innerHTML = "";
  if (facts.length === 0) {
    factsList.innerHTML = `<li class="side__empty">nothing remembered yet</li>`;
    return;
  }
  facts.forEach((fact) => {
    const li = document.createElement("li");
    li.textContent = fact;
    factsList.appendChild(li);
  });
});

socket.on("conversation_reset", () => {
  logEl.innerHTML = "";
  const boot = document.createElement("div");
  boot.className = "boot";
  boot.innerHTML = `
    <div class="boot__line">JOSH AI v1.0</div>
    <div class="boot__line">conversation cleared — long-term memory kept</div>
  `;
  logEl.appendChild(boot);
});

// ---------------- Input handling ----------------

form.addEventListener("submit", (e) => {
  e.preventDefault();
  const message = field.value.trim();
  if (!message) return;

  appendMessage("user", message);
  startTrace();
  socket.emit("user_message", { message });

  field.value = "";
  field.focus();
});

resetBtn.addEventListener("click", () => {
  socket.emit("reset_conversation");
});
