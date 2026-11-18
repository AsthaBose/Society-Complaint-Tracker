"use strict";

// ---------- tiny helpers ----------
const $ = (sel) => document.querySelector(sel);
const show = (el, on = true) => el.classList.toggle("hidden", !on);

// Everything user-written goes through textContent or this function, never raw innerHTML.
const esc = (s) =>
  String(s).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

const store = {
  get(k) { try { return localStorage.getItem(k); } catch { return null; } },
  set(k, v) { try { localStorage.setItem(k, v); } catch { /* private mode: stay logged in for this tab only */ } },
  del(k) { try { localStorage.removeItem(k); } catch { /* ignore */ } },
};

const state = { token: store.get("token"), user: null };

function toast(msg) {
  const t = $("#toast");
  t.textContent = msg;
  show(t);
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => show(t, false), 2500);
}

// Server timestamps are naive UTC; append Z so the browser converts to the viewer's local time.
const fmt = (iso) => new Date(iso + "Z").toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
const label = (s) => s.replace("_", " ");

async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  if (body) headers["Content-Type"] = "application/json";
  if (state.token) headers.Authorization = "Bearer " + state.token;
  const res = await fetch("/api" + path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  if (res.status === 401 && state.token) {
    logout();
    throw new Error("Session expired. Please log in again.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const d = data.detail;
    // FastAPI validation errors are a list of {loc, msg}; show the first one readably.
    throw new Error(Array.isArray(d) ? `${d[0].loc.slice(-1)[0]}: ${d[0].msg}` : d || "Something went wrong");
  }
  return data;
}

// ---------- views ----------
function setView(name) {
  show($("#view-auth"), name === "auth");
  show($("#view-main"), name === "main");
  show($("#view-detail"), name === "detail");
}

function logout() {
  state.token = null;
  state.user = null;
  store.del("token");
  show($("#userbox"), false);
  setView("auth");
}

function startSession(token, user) {
  state.token = token;
  state.user = user;
  store.set("token", token);
  $("#whoami").textContent = `${user.name} · ${user.flat_no} · ${user.role}`;
  show($("#userbox"));
  const committee = user.role === "committee";
  $("#list-title").textContent = committee ? "All complaints" : "My complaints";
  show($("#stats"), committee);
  setView("main");
  refresh();
}

async function refresh() {
  const tasks = [loadList()];
  if (state.user.role === "committee") tasks.push(loadStats());
  await Promise.allSettled(tasks);
}

async function loadStats() {
  const s = await api("/stats");
  const hours = s.avg_resolution_hours;
  const avg = hours === null ? "–" : hours < 48 ? hours + " h" : (hours / 24).toFixed(1) + " d";
  const cards = [
    ["Open", s.open], ["In progress", s.in_progress], ["Resolved", s.resolved],
    ["High urgency open", s.high_urgency_open], ["Avg. time to resolve", avg],
  ];
  $("#stats").innerHTML = cards
    .map(([l, n]) => `<div class="stat"><div class="num">${esc(n)}</div><div class="lbl">${esc(l)}</div></div>`)
    .join("");
}

async function loadList() {
  const params = new URLSearchParams();
  if ($("#filter-status").value) params.set("status", $("#filter-status").value);
  if ($("#filter-category").value) params.set("category", $("#filter-category").value);
  const qs = params.toString();
  const items = await api("/complaints" + (qs ? "?" + qs : ""));

  const ul = $("#complaint-list");
  ul.innerHTML = "";
  show($("#empty"), items.length === 0);
  for (const c of items) {
    const li = document.createElement("li");
    const btn = document.createElement("button");
    btn.className = "item";
    btn.innerHTML =
      `<div class="t"></div>` +
      `<div class="meta"><span class="badge b-${esc(c.status)}">${esc(label(c.status))}</span>` +
      `<span class="badge b-${esc(c.urgency)}">${esc(c.urgency)}</span>` +
      `<span class="badge b-cat">${esc(c.category)}</span> ` +
      `<span class="who"></span></div>`;
    btn.querySelector(".t").textContent = c.title;
    btn.querySelector(".who").textContent = `${c.author_name} (${c.flat_no}) · ${fmt(c.created_at)}`;
    btn.addEventListener("click", () => openDetail(c.id));
    li.appendChild(btn);
    ul.appendChild(li);
  }
}

async function openDetail(id) {
  const c = await api("/complaints/" + id);
  const box = $("#detail");
  const committee = state.user.role === "committee";

  box.innerHTML = `
    <h2></h2>
    <div><span class="badge b-${esc(c.status)}">${esc(label(c.status))}</span>
      <span class="badge b-${esc(c.urgency)}">${esc(c.urgency)}</span>
      <span class="badge b-cat">${esc(c.category)}</span></div>
    <p class="muted meta-line"></p>
    <p class="detail-desc"></p>
    <h3>History</h3>
    <ul class="timeline"></ul>
    ${committee ? `
    <form class="update-form stack">
      <h3>Update status</h3>
      <label>Status
        <select name="status">
          <option value="open">Open</option>
          <option value="in_progress">In progress</option>
          <option value="resolved">Resolved</option>
        </select></label>
      <label>Note for the resident <textarea name="note" rows="2" maxlength="1000"></textarea></label>
      <button class="btn primary">Save update</button>
      <p class="error"></p>
    </form>` : ""}`;

  box.querySelector("h2").textContent = c.title;
  box.querySelector(".meta-line").textContent = `${c.author_name} (${c.flat_no}) · reported ${fmt(c.created_at)}`;
  box.querySelector(".detail-desc").textContent = c.description;

  const tl = box.querySelector(".timeline");
  for (const u of c.updates) {
    const li = document.createElement("li");
    li.innerHTML = `<strong>${esc(label(u.status))}</strong> <span class="muted"></span><div class="note"></div>`;
    li.querySelector(".muted").textContent = `· ${u.editor_name} · ${fmt(u.created_at)}`;
    li.querySelector(".note").textContent = u.note;
    tl.appendChild(li);
  }

  if (committee) {
    const form = box.querySelector(".update-form");
    form.status.value = c.status;
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const err = form.querySelector(".error");
      err.textContent = "";
      try {
        await api(`/complaints/${id}/status`, {
          method: "PATCH",
          body: { status: form.status.value, note: form.note.value },
        });
        toast("Updated");
        await openDetail(id);
      } catch (ex) {
        err.textContent = ex.message;
      }
    });
  }
  setView("detail");
}

