import { royalty, inkForPaper, isLarge, SYMBOL, MARKET, PRICING_SOURCE } from "./pricing.js";

const view = document.getElementById("view");
const STEPS = [
  ["brief", "Brief"], ["questions", "Questions"], ["outline", "Outline"], ["manuscript", "Manuscript"],
  ["preview", "Preview"], ["art", "Art & build"], ["publish", "Publish"],
];
const TYPES = {
  picture_book: { label: "Picture book", icon: "image", trim: "8.5x8.5", paper: "premium_color", hint: "Ages 2–8 · art on every page" },
  storybook: { label: "Storybook", icon: "book", trim: "8.27x11.69", paper: "premium_color", hint: "Full color · story, exercises, tips and games" },
  comic: { label: "Comic", icon: "grid", trim: "7x10", paper: "premium_color", hint: "Panels and speech balloons" },
};
const PAPERS = { white_bw: "Black & white · white", cream_bw: "Black & white · cream",
  standard_color: "Standard color", premium_color: "Premium color" };

// ---------- icons (inline, 16px, stroke) ----------
const ICONS = {
  library: '<path d="M4 4h4v16H4zM10 4h4v16h-4z"/><path d="m16.5 4.5 3.5 1-4 15-3.5-1"/>',
  plus: '<path d="M12 5v14M5 12h14"/>',
  users: '<circle cx="9" cy="8.5" r="3.2"/><path d="M3.5 19.5c.6-3.4 2.8-5.2 5.5-5.2s4.9 1.8 5.5 5.2"/><circle cx="16.5" cy="9" r="2.6"/><path d="M15.5 14.4c2.6-.2 4.4 1.4 5 4.6"/>',

  compass: '<circle cx="12" cy="12" r="9"/><path d="m15.5 8.5-2 5-5 2 2-5z"/>',
  settings: '<path d="M4 7h10M18 7h2M4 17h4M12 17h8"/><circle cx="16" cy="7" r="2"/><circle cx="10" cy="17" r="2"/>',
  check: '<path d="m5 12.5 4.5 4.5L19 7.5"/>',
  x: '<path d="M6 6l12 12M18 6 6 18"/>',
  alert: '<path d="M12 4 2.5 20h19z"/><path d="M12 10v4M12 17.2v.1"/>',
  info: '<circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.1"/>',
  sparkle: '<path d="M12 3.5 13.8 10.2 20.5 12l-6.7 1.8L12 20.5l-1.8-6.7L3.5 12l6.7-1.8z"/>',
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4 3.5"/>',
  book: '<path d="M4 5.5c2.7-1 5.5-.8 8 .7v13c-2.5-1.5-5.3-1.7-8-.7zM20 5.5c-2.7-1-5.5-.8-8 .7v13c2.5-1.5 5.3-1.7 8-.7z"/>',
  grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="17" height="7" rx="1.5"/>',
  download: '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14"/>',
  file: '<path d="M7 3.5h7l4.5 4.5v12.5H7z"/><path d="M14 3.5V8h4.5"/>',
  copy: '<rect x="8.5" y="8.5" width="11" height="11" rx="2"/><path d="M15.5 8.5v-3a1.5 1.5 0 0 0-1.5-1.5H6A1.5 1.5 0 0 0 4.5 5.5V14A1.5 1.5 0 0 0 6 15.5h2.5"/>',
  more: '<circle cx="6" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="18" cy="12" r="1"/>',
  trash: '<path d="M4.5 7h15M10 11v6M14 11v6M6.5 7l1 13h9l1-13M9.5 7V4.5h5V7"/>',
  refresh: '<path d="M19.5 12a7.5 7.5 0 1 1-2.2-5.3M19.5 4.5v4h-4"/>',
  play: '<path d="M7.5 5v14l11-7z"/>',
  edit: '<path d="M4.5 19.5h4l10-10-4-4-10 10z"/><path d="m13 7 4 4"/>',
  eye: '<path d="M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12z"/><circle cx="12" cy="12" r="2.8"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  chevL: '<path d="m15 5-7 7 7 7"/>',
  chevR: '<path d="m9 5 7 7-7 7"/>',
  layers: '<path d="m12 3.5 9 5-9 5-9-5z"/><path d="m3 13.5 9 5 9-5"/>',
  wand: '<path d="m4 20 11-11M14 4v3M12.5 5.5h3M19 9v3M17.5 10.5h3"/><path d="m13 8 3 3"/>',
  ext: '<path d="M14 4.5h5.5V10M19.5 4.5 11 13M18 13.5v5a1.5 1.5 0 0 1-1.5 1.5h-11A1.5 1.5 0 0 1 4 18.5v-11A1.5 1.5 0 0 1 5.5 6h5"/>',
  mic: '<rect x="9" y="3.5" width="6" height="11" rx="3"/><path d="M5.5 11.5a6.5 6.5 0 0 0 13 0M12 18v2.5"/>',
  dollar: '<path d="M12 3.5v17M16 7.5c-.6-1.3-2.1-2-4-2-2.4 0-4 1.2-4 3s1.6 2.6 4 3c2.4.4 4 1.2 4 3s-1.6 3-4 3c-1.9 0-3.4-.7-4-2"/>',
};
const icon = (n, cls = "") => `<svg class="i ${cls}" viewBox="0 0 24 24" aria-hidden="true">${ICONS[n] || ""}</svg>`;

// ---------- full-screen image viewer ----------
// Click any preview image (book spreads, cover, art review, characters) to see it full screen.
// Arrows / swipe browse the images in the same group, Esc or a click outside closes, a click on the image toggles 100%.
const LIGHTBOX_IMGS = ".spread img, .cover-view img, .shot .img img";
document.addEventListener("click", (e) => {
  const img = e.target.closest(LIGHTBOX_IMGS);
  if (!img || e.button !== 0) return;
  const group = img.closest(".spreads, .cover-view, .review") || img.parentElement;
  const imgs = [...group.querySelectorAll(LIGHTBOX_IMGS)];
  openLightbox(imgs, imgs.indexOf(img));
});

function openLightbox(imgs, i) {
  const prevFocus = document.activeElement;
  const box = document.createElement("div");
  box.className = "lightbox";
  box.setAttribute("role", "dialog");
  box.setAttribute("aria-modal", "true");
  const many = imgs.length > 1;
  box.innerHTML = `<div class="lb-stage"><img alt=""></div>
    <div class="lb-bar"><span class="lb-cap"></span>
      <a class="btn icon ghost lb-open" target="_blank" rel="noopener" aria-label="Open in new tab">${icon("ext")}</a>
      <button class="btn icon ghost lb-close" aria-label="Close">${icon("x")}</button></div>
    ${many ? `<button class="lb-nav prev" aria-label="Previous">${icon("chevL")}</button>
      <button class="lb-nav next" aria-label="Next">${icon("chevR")}</button>` : ""}`;
  const big = box.querySelector(".lb-stage img"), stage = box.querySelector(".lb-stage");
  const show = (n) => {
    i = (n + imgs.length) % imgs.length;
    const t = imgs[i], full = t.dataset.full || t.currentSrc || t.src;
    box.classList.remove("actual");
    big.onerror = () => { if (big.src !== t.src) big.src = t.src; };  // no full-size file: fall back to the preview
    big.src = full;
    big.alt = t.alt;
    box.querySelector(".lb-open").href = full;
    box.querySelector(".lb-cap").textContent = `${t.alt || ""}${many ? `  ·  ${i + 1} / ${imgs.length}` : ""}`;
  };
  const close = () => { document.removeEventListener("keydown", key, true); box.remove(); prevFocus?.focus?.(); };
  const key = (e) => {
    if (e.key === "Escape") close();
    else if (many && e.key === "ArrowRight") show(i + 1);
    else if (many && e.key === "ArrowLeft") show(i - 1);
    else return;
    e.preventDefault(); e.stopPropagation();
  };
  box.addEventListener("click", (e) => {
    if (e.target.closest(".lb-close")) close();
    else if (e.target.closest(".lb-nav.prev")) show(i - 1);
    else if (e.target.closest(".lb-nav.next")) show(i + 1);
    else if (e.target === big) box.classList.toggle("actual");
    else if (!e.target.closest(".lb-bar")) close();
  });
  let x0 = null;
  stage.addEventListener("touchstart", (e) => { x0 = e.touches[0].clientX; }, { passive: true });
  stage.addEventListener("touchend", (e) => {
    if (x0 == null || !many || box.classList.contains("actual")) return;
    const dx = e.changedTouches[0].clientX - x0; x0 = null;
    if (Math.abs(dx) > 50) show(dx < 0 ? i + 1 : i - 1);
  });
  document.addEventListener("keydown", key, true);
  document.body.append(box);
  show(i);
  box.querySelector(".lb-close").focus();
}

// ---------- helpers ----------
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const $ = (sel, root = view) => root.querySelector(sel);
const $$ = (sel, root = view) => [...root.querySelectorAll(sel)];
const money = (x) => `$${Number(x).toFixed(2)}`;
const bytes = (n) => (n > 1e6 ? `${(n / 1e6).toFixed(1)} MB` : `${Math.max(1, Math.round(n / 1e3))} KB`);

