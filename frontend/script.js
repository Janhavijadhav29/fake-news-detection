const $ = (id) => document.getElementById(id);
let mode = "text";
let lastResult = null;
let pieChart = null;
let barChart = null;

/* ---------------- helpers ---------------- */
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

function toast(msg) {
  const t = $("toast");
  t.textContent = msg;
  t.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => (t.hidden = true), 2500);
}

async function api(url, options = {}) {
  const res = await fetch(url, options);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || "Something went wrong");
  return data;
}

/* ---------------- theme ---------------- */
function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  $("themeBtn").textContent = theme === "dark" ? "Light mode" : "Dark mode";
  try { localStorage.setItem("theme", theme); } catch (e) {}
  if (pieChart) loadDashboard();
}
$("themeBtn").addEventListener("click", () =>
  setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark")
);
try { setTheme(localStorage.getItem("theme") || "light"); } catch (e) { setTheme("light"); }

/* ---------------- tabs ---------------- */
document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
    tab.classList.add("active");
    document.querySelectorAll(".panel").forEach((p) => (p.hidden = true));
    $(`tab-${tab.dataset.tab}`).hidden = false;
    if (tab.dataset.tab === "dashboard") loadDashboard();
    if (tab.dataset.tab === "history") loadHistory();
  })
);

/* ---------------- text / url mode ---------------- */
document.querySelectorAll(".mode").forEach((btn) =>
  btn.addEventListener("click", () => {
    document.querySelectorAll(".mode").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    mode = btn.dataset.mode;
    $("textMode").hidden = mode !== "text";
    $("urlMode").hidden = mode !== "url";
    $("voiceBtn").hidden = mode !== "text";
  })
);

function updateCount() {
  const text = $("newsText").value;
  const words = text.trim() ? text.trim().split(/\s+/).length : 0;
  $("charCount").textContent = `${words} words · ${text.length} characters`;
}
$("newsText").addEventListener("input", updateCount);

document.querySelectorAll("[data-example]").forEach((chip) =>
  chip.addEventListener("click", () => {
    $("newsText").value = chip.dataset.example;
    updateCount();
  })
);

$("clearBtn").addEventListener("click", () => {
  $("newsText").value = "";
  $("newsUrl").value = "";
  updateCount();
  $("result").hidden = true;
  $("error").hidden = true;
});

// Ctrl + Enter to analyze
$("newsText").addEventListener("keydown", (e) => {
  if (e.key === "Enter" && e.ctrlKey) $("checkBtn").click();
});

/* ---------------- voice input ---------------- */
const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (!SpeechRecognition) {
  $("voiceBtn").disabled = true;
  $("voiceBtn").title = "Voice input is not supported in this browser";
} else {
  const rec = new SpeechRecognition();
  rec.lang = "en-IN";
  rec.interimResults = false;
  rec.onresult = (e) => {
    $("newsText").value += (($("newsText").value ? " " : "") + e.results[0][0].transcript);
    updateCount();
  };
  rec.onend = () => {
    $("voiceBtn").classList.remove("listening");
    $("voiceBtn").textContent = "Voice input";
  };
  $("voiceBtn").addEventListener("click", () => {
    $("voiceBtn").classList.add("listening");
    $("voiceBtn").textContent = "Listening…";
    rec.start();
  });
}