// ---------- events ----------
document.querySelectorAll(".tab").forEach((tab) =>
  tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach((t) => t.classList.toggle("active", t === tab));
    show($("#form-login"), tab.dataset.tab === "login");
    show($("#form-register"), tab.dataset.tab === "register");
    $("#auth-error").textContent = "";
  })
);

async function submitAuth(form, path, pick) {
  const btn = form.querySelector("button");
  btn.disabled = true;
  $("#auth-error").textContent = "";
  try {
    const body = pick(Object.fromEntries(new FormData(form)));
    const res = await api(path, { method: "POST", body });
    startSession(res.access_token, res.user);
    form.reset();
  } catch (ex) {
    $("#auth-error").textContent = ex.message;
  } finally {
    btn.disabled = false;
  }
}

$("#form-login").addEventListener("submit", (e) => {
  e.preventDefault();
  submitAuth(e.target, "/auth/login", (d) => d);
});
$("#form-register").addEventListener("submit", (e) => {
  e.preventDefault();
  submitAuth(e.target, "/auth/register", (d) => {
    if (!d.committee_code) delete d.committee_code;
    return d;
  });
});

$("#form-complaint").addEventListener("submit", async (e) => {
  e.preventDefault();
  const form = e.target;
  const btn = form.querySelector("button");
  const err = $("#complaint-error");
  err.textContent = "";
  btn.disabled = true;
  try {
    const body = Object.fromEntries(new FormData(form));
    if (!body.category) delete body.category;
    if (!body.urgency) delete body.urgency;
    await api("/complaints", { method: "POST", body });
    form.reset();
    toast("Complaint submitted");
    await refresh();
  } catch (ex) {
    err.textContent = ex.message;
  } finally {
    btn.disabled = false;
  }
});

$("#filter-status").addEventListener("change", loadList);
$("#filter-category").addEventListener("change", loadList);
$("#back").addEventListener("click", () => { setView("main"); refresh(); });
$("#logout").addEventListener("click", logout);

// ---------- boot ----------
(async function boot() {
  if (!state.token) return setView("auth");
  try {
    startSession(state.token, await api("/auth/me"));
  } catch {
    logout();
  }
})();