function timeAgo(sec) {
  if (!sec) return "";
  const d = Date.now() / 1000 - sec;
  if (d < 60) return "just now";
  if (d < 3600) return `${Math.floor(d / 60)} min ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`;
  return new Date(sec * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

async function api(method, url, body) {
  const res = await fetch(url, { method, headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined });
  const data = res.headers.get("content-type")?.includes("json") ? await res.json() : await res.text();
  if (!res.ok) throw new Error(typeof data === "object" ? (typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail)) : data);
  return data;
}

function toast(msg, err = false) {
  const t = document.createElement("div");
  t.className = "toast" + (err ? " err" : "");
  t.innerHTML = `${icon(err ? "alert" : "check")}<div>${esc(msg)}</div>`;
  document.getElementById("toasts").append(t);
  setTimeout(() => { t.classList.add("out"); setTimeout(() => t.remove(), 220); }, err ? 7000 : 3200);
}

// Promise-based modal. Resolves to the form values (or true) on confirm, null on cancel.
function modal({ title, body = "", confirm = "Confirm", danger = false, fields = "" }) {
  return new Promise((resolve) => {
    const root = document.getElementById("modal-root");
    root.innerHTML = `<div class="backdrop"><form class="modal" role="dialog" aria-modal="true" aria-labelledby="m-t">
      <div class="mb"><h2 id="m-t">${esc(title)}</h2>${body ? `<p>${body}</p>` : ""}${fields}</div>
      <div class="mf"><button type="button" class="btn" data-x>Cancel</button>
        <button class="btn ${danger ? "danger solid" : "primary"}">${esc(confirm)}</button></div></form></div>`;
    const form = $("form", root);
    const close = (v) => { root.innerHTML = ""; document.removeEventListener("keydown", onKey); resolve(v); };
    const onKey = (e) => e.key === "Escape" && close(null);
    document.addEventListener("keydown", onKey);
    $("[data-x]", root).onclick = () => close(null);
    // braces matter: an onclick that returns false cancels the click, which would block the submit button
    $(".backdrop", root).onclick = (e) => { if (e.target.classList.contains("backdrop")) close(null); };
    form.onsubmit = (e) => { e.preventDefault(); const v = Object.fromEntries(new FormData(form)); close(Object.keys(v).length ? v : true); };
    voiceify(root);
    (form.querySelector("input,textarea") || form.querySelector(".btn.primary,.btn.solid")).focus();
  });
}

// run an async action with a spinner on the button; errors become a toast
async function busy(btn, label, fn) {
  const old = btn.innerHTML; btn.disabled = true;
  btn.innerHTML = `<span class="spin"></span>${esc(label)}`;
  try { return await fn(); } catch (e) { toast(e.message, true); } finally { if (btn.isConnected) { btn.disabled = false; btn.innerHTML = old; } }
}

function note(kind, html) {
  const ic = { ok: "check", warn: "alert", err: "alert", info: "info" }[kind] || "info";
  return `<div class="note ${kind}">${icon(ic)}<div class="body">${html}</div></div>`;
}

function badge(status) {
  const map = { ready: "ok", "preflight failed": "err", "mock preview": "warn", manuscript: "accent" };
  const label = { ready: "Ready to publish", "preflight failed": "Preflight failed", "mock preview": "Preview built",
    manuscript: "Manuscript", draft: "Draft" }[status] || status;
  return `<span class="badge ${map[status] || ""}">${esc(label)}</span>`;
}

function md(src) {
  const inline = (s) => esc(s).replace(/\*\*(.+?)\*\*/g, "<b>$1</b>").replace(/\*(.+?)\*/g, "<i>$1</i>").replace(/`(.+?)`/g, "<code>$1</code>");
  const out = []; let list = null;
  const close = () => { if (list) { out.push(`</${list}>`); list = null; } };
  for (const line of src.split("\n")) {
    let m;
    if ((m = line.match(/^(#{1,4})\s+(.*)/))) { close(); const n = Math.min(m[1].length + 1, 3); out.push(`<h${n}>${inline(m[2])}</h${n}>`); }
    else if ((m = line.match(/^\s*[-*]\s+(.*)/))) { if (list !== "ul") { close(); out.push("<ul>"); list = "ul"; } out.push(`<li>${inline(m[1])}</li>`); }
    else if ((m = line.match(/^\s*\d+[.)]\s+(.*)/))) { if (list !== "ol") { close(); out.push("<ol>"); list = "ol"; } out.push(`<li>${inline(m[1])}</li>`); }
    else if (!line.trim()) close();
    else { close(); out.push(`<p>${inline(line)}</p>`); }
  }
  close();
  return out.join("");
}

// tinted placeholder cover from the title
function coverPlaceholder(title, type) {
  let h = 0; for (const c of title || "") h = (h * 31 + c.charCodeAt(0)) % 360;
  const bg = `linear-gradient(160deg, hsl(${h} 55% 46%), hsl(${(h + 40) % 360} 60% 32%))`;
  return `<div class="ph" style="background:${bg}"><span>${esc(TYPES[type]?.label || "Book")}</span><b>${esc(title)}</b></div>`;
}

// ---------- voice input ----------
// A mic button on text fields: speak, and the words are typed into the field (browser speech recognition,
// free, no credits). The language is set in Settings.
const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
let dictation = null;

function voiceify(root) {
  if (!Speech) return;
  root.querySelectorAll("textarea.input:not(.code), input.input:not([type]), input.input[type=text]").forEach((f) => {
    if (f.closest(".voice-wrap")) return;
    const wrap = document.createElement("div");
    wrap.className = `voice-wrap${f.tagName === "TEXTAREA" ? " area" : ""}`;
    f.replaceWith(wrap);
    f.dir = "auto";
    const b = document.createElement("button");
    b.type = "button"; b.className = "mic"; b.title = "Speak to fill this field"; b.setAttribute("aria-label", "Dictate");
    b.innerHTML = icon("mic");
    b.onclick = () => dictate(f, b);
    wrap.append(f, b);
  });
}

function dictate(field, btn) {
  if (dictation) { const same = dictation.btn === btn; dictation.rec.stop(); if (same) return; }
  const rec = new Speech();
  rec.lang = settingsCache?.settings?.voice_lang || "fa-IR";
  rec.interimResults = true; rec.continuous = true;
  const before = field.value && !/\s$/.test(field.value) ? `${field.value} ` : field.value;
  rec.onresult = (e) => {
    field.value = before + [...e.results].map((r) => r[0].transcript).join("");
    field.dispatchEvent(new Event("input", { bubbles: true }));
  };
  rec.onerror = (e) => {
    if (e.error === "not-allowed") toast("Allow the microphone for this page to use voice input", true);
    else if (!["aborted", "no-speech"].includes(e.error)) toast(`Voice input: ${e.error}`, true);
  };
  rec.onend = () => { btn.classList.remove("on"); if (dictation?.rec === rec) dictation = null; };
  dictation = { rec, btn };
  btn.classList.add("on");
  rec.start();
}

// ---------- jobs ----------
function logLine(s) {
  const cls = /^(ERROR|FAILED|NEEDS ATTENTION)/.test(s) ? "e" : /^WARN/.test(s) ? "w" : /PASS|score \d/.test(s) ? "g" : "";
  return `<span class="${cls}">${esc(s)}</span>\n`;
}

function jobPanel(title) {
  return `<div class="job" id="job" hidden>
    <div class="job-h"><span class="spin" id="job-spin"></span>
      <div class="job-tt"><div class="t" id="job-t">${esc(title)}</div><div class="faint small" id="job-sub"></div></div>
      <div class="job-n num" id="job-n"></div></div>
    <div class="progress indet" id="job-p"><i></i></div>
    <div class="job-live" id="job-live" hidden><div class="review" id="job-grid"></div></div>
    <details class="logbox" id="job-d"><summary>Show log</summary><pre class="log" id="job-log"></pre></details></div>`;
}

const dur = (sec) => sec < 60 ? `${Math.max(1, Math.round(sec))}s` : sec < 3600 ? `${Math.round(sec / 60)} min` : `${(sec / 3600).toFixed(1)} h`;
const JOB_LABELS = { mock: "Building preview", pilot: "Generating pilot", art: "Generating art",
  regen: "Redrawing image", build: "Building print files" };

// one tile in the live grid: a finished image, a failed one, or one being drawn right now
function liveTile(slug, id, im) {
  if (!im) return `<div class="shot drawing" data-tile="${esc(id)}"><div class="img"><div class="sk"></div><span class="spin"></span></div>
    <div class="m"><div class="row between"><span class="tag">${esc(id)}</span><span class="faint xs">drawing…</span></div></div></div>`;
  const score = /score (\d+)/.exec(im.result)?.[1];
  const badge = im.failed ? `<span class="badge err">failed</span>`
    : score ? `<span class="badge ${+score >= 7 ? "ok" : "warn"}">${score}/10</span>`
    : /no cost/.test(im.result) ? `<span class="badge plain">already had</span>` : `<span class="badge ok">done</span>`;
  const src = `/api/books/${slug}/build/thumbs/${id}.jpg?${Math.round(im.t)}`;
  return `<div class="shot landed ${im.failed ? "bad" : ""}" data-tile="${esc(id)}"><div class="img">${im.failed ? icon("alert")
      : `<img src="${src}" data-full="/api/books/${slug}/build/art/${id}.png?${Math.round(im.t)}" alt="${esc(id)}">`}</div>
    <div class="m"><div class="row between"><span class="tag">${esc(id)}</span>${badge}</div></div></div>`;
}

// Follow a job until it ends. Works the same for a job just started and one picked up again after a
// page refresh: everything shown comes from the server. total = expected image count if the server doesn't say.
async function watchJob(id, title, total = 0) {
  const box = $("#job"), pre = $("#job-log"), bar = $("#job-p"), n = $("#job-n"), sub = $("#job-sub");
  const live = $("#job-live"), grid = $("#job-grid");
  box.hidden = false; pre.innerHTML = ""; grid.innerHTML = ""; $("#job-t").textContent = title; $("#job-spin").hidden = false;
  bar.className = "progress indet"; bar.firstElementChild.style.width = "";
  box.scrollIntoView({ behavior: "smooth", block: "nearest" });
  const base = title.replace(/…$/, "");
  let since = 0, failures = 0;
  for (;;) {
    let j;
    try { j = await api("GET", `/api/jobs/${id}?since=${since}`); }
    catch (e) {
      // the server restarted (jobs live in its memory) or the network dropped
      if (/404|Not Found/i.test(e.message)) { $("#job-spin").hidden = true; sub.textContent = "This job is gone: the server was restarted. Images finished before that are saved; run it again to continue."; bar.className = "progress failed"; return { status: "failed", result: {} }; }
      if (++failures > 20) throw e;
      sub.textContent = "Connection lost, retrying…"; await new Promise((r) => setTimeout(r, 2000)); continue;
    }
    failures = 0;
    if (j.lines.length) { pre.insertAdjacentHTML("beforeend", j.lines.map(logLine).join("")); pre.scrollTop = pre.scrollHeight; }
    since = j.next;
    const pg = j.progress, tot = pg.total || total, done = pg.done;
    const elapsed = (j.ended || j.now) - j.started;
    if (tot) {
      const pct = Math.min(100, Math.round((done / tot) * 100));
      bar.className = "progress"; bar.firstElementChild.style.width = `${Math.max(pct, 2)}%`;
      n.innerHTML = `<b>${pct}%</b><span class="faint"> · ${done} of ${tot}</span>`;
      // only count images actually drawn this run for the time estimate (cached ones are instant)
      const drawn = pg.images.filter((x) => !/no cost/.test(x.result));
      const left = tot - done;
      // images per second so far already includes the parallel workers
      const eta = drawn.length >= 2 && left > 0 ? left / (drawn.length / elapsed) : null;
      sub.textContent = [pg.phase, pg.active.length ? `drawing ${pg.active.join(", ")}` : "", `${dur(elapsed)} elapsed`,
        eta ? `about ${dur(eta)} left` : left ? "estimating time left…" : ""].filter(Boolean).join(" · ");
    } else {
      sub.textContent = `${dur(elapsed)} elapsed`;
    }
    // live grid: finished images appear as they land; the ones being drawn show as placeholders
    if (pg.images.length || pg.active.length) {
      live.hidden = false;
      const want = [...pg.images.map((x) => x.id), ...pg.active.filter((a) => !pg.images.some((x) => x.id === a))];
      const byId = Object.fromEntries(pg.images.map((x) => [x.id, x]));
      for (const sid of want) {
        const el = grid.querySelector(`[data-tile="${CSS.escape(sid)}"]`);
        const landed = !!byId[sid];
        if (el && (el.classList.contains("landed") || !landed)) continue;
        const html = liveTile(j.slug, sid, byId[sid]);
        if (el) el.outerHTML = html; else grid.insertAdjacentHTML("beforeend", html);
      }
      $$("[data-tile]", grid).forEach((el) => { if (!want.includes(el.dataset.tile)) el.remove(); });
    }
    if (j.status !== "running") {
      $("#job-spin").hidden = true;
      bar.className = `progress ${j.status === "done" ? "done" : "failed"}`; bar.firstElementChild.style.width = "100%";
      $("#job-t").textContent = j.status === "done" ? `${base}: done` : `${base}: failed`;
      sub.textContent = `${j.status === "done" ? "Finished" : "Stopped"} in ${dur(elapsed)}` + (tot ? ` · ${done} of ${tot} images` : "");
      if (j.status !== "done") $("#job-d").open = true;
      return j;
    }
    await new Promise((r) => setTimeout(r, 1500));
  }
}

let settingsCache = null;
let setupCache = null;
async function setupStatus() {
  try { return (setupCache ??= await api("GET", "/api/setup")); } catch { return { onboarded: true }; }
}
async function getSettings() { return (settingsCache ??= await api("GET", "/api/settings")); }

// ---------- shell ----------
const NAV = [["library", "#/", "Library", "library"], ["new", "#/new", "New book", "plus"],
  ["characters", "#/characters", "Characters", "users"], ["templates", "#/templates", "Templates", "layers"],
  ["guide", "#/guide", "Publishing guide", "compass"], ["settings", "#/settings", "Settings", "settings"]];
document.getElementById("nav").innerHTML = NAV.map(([k, h, l, i]) => `<a href="${h}" data-nav="${k}">${icon(i)}<span>${l}</span></a>`).join("");

async function renderConn() {
  try {
    const { settings: s, credit } = await getSettings();
    const viaKey = !!s.anthropic_api_key;
    document.getElementById("conn").innerHTML = `<a class="conn" href="#/settings">
      <span class="sdot ${s.openai_api_key ? "ok" : "warn"}"></span>
      <span>Claude via ${viaKey ? "API key" : "Claude login"}<br><span class="faint">${s.openai_api_key ? "Images ready" : "Add OpenAI key for art"}${
        credit?.remaining != null ? ` · ~${money(credit.remaining)} credit` : ""}</span></span></a>`;
  } catch { /* offline */ }
}

async function route() {
  const parts = location.hash.replace(/^#\/?/, "").split("/").filter(Boolean);
  const top = parts[0] || "library";
  $$("[data-nav]", document).forEach((a) => a.classList.toggle("active", a.dataset.nav === (top === "book" ? "library" : top)));
  if (top !== "setup" && !(await setupStatus()).onboarded) { location.replace("#/setup"); return; }
  view.innerHTML = `<div class="page"><div class="sk" style="height:36px;width:220px;margin-bottom:24px"></div><div class="sk" style="height:240px"></div></div>`;
  try {
    if (top === "setup") await setupView(Number(parts[1]) || 1);
    else if (top === "library") await library();
    else if (top === "new") await newBook();
    else if (top === "book") await bookView(parts[1], parts[2]);
    else if (top === "characters") await characterLibrary();
    else if (top === "templates") await templateLibrary();
    else if (top === "guide") guide(parts[1]);
    else if (top === "settings") await settingsView();
    else view.innerHTML = `<div class="page">${note("info", `Page not found. <a href="#/">Back to the library</a>`)}</div>`;
  } catch (e) {
    view.innerHTML = `<div class="page">${note("err", esc(e.message))}</div>`;
  }
  view.focus({ preventScroll: true });
  window.scrollTo(0, 0);
}
window.addEventListener("hashchange", route);
renderConn();
route();

// ---------- library ----------
async function library() {
  const books = await api("GET", "/api/books");
  const filter = sessionStorage.getItem("lib-filter") || "all";
  const show = (b) => filter === "all" || (filter === "ready" ? b.status === "ready" : b.status !== "ready");
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Library</h1><p class="sub">${books.length ? `${books.length} book${books.length > 1 ? "s" : ""}` : "Your books will appear here."}</p></div>
      <div class="row gap3">${books.length ? `<div class="seg" id="filter">${[["all", "All"], ["progress", "In progress"], ["ready", "Ready"]].map(([k, l]) =>
        `<button data-f="${k}" class="${k === filter ? "on" : ""}">${l}</button>`).join("")}</div>` : ""}
        <a class="btn primary" href="#/new">${icon("plus")}New book</a></div></div>
    ${books.length ? `<div class="books">${books.filter(show).map((b) => `
      <a class="book" href="#/book/${b.slug}">
        <div class="cover">${b.cover ? `<img src="/api/books/${b.slug}/front.jpg?${b.updated}" alt="">` : coverPlaceholder(b.title, b.type)}</div>
        <div class="meta"><h3>${esc(b.title)}</h3>
          <div class="row between">${badge(b.status)}<span class="faint xs">${timeAgo(b.updated)}</span></div>
          <span class="faint xs">${esc(TYPES[b.type]?.label || "")}${b.pages ? ` · ${b.pages} pages` : ""}</span></div></a>`).join("")}
      <a class="newtile" href="#/new">${icon("plus")}New book</a></div>`
    : `<div class="card"><div class="empty"><div class="ico">${icon("sparkle")}</div><h2>Start your first book</h2>
        <p>Describe the book you want. Claude asks a few questions, outlines it and writes the manuscript, then MosiBooks illustrates and lays it out for print.</p>
        <a class="btn primary" href="#/new">${icon("plus")}New book</a></div></div>`}</div>`;
  $$("#filter button").forEach((b) => (b.onclick = () => { try { sessionStorage.setItem("lib-filter", b.dataset.f); } catch {} library(); }));
}

// ---------- character library ----------
async function characterLibrary() {
  const { characters: chars } = await api("GET", "/api/characters");
  const v = Date.now();
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Characters</h1><p class="sub">Every character drawn for any of your books. A book that uses one of
      these names starts from exactly this look, so a series stays consistent. Pick them in a new book's brief.</p></div></div>
    ${chars.length ? `<div class="card"><div class="card-b"><div class="review">${chars.map((c) => `
      <div class="shot"><div class="img"><img src="/api/characters/${encodeURIComponent(c.id)}.png?${v}" alt="${esc(c.name)}" loading="lazy"></div>
        <div class="m"><div class="row between"><span class="tag">${esc(c.name)}</span><span class="faint xs">${esc(c.locked_at || "")}</span></div>
          <p class="faint xs">${esc(c.description)}</p>
          <span class="faint xs">From ${esc(c.source_book || "a book")}</span>
          <div class="row between">
            <label class="btn sm ghost"><input type="file" accept="image/png,image/jpeg,image/webp" hidden data-up="${esc(c.id)}">${icon("image")}Replace image</label>
            <button class="btn sm ghost" data-del="${esc(c.id)}" data-name="${esc(c.name)}">${icon("trash")}Remove</button></div></div></div>`).join("")}</div></div></div>`
    : `<div class="card"><div class="empty"><div class="ico">${icon("users")}</div><h2>No characters yet</h2>
        <p>When a book's character sheets are drawn, each character is locked and saved here automatically.</p></div></div>`}</div>`;
  $$("[data-up]").forEach((inp) => (inp.onchange = async () => {
    const f = inp.files[0]; if (!f) return;
    const res = await fetch(`/api/characters/${encodeURIComponent(inp.dataset.up)}/sheet`, { method: "POST", body: f });
    if (!res.ok) { toast((await res.json()).detail || "Upload failed", true); return; }
    toast("Image replaced. New books use it from now on."); characterLibrary();
  }));
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!(await modal({ title: `Remove ${b.dataset.name}?`, body: "New books won't reuse this look. Books that already use it keep their own copy.", confirm: "Remove", danger: true }))) return;
    await api("DELETE", `/api/characters/${encodeURIComponent(b.dataset.del)}`); toast(`${b.dataset.name} removed`); characterLibrary();
  }));
}

// ---------- brief ----------
async function newBook() {
  view.innerHTML = `<div class="page narrow"><div class="crumb"><a href="#/">Library</a>/<span>New book</span></div>
    <div class="head"><div><h1>New book</h1><p class="sub">Tell Claude what you have in mind. The more specific, the fewer questions it asks.</p></div></div>
    <div id="brief-host"></div></div>`;
  $("#brief-host").append(await briefForm());
}

async function uploadSource(slug, file) {
  const res = await fetch(`/api/books/${slug}/sources?name=${encodeURIComponent(file.name)}`, { method: "POST", body: file });
  const data = await res.json();
  if (!res.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}

async function briefForm(slug, brief = {}, sources = []) {
  const { settings: s, trims } = await getSettings();
  const type = "storybook";
  const el = document.createElement("form");
  el.className = "card";
  el.innerHTML = `
    <div class="card-b stack" style="gap:20px">
      <input type="hidden" name="type" value="storybook"><input type="hidden" name="paper" value="premium_color">
      <div class="field"><label for="idea">The idea</label>
        <textarea class="input" id="idea" name="idea" rows="5" required placeholder="A shy hedgehog who is afraid of the dark learns the night is full of friends. Children practise the past tense…">${esc(brief.idea)}</textarea>
        <span class="hint">A full-color illustrated book: the story, exercises and learning tips, and games at the end. Say what children should learn, plus premise, characters and setting.</span></div>
      <div class="field"><span class="label">Reference files <span class="faint">· optional</span></span>
        <div class="attach" id="attach">
          <div class="attach-list" id="attach-list"></div>
          <label class="btn"><input type="file" id="attach-in" accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp,.gif,image/*" multiple hidden>${icon("file")}Attach files</label></div>
        <span class="hint">PDF, Word, text, Markdown or images: notes, a draft, research, a story to adapt, sketches or style references. Claude reads the text and looks at the images (attach scanned pages as images).</span></div>
      <div class="field" id="cast-field" hidden><span class="label">Characters from your library <span class="faint">· optional</span></span>
        <div class="cast" id="cast"></div>
        <span class="hint">Ticked characters are written into the story with their exact look, for a series.</span></div>
      <div class="form-grid">
        <div class="field"><label for="audience">Reader age</label><input class="input" id="audience" name="audience" value="${esc(brief.audience || "")}" placeholder="3–6"></div>
        <div class="field"><label for="tone">Tone</label><input class="input" id="tone" name="tone" value="${esc(brief.tone || "")}" placeholder="Gentle, funny, adventurous…"></div>
        <div class="field"><label for="length">Length</label><input class="input" id="length" name="length" value="${esc(brief.length || "")}" placeholder="32 pages · 8 chapters"></div>
        <div class="field"><label for="language">Language</label><input class="input" id="language" name="language" value="${esc(brief.language || "English")}"></div>
        <div class="field full"><label for="art">Art style <span class="faint">· optional</span></label><input class="input" id="art" name="art" value="${esc(brief.art || "")}" placeholder="Soft watercolor, bold ink lines, retro print…"></div>
      </div>
      ${briefExtras(brief)}
      <div id="langwarn" hidden>${note("warn", "Words are lettered into the pictures by the image model, which only writes Latin script reliably. Persian, Arabic and other scripts aren't supported yet.")}</div>
      <hr style="margin:0">
      <div class="form-grid">
        <div class="field"><label for="title">Working title <span class="faint">· optional</span></label><input class="input" id="title" name="title" value="${esc(brief.title || "")}"></div>
        <div class="field"><label for="author">Author on the cover</label><input class="input" id="author" name="author" value="${esc(brief.author ?? s.default_author)}" placeholder="Your name"></div>
        <div class="field"><label for="trim">Trim size</label><select class="input" id="trim" name="trim">${trims.map((t) => `<option ${t === (brief.trim || TYPES[type].trim) ? "selected" : ""}>${t}</option>`).join("")}</select></div>
        <div class="field"><span class="label">Page numbers</span>
          <label class="check" style="height:36px"><input type="checkbox" name="page_numbers" ${brief.page_numbers === false ? "" : "checked"}> Print a number on every page</label></div>
      </div>
    </div>
    <div class="card-f row between"><span class="faint small">Claude replies in about 10 seconds.</span>
      <button class="btn primary" type="submit">${icon("sparkle")}${slug ? "Save and ask again" : "Continue"}</button></div>`;
  let saved = sources.slice(), pending = [];
  const list = $("#attach-list", el);
  const drawFiles = () => {
    list.innerHTML = [...saved.map((f) => [f.name, /\.(png|jpe?g|webp|gif)$/i.test(f.name) ? `${bytes(f.bytes)} · image` : `${bytes(f.bytes)} · ${f.chars.toLocaleString()} characters`, "saved"]),
      ...pending.map((f) => [f.name, `${bytes(f.size)} · read on continue`, "pending"])].map(([n, d, k]) => `
      <div class="attach-item"><span class="fi">${icon("file")}</span><div><b>${esc(n)}</b><span>${esc(d)}</span></div>
        <button type="button" class="btn icon ghost" data-${k}="${esc(n)}" aria-label="Remove ${esc(n)}">${icon("x")}</button></div>`).join("");
    $$("[data-saved]", list).forEach((b) => (b.onclick = () => busy(b, "", async () => {
      saved = (await api("DELETE", `/api/books/${slug}/sources/${encodeURIComponent(b.dataset.saved)}`)).sources; drawFiles();
    })));
    $$("[data-pending]", list).forEach((b) => (b.onclick = () => { pending = pending.filter((f) => f.name !== b.dataset.pending); drawFiles(); }));
  };
  const addFiles = (files) => {
    for (const f of files) {
      if (!/\.(pdf|txt|md|docx|png|jpe?g|webp|gif)$/i.test(f.name)) { toast(`${f.name}: attach PDF, Word, text, Markdown or image files`, true); continue; }
      pending = [...pending.filter((p) => p.name !== f.name), f];
    }
    drawFiles();
  };
  $("#attach-in", el).onchange = (e) => { addFiles(e.target.files); e.target.value = ""; };
  const zone = $("#attach", el);
  zone.ondragover = (e) => { e.preventDefault(); zone.classList.add("over"); };
  zone.ondragleave = () => zone.classList.remove("over");
  zone.ondrop = (e) => { e.preventDefault(); zone.classList.remove("over"); addFiles(e.dataTransfer.files); };
  drawFiles();
  voiceify(el);
  const lang = () => ($("#langwarn", el).hidden = /^(english|en|)$|french|german|spanish|italian|dutch|portuguese/i.test(el.language.value.trim()));
  el.language.addEventListener("input", lang); lang();
  api("GET", "/api/characters").then(({ characters: lib }) => {
    if (!lib.length) return;
    $("#cast-field", el).hidden = false;
    $("#cast", el).innerHTML = lib.map((c) => `<label class="castpick"><input type="checkbox" name="cast" value="${esc(c.name)}" ${(brief.cast || []).includes(c.name) ? "checked" : ""}>
      <img src="/api/characters/${encodeURIComponent(c.id)}.png" alt=""><span>${esc(c.name)}</span></label>`).join("");
  }).catch(() => {});
  const structure = structureEditor(el, brief.structure || {});
  el.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = {};
    for (const [k, v] of new FormData(el)) {  // "learning.topic" -> data.learning.topic
      const [a, b] = k.split(".");
      if (b) (data[a] ||= {})[b] = v; else if (!k.startsWith("_")) data[k] = v;
    }
    data.structure = { ...(data.structure || {}), ...structure.value() };
    data.cast = $$("[name=cast]:checked", el).map((c) => c.value);
    data.page_numbers = el.page_numbers.checked;
    busy(el.querySelector("[type=submit]"), "Claude is reading…", async () => {
      let id = slug;
      if (!id) id = (await api("POST", "/api/books", data)).slug;
      else await api("PUT", `/api/books/${id}/state`, { brief: data });
      // after a failed upload, a retry should update the book just created instead of making another
      slug = id;
      for (const f of pending) {
        saved = [...saved.filter((s) => s.name !== f.name), await uploadSource(id, f)];
        pending = pending.filter((p) => p !== f); drawFiles();
      }
      await api("POST", `/api/books/${id}/claude/questions`);
      location.hash = `#/book/${id}/questions`;
    });
  });
  return el;
}