/* ---------------- analyze ---------------- */
$("checkBtn").addEventListener("click", async () => {
  $("error").hidden = true;
  let url, body;
  if (mode === "text") {
    const text = $("newsText").value.trim();
    if (text.length < 10) return showError("Please enter at least 10 characters of news text.");
    url = "/api/predict";
    body = { text };
  } else {
    const link = $("newsUrl").value.trim();
    if (!/^https?:\/\//.test(link)) return showError("Please enter a valid URL starting with http:// or https://");
    url = "/api/predict-url";
    body = { url: link };
  }

  $("checkBtn").disabled = true;
  $("checkBtn").textContent = "Analyzing…";
  try {
    const data = await api(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    showResult(data, body.text || data.article_preview || "");
  } catch (err) {
    showError(err.message);
  } finally {
    $("checkBtn").disabled = false;
    $("checkBtn").textContent = "Analyze";
  }
});

function showError(msg) {
  $("error").textContent = msg;
  $("error").hidden = false;
}

function showResult(data, originalText) {
  lastResult = data;
  const cls = data.prediction.toLowerCase();
  $("stamp").textContent = data.prediction;
  $("stamp").className = `stamp ${cls}`;
  $("resultText").textContent = `This news looks ${data.prediction} (${data.confidence}% confidence)`;
  $("resultText").className = `result-text ${cls}`;

  const real = data.probabilities.REAL ?? 0;
  const fake = data.probabilities.FAKE ?? 0;
  $("realBar").style.width = `${real}%`;
  $("fakeBar").style.width = `${fake}%`;
  $("realPct").textContent = `${real}%`;
  $("fakePct").textContent = `${fake}%`;
  $("articleTitle").textContent = data.article_title ? `Article: ${data.article_title}` : "";
  $("fbMsg").textContent = "";

  // key words
  $("keyWords").innerHTML = data.key_words.length
    ? data.key_words
        .map((k) => `<li class="${k.towards}"><span>${escapeHtml(k.word)}</span><span>→ ${k.towards}</span></li>`)
        .join("")
    : `<li class="muted">No strong key words found.</li>`;

  // red flags
  $("redFlags").innerHTML = data.red_flags.length
    ? data.red_flags.map((f) => `<li>${escapeHtml(f)}</li>`).join("")
    : `<li class="ok">No common warning signs found.</li>`;

  const s = data.text_stats;
  $("textStats").textContent = `${s.words} words · ${s.sentences} sentences · ~${s.reading_time_sec}s read`;

  // highlighted text
  const map = {};
  data.key_words.forEach((k) => (map[k.word] = k.towards));
  $("highlighted").innerHTML = originalText
    .split(/(\s+)/)
    .map((tok) => {
      const key = tok.toLowerCase().replace(/[^a-z]/g, "");
      if (map[key]) return `<mark class="hl-${map[key].toLowerCase()}">${escapeHtml(tok)}</mark>`;
      return escapeHtml(tok);
    })
    .join("");

  $("result").hidden = false;
  $("result").scrollIntoView({ behavior: "smooth", block: "start" });
}

/* ---------------- feedback & copy ---------------- */
async function sendFeedback(isCorrect) {
  if (!lastResult) return;
  try {
    const d = await api("/api/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ prediction_id: lastResult.id, is_correct: isCorrect }),
    });
    $("fbMsg").textContent = d.message;
  } catch (e) {
    $("fbMsg").textContent = e.message;
  }
}
$("fbYes").addEventListener("click", () => sendFeedback(true));
$("fbNo").addEventListener("click", () => sendFeedback(false));

$("copyBtn").addEventListener("click", async () => {
  if (!lastResult) return;
  const text = `Fake News Detector result: ${lastResult.prediction} (${lastResult.confidence}% confidence)`;
  try {
    await navigator.clipboard.writeText(text);
    toast("Result copied to clipboard");
  } catch (e) {
    toast(text);
  }
});

/* ---------------- batch ---------------- */
$("batchBtn").addEventListener("click", async () => {
  $("batchError").hidden = true;
  const file = $("batchFile").files[0];
  if (!file) {
    $("batchError").textContent = "Please choose a CSV file first.";
    $("batchError").hidden = false;
    return;
  }
  const form = new FormData();
  form.append("file", file);
  $("batchBtn").disabled = true;
  $("batchBtn").textContent = "Checking…";
  try {
    const data = await api("/api/predict-batch", { method: "POST", body: form });
    $("bTotal").textContent = data.summary.total;
    $("bReal").textContent = data.summary.real;
    $("bFake").textContent = data.summary.fake;
    $("batchBody").innerHTML = data.results
      .map(
        (r, i) => `<tr><td>${i + 1}</td><td class="text" title="${escapeHtml(r.text)}">${escapeHtml(r.text)}</td>
        <td><span class="badge ${r.prediction}">${r.prediction}</span></td><td>${r.confidence}%</td></tr>`
      )
      .join("");
    $("batchResult").hidden = false;
  } catch (e) {
    $("batchError").textContent = e.message;
    $("batchError").hidden = false;
  } finally {
    $("batchBtn").disabled = false;
    $("batchBtn").textContent = "Run batch check";
  }
});

/* ---------------- dashboard ---------------- */
async function loadDashboard() {
  const s = await api("/api/stats");
  $("statTotal").textContent = s.total;
  $("statReal").textContent = s.real;
  $("statFake").textContent = s.fake;
  $("statConf").textContent = `${s.avg_confidence}%`;
  $("feedbackMeta").textContent = s.feedback_total
    ? `User feedback: ${s.feedback_correct} of ${s.feedback_total} predictions marked correct (${Math.round(
        (s.feedback_correct / s.feedback_total) * 100
      )}%).`
    : "No user feedback yet. Mark results as correct / wrong to improve the model.";

  if (window.Chart) {
    const css = getComputedStyle(document.documentElement);
    const realC = css.getPropertyValue("--real").trim();
    const fakeC = css.getPropertyValue("--fake").trim();
    const inkC = css.getPropertyValue("--ink").trim();
    Chart.defaults.color = inkC;

    pieChart?.destroy();
    pieChart = new Chart($("pieChart"), {
      type: "doughnut",
      data: { labels: ["Real", "Fake"], datasets: [{ data: [s.real, s.fake], backgroundColor: [realC, fakeC] }] },
      options: { plugins: { legend: { position: "bottom" } } },
    });

    barChart?.destroy();
    barChart = new Chart($("barChart"), {
      type: "bar",
      data: {
        labels: s.daily.map((d) => d.day),
        datasets: [
          { label: "Real", data: s.daily.map((d) => d.real), backgroundColor: realC },
          { label: "Fake", data: s.daily.map((d) => d.fake), backgroundColor: fakeC },
        ],
      },
      options: {
        scales: { x: { stacked: true }, y: { stacked: true, beginAtZero: true, ticks: { precision: 0 } } },
        plugins: { legend: { position: "bottom" } },
      },
    });
  }

  try {
    const m = await api("/api/model-info");
    $("modelMeta").textContent = `Active model: ${m.best_model} · trained ${m.trained_at} on ${m.dataset} (${m.train_size} train / ${m.test_size} test rows)`;
    $("modelBody").innerHTML = m.results
      .map(
        (r) => `<tr class="${r.model === m.best_model ? "best" : ""}"><td>${r.model}${r.model === m.best_model ? " ★" : ""}</td>
        <td>${r.accuracy}%</td><td>${r.precision}%</td><td>${r.recall}%</td><td>${r.f1}%</td></tr>`
      )
      .join("");
  } catch (e) {
    $("modelMeta").textContent = e.message;
  }
}

$("retrainBtn").addEventListener("click", async () => {
  $("retrainBtn").disabled = true;
  $("retrainBtn").textContent = "Training…";
  try {
    await api("/api/retrain", { method: "POST" });
    toast("Model retrained");
    loadDashboard();
  } catch (e) {
    toast(e.message);
  } finally {
    $("retrainBtn").disabled = false;
    $("retrainBtn").textContent = "Retrain with feedback";
  }
});

/* ---------------- history ---------------- */
async function loadHistory() {
  const params = new URLSearchParams({ search: $("searchBox").value, label: $("labelFilter").value });
  const rows = await api(`/api/history?${params}`);
  if (!rows.length) {
    $("historyBody").innerHTML = `<tr><td colspan="8" class="muted">No checks found.</td></tr>`;
    return;
  }
  $("historyBody").innerHTML = rows
    .map((r) => {
      const fb = r.is_correct === null ? "—" : r.is_correct ? "Correct" : "Wrong";
      return `<tr>
        <td>${r.id}</td>
        <td class="text" title="${escapeHtml(r.news_text)}">${escapeHtml(r.news_text)}</td>
        <td>${r.source}</td>
        <td><span class="badge ${r.prediction}">${r.prediction}</span></td>
        <td>${r.confidence}%</td>
        <td>${fb}</td>
        <td>${r.created_at}</td>
        <td><button class="del" data-id="${r.id}">Delete</button></td>
      </tr>`;
    })
    .join("");
}

$("historyBody").addEventListener("click", async (e) => {
  if (!e.target.matches(".del")) return;
  await api(`/api/history/${e.target.dataset.id}`, { method: "DELETE" });
  loadHistory();
});

let searchTimer;
$("searchBox").addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(loadHistory, 300);
});
$("labelFilter").addEventListener("change", loadHistory);

$("clearHistoryBtn").addEventListener("click", async () => {
  if (!confirm("Delete all saved checks?")) return;
  await api("/api/history", { method: "DELETE" });
  loadHistory();
  toast("History cleared");
});
