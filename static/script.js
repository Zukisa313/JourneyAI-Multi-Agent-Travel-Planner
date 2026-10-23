const form = document.getElementById("trip-form");
const submitBtn = document.getElementById("submit-btn");
const errorEl = document.getElementById("form-error");
const steps = [...document.querySelectorAll("#steps li")];
const resultSection = document.getElementById("result");
const resultBody = document.getElementById("result-body");
const copyBtn = document.getElementById("copy-btn");

const ORDER = ["flight_agent", "hotel_agent", "itinerary_agent", "final_agent"];
let planMarkdown = "";

function setStep(node, state, label) {
  const li = steps.find((s) => s.dataset.node === node);
  if (!li) return;
  li.className = state;
  li.querySelector(".status").textContent = label;
}

function resetSteps() {
  steps.forEach((li) => {
    li.className = "";
    li.querySelector(".status").textContent = "Waiting";
  });
  setStep(ORDER[0], "running", "Working");
}

function showError(message) {
  errorEl.textContent = message;
  errorEl.hidden = false;
  const running = steps.find((s) => s.classList.contains("running"));
  if (running) setStep(running.dataset.node, "failed", "Failed");
}

function handleEvent(evt) {
  if (evt.node === "error") return showError(evt.message);
  if (evt.node === "done") return;

  setStep(evt.node, "done", "Done");
  const next = ORDER[ORDER.indexOf(evt.node) + 1];
  if (next) setStep(next, "running", "Working");

  if (evt.node === "final_agent") {
    planMarkdown = evt.output.final_response;
    resultBody.innerHTML = DOMPurify.sanitize(marked.parse(planMarkdown));
    resultSection.hidden = false;
    resultSection.scrollIntoView({ behavior: "smooth" });
  }
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  errorEl.hidden = true;
  resultSection.hidden = true;

  const payload = Object.fromEntries(new FormData(form).entries());
  if (payload.end_date < payload.start_date) {
    return showError("The return date must be on or after the departure date.");
  }

  submitBtn.disabled = true;
  submitBtn.textContent = "Planning…";
  resetSteps();

  try {
    const res = await fetch("/api/plan", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.error || `Request failed (${res.status})`);
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split("\n");
      buffer = lines.pop();
      lines.filter(Boolean).forEach((line) => handleEvent(JSON.parse(line)));
    }
  } catch (err) {
    showError(err.message);
  } finally {
    submitBtn.disabled = false;
    submitBtn.textContent = "Plan my trip";
  }
});

copyBtn.addEventListener("click", async () => {
  await navigator.clipboard.writeText(planMarkdown);
  copyBtn.textContent = "Copied";
  setTimeout(() => (copyBtn.textContent = "Copy plan"), 1500);
});