// ---------- learning point, writing style, book structure (all optional) ----------
function briefExtras(brief) {
  const L = brief.learning || {}, W = brief.writing || {}, S = brief.structure || {};
  const filled = (o) => Object.values(o || {}).some((v) => v && (!Array.isArray(v) || v.length));
  return `
    <details class="more" ${filled(L) ? "open" : ""}><summary>${icon("sparkle")}Learning point <span class="faint">· optional</span></summary>
      <div class="form-grid">
        <div class="field"><label for="l-topic">What the book teaches</label>
          <input class="input" id="l-topic" name="learning.topic" value="${esc(L.topic || "")}" placeholder="Adjectives and their opposites"></div>
        <div class="field"><label for="l-targets">Target words or concepts</label>
          <input class="input" id="l-targets" name="learning.targets" value="${esc(L.targets || "")}" placeholder="chaud/froid, grand/petit… (Claude picks if empty)"></div>
        <div class="field full"><label for="l-explain">What the child should understand</label>
          <textarea class="input" id="l-explain" name="learning.explain" rows="2" placeholder="An adjective describes a noun; many have an opposite.">${esc(L.explain || "")}</textarea></div>
        <div class="field full"><label for="l-marking">How to mark it in the story</label>
          <textarea class="input" id="l-marking" name="learning.marking" rows="2" placeholder="The adjective in violet, its opposite in parentheses right after it.">${esc(L.marking || "")}</textarea>
          <span class="hint">Your rule, in your words. Claude writes every story page by it; the marked words are lettered or printed in the highlight style. Leave empty and Claude asks.</span></div>
      </div></details>
    <details class="more" ${filled(W) ? "open" : ""}><summary>${icon("edit")}Writing style <span class="faint">· optional</span></summary>
      <div class="form-grid">
        <div class="field"><label for="w-by">Inspired by</label>
          <input class="input" id="w-by" name="writing.inspired_by" value="${esc(W.inspired_by || "")}" placeholder="An author whose style you like"></div>
        <div class="field"><label for="w-notes">Style notes</label>
          <input class="input" id="w-notes" name="writing.notes" value="${esc(W.notes || "")}" placeholder="Short rhyming lines, absurd humour, lots of dialogue"></div>
        <div class="field full"><label for="w-sample">A sample of the style</label>
          <textarea class="input" id="w-sample" name="writing.sample" rows="3" placeholder="Paste a passage. Claude takes the manner (rhythm, tone, humour), never the sentences.">${esc(W.sample || "")}</textarea></div>
      </div></details>
    <details class="more" id="structure" ${filled(S.sections) ? "open" : ""}><summary>${icon("layers")}Book structure <span class="faint">· optional</span></summary>
      <div class="stack" style="gap:12px">
        <div class="row gap3 wrap"><select class="input" id="tpl" name="_tpl" style="max-width:320px"><option value="">Free: Claude plans the pages</option></select>
          <span class="faint small" id="tpl-total"></span></div>
        <div id="secs" class="secs"></div>
        <div class="row gap3 wrap" id="sec-tools" hidden><select class="input" id="sec-add" name="_add" style="max-width:240px"><option value="">+ Add a section…</option></select>
          <button type="button" class="btn sm" id="tpl-save">${icon("copy")}Save as template</button></div>
        <div class="form-grid" id="sec-extra" hidden>
          <div class="field full"><label for="s-back">Back cover must include</label>
            <input class="input" id="s-back" name="structure.back_cover" value="${esc(S.back_cover || "")}" placeholder="Summary, learning goal, age 6–9, the activities, barcode space"></div>
          <div class="field full"><label for="s-coll">Other books in this collection</label>
            <textarea class="input" id="s-coll" name="structure.collection" rows="2" placeholder="Les aventures de Zigooli: verbs (published) · Nina va à l'école: adjectives (coming soon)">${esc(S.collection || "")}</textarea>
            <span class="hint">Only these appear on the collection page. Nothing is invented.</span></div></div>
      </div></details>`;
}

// the section list of the brief's book structure: pick a template, then change it for this book only
function structureEditor(el, initial) {
  let kinds = {}, tpls = [], secs = (initial.sections || []).map((x) => ({ ...x }));
  let tplId = initial.template || "";
  const host = $("#secs", el);
  const total = () => secs.filter((x) => x.enabled !== false).reduce((n, x) => n + (Number(x.pages) || 0), 0);
  const draw = () => {
    $("#sec-tools", el).hidden = $("#sec-extra", el).hidden = !secs.length;
    $("#tpl-total", el).textContent = secs.length ? `${total()} interior pages · front and back cover separate` : "";
    host.innerHTML = secs.map((x, i) => `
      <div class="secrow ${x.enabled === false ? "off" : ""}" data-i="${i}">
        <input type="checkbox" data-k="enabled" ${x.enabled === false ? "" : "checked"} aria-label="Include ${esc(kinds[x.kind]?.label || x.kind)}">
        <span class="sk-label" title="${esc(kinds[x.kind]?.guide || "")}">${esc(kinds[x.kind]?.label || x.kind)}</span>
        <input class="input" type="number" min="0" max="60" data-k="pages" value="${Number(x.pages) || 0}" aria-label="Pages">
        <input class="input" data-k="title" value="${esc(x.title || "")}" placeholder="Title on the page (optional)">
        <input class="input" data-k="note" value="${esc(x.note || "")}" placeholder="Note for Claude (optional)">
        <span class="row"><button type="button" class="btn icon ghost" data-mv="-1" aria-label="Move up">↑</button>
          <button type="button" class="btn icon ghost" data-mv="1" aria-label="Move down">↓</button>
          <button type="button" class="btn icon ghost" data-rm aria-label="Remove">${icon("x")}</button></span></div>`).join("");
    $$(".secrow", host).forEach((row) => {
      const i = Number(row.dataset.i);
      $$("[data-k]", row).forEach((inp) => (inp.oninput = () => {
        const k = inp.dataset.k;
        secs[i][k] = k === "enabled" ? inp.checked : k === "pages" ? Number(inp.value) : inp.value;
        if (k !== "title" && k !== "note") draw();
      }));
      $$("[data-mv]", row).forEach((b) => (b.onclick = () => {
        const j = i + Number(b.dataset.mv);
        if (j < 0 || j >= secs.length) return;
        [secs[i], secs[j]] = [secs[j], secs[i]]; draw();
      }));
      $("[data-rm]", row).onclick = () => { secs.splice(i, 1); draw(); };
    });
  };
  const pick = $("#tpl", el);
  pick.onchange = () => {
    tplId = pick.value;
    const t = tpls.find((x) => x.id === tplId);
    secs = t ? t.sections.map((x) => ({ ...x })) : [];
    if (t?.back_cover && !$("#s-back", el).value) $("#s-back", el).value = t.back_cover;
    if (t?.audience && el.audience && !el.audience.value) el.audience.value = t.audience;
    draw();
  };
  $("#sec-add", el).onchange = (e) => {
    if (!e.target.value) return;
    secs.push({ kind: e.target.value, pages: 1, enabled: true }); e.target.value = ""; draw();
  };
  $("#tpl-save", el).onclick = async () => {
    const name = prompt("Name of the template", tpls.find((x) => x.id === tplId)?.name || "");
    if (!name) return;
    try {
      const t = await api("POST", "/api/templates", { name, sections: secs, back_cover: $("#s-back", el).value || undefined,
        audience: el.audience?.value || undefined });
      tpls = [...tpls.filter((x) => x.id !== t.id), t]; tplId = t.id; fill(); toast(`Saved “${name}”. Every new book can start from it.`);
    } catch (e) { toast(e.message, true); }
  };
  const fill = () => {
    pick.innerHTML = `<option value="">Free: Claude plans the pages</option>` +
      tpls.map((t) => `<option value="${esc(t.id)}" ${t.id === tplId ? "selected" : ""}>${esc(t.name)} · ${t.pages} pages</option>`).join("");
  };
  api("GET", "/api/templates").then((r) => {
    kinds = r.kinds; tpls = r.templates; fill();
    $("#sec-add", el).innerHTML = `<option value="">+ Add a section…</option>` +
      Object.entries(kinds).map(([k, v]) => `<option value="${k}">${esc(v.label)}</option>`).join("");
    draw();
  }).catch(() => {});
  draw();
  return { value: () => (secs.length ? { template: tplId, sections: secs } : { template: "", sections: [] }) };
}

// ---------- templates library ----------
async function templateLibrary() {
  const { templates: list, kinds } = await api("GET", "/api/templates");
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Templates</h1><p class="sub">Book structures: which sections a book has, in what order and how many pages each.
      Pick one in a new book's brief and change it there for that book. Save a changed structure from the brief to add it here.</p></div></div>
    <div class="stack">${list.map((t) => `
      <div class="card"><div class="card-b stack" style="gap:8px">
        <div class="row between"><div><h3 style="margin:0">${esc(t.name)}</h3><span class="faint xs">${t.pages} interior pages${t.audience ? ` · ages ${esc(t.audience)}` : ""}${t.builtin ? " · built in" : ""}</span></div>
          ${t.builtin && !t.saved ? "" : `<button class="btn sm ghost" data-del="${esc(t.id)}" data-name="${esc(t.name)}">${icon("trash")}${t.builtin ? "Restore original" : "Remove"}</button>`}</div>
        ${t.description ? `<p class="muted small" style="margin:0">${esc(t.description)}</p>` : ""}
        <div class="chips">${t.sections.filter((x) => x.enabled !== false).map((x) =>
          `<span class="tag">${esc(x.title || kinds[x.kind]?.label || x.kind)} · ${x.pages}</span>`).join("")}</div></div></div>`).join("")}</div></div>`;
  $$("[data-del]").forEach((b) => (b.onclick = async () => {
    if (!(await modal({ title: `Remove ${b.dataset.name}?`, body: "Books already written keep their structure.", confirm: "Remove", danger: true }))) return;
    try { await api("DELETE", `/api/templates/${encodeURIComponent(b.dataset.del)}`); toast("Removed"); } catch (e) { toast(e.message, true); }
    templateLibrary();
  }));
}

// ---------- book wizard ----------
async function bookView(slug, step) {
  const b = await api("GET", `/api/books/${slug}`);
  const st = b.state;
  const reached = Math.max(STEPS.findIndex(([k]) => k === st.step), b.yaml ? 3 : 0, b.last_build ? 4 : 0, b.last_build === "real" ? 6 : 0);
  step ||= st.step || (b.yaml ? "manuscript" : "brief");
  const idx = STEPS.findIndex(([k]) => k === step);
  view.innerHTML = `<div class="page">
    <div class="crumb"><a href="#/">Library</a>/<span>${esc(b.title)}</span></div>
    <div class="head nowrap"><div class="row gap3" style="min-width:0"><h1>${esc(b.title)}</h1>${badge(b.status)}</div>
      <div class="menu"><button class="btn icon" id="more" aria-label="More actions" aria-haspopup="true">${icon("more")}</button>
        <div class="menu-pop" id="more-pop" hidden>
          <button id="dl">${icon("download")}Download .zip</button>
          <button class="danger" id="del">${icon("trash")}Delete book</button></div></div></div>
    <div class="book-layout">
      <ol class="steps">${STEPS.map(([k, label], i) => {
        const cls = i === idx ? "current" : i <= reached ? "done" : i > reached + 1 ? "locked" : "";
        return `<li><a class="${cls}" href="#/book/${slug}/${k}"><span class="dot">${cls === "done" ? icon("check") : i + 1}</span>${label}</a></li>`;
      }).join("")}</ol>
      <section id="step"></section></div></div>`;
  const pop = $("#more-pop");
  $("#more").onclick = (e) => { e.stopPropagation(); pop.hidden = !pop.hidden; };
  document.addEventListener("click", () => (pop.hidden = true), { once: true });
  $("#dl").onclick = () => (location.href = `/api/books/${slug}/download.zip`);
  $("#del").onclick = async () => {
    if (!(await modal({ title: "Delete this book?", body: `“${esc(b.title)}” and all its files, art and builds will be removed. This can't be undone.`, confirm: "Delete", danger: true }))) return;
    await api("DELETE", `/api/books/${slug}`); toast("Book deleted"); location.hash = "#/";
  };
  if (b.job) {
    const where = b.job_kind === "mock" ? "preview" : "art";
    if (step !== where) $("#step").insertAdjacentHTML("beforebegin", `<div class="job-banner">${note("info",
      `<span class="spin"></span> ${esc(JOB_LABELS[b.job_kind] || "A job")} is running in the background. <a href="#/book/${slug}/${where}">Watch progress</a>`)}</div>`);
  }
  const steps = { brief: stepBrief, questions: stepQuestions, outline: stepOutline, manuscript: stepManuscript,
    preview: stepPreview, art: stepArt, publish: stepPublish };
  await steps[step]($("#step"), b, slug);
}

const stepHead = (title, sub, right = "") =>
  `<div class="step-head row between"><div><h2>${title}</h2><p>${sub}</p></div>${right}</div>`;

async function stepBrief(host, b, slug) {
  host.innerHTML = stepHead("Brief", "What the book is about. Changing it makes Claude ask its questions again.");
  host.append(await briefForm(slug, b.state.brief || {}, b.sources || []));
}

function stepQuestions(host, b, slug) {
  const qs = b.state.questions;
  if (!qs) {
    host.innerHTML = stepHead("Questions", "Claude asks what it needs to know before outlining.") +
      `<div class="card"><div class="empty"><div class="ico">${icon("sparkle")}</div><p>Claude hasn't asked its questions yet.</p>
       <button class="btn primary" id="ask">${icon("sparkle")}Ask Claude</button></div></div>`;
    $("#ask").onclick = (e) => busy(e.currentTarget, "Thinking…", async () => { await api("POST", `/api/books/${slug}/claude/questions`); route(); });
    return;
  }
  const answers = b.state.answers || {};
  host.innerHTML = stepHead("A few questions", "Pick a suggestion or write your own. Leave one blank and Claude decides.") + `
    <div class="card"><div class="card-b" id="qs">${qs.map((q, i) => `
      <div class="q" data-id="${esc(q.id)}"><span class="n">${i + 1}</span><div>
        <div class="qt">${esc(q.question)}</div>
        ${q.options?.length ? `<div class="chips">${q.options.map((o) => `<button type="button" class="chip ${answers[q.id] === o ? "on" : ""}">${esc(o)}</button>`).join("")}</div>` : ""}
        <input class="input" aria-label="${esc(q.question)}" value="${esc(answers[q.id] || "")}" placeholder="Your answer"></div></div>`).join("")}</div>
      <div class="card-f row between"><a class="btn ghost" href="#/book/${slug}/brief">${icon("edit")}Edit brief</a>
        <button class="btn primary" id="next">${icon("sparkle")}Write the outline</button></div></div>`;
  $$(".q").forEach((q) => {
    const input = $("input", q);
    $$(".chip", q).forEach((c) => (c.onclick = () => { $$(".chip", q).forEach((x) => x.classList.remove("on")); c.classList.add("on"); input.value = c.textContent; }));
    input.oninput = () => $$(".chip", q).forEach((x) => x.classList.toggle("on", x.textContent === input.value));
  });
  voiceify(host);
  $("#next").onclick = (e) => busy(e.currentTarget, "Outlining… about 30 s", async () => {
    const ans = Object.fromEntries($$(".q").map((q) => [q.dataset.id, $("input", q).value.trim()]).filter(([, v]) => v));
    await api("POST", `/api/books/${slug}/claude/outline`, { answers: ans });
    location.hash = `#/book/${slug}/outline`;
  });
}

function stepOutline(host, b, slug) {
  const outline = b.state.outline;
  if (!outline) { host.innerHTML = stepHead("Outline", "") + note("info", `Answer Claude's questions first. <a href="#/book/${slug}/questions">Go to questions</a>`); return; }
  host.innerHTML = stepHead("Outline", "The plan for the book. Approve it, ask for changes, or edit it yourself.") + `
    <div class="split">
      <div class="card"><div class="card-h"><h3>Outline</h3><div class="seg" id="mode"><button class="on" data-m="read">Read</button><button data-m="edit">Edit</button></div></div>
        <div class="card-b"><div class="doc" id="rendered">${md(outline)}</div>
          <textarea class="input" id="raw" rows="28" hidden style="font-size:14px">${esc(outline)}</textarea></div></div>
      <div class="stack sticky">
        <div class="card"><div class="card-b stack">
          <div><h3>Looks right?</h3><p class="muted small">Claude writes the full manuscript: every page's text, art prompts, characters and cover. About a minute.</p></div>
          <button class="btn primary" id="write">${icon("sparkle")}Write the manuscript</button></div></div>
        <div class="card"><div class="card-b stack tight">
          <label class="label" for="fb">Ask for changes</label>
          <textarea class="input" id="fb" rows="4" placeholder="Happier ending, add a little brother, fewer pages…"></textarea>
          <button class="btn" id="revise">${icon("refresh")}Revise outline</button></div></div>
      </div></div>`;
  $$("#mode button").forEach((btn) => (btn.onclick = () => {
    $$("#mode button").forEach((x) => x.classList.toggle("on", x === btn));
    const edit = btn.dataset.m === "edit";
    if (!edit) $("#rendered").innerHTML = md($("#raw").value);
    $("#raw").hidden = !edit; $("#rendered").hidden = edit;
  }));
  voiceify(host);
  $("#revise").onclick = (e) => busy(e.currentTarget, "Revising…", async () => {
    const feedback = $("#fb").value.trim();
    if (!feedback) throw new Error("Write what you want changed first");
    await api("POST", `/api/books/${slug}/claude/outline`, { feedback }); route();
  });
  $("#write").onclick = (e) => busy(e.currentTarget, "Writing… about 1 min", async () => {
    await api("POST", `/api/books/${slug}/claude/write`, { outline: $("#raw").value });
    location.hash = `#/book/${slug}/manuscript`;
  });
}

function pagesReader(pages) {
  if (!pages?.length) return `<p class="muted">No pages to show. Check the YAML for errors.</p>`;
  return pages.map((p, i) => `<div class="pg"><div class="no"><b>p${String(i + 1).padStart(2, "0")}</b>${p.layout ? `<span class="tag">${esc(p.layout.replace("_", " "))}</span>` : ""}
    <button class="btn sm ghost" data-redopage="${i + 1}" title="Tell Claude what to change on this page">${icon("refresh")}Redo</button></div><div>
    ${p.chapter ? `<div class="chapter">${esc(p.chapter)}</div>` : ""}
    <div class="txt">${esc(p.text) || (p.panels ? `<span class="muted">${p.panels} comic panels</span>` : `<span class="faint">No text</span>`)}</div>
    ${p.prompt ? `<div class="art">${icon("image")}<span>${esc(p.prompt)}</span></div>` : ""}</div></div>`).join("");
}

function stepManuscript(host, b, slug) {
  if (!b.yaml) { host.innerHTML = stepHead("Manuscript", "") + note("info", `No manuscript yet. <a href="#/book/${slug}/outline">Approve the outline</a> and Claude will write it.`); return; }
  host.innerHTML = stepHead("Manuscript", `${b.pages_view.length} pages. Read it through, edit, or ask Claude for changes.`) + `
    <div class="split">
      <div class="card"><div class="card-h"><div class="seg" id="mode"><button class="on" data-m="read">Pages</button><button data-m="yaml">YAML</button></div>
          <div class="row"><span id="vstate"></span><button class="btn sm primary" id="save" hidden>Save</button></div></div>
        <div class="card-b"><div id="err"></div><div id="lint" style="margin-bottom:16px"></div>
          <div class="pages" id="reader">${pagesReader(b.pages_view)}</div>
          <textarea class="input code" id="yaml" spellcheck="false" hidden>${esc(b.yaml)}</textarea></div></div>
      <div class="stack sticky">
        <div class="card"><div class="card-b stack tight">
          <label class="label" for="ins">Ask Claude to change something</label>
          <textarea class="input" id="ins" rows="4" placeholder="Make page 5 funnier. Shorten the blurb…"></textarea>
          <button class="btn" id="rev">${icon("wand")}Apply with Claude</button></div></div>
        <div class="card"><div class="card-b stack">
          <div><h3>Next: free preview</h3><p class="muted small">Lay out the whole book with placeholder art to check pacing and page count.</p></div>
          <a class="btn primary" href="#/book/${slug}/preview">Preview the book${icon("arrow")}</a></div></div>
      </div></div>`;
  const setValid = (err) => {
    $("#err").innerHTML = err ? `<div style="margin-bottom:16px">${note("err", `<b>book.yaml has errors</b><pre>${esc(err)}</pre>`)}</div>` : "";
    $("#vstate").innerHTML = err ? `<span class="badge err">Invalid</span>` : `<span class="badge ok">Valid</span>`;
  };
  setValid(b.yaml_error);
  $$("#mode button").forEach((btn) => (btn.onclick = () => {
    $$("#mode button").forEach((x) => x.classList.toggle("on", x === btn));
    const y = btn.dataset.m === "yaml";
    $("#yaml").hidden = !y; $("#reader").hidden = y; $("#save").hidden = !y;
  }));
  $("#save").onclick = (e) => busy(e.currentTarget, "Saving", async () => {
    try {
      const r = await api("PUT", `/api/books/${slug}/yaml`, { yaml: $("#yaml").value });
      $("#reader").innerHTML = pagesReader(r.pages_view); setValid(null); wirePages(); showLint(); toast("Manuscript saved");
    } catch (err) {
      setValid(err.message);
      if (await modal({ title: "Save with errors?", body: "The YAML doesn't validate. You can save it anyway and keep fixing it, but the book won't build until it's valid.", confirm: "Save anyway" }))
        await api("PUT", `/api/books/${slug}/yaml`, { yaml: $("#yaml").value, save_invalid: true });
    }
  });
  const revise = async (instruction) => {
    const r = await api("POST", `/api/books/${slug}/claude/revise`, { instruction, yaml: $("#yaml").value });
    $("#yaml").value = r.yaml; $("#reader").innerHTML = pagesReader(r.pages_view); setValid(null); wirePages();
    showLint();
    toast("Manuscript updated");
  };
  // the prompt check, shown here where it can still be fixed for free, before any art is paid for
  const showLint = async () => {
    const p = await loadPlan(slug);
    if (p.error) { $("#lint").innerHTML = ""; return; }
    const issues = p.lint || [];
    $("#lint").innerHTML = lintHtml(issues) + (issues.length ? `<div style="margin-top:8px"><button class="btn sm" id="fixlint">${icon("wand")}Fix these with Claude</button></div>` : "");
    if (issues.length) $("#fixlint").onclick = (e) => busy(e.currentTarget, "Claude is fixing…", () => revise(
      "Fix these prompt-check notes, changing only what each one needs:\n" + issues.map((i) => `- ${i.where}: ${i.message}`).join("\n")));
  };
  const wirePages = () => $$("[data-redopage]").forEach((btn) => (btn.onclick = async () => {
    const n = btn.dataset.redopage;
    const v = await modal({ title: `Redo page ${n}`, confirm: "Redo page",
      body: "Claude rewrites only this page (its text and picture prompt) and leaves the others as they are.",
      fields: `<div class="field"><label for="m-fix">What should change?</label>
        <textarea class="input" id="m-fix" name="fix" rows="3" required placeholder="Make the exercise easier, add a tip about…"></textarea></div>` });
    if (!v?.fix?.trim()) return;
    busy(btn, "Redoing…", () => revise(`On page ${n} only: ${v.fix.trim()}. Leave every other page exactly as it is.`));
  }));
  wirePages();
  showLint();
  voiceify(host);
  $("#rev").onclick = (e) => busy(e.currentTarget, "Claude is editing…", async () => {
    const instruction = $("#ins").value.trim();
    if (!instruction) throw new Error("Describe the change first");
    await revise(instruction); $("#ins").value = "";
  });
}

async function loadPlan(slug) {
  try { return await api("GET", `/api/books/${slug}/plan`); } catch (e) { return { error: e.message }; }
}

function lintHtml(issues) {
  if (!issues?.length) return note("ok", "Prompt check passed. Every illustration prompt looks good.");
  const err = issues.some((i) => i.level === "error");
  return note(err ? "err" : "warn", `<b>Prompt check: ${issues.length} ${issues.length > 1 ? "notes" : "note"}</b><ul>${issues.map((i) =>
    `<li><b>${esc(i.where)}</b> · ${esc(i.message)}</li>`).join("")}</ul>`);
}

async function spreadViewer(el, slug) {
  const pr = await api("GET", `/api/books/${slug}/proofs`);
  if (!pr.pages.length) { el.innerHTML = ""; return; }
  const v = Date.now(), src = (n) => `/api/books/${slug}/build/proofs/${n}?${v}`;
  const spreads = [[null, pr.pages[0]]];
  for (let i = 1; i < pr.pages.length; i += 2) spreads.push([pr.pages[i], pr.pages[i + 1] || null]);
  let width = 880;
  try { width = +localStorage.getItem("zoom") || 880; } catch {}
  el.innerHTML = `<div class="viewer" style="--w:${width}px">
    <div class="viewer-bar"><div class="seg" id="vmode"><button class="on" data-v="spreads">Spreads</button>${pr.cover ? `<button data-v="cover">Cover</button>` : ""}</div>
      <label class="row small muted">Zoom <input type="range" id="zoom" min="420" max="1200" step="20" value="${width}"></label></div>
    <div class="spreads" id="v-spreads">${spreads.map((s, i) => `
      <div class="spread ${i === 0 ? "first" : ""}">${s.map((p) => (p ? `<img src="${src(p)}" alt="${esc(p)}" loading="lazy">` : `<div class="blank"></div>`)).join("")}</div>
      <div class="spread-label">${i === 0 ? "1" : `${2 * i} – ${2 * i + 1}`}</div>`).join("")}</div>
    <div class="cover-view" id="v-cover" hidden>${pr.cover ? `<img src="${src("cover.png")}" alt="Full cover: back, spine, front">` : ""}</div></div>`;
  $("#zoom", el).oninput = (e) => { el.firstElementChild.style.setProperty("--w", `${e.target.value}px`); try { localStorage.setItem("zoom", e.target.value); } catch {} };
  $$("#vmode button", el).forEach((b) => (b.onclick = () => {
    $$("#vmode button", el).forEach((x) => x.classList.toggle("on", x === b));
    $("#v-spreads", el).hidden = b.dataset.v !== "spreads"; $("#v-cover", el).hidden = b.dataset.v !== "cover";
  }));
}

async function stepPreview(host, b, slug) {
  const p = await loadPlan(slug);
  if (p.error) { host.innerHTML = stepHead("Preview", "") + note("err", `${esc(p.error)}<br><a href="#/book/${slug}/manuscript">Fix the manuscript</a>`); return; }
  const has = !!b.last_build;
  host.innerHTML = stepHead("Free preview", "Placeholder art with real typesetting, real KDP geometry and preflight. Costs nothing.",
    `<button class="btn primary" id="mock">${icon(has ? "refresh" : "play")}${has ? "Rebuild preview" : "Build preview"}</button>`) + `
    <div class="stack">
      <div class="stats">
        <div class="stat"><div class="k">Pages</div><div class="v">${b.pages ?? "–"}</div><div class="s">${b.pages ? "incl. front matter" : "build to see"}</div></div>
        <div class="stat"><div class="k">Illustrations</div><div class="v">${p.slots.length}</div><div class="s">incl. character sheets</div></div>
        <div class="stat"><div class="k">Estimated art cost</div><div class="v" id="est">${money(p.estimate_usd)}</div><div class="s">each image generated once</div></div>
      </div>
      ${jobPanel("Building preview…")}
      <div id="viewer"></div>
      ${lintHtml(p.lint)}
      <div class="card"><div class="card-h"><div><h3>Illustrations</h3><p>All at <b>${esc(p.quality)}</b> (~${money(p.base_cost_usd)} each). Switch on <b>High</b> for images that deserve it (~${money(p.high_cost_usd)} each).</p></div>
          <span class="faint small">${esc(p.model)}</span></div>
        <div class="card-b table-wrap" id="slots">${slotTable(p)}</div>
        <div class="card-f row between"><span class="faint small">Cached images are never paid for twice.</span>
          <a class="btn primary sm" href="#/book/${slug}/art">Continue to art${icon("arrow")}</a></div></div>
    </div>`;
  if (has) spreadViewer($("#viewer"), slug);
  wireSlotTable(slug);
  const followMock = async (job) => {
    const j = await watchJob(job, "Building preview…", p.slots.length);
    if (j.status === "done") { await spreadViewer($("#viewer"), slug); toast(`Preview built: preflight ${j.result.preflight?.ok ? "passed" : "failed"}`); }
    else toast("Preview failed. See the log.", true);
  };
  $("#mock").onclick = (e) => busy(e.currentTarget, "Building…", async () => {
    const { job } = await api("POST", `/api/books/${slug}/jobs/mock`);
    await followMock(job);
  });
  if (b.job && b.job_kind === "mock") { $("#mock").disabled = true; followMock(b.job).finally(() => ($("#mock").disabled = false)); }
}

function slotTable(p) {
  return `<table><thead><tr><th>Slot</th><th>Kind</th><th>Characters</th><th class="r">Est.</th><th class="r">High</th></tr></thead>
    <tbody>${p.slots.map((s) => `<tr><td><span class="tag">${esc(s.id)}</span></td><td>${esc(s.kind.replace(/_/g, " "))}</td>
      <td class="muted">${esc(s.characters.join(", ")) || "–"}</td><td class="r">${money(s.cost_usd)}</td>
      <td class="r"><label class="switch"><input type="checkbox" data-high="${esc(s.id)}" ${s.quality === "high" ? "checked" : ""} aria-label="High quality for ${esc(s.id)}"><i></i></label></td></tr>`).join("")}</tbody></table>`;
}

function wireSlotTable(slug) {
  $$("[data-high]").forEach((c) => (c.onchange = async () => {
    try {
      const p = await api("PUT", `/api/books/${slug}/high`, { slots: [c.dataset.high], on: c.checked });
      $("#slots").innerHTML = slotTable(p); wireSlotTable(slug);
      $("#est").textContent = money(p.estimate_usd);
      toast(`${c.dataset.high} → ${c.checked ? "high" : p.quality} · book now ~${money(p.estimate_usd)}`);
    } catch (e) { c.checked = !c.checked; toast(e.message, true); }
  }));
}

async function reviewGrid(el, slug, slots) {
  const r = await api("GET", `/api/books/${slug}/review`);
  if (!r.slots.length) { el.hidden = true; return; }
  el.hidden = false;
  const bad = r.slots.filter((s) => !s.ok).length;
  const v = Date.now();
  el.innerHTML = `<div class="card-h"><div><h3>Art review ${r.mock ? `<span class="badge warn" style="margin-left:6px">placeholder art</span>` : ""}</h3>
      <p>${r.slots.length} images · ${bad ? `<span style="color:var(--warn)">${bad} need attention</span>` : "all passed"}</p></div></div>
    <div class="card-b"><div class="review">${r.slots.map((s) => `
      <div class="shot ${s.ok ? "" : "bad"}"><div class="img"><img src="/api/books/${slug}/build/${s.thumb}?${v}" data-full="/api/books/${slug}/build/art/${s.id}.png?${v}" alt="${esc(s.id)}" loading="lazy"></div>
        <div class="m"><div class="row between"><span class="tag">${esc(s.id)}</span>
          ${s.score == null ? `<span class="badge plain">not reviewed</span>` : `<span class="badge ${s.ok ? "ok" : "warn"}">${s.score}/10</span>`}</div>
          ${s.issues.length ? `<ul>${s.issues.slice(0, 3).map((i) => `<li>${esc(i)}</li>`).join("")}</ul>` : ""}
          <div class="row between"><span class="faint xs">${s.ok ? "" : "needs a fix"}</span>
            <button class="btn sm ghost" data-redo="${esc(s.id)}">${icon("refresh")}Redo</button></div></div></div>`).join("")}</div></div>`;
  $$("[data-redo]", el).forEach((btn) => (btn.onclick = () => slots.redo(btn.dataset.redo, btn)));
}

async function characterCard(el, slug) {
  const r = await api("GET", `/api/books/${slug}/characters`).catch(() => null);
  if (!r || !r.characters.length) { el.hidden = true; return; }
  el.hidden = false;
  const locked = r.characters.filter((c) => c.locked).length;
  const v = Date.now();
  el.innerHTML = `<div class="card-h"><div><h3>Characters</h3>
      <p>${locked} of ${r.characters.length} locked. A locked look is reused on every page and in later books of the series.</p></div></div>
    <div class="card-b"><div class="review">${r.characters.map((c) => `
      <div class="shot"><div class="img">${c.locked ? `<img src="/api/books/${slug}/characters/${encodeURIComponent(c.id)}.png?${v}" alt="${esc(c.name)}" loading="lazy">` : ""}</div>
        <div class="m"><div class="row between"><span class="tag">${esc(c.name)}</span>
          ${c.locked ? `<span class="badge ok">locked</span>` : `<span class="badge plain">drawn on the next run</span>`}</div>
          ${r.drifted.includes(c.name) ? `<p class="faint xs">book.yaml describes this character differently; the locked look is used.</p>` : ""}
          ${c.source_book ? `<span class="faint xs">from ${esc(c.source_book)}</span>` : ""}</div></div>`).join("")}</div></div>`;
}

async function stepArt(host, b, slug) {
  const p = await loadPlan(slug);
  if (p.error) { host.innerHTML = stepHead("Art & build", "") + note("err", esc(p.error)); return; }
  let done = p.slots.filter((s) => s.has_art).length;
  const chars = p.slots.filter((s) => s.kind === "character").length;
  const errors = p.lint.some((i) => i.level === "error");
  host.innerHTML = stepHead("Art & build", "Try the look first, then illustrate everything and build the print files.") + `
    <div class="stack">
      <div class="phases">
        <div class="phase"><span class="k">${icon("eye")}Step 1 · Pilot</span><h3>Test the look</h3>
          <p>Character sheets, the cover and the first few pages. Check them before you pay for everything.</p>
          <div class="row"><input class="input" id="pp" type="number" min="1" max="10" value="3" style="width:72px" aria-label="Pilot pages"><span class="muted small">pages</span>
            <button class="btn" id="pilot" style="margin-left:auto">Run pilot</button></div></div>
        <div class="phase"><span class="k">${icon("layers")}Step 2 · All art</span><h3 id="done">${done} of ${p.slots.length} images</h3>
          <p>About <b>${money(p.estimate_usd)}</b> for everything. Each image is generated once and never redrawn unless you press Redo. Images you already have are free.</p>
          <button class="btn primary" id="all">${icon("sparkle")}Generate all art</button></div>
        <div class="phase"><span class="k">${icon("file")}Step 3 · Build</span><h3>Print files</h3>
          <p>Lays out interior.pdf and cover.pdf with the real art and runs KDP preflight.</p>
          <button class="btn" id="build" disabled>Build &amp; preflight</button>
          <p class="faint xs" id="build-hint"></p></div>
      </div>
      ${lintHtml(p.lint)}
      ${errors ? `<label class="check"><input type="checkbox" id="force"> Run anyway, ignoring prompt-check errors</label>` : ""}
      ${jobPanel("Working…")}
      <div id="pf"></div>
      <div class="card" id="charcard" hidden></div>
      <div class="card" id="reviewcard" hidden></div>
    </div>`;
  const jobButtons = () => ["#pilot", "#all", "#build", "#pp"].map((q) => $(q)).filter(Boolean);
  const follow = async (job, kind, label, total) => {
    jobButtons().forEach((b) => (b.disabled = true));
    try {
      const j = await watchJob(job, label, total);
      if (j.status !== "done") { toast("The job stopped. See the log.", true); }
      if (kind !== "build") { await characterCard($("#charcard"), slug); await reviewGrid($("#reviewcard"), slug, actions); await refreshDone(); }
      if (j.result?.preflight) showPreflight(j.result.preflight);
      if (j.status === "done") toast(`${label.replace(/…$/, "")}: done`);
      return j;
    } finally {
      if (host.isConnected) { jobButtons().forEach((b) => (b.disabled = false)); syncBuild(); }
    }
  };
  const run = async (btn, kind, body, label, total) => busy(btn, label, async () => {
    const { job } = await api("POST", `/api/books/${slug}/jobs/${kind}`, { ...body, force: $("#force")?.checked });
    return follow(job, kind, label, total);
  });
  const showPreflight = (r) => {
    $("#pf").innerHTML = `<div class="card"><div class="card-h"><h3>Preflight</h3>${r.ok ? `<span class="badge ok">Passed</span>` : `<span class="badge err">Failed</span>`}</div>
      <div class="card-b stack"><ul class="checklist">
        ${r.errors.map((e) => `<li class="e">${icon("x")}<span>${esc(e)}</span></li>`).join("")}
        ${r.warnings.map((w) => `<li class="w">${icon("alert")}<span>${esc(w)}</span></li>`).join("")}
        ${r.ok ? `<li class="o">${icon("check")}<span>${r.pages} pages · ${esc(r.trim)} · fonts embedded · bleed, margins and cover size match KDP</span></li>` : ""}</ul>
        ${r.ok ? `<div><a class="btn primary" href="#/book/${slug}/publish">Download &amp; publish${icon("arrow")}</a></div>` : ""}</div></div>`;
  };
  // the interior needs every image, so Build stays locked until Step 2 is complete
  const syncBuild = () => {
    const left = p.slots.length - done;
    $("#done").textContent = `${done} of ${p.slots.length} images`;
    $("#build").disabled = left > 0;
    $("#build-hint").textContent = left ? `${left} image${left > 1 ? "s" : ""} still missing. Run Generate all art first.` : "";
  };
  const refreshDone = async () => {
    const np = await loadPlan(slug);
    if (np.error) return;
    done = np.slots.filter((s) => s.has_art).length;
    syncBuild();
  };
  const cost = (title, body) => modal({ title, body: `${body}<br><br>This uses the OpenAI image API and costs real money.`, confirm: "Generate" });
  const actions = {
    redo: async (id, btn) => {
      const slot = p.slots.find((s) => s.id === id);
      const isHigh = slot?.quality === "high";
      const v = await modal({ title: `Redo ${id}`, confirm: "Redo image",
        body: `Draws this image once more with your correction: about ${money(isHigh ? p.high_cost_usd : p.base_cost_usd)}.`,
        fields: `<div class="field"><label for="m-note">What should change?</label>
          <textarea class="input" id="m-note" name="note" rows="3" required placeholder="Pip smaller, facing left, softer light. Spell 'wiggles' with two g's."></textarea></div>
          <label class="check"><input type="checkbox" name="high" ${isHigh ? "checked" : ""}> High quality (~${money(p.high_cost_usd)} instead of ~${money(p.base_cost_usd)})</label>` });
      if (!v) return;
      if (!!v.high !== isHigh) await api("PUT", `/api/books/${slug}/high`, { slots: [id], on: !!v.high });
      run(btn, "regen", { slots: [id], note: (v.note || "").trim() || null }, `Regenerating ${id}…`, 1);
    },
  };
  // grab the button before awaiting the modal: e.currentTarget is null once the handler yields
  $("#pilot").onclick = async (e) => {
    const btn = e.currentTarget, n = +$("#pp").value;
    if (await cost("Run the pilot?", `Character sheets, the cover and ${n} page${n > 1 ? "s" : ""}.`))
      run(btn, "pilot", { pages: n }, "Generating pilot…", chars + 1 + n);
  };
  $("#all").onclick = async (e) => {
    const btn = e.currentTarget;
    if (await cost("Generate all illustrations?", `${p.slots.length - done} missing images, about <b>${money(p.slots.filter((s) => !s.has_art).reduce((a, s) => a + s.cost_usd, 0))}</b>.`))
      run(btn, "art", {}, "Generating art…", p.slots.length);
  };
  $("#build").onclick = (e) => run(e.currentTarget, "build", {}, "Building print files…", 0);
  syncBuild();
  characterCard($("#charcard"), slug);
  reviewGrid($("#reviewcard"), slug, actions);
  // a job still running on the server (e.g. after a page refresh): pick it up where it is
  if (b.job && b.job_kind !== "mock") follow(b.job, b.job_kind, `${JOB_LABELS[b.job_kind] || "Working"}…`, 0);
}

async function stepPublish(host, b, slug) {
  const built = b.last_build === "real";
  const listing = b.state.listing;
  let paper = "premium_color", trim = "8.5x8.5";
  const m = b.yaml?.match(/^paper:\s*(\S+)/m); if (m) paper = m[1];
  const t = b.yaml?.match(/^trim:\s*['"]?([\d.x]+)/m); if (t) trim = t[1];
  const file = (name, label, sub) => `<a class="file ${b.files?.[name] ? "" : "off"}" href="/api/books/${slug}/build/${name}" download>
    <span class="fi">${icon("file")}</span><span><b>${label}</b><span>${b.files?.[name] ? `${bytes(b.files[name])} · ${sub}` : "not built"}</span></span></a>`;
  host.innerHTML = stepHead("Publish", "Your print files, the Amazon listing and what you'll earn.") + `
    <div class="stack">
      ${built ? note("ok", `Ready for KDP. In KDP choose <b>${esc(trim)}</b>, <b>${esc(PAPERS[paper] || paper)}</b> and <b>Bleed</b>.`)
        : note("warn", `${b.last_build === "mock" ? "These files use placeholder art. Don't upload them." : "Nothing built yet."} <a href="#/book/${slug}/art">Go to Art &amp; build</a>`)}
      ${built && b.preflight && (b.preflight.errors.length || b.preflight.warnings.length) ? note(b.preflight.errors.length ? "err" : "warn",
        `<b>Check before uploading</b><ul>${[...b.preflight.errors, ...b.preflight.warnings].map((w) => `<li>${esc(w)}</li>`).join("")}</ul>`) : ""}
      <div class="files">
        ${file("interior.pdf", "interior.pdf", `${b.pages || "?"} pages`)}
        ${file("cover.pdf", "cover.pdf", "wraparound")}
        <a class="file" href="/api/books/${slug}/download.zip"><span class="fi">${icon("download")}</span><span><b>Everything</b><span>.zip · PDFs, listing, book.yaml</span></span></a>
      </div>
      <div class="card"><div class="card-h"><div><h3>Amazon listing</h3><p>Description, keywords, categories, price and AI disclosure.</p></div>
        <button class="btn ${listing ? "" : "primary"} sm" id="gen">${icon("sparkle")}${listing ? "Regenerate" : "Draft with Claude"}</button></div>
        <div class="card-b" id="listing">${listing ? listingHtml(listing) : `<p class="muted">Claude reads the finished book and drafts every field KDP asks for.</p>`}</div></div>
      <div class="card"><div class="card-h"><h3>Royalty</h3><a class="small" href="#/guide/pricing">Pricing guide</a></div><div class="card-b" id="calc"></div></div>
    </div>`;
  calculator($("#calc"), { pages: b.pages || 32, paper, trim, price: listing?.suggested_price_usd });
  wireCopy();
  $("#gen").onclick = (e) => busy(e.currentTarget, "Writing…", async () => {
    const st = await api("POST", `/api/books/${slug}/listing`);
    $("#listing").innerHTML = listingHtml(st.listing); wireCopy();
    calculator($("#calc"), { pages: b.pages || 32, paper, trim, price: st.listing.suggested_price_usd });
  });
}

function wireCopy() {
  $$("[data-copy]").forEach((b) => (b.onclick = () => navigator.clipboard.writeText(b.dataset.copy).then(() => toast("Copied"))));
}

function listingHtml(l) {
  const copy = (text) => `<button class="btn sm ghost" data-copy="${esc(text)}">${icon("copy")}Copy</button>`;
  return `<div class="stack">
    <div><div class="row between" style="margin-bottom:6px"><span class="label">Description</span>${copy(l.description)}</div>
      <div class="well small" style="white-space:pre-wrap">${esc(l.description)}</div></div>
    <div class="form-grid">
      <div><div class="row between" style="margin-bottom:6px"><span class="label">Keywords</span>${copy(l.keywords.join("\n"))}</div>
        <div class="chips">${l.keywords.map((k) => `<span class="chip" style="cursor:default">${esc(k)}</span>`).join("")}</div></div>
      <dl class="kv"><dt>Categories</dt><dd>${l.categories.map(esc).join("<br>")}</dd>
        <dt>Reading age</dt><dd>${esc(l.reading_age)}</dd>
        ${l.suggested_price_usd ? `<dt>Suggested price</dt><dd><b>${money(l.suggested_price_usd)}</b> <span class="muted">${esc(l.price_reasoning || "")}</span></dd>` : ""}
        <dt>AI disclosure</dt><dd>${esc(l.ai_disclosure)}</dd></dl>
    </div></div>`;
}

// ---------- royalty calculator ----------
function calculator(el, { pages = 32, paper = "premium_color", trim = "8.5x8.5", price } = {}) {
  el.innerHTML = `
    <div class="form-grid" style="grid-template-columns:repeat(auto-fit,minmax(130px,1fr))">
      <div class="field"><label for="c-cur">Marketplace</label><select class="input" id="c-cur">${Object.entries(MARKET).map(([k, v]) => `<option value="${k}">${v}</option>`).join("")}</select></div>
      <div class="field"><label for="c-ink">Ink</label><select class="input" id="c-ink"><option value="black">Black &amp; white</option><option value="standard">Standard color</option><option value="premium">Premium color</option></select></div>
      <div class="field"><label for="c-trim">Trim</label><input class="input" id="c-trim" value="${esc(trim)}"></div>
      <div class="field"><label for="c-pages">Pages</label><input class="input num" id="c-pages" type="number" min="24" max="828" step="2" value="${pages}"></div>
      <div class="field"><label for="c-price">List price</label><input class="input num" id="c-price" type="number" min="0" step="0.01" value="${price || 12.99}"></div>
    </div>
    <div id="c-out" style="margin-top:16px"></div>
    <p class="faint xs" style="margin-top:12px">KDP rates verified ${PRICING_SOURCE.verified} ·
      <a href="${PRICING_SOURCE.printing}" target="_blank" rel="noopener">printing cost</a> ·
      <a href="${PRICING_SOURCE.royalty}" target="_blank" rel="noopener">royalty</a>. UK/EU: enter the price before VAT.</p>`;
  $("#c-ink", el).value = inkForPaper(paper);
  const update = () => {
    const currency = $("#c-cur", el).value, sym = SYMBOL[currency];
    const tr = $("#c-trim", el).value.trim();
    const r = royalty({ currency, ink: $("#c-ink", el).value, pages: +$("#c-pages", el).value,
      large: /^\d+(\.\d+)?x\d+(\.\d+)?$/.test(tr) ? isLarge(tr) : false, price: +$("#c-price", el).value });
    if (r.error) { $("#c-out", el).innerHTML = note("warn", esc(r.error)); return; }
    const f = (x) => `${x < 0 ? "−" : ""}${sym}${Math.abs(x).toFixed(2)}`;
    $("#c-out", el).innerHTML = `<div class="stats">
        <div class="stat"><div class="k">Printing cost</div><div class="v">${f(r.printing)}</div><div class="s">per copy</div></div>
        <div class="stat"><div class="k">Amazon royalty</div><div class="v ${r.amazon > 0 ? "ok" : "err"}">${f(r.amazon)}</div><div class="s">${r.rate * 100}% rate</div></div>
        <div class="stat"><div class="k">Expanded distribution</div><div class="v ${r.expanded > 0 ? "ok" : "err"}">${f(r.expanded)}</div><div class="s">40% rate</div></div>
      </div>
      <p class="muted small" style="margin-top:12px">Minimum list price <b class="num">${f(r.minPrice)}</b> · with expanded distribution <b class="num">${f(r.minExpanded)}</b> · 60% rate from <b class="num">${f(r.threshold)}</b></p>`;
  };
  $$("input,select", el).forEach((i) => i.addEventListener("input", update));
  update();
}

// ---------- guide ----------
function guide(anchor) {
  const S = [["prepare", "Before you upload"], ["kdp", "Upload to KDP"], ["pricing", "Pricing"], ["calculator", "Royalty calculator"],
    ["ebook", "Kindle eBook"], ["other", "Other channels"], ["after", "After launch"]];
  const steps = (items) => `<ol class="numbered">${items.map(([t, d]) => `<li><div><b>${t}</b><span>${d}</span></div></li>`).join("")}</ol>`;
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Publishing guide</h1><p class="sub">From your MosiBooks PDFs to a book people can buy.</p></div></div>
    <div class="guide">
      <nav class="toc" id="toc">${S.map(([id, t]) => `<a href="#/guide/${id}" data-s="${id}">${t}</a>`).join("")}</nav>
      <div>
        <section class="gsec" id="g-prepare"><h2>Before you upload</h2><p class="lead">Four checks that save you from a reprint.</p>${steps([
          ["Preflight passes with real art", "Never upload a preview build. Art & build must show Preflight passed."],
          ["Read every page", "Look in the spread viewer for typos, wrong character details, odd hands or faces, and text over busy art. Redo any image with a note."],
          ["Decide on the ISBN", "KDP's free ISBN works only on Amazon and lists “Independently published”. Buy your own (Bowker in the US, Nielsen in the UK) to use IngramSpark too or show your own imprint."],
          ["Have the listing ready", "Title, description, 7 keywords and categories. The Publish step drafts them with Claude."]])}</section>

        <section class="gsec" id="g-kdp"><h2>Upload to Amazon KDP</h2><p class="lead">Paperback, step by step, at <a href="https://kdp.amazon.com" target="_blank" rel="noopener">kdp.amazon.com</a>.</p>${steps([
          ["Account, tax and bank", "Finish the tax interview and payment details first. You can't publish without them."],
          ["Create → Paperback → Details", "Language, title, subtitle, author exactly as on the cover, description, and “I own the copyright”."],
          ["Keywords, categories, audience", "Paste the 7 keyword phrases, pick categories and the reading age. Sexually explicit content: No."],
          ["ISBN", "Free KDP ISBN or your own. It can't be changed after publishing."],
          ["Print options: match book.yaml", "Ink and paper, trim size, <b>Bleed (PDF only)</b>, and cover finish. Matte suits illustrated books, glossy makes colors pop."],
          ["Upload the files", "Upload <code>interior.pdf</code> as the manuscript, then “Upload a cover you already have” → <code>cover.pdf</code>. The barcode area is already clear and the spine is sized from your real page count."],
          ["AI-generated content", "Answer honestly. The images are AI-generated. The text is AI-generated if Claude wrote it, AI-assisted if you wrote it and Claude edited. The Publish step drafts this answer."],
          ["Launch Previewer", "Check every page. A margin or bleed warning means a setting doesn't match the file. Fix the setting, not the PDF."],
          ["Order a proof copy", "Paper is darker than screens. If the art looks heavy, lighten the style in book.yaml and regenerate."],
          ["Price and publish", "See pricing below. Review takes up to 72 hours. Then the book appears on Amazon within a few days."]])}</section>

        <section class="gsec" id="g-pricing"><h2>Pricing</h2>
          <p class="lead">Royalty = rate × list price − printing cost. The rate is <b>60%</b> from $9.99 / £7.99 / €9.99 and <b>50%</b> below. Expanded distribution (bookstores and libraries) pays 40%, and printing comes out of that too.</p>
          <div class="card"><div class="card-b table-wrap"><table><thead><tr><th>Book</th><th>Typical trim · ink</th><th class="r">Typical US price</th><th>Why</th></tr></thead><tbody>
            <tr><td><b>Picture book</b><br><span class="faint xs">24–40 pages</span></td><td>8.5×8.5 · premium color</td><td class="r">$10.99–14.99</td><td class="muted">Printing is a flat ~$3.60–4.20 at this length. Stay at $9.99 or more for the 60% rate.</td></tr>
            <tr><td><b>Storybook</b><br><span class="faint xs">80–200 pages</span></td><td>6×9 · cream B&amp;W</td><td class="r">$8.99–12.99</td><td class="muted">Cheap to print, so margins are good. Spine text is allowed from 80 pages.</td></tr>
            <tr><td><b>Comic</b><br><span class="faint xs">48–120 pages</span></td><td>7×10 · premium color</td><td class="r">$14.99–24.99</td><td class="muted">Color costs per page. Check the calculator before you settle the length.</td></tr>
          </tbody></table></div></div>
          <ul class="dots">
            <li>Price within the range of the top 10 sellers in your category. A first book sells better slightly under the median.</li>
            <li>End prices in .99 and set each marketplace yourself instead of auto-converting from USD.</li>
            <li>Turn on expanded distribution only when the calculator shows a positive amount. For short color books it often doesn't.</li>
            <li>For premium color, 24 to 40 pages cost the same flat fee, so use the full 40 if the story allows.</li>
          </ul>
          <p class="faint xs" style="margin-top:12px">Typical price ranges are guidance, not KDP figures. Check against current best-sellers in your category.</p></section>

        <section class="gsec" id="g-calculator"><h2>Royalty calculator</h2><p class="lead">What you earn per copy sold.</p><div class="card"><div class="card-b" id="g-calc"></div></div></section>

        <section class="gsec" id="g-ebook"><h2>Kindle eBook</h2>
          <p>Your PDFs are print files. A Kindle edition is a separate fixed-layout upload made with Kindle Create or Kindle Kids' Book Creator (KDP Help → Tools and Resources), using the page images in <code>build/proofs/</code>.</p>
          <p>eBooks pay 70% inside KDP's price band (in the US, $2.99–$9.99), minus a delivery cost based on file size, which adds up for image-heavy books. Outside the band they pay 35%. Current rules: <a href="https://kdp.amazon.com/en_US/help/topic/G200644210" target="_blank" rel="noopener">eBook Royalties</a>.</p></section>

        <section class="gsec" id="g-other"><h2>Other channels</h2><p class="lead">The same PDFs work almost everywhere. Only the cover spine differs.</p>
          <div class="card"><div class="card-b table-wrap"><table><thead><tr><th>Where</th><th>Good for</th><th>What to upload</th></tr></thead><tbody>
            <tr><td><a href="https://www.ingramspark.com" target="_blank" rel="noopener">IngramSpark</a></td><td class="muted">Bookstores, libraries, hardcovers</td><td class="muted">interior.pdf as is. Compare the spine width with their cover template. Needs your own ISBN.</td></tr>
            <tr><td><a href="https://www.lulu.com" target="_blank" rel="noopener">Lulu</a></td><td class="muted">Direct sales, hardcover, coil-bound</td><td class="muted">interior.pdf. Size the cover with Lulu's calculator.</td></tr>
            <tr><td><a href="https://press.barnesandnoble.com" target="_blank" rel="noopener">B&amp;N Press</a></td><td class="muted">Barnes &amp; Noble online and in-store</td><td class="muted">interior.pdf and cover.pdf. Check their spine width.</td></tr>
            <tr><td>Etsy · Gumroad · Shopify</td><td class="muted">Digital PDFs, printables</td><td class="muted">A screen PDF made from build/proofs, or interior.pdf as print-at-home.</td></tr>
          </tbody></table></div></div></section>

        <section class="gsec" id="g-after"><h2>After launch</h2><ul class="dots">
          <li>Early reviews: give copies to readers in your audience. Never pay for reviews; Amazon bans it.</li>
          <li>Amazon Ads: start with automatic targeting on a small daily budget, then move the keywords that convert into manual campaigns.</li>
          <li>A+ Content (KDP Marketing) with spreads from the book noticeably lifts conversion for picture books.</li>
          <li>A series sells the next book. Reuse the same style and characters for a consistent look.</li></ul></section>
      </div></div></div>`;
  calculator($("#g-calc"));
  const links = $$("#toc a");
  links.forEach((a) => (a.onclick = (e) => { e.preventDefault(); $(`#g-${a.dataset.s}`).scrollIntoView({ behavior: "smooth" }); }));
  const io = new IntersectionObserver((es) => es.forEach((en) => en.isIntersecting &&
    links.forEach((a) => a.classList.toggle("on", `g-${a.dataset.s}` === en.target.id))), { rootMargin: "-20% 0px -70% 0px" });
  $$(".gsec").forEach((s) => io.observe(s));
  if (anchor) $(`#g-${anchor}`)?.scrollIntoView();
}

// ---------- settings ----------
async function settingsView() {
  settingsCache = null;
  const { settings: s, trims, path, credit, server } = await getSettings();
  const input = (k, opts = {}) => opts.select
    ? `<select class="input" id="s-${k}" name="${k}">${opts.select.map(([v, t]) => `<option value="${v}" ${String(s[k]) === String(v) ? "selected" : ""}>${t}</option>`).join("")}</select>`
    : `<input class="input ${opts.type === "number" ? "num" : ""}" id="s-${k}" name="${k}" type="${opts.type || "text"}" value="${esc(s[k])}" ${opts.step ? `step="${opts.step}"` : ""} autocomplete="off" spellcheck="false" ${opts.ph ? `placeholder="${esc(opts.ph)}"` : ""}>`;
  const field = (k, label, opts = {}) => `<div class="field ${opts.full ? "full" : ""}"><label for="s-${k}">${label}</label>
    ${opts.secret ? `<div class="input-group">${input(k, { ...opts, type: "password" })}<button type="button" class="btn icon" data-reveal="s-${k}" aria-label="Show">${icon("eye")}</button></div>` : input(k, opts)}
    ${opts.hint ? `<span class="hint">${opts.hint}</span>` : ""}</div>`;
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Settings</h1><p class="sub">${server ? "Your own settings and keys, saved with your account. Other people on this server can't see them."
      : `Stored only on this Mac in <code>${esc(path)}</code>, readable by you only.`}</p></div>
      <a class="btn sm" href="#/setup">${icon("sparkle")}Run setup again</a></div>
    <form id="sf">
      <div class="sgroup"><div class="about"><h2>Claude</h2><p>Asks the questions and writes the outline, manuscript and listing. ${server ? "It uses your own Anthropic API key." : "By default it uses the Claude account you're logged into in Claude Code."}</p></div>
        <div class="stack"><div class="form-grid">
          ${field("anthropic_api_key", "Anthropic API key", server ? { secret: true, ph: "sk-ant-…", hint: `Required. Create one at <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com</a>.`, full: true }
            : { secret: true, ph: "Leave empty to use your Claude login", hint: "Optional. Set it to pay per token instead of using your subscription.", full: true })}
          ${field("claude_model", "Model", { select: [["claude-opus-5-5", "Opus 5.5 · best writing"], ["claude-sonnet-5-5", "Sonnet 5.5 · faster"], ["claude-fable-5-1", "Fable 5.1"], ["claude-haiku-5-5", "Haiku 5.5 · fastest"]] })}
        </div><div class="testline"><button type="button" class="btn sm" data-test="claude">Test connection</button><span id="t-claude"></span></div></div></div>

      <div class="sgroup"><div class="about"><h2>Images</h2><p>OpenAI draws the illustrations and reviews each one. New books copy these values into their book.yaml.</p></div>
        <div class="stack">
          <div class="credit">
            <div><div class="k">OpenAI credit left</div>
              <div class="v num ${credit.remaining != null && credit.remaining < 5 ? "low" : ""}">${credit.remaining != null ? money(credit.remaining) : "–"}</div>
              <div class="faint xs">${credit.balance ? `${money(credit.balance)} entered ${timeAgo(credit.set_at)} − ~${money(credit.spent)} for ${credit.images} image${credit.images === 1 ? "" : "s"} since (estimated)` : "Enter your balance below to track it"}</div></div>
            <a class="btn primary sm" href="${esc(credit.buy_url)}" target="_blank" rel="noopener">${icon("dollar")}Buy credits${icon("ext")}</a></div>
          <div class="form-grid">
          ${field("openai_credit_usd", "Credit balance on OpenAI (USD)", { type: "number", step: "0.01", hint: `OpenAI doesn't share the balance with apps. Copy it from the <a href="${esc(credit.buy_url)}" target="_blank" rel="noopener">billing page</a> after buying; MosiBooks then subtracts each image it generates.`, full: true })}
          ${field("openai_api_key", "OpenAI API key", { secret: true, ph: "sk-…", hint: "Required for real art. Previews are free without it.", full: true })}
          ${field("image_model", "Image model")}
          ${field("image_quality", "Default quality", { select: [["low", "low · ~$0.01"], ["medium", "medium · ~$0.05 (recommended)"], ["high", "high · ~$0.21"]], hint: "Per image. Mark single images as high in the Preview step." })}
          ${field("review", "Vision review", { select: [["true", "On · flags problems, never redraws"], ["false", "Off · cheapest"]] })}
          ${field("est_cost_per_image_usd", "Cost per image (USD)", { type: "number", step: "0.01", hint: "Only used for estimates." })}
          ${field("max_workers", "Parallel requests", { type: "number" })}
          ${server ? "" : field("realesrgan_path", "Real-ESRGAN binary", { ph: "Auto-detected", hint: "Optional, for sharper upscaling.", full: true })}
        </div><div class="testline"><button type="button" class="btn sm" data-test="openai">Test key</button><span id="t-openai"></span></div></div></div>

      <div class="sgroup"><div class="about"><h2>Defaults</h2><p>Prefilled on every new book.</p></div>
        <div class="form-grid">
          ${field("default_author", "Author name", { full: true })}
          ${field("voice_lang", "Voice input language", { select: [["fa-IR", "فارسی · Persian"], ["en-US", "English"], ["fr-FR", "Français"], ["de-DE", "Deutsch"], ["es-ES", "Español"]], hint: "The language you speak into the mic buttons." })}
          ${field("default_trim", "Trim size", { select: trims.map((t) => [t, t]) })}
          ${server ? "" : field("books_dir", "Books folder", { full: true })}
        </div></div>
      <div class="savebar" id="savebar" hidden><span class="small muted">You have unsaved changes.</span>
        <div class="row"><button type="button" class="btn sm ghost" id="reset">Discard</button><button class="btn sm primary" type="submit">Save changes</button></div></div>
    </form></div>`;
  const form = $("#sf");
  const collect = () => {
    const d = Object.fromEntries(new FormData(form));
    for (const k of ["est_cost_per_image_usd", "max_workers", "openai_credit_usd"]) d[k] = Number(d[k]);
    d.review = d.review === "true";
    return d;
  };
  form.addEventListener("input", () => ($("#savebar").hidden = false));
  $("#reset").onclick = () => settingsView();
  form.onsubmit = (e) => {
    e.preventDefault();
    busy(form.querySelector("[type=submit]"), "Saving", async () => {
      await api("PUT", "/api/settings", collect()); settingsCache = null; renderConn(); toast("Settings saved"); settingsView();
    });
  };
  $$("[data-reveal]").forEach((b) => (b.onclick = () => { const i = $(`#${b.dataset.reveal}`); i.type = i.type === "password" ? "text" : "password"; }));
  $$("[data-test]").forEach((b) => (b.onclick = () => busy(b, "Testing", async () => {
    const out = $(`#t-${b.dataset.test}`);
    await api("PUT", "/api/settings", collect()); $("#savebar").hidden = true; settingsCache = null; renderConn();
    try { out.innerHTML = `<span class="badge ok">${esc((await api("POST", `/api/settings/test/${b.dataset.test}`)).message)}</span>`; }
    catch (err) { out.innerHTML = `<span class="badge err">${esc(err.message)}</span>`; }
  })));
}

// ---------- first-run setup ----------
const SETUP_STEPS = ["Claude", "Illustrations", "About you"];

async function setupView(step) {
  settingsCache = null; setupCache = null;
  const [{ settings: s }, st] = await Promise.all([getSettings(), setupStatus()]);
  const go = (n) => (location.hash = `#/setup/${n}`);
  const bar = `<ol class="setup-bar">${SETUP_STEPS.map((l, i) =>
    `<li class="${i + 1 < step ? "done" : i + 1 === step ? "current" : ""}"><span class="dot">${i + 1 < step ? icon("check") : i + 1}</span>${l}</li>`).join("")}</ol>`;
  const shell = (body) => `<div class="page setup">
    <div class="setup-hero"><h1>Welcome to MosiBooks</h1><p class="muted">${st.user ? `Signed in as <b>${esc(st.user)}</b>. ` : ""}Two quick connections and you're ready to make your first book. About 3 minutes.</p></div>
    ${bar}<div class="card"><div class="card-b">${body}</div></div></div>`;
  const result = (id) => `<div class="setup-result" id="${id}"></div>`;
  const show = (id, ok, msg) => ($(`#${id}`).innerHTML = note(ok ? "ok" : "err", msg));

  if (step === 1) {
    const sub = !st.server && !s.anthropic_api_key;
    view.innerHTML = shell(`
      <h2>Connect Claude</h2>
      <p class="muted small">Claude asks you about your idea and writes the outline, the story and the Amazon listing. Pick how to connect:</p>
      <div class="choices">
        <label class="choice" ${st.server ? "hidden" : ""}><input type="radio" name="how" value="sub" ${sub ? "checked" : ""}>
          <div><b>My Claude subscription</b> <span class="badge ok">Recommended</span>
          <div class="faint small">Uses the Claude account signed in to Claude Code on this computer. No extra cost.</div></div></label>
        <label class="choice"><input type="radio" name="how" value="key" ${sub ? "" : "checked"}>
          <div><b>An Anthropic API key</b>
          <div class="faint small">${st.server ? "Your own key: what Claude writes for your books is billed to your Anthropic account."
            : "Pay per use from console.anthropic.com. Good on a server without Claude Code."}</div></div></label>
      </div>
      <div id="how-sub" class="how">
        ${st.claude.logged_in
          ? note("ok", `Signed in to Claude as <b>${esc(st.claude.email || "your account")}</b>${st.claude.plan ? ` (${esc(st.claude.plan)} plan)` : ""}.`)
          : `<div class="signin">
              <button type="button" class="btn primary" id="signin">${icon("sparkle")}Sign in with Claude</button>
              <span class="faint small" id="signin-msg">A Claude sign-in page will open in your browser.</span></div>
            <details class="faint small"><summary>Didn't open?</summary>
              In Terminal, from the MosiBooks folder, run
              <div class="cmd"><code>mosibooks claude-login</code><button type="button" class="btn sm ghost" data-copy="mosibooks claude-login">${icon("copy")}</button></div>
              and follow the link it prints. This page notices when you're done.</details>`}
      </div>
      <div id="how-key" class="how" hidden>
        <ol class="howto small">
          <li>Open <a href="https://console.anthropic.com/settings/keys" target="_blank" rel="noopener">console.anthropic.com → API keys ${icon("ext")}</a> and create a key.</li>
          <li>Paste it here:</li></ol>
        <div class="input-group"><input class="input" id="akey" type="password" placeholder="sk-ant-…" autocomplete="off" spellcheck="false"
          value="${esc(s.anthropic_api_key)}"></div>
      </div>
      ${result("r1")}
      <div class="setup-actions"><a href="#" id="skip" class="small faint">Skip for now</a>
        <div class="row"><button class="btn" id="check">Check connection</button><button class="btn primary" id="next" disabled>Continue</button></div></div>`);
    let poll;
    const waitForLogin = (deadline) => {
      clearTimeout(poll);
      if (!location.hash.startsWith("#/setup") || Date.now() > deadline) return;
      poll = setTimeout(async () => {
        setupCache = null;
        const now = await setupStatus();
        if (now.claude?.logged_in) { toast("Signed in to Claude"); setupView(1); } else waitForLogin(deadline);
      }, 2500);
    };
    if ($("#signin") && !st.server) {
      $("#signin").onclick = () => busy($("#signin"), "Opening", async () => {
        await api("POST", "/api/setup/claude-login");
        $("#signin-msg").textContent = "Approve the sign-in in your browser tab. This page updates by itself.";
        waitForLogin(Date.now() + 5 * 60 * 1000);
      });
      waitForLogin(Date.now() + 5 * 60 * 1000);  // also catch a sign-in done from Terminal
    }
    const mode = () => $("input[name=how]:checked").value;
    const sync = () => { $("#how-sub").hidden = mode() !== "sub"; $("#how-key").hidden = mode() !== "key"; $("#next").disabled = true; $("#r1").innerHTML = ""; };
    $$("input[name=how]").forEach((r) => (r.onchange = sync)); sync();
    if (sub && st.claude.logged_in) $("#next").disabled = false;
    $$("input[name=how]").forEach((r) => r.addEventListener("change", () => {
      if (mode() === "sub" && st.claude.logged_in) $("#next").disabled = false;
    }));
    $("#check").onclick = () => busy($("#check"), "Checking", async () => {
      const key = mode() === "key" ? $("#akey").value.trim() : "";
      if (mode() === "key" && !key) return show("r1", false, "Paste your API key first.");
      await api("PUT", "/api/settings", { anthropic_api_key: key });
      try {
        await api("POST", "/api/settings/test/claude");
        show("r1", true, "Claude is connected."); $("#next").disabled = false; $("#next").focus();
      } catch (e) {
        show("r1", false, mode() === "key"
          ? `That key didn't work: ${esc(e.message)}`
          : `Couldn't reach Claude. Sign in first with the button above, then try again.<div class="faint xs">${esc(e.message)}</div>`);
      }
    });
    $("#next").onclick = () => go(2);
    $("#skip").onclick = (e) => { e.preventDefault(); go(2); };
    wireCopy();
    return;
  }

  if (step === 2) {
    view.innerHTML = shell(`
      <h2>Connect OpenAI for illustrations</h2>
      <p class="muted small">OpenAI draws the pictures. You pay OpenAI directly, usually about $0.05 per image (a 32-page picture book is roughly $2–4).</p>
      <ol class="howto small">
        <li>Open <a href="https://platform.openai.com/api-keys" target="_blank" rel="noopener">platform.openai.com → API keys ${icon("ext")}</a> and create a new secret key.</li>
        <li>Add a little credit on the <a href="https://platform.openai.com/settings/organization/billing/overview" target="_blank" rel="noopener">billing page ${icon("ext")}</a> ($10 is plenty to start).</li>
        <li>Paste the key here:</li></ol>
      <div class="input-group"><input class="input" id="okey" type="password" placeholder="sk-…" autocomplete="off" spellcheck="false" value="${esc(s.openai_api_key)}"></div>
      <div class="field" style="margin-top:12px"><label for="credit">Credit you added, in USD <span class="faint">(optional)</span></label>
        <input class="input num" id="credit" type="number" step="0.01" min="0" value="${s.openai_credit_usd || ""}" placeholder="10">
        <span class="hint">MosiBooks keeps a running estimate of what's left, so you know before you run out.</span></div>
      ${result("r2")}
      <div class="setup-actions"><a href="#" id="skip" class="small faint">Skip: I'll try free previews first</a>
        <div class="row"><a class="btn ghost" href="#/setup/1">Back</a><button class="btn" id="check">Check key</button><button class="btn primary" id="next" ${s.openai_api_key ? "" : "disabled"}>Continue</button></div></div>`);
    $("#okey").oninput = () => ($("#next").disabled = true);
    $("#check").onclick = () => busy($("#check"), "Checking", async () => {
      const key = $("#okey").value.trim();
      if (!key) return show("r2", false, "Paste your OpenAI key first.");
      await api("PUT", "/api/settings", { openai_api_key: key, openai_credit_usd: Number($("#credit").value) || 0 });
      try {
        show("r2", true, esc((await api("POST", "/api/settings/test/openai")).message));
        $("#next").disabled = false; $("#next").focus();
      } catch (e) { show("r2", false, `That key didn't work: ${esc(e.message)}`); }
    });
    $("#next").onclick = async () => {
      if ($("#credit").value) await api("PUT", "/api/settings", { openai_credit_usd: Number($("#credit").value) || 0 });
      go(3);
    };
    $("#skip").onclick = (e) => { e.preventDefault(); go(3); };
    return;
  }

  view.innerHTML = shell(`
    <h2>A little about you</h2>
    <p class="muted small">Prefilled on every new book. You can change these any time in Settings.</p>
    <div class="form-grid" style="margin-top:12px">
      <div class="field full"><label for="author">Author name on the cover</label>
        <input class="input" id="author" value="${esc(s.default_author)}" placeholder="Your pen name"></div>
      <div class="field"><label for="voice">Language you'll speak in</label>
        <select class="input" id="voice">${[["fa-IR", "فارسی · Persian"], ["en-US", "English"], ["fr-FR", "Français"], ["de-DE", "Deutsch"], ["es-ES", "Español"]]
          .map(([v, t]) => `<option value="${v}" ${s.voice_lang === v ? "selected" : ""}>${t}</option>`).join("")}</select>
        <span class="hint">For the mic buttons.</span></div>
    </div>
    <div class="summary">
      <div>${icon(s.anthropic_api_key || st.claude.logged_in ? "check" : "alert")} Claude: ${s.anthropic_api_key ? "API key"
        : st.claude.logged_in ? `your Claude subscription (${esc(st.claude.email || "")})` : `not connected yet. <a href="#/setup/1">Connect</a>`}</div>
      <div>${icon(s.openai_api_key ? "check" : "alert")} Illustrations: ${s.openai_api_key ? "OpenAI connected" : `not connected yet, free previews only. <a href="#/setup/2">Connect</a>`}</div>
    </div>
    <div class="setup-actions"><a class="btn ghost" href="#/setup/2">Back</a>
      <button class="btn primary" id="finish">${icon("sparkle")}Start my first book</button></div>`);
  $("#finish").onclick = () => busy($("#finish"), "Finishing", async () => {
    await api("PUT", "/api/settings", { default_author: $("#author").value.trim(), voice_lang: $("#voice").value });
    await api("POST", "/api/setup/done");
    setupCache = null; settingsCache = null; renderConn();
    toast("You're all set"); location.hash = "#/new";
  });
}

// ---------- sign out (only shown when the server has login enabled) ----------
fetch("/api/auth/status").then((r) => r.json()).then((s) => {
  if (!s.enabled) return;
  const b = document.getElementById("signout");
  b.hidden = false;
  if (s.mode === "accounts" && s.user) { b.textContent = `Sign out · ${s.user}`; b.title = s.user; }
  b.onclick = async () => { await fetch("/api/logout", { method: "POST" }); location.href = "/login"; };
}).catch(() => {});
