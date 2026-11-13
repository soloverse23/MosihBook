import { royalty, inkForPaper, isLarge, SYMBOL, MARKET, PRICING_SOURCE } from "./pricing.js";

const view = document.getElementById("view");
const STEPS = [
  ["brief", "Brief"], ["questions", "Questions"], ["outline", "Outline"], ["manuscript", "Manuscript"],
  ["art", "Art & build"], ["control", "Control & correction"], ["publish", "Publish"],
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
  globe: '<circle cx="12" cy="12" r="8.5"/><path d="M3.5 12h17M12 3.5c2.3 2.4 3.5 5.2 3.5 8.5s-1.2 6.1-3.5 8.5c-2.3-2.4-3.5-5.2-3.5-8.5s1.2-6.1 3.5-8.5z"/>',
  image: '<rect x="3.5" y="4.5" width="17" height="15" rx="2"/><circle cx="9" cy="10" r="1.6"/><path d="m4 17 5-4.5 4 3.5 3-2.5 4 3.5"/>',
  book: '<path d="M4 5.5c2.7-1 5.5-.8 8 .7v13c-2.5-1.5-5.3-1.7-8-.7zM20 5.5c-2.7-1-5.5-.8-8 .7v13c2.5-1.5 5.3-1.7 8-.7z"/>',
  grid: '<rect x="3.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="13.5" y="3.5" width="7" height="7" rx="1.5"/><rect x="3.5" y="13.5" width="17" height="7" rx="1.5"/>',
  download: '<path d="M12 4v11M7.5 10.5 12 15l4.5-4.5M5 19.5h14"/>',
  upload: '<path d="M12 15V4M7.5 8.5 12 4l4.5 4.5M5 19.5h14"/>',
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
const LIGHTBOX_IMGS = ".spread img, .cover-view img, .shot .img img, .insp-img img";
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
  const res = await fetch(url, { method, cache: "no-store", headers: body ? { "Content-Type": "application/json" } : {},
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

// warnings the user dismissed with "Ignore", remembered per book in this browser
const ignoreStore = (slug) => `ignored:${slug}`;
function ignoredSet(slug) {
  try { return new Set(JSON.parse(localStorage.getItem(ignoreStore(slug)) || "[]")); } catch { return new Set(); }
}
const notIgnored = (slug, list, key = (x) => x) => { const s = ignoredSet(slug); return (list || []).filter((x) => !s.has(key(x))); };
const ignoreBtn = (slug, key) => `<button class="btn sm ghost ignore" data-slug="${esc(slug)}" data-ignore="${esc(key)}">Ignore</button>`;
document.addEventListener("click", (e) => {
  const b = e.target.closest("[data-ignore]");
  if (!b) return;
  const s = ignoredSet(b.dataset.slug); s.add(b.dataset.ignore);
  try { localStorage.setItem(ignoreStore(b.dataset.slug), JSON.stringify([...s])); } catch {}
  const box = b.closest("[data-ignorable]");
  b.closest("li")?.remove();
  if (box && !box.querySelector("li")) box.remove();
});

function badge(status) {
  const map = { ready: "ok", "preflight failed": "err", "mock preview": "warn", manuscript: "accent" };
  const label = { ready: "Ready to publish", "preflight failed": "Preflight failed", "mock preview": "Placeholder build",
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

// Typing by hand in any box stops the mic (our own dictated "input" events are not trusted keystrokes).
document.addEventListener("keydown", (e) => {
  if (!dictation || !e.isTrusted) return;
  if (["Shift", "Control", "Alt", "Meta", "CapsLock", "Tab", "Escape"].includes(e.key)) return;
  if (e.ctrlKey || e.metaKey) return;
  if (!e.target.matches?.("input, textarea, [contenteditable]")) return;
  dictation.rec.stop();
}, true);

// ---------- jobs ----------
function logLine(s) {
  const cls = /^(ERROR|FAILED|NEEDS ATTENTION)/.test(s) ? "e" : /^WARN/.test(s) ? "w" : /PASS/.test(s) ? "g" : "";
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
  const badge = im.failed ? `<span class="badge err">failed</span>`
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
    ${books.length ? `<div class="books">${books.filter(show).map((b) => `<div class="tile${b.origin ? " edition" : ""}">${b.status === "ready"
      ? `<button class="btn sm tile-act" data-tr="${b.origin?.slug || b.slug}" data-title="${esc(b.origin?.title || b.title)}" title="Same pictures, translated text">${icon("globe")}Translate</button>` : ""}
      <a class="book" href="#/book/${b.slug}">
        <div class="cover">${b.cover ? `<img src="/api/books/${b.slug}/front.jpg?${b.updated}" alt="">` : coverPlaceholder(b.title, b.type)}
          ${b.origin || b.editions ? `<span class="lang-tag">${icon("globe")}${esc(b.language)}</span>` : ""}</div>
        <div class="meta"><h3>${esc(b.title)}</h3>
          ${b.origin ? `<span class="ed-of xs" title="Same book, same pictures">Translation of <b>${esc(b.origin.title)}</b></span>`
            : b.editions ? `<span class="ed-of xs">Original · ${b.editions} languages</span>` : ""}
          <div class="row between">${badge(b.status)}<span class="faint xs">${timeAgo(b.updated)}</span></div>
          <span class="faint xs">${esc(TYPES[b.type]?.label || "")}${b.pages ? ` · ${b.pages} pages` : ""}</span></div></a></div>`).join("")}
      <a class="newtile" href="#/new">${icon("plus")}New book</a></div>`
    : `<div class="card"><div class="empty"><div class="ico">${icon("sparkle")}</div><h2>Start your first book</h2>
        <p>Describe the book you want. Claude asks a few questions, outlines it and writes the manuscript, then MosiBooks illustrates and lays it out for print.</p>
        <a class="btn primary" href="#/new">${icon("plus")}New book</a></div></div>`}</div>`;
  $$("#filter button").forEach((b) => (b.onclick = () => { try { sessionStorage.setItem("lib-filter", b.dataset.f); } catch {} library(); }));
  $$("[data-tr]").forEach((b) => (b.onclick = () => translateBook(b.dataset.tr, b.dataset.title, b)));
}

// A finished book in another language: Claude translates the words, the illustrations are reused.
// the languages a book can be written in (bookforge/words.py LANGUAGES)
const LANGS = ["English", "French", "German", "Romanian", "Spanish"];
const LANG_NATIVE = { English: "English", French: "Français · French", German: "Deutsch · German",
  Romanian: "Română · Romanian", Spanish: "Español · Spanish" };
const LANG_ALIAS = { en: "English", fr: "French", francais: "French", "français": "French", de: "German", deutsch: "German",
  germany: "German", ro: "Romanian", romana: "Romanian", "română": "Romanian", es: "Spanish", espanol: "Spanish", "español": "Spanish" };
const langOf = (v) => { const k = String(v || "English").trim().toLowerCase();
  return LANGS.find((l) => l.toLowerCase() === k) || LANG_ALIAS[k] || "English"; };
async function translateBook(slug, title, btn) {
  const v = await modal({ title: `Translate “${title}”`, confirm: "Translate",
    body: "The same art and the same text, translated by Claude. Pictures without words in them are reused as they are, and the new book is laid out straight away.",
    fields: `<div class="field" style="margin-top:var(--s3)"><label for="tr-lang-m">Language</label>
      <select class="input" id="tr-lang-m" name="language">${LANGS.map((l) => `<option value="${l}">${LANG_NATIVE[l]}</option>`).join("")}</select></div>` });
  if (v?.language?.trim()) await runTranslate(slug, v.language.trim(), btn);
}

async function runTranslate(slug, language, btn) {
  toast(`Claude is translating into ${language}. This takes about a minute.`);
  const r = await busy(btn, "Translating…", () => api("POST", `/api/books/${slug}/translate`, { language }));
  if (!r) return;
  if (!r.redraw.length) {
    await api("POST", `/api/books/${r.slug}/jobs/build`).catch((e) => toast(e.message, true));
    toast(`Translated. All ${r.reused.length} pictures reused, laying out the book now.`);
  } else {
    toast(`Translated. ${r.reused.length} pictures reused. ${r.redraw.length} have the words drawn into them and need redrawing (about ${money(r.redraw_cost_usd)}).`);
  }
  location.hash = `#/book/${r.slug}/art`;
}

// ---------- character library ----------
async function characterLibrary() {
  const { characters: chars } = await api("GET", "/api/characters");
  const v = Date.now();
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Characters</h1><p class="sub">Every character drawn for any of your books. A book that uses one of
      these names starts from exactly this look, so a series stays consistent. Pick them in a new book's brief.</p></div>
      <div class="row">
        <label class="btn sm ghost"><input type="file" accept=".zip,application/zip" hidden id="charImport">${icon("upload")}Import</label>
        ${chars.length ? `<a class="btn sm ghost" href="/api/characters/export.zip" download="characters.zip">${icon("download")}Export all</a>` : ""}</div></div>
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
  $("#charImport").onchange = async (e) => {
    const f = e.target.files[0]; if (!f) return;
    const res = await fetch("/api/characters/import", { method: "POST", body: f });
    const r = await res.json();
    if (!res.ok) { toast(r.detail || "Import failed", true); return; }
    const n = r.added.length + r.replaced.length;
    toast(`Imported ${n} character${n === 1 ? "" : "s"}${r.replaced.length ? ` (${r.replaced.length} replaced: ${r.replaced.join(", ")})` : ""}.`);
    characterLibrary();
  };
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

// Popular art styles shown as pictures (the same scene in each), so a writer sees what they pick.
// Tones work the same way, shown as the same opening line written in each tone.
// The chosen preset's direction goes into the field; "Other" lets them describe their own.
let artStyles, tones;
const loadArtStyles = () => (artStyles ||= fetch("/styles/styles.json").then((r) => r.json()).catch(() => []));
const loadTones = () => (tones ||= fetch("/styles/tones.json").then((r) => r.json()).catch(() => []));
const isArtQuestion = (q) => q.id === "art_style" || /\b(art|illustration|drawing) style\b/i.test(q.question || "");
const isToneQuestion = (q) => !isArtQuestion(q) && (q.id === "tone" || /\btone\b/i.test(q.question || ""));

function stylePicker(styles, { name = "", id = "", value = "", label = "Art style" } = {}) {
  return presetPicker(styles.map((s) => ({ name: s.name, value: s.art, face: `<img src="/styles/${esc(s.id)}.jpg" alt="" loading="lazy">` })),
    { name, id, value, label, other: "Other style", placeholder: "Describe the style: linocut prints, 1950s retro, pixel art…" });
}

function tonePicker(list, { name = "", id = "", value = "", label = "Tone" } = {}) {
  return presetPicker(list.map((t) => ({ name: t.name, value: t.tone, face: `<span class="tone-sample">${esc(t.sample)}</span>` })),
    { name, id, value, label, other: "Other tone", placeholder: "Describe the tone: dry humour, poetic, matter-of-fact…", cls: "tone-pick" });
}

function presetPicker(items, { name, id, value, label, other: otherLabel, placeholder, cls = "" }) {
  const preset = items.find((s) => s.value === value);
  const other = !!value && !preset;
  return `<div class="style-pick ${cls}" role="radiogroup" aria-label="${esc(label)}">
    <div class="style-grid">${items.map((s) => `
      <button type="button" class="style-card ${preset === s ? "on" : ""}" data-value="${esc(s.value)}" role="radio" aria-checked="${preset === s}" title="${esc(s.value)}">
        ${s.face}<span>${esc(s.name)}</span></button>`).join("")}
      <button type="button" class="style-card other ${other ? "on" : ""}" data-other role="radio" aria-checked="${other}">
        <span class="ph">${icon("edit")}</span><span>${esc(otherLabel)}</span></button></div>
    <div class="style-other" ${other ? "" : "hidden"}><input class="input" ${id ? `id="${id}"` : ""} ${name ? `name="${name}"` : ""}
      aria-label="${esc(label)}" value="${esc(value)}" placeholder="${esc(placeholder)}"></div>
  </div>`;
}

function wireStylePicker(root) {
  $$(".style-pick", root).forEach((p) => {
    const input = $("input", p), box = $(".style-other", p), cards = $$(".style-card", p);
    const select = (card) => cards.forEach((c) => { c.classList.toggle("on", c === card); c.setAttribute("aria-checked", c === card); });
    cards.forEach((c) => (c.onclick = () => {
      const off = c.classList.contains("on");
      select(off ? null : c);
      if (c.dataset.other !== undefined) {
        box.hidden = off;
        if (!off) { if (cards.some((x) => x.dataset.value === input.value)) input.value = ""; input.focus(); } else input.value = "";
      } else { box.hidden = true; input.value = off ? "" : c.dataset.value; }  // click again: none, Claude decides
      input.dispatchEvent(new Event("input", { bubbles: true }));
    }));
  });
}

// The brief, in five numbered parts. Only the idea is required; each optional part says what it is for and,
// closed, what it holds now, so nothing is asked twice: Claude's questions cover only what is left open.
async function briefForm(slug, brief = {}, sources = []) {
  const { settings: s, trims } = await getSettings();
  const type = "storybook";
  const [styles, toneList] = await Promise.all([loadArtStyles(), loadTones()]);
  const L = brief.learning || {}, W = brief.writing || {}, S = brief.structure || {};
  const filled = (o) => Object.values(o || {}).some((v) => v && (!Array.isArray(v) || v.length));
  const part = (n, id, title, why, body, { optional = true, open = true } = {}) => optional ? `
    <details class="bsec" id="${id}" ${open ? "open" : ""}><summary><span class="bn">${n}</span><div class="bt"><h3>${title}</h3><p>${why}</p></div>
      <span class="bstat" data-stat="${id}"></span>${icon("chevR", "chev")}</summary><div class="bbody">${body}</div></details>` : `
    <section class="bsec" id="${id}"><div class="bhead"><span class="bn">${n}</span><div class="bt"><h3>${title}</h3><p>${why}</p></div></div><div class="bbody">${body}</div></section>`;
  const el = document.createElement("form");
  el.className = "brief";
  el.innerHTML = `
    <input type="hidden" name="type" value="storybook"><input type="hidden" name="paper" value="premium_color">
    ${part(1, "b-story", "The story", "What happens, for whom. The only part you must fill in.", `
      <div class="field"><label for="idea">The idea</label>
        <textarea class="input" id="idea" name="idea" rows="5" required placeholder="A shy hedgehog who is afraid of the dark learns the night is full of friends.">${esc(brief.idea)}</textarea>
        <span class="hint">Premise, main character, setting, how it ends if you know. The lesson goes in part 2.</span></div>
      <div class="form-grid">
        <div class="field"><label for="audience">Reader age</label><input class="input" id="audience" name="audience" value="${esc(brief.audience || "")}" placeholder="3–6"></div>
        <div class="field"><label for="language">Language</label><select class="input" id="language" name="language">${
          LANGS.map((l) => `<option value="${l}" ${langOf(brief.language) === l ? "selected" : ""}>${LANG_NATIVE[l]}</option>`).join("")}</select>
          <span class="hint">Every word in the book, pictures included, is written in this language.</span></div>
      </div>
      <div class="field" id="cast-field" hidden><span class="label">Characters from your library <span class="faint">· optional</span></span>
        <div class="cast" id="cast"></div>
        <span class="hint">Ticked characters are written into the story with their exact look, for a series.</span></div>
      <div class="field"><span class="label">Reference files <span class="faint">· optional</span></span>
        <div class="attach" id="attach">
          <div class="attach-list" id="attach-list"></div>
          <label class="btn"><input type="file" id="attach-in" accept=".pdf,.txt,.md,.docx,.png,.jpg,.jpeg,.webp,.gif,image/*" multiple hidden>${icon("file")}Attach files</label></div>
        <span class="hint">Notes, a draft, a story to adapt, sketches or style references (PDF, Word, text, Markdown, images).</span></div>`, { optional: false })}
    ${part(2, "b-learn", "What it teaches", "The lesson the story carries, and how it shows on the page. Empty: Claude asks.", `
      <div class="form-grid">
        <div class="field"><label for="l-topic">Topic</label>
          <input class="input" id="l-topic" name="learning.topic" value="${esc(L.topic || "")}" placeholder="Adjectives and their opposites"></div>
        <div class="field"><label for="l-targets">Target words or concepts</label>
          <input class="input" id="l-targets" name="learning.targets" value="${esc(L.targets || "")}" placeholder="chaud/froid, grand/petit… (Claude picks if empty)"></div>
        <div class="field full"><label for="l-explain">What the child should understand</label>
          <textarea class="input" id="l-explain" name="learning.explain" rows="2" placeholder="An adjective describes a noun; many have an opposite.">${esc(L.explain || "")}</textarea></div>
        <div class="field full"><label for="l-marking">How it's marked in the story</label>
          <textarea class="input" id="l-marking" name="learning.marking" rows="2" placeholder="The adjective in violet, its opposite in parentheses right after it.">${esc(L.marking || "")}</textarea>
          <span class="hint">Claude writes every story page by this rule; marked words print in the highlight style.</span></div>
      </div>`, { open: filled(L) })}
    ${part(3, "b-structure", "Pages & structure", "Which parts the book has, in what order: intro, story, exercises, closing.", `
      <div class="tpl-cards" id="tpls" role="radiogroup" aria-label="Structure"></div>
      <details class="ask-d" id="tpl-ask">
        <summary>${icon("sparkle")}<span id="tpl-ask-label">Or describe the structure you want</span>${icon("chevR", "chev")}</summary>
        <div class="ask-d-b"><textarea class="input" id="tpl-prompt" rows="2" aria-label="Describe the structure"></textarea>
        <div class="row between wrap gap3"><span class="faint xs">Claude builds the order for this book. You can still change it below and save it as a template.</span>
          <button type="button" class="btn sm" id="tpl-go">${icon("sparkle")}Build with Claude</button></div></div></details>
      <div class="field" id="len-field" style="max-width:360px"><label for="length">Length</label>
        <input class="input" id="length" name="length" value="${esc(brief.length || "")}" placeholder="32 pages · 8 chapters">
        <span class="hint">Claude plans the pages itself: no fixed exercise section.</span></div>
      <div id="tpl-body" hidden>
        <div class="row between wrap gap3"><span class="faint small" id="tpl-total"></span>
          <span class="row"><button type="button" class="btn sm ghost" id="sec-edit">${icon("edit")}Customize sections</button>
            <button type="button" class="btn sm ghost" id="tpl-save">${icon("copy")}Save as template</button></span></div>
        <div id="sec-flow" class="sec-flow"></div>
        <div id="sec-editor" class="stack" style="gap:10px" hidden>
          <div id="secs" class="secs"></div>
          <div class="row gap3 wrap"><select class="input" id="sec-add" name="_add" style="max-width:240px"><option value="">+ Add a section…</option></select></div></div>
        <div class="form-grid">
          <div class="field full"><label for="s-back">Back cover must include</label>
            <input class="input" id="s-back" name="structure.back_cover" value="${esc(S.back_cover || "")}" placeholder="Summary, learning goal, age 6–9, the activities, barcode space"></div>
          <div class="field full" id="coll-field"><label for="s-coll">Other books in this collection</label>
            <textarea class="input" id="s-coll" name="structure.collection" rows="2" placeholder="Les aventures de Zigooli: verbs (published) · Nina va à l'école: adjectives (coming soon)">${esc(S.collection || "")}</textarea>
            <span class="hint">Only these appear on the collection page. Nothing is invented.</span></div></div>
      </div>
      <div class="acts" id="acts"></div>`, { optional: false })}
    ${part(4, "b-voice", "Voice & look", "How it sounds and how it's drawn. Empty: Claude proposes.", `
      <div class="form-grid">
        <div class="field full"><span class="label">Tone <span class="faint">· pick one, or leave it to Claude</span></span>
          ${tonePicker(toneList, { name: "tone", id: "tone", value: brief.tone || "" })}</div>
        <div class="field full"><span class="label">Art style <span class="faint">· pick one, or leave it to Claude</span></span>
          ${stylePicker(styles, { name: "art", id: "art", value: brief.art || "" })}</div>
        <div class="field"><label for="w-by">Writing inspired by</label>
          <input class="input" id="w-by" name="writing.inspired_by" value="${esc(W.inspired_by || "")}" placeholder="An author whose style you like"></div>
        <div class="field"><label for="w-notes">Style notes</label>
          <input class="input" id="w-notes" name="writing.notes" value="${esc(W.notes || "")}" placeholder="Short rhyming lines, lots of dialogue"></div>
        <div class="field full"><label for="w-sample">A sample of the style</label>
          <textarea class="input" id="w-sample" name="writing.sample" rows="3" placeholder="Paste a passage. Claude takes the manner (rhythm, tone, humour), never the sentences.">${esc(W.sample || "")}</textarea></div>
      </div>`, { open: filled(W) || !!(brief.tone || brief.art) })}
    ${part(5, "b-print", "Cover & print", "Title and author on the cover, trim size, page numbers.", `
      <div class="form-grid">
        <div class="field"><label for="title">Working title</label><input class="input" id="title" name="title" value="${esc(brief.title || "")}" placeholder="Claude proposes one if empty"></div>
        <div class="field"><label for="author">Author on the cover</label><input class="input" id="author" name="author" value="${esc(brief.author ?? s.default_author)}" placeholder="Your name"></div>
        <div class="field"><label for="trim">Trim size</label><select class="input" id="trim" name="trim">${trims.map((t) => `<option ${t === (brief.trim || TYPES[type].trim) ? "selected" : ""}>${t}</option>`).join("")}</select></div>
        <div class="field"><span class="label">Page numbers</span>
          <label class="check" style="height:36px"><input type="checkbox" name="page_numbers" ${brief.page_numbers === false ? "" : "checked"}> Print a number on every page</label></div>
      </div>`, { open: false })}
    <div class="brief-foot row between"><span class="faint small">Only the idea is required. Next, Claude asks about what's still open (about 10 seconds).</span>
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
  wireStylePicker(el);
  api("GET", "/api/characters").then(({ characters: lib }) => {
    if (!lib.length) return;
    $("#cast-field", el).hidden = false;
    $("#cast", el).innerHTML = lib.map((c) => `<label class="castpick"><input type="checkbox" name="cast" value="${esc(c.name)}" ${(brief.cast || []).includes(c.name) ? "checked" : ""}>
      <img src="/api/characters/${encodeURIComponent(c.id)}.png" alt=""><span>${esc(c.name)}</span></label>`).join("");
  }).catch(() => {});
  const structure = structureEditor(el, S);
  // what each closed optional part holds, so it reads at a glance without opening it
  const val = (n) => (el.elements[n]?.value || "").trim();
  const stats = {
    "b-learn": () => val("learning.topic") || (val("learning.marking") ? "Marking rule set" : ""),
    "b-voice": () => [toneList.find((x) => x.tone === val("tone"))?.name || val("tone"), styles.find((x) => x.art === val("art"))?.name || val("art"), val("writing.inspired_by") && `like ${val("writing.inspired_by")}`].filter(Boolean).join(" · "),
    "b-print": () => [val("title") || "Title by Claude", val("trim"), el.page_numbers.checked ? "numbered" : "no numbers"].join(" · "),
  };
  const stat = () => Object.entries(stats).forEach(([id, f]) => {
    const t = f();
    $(`[data-stat="${id}"]`, el).innerHTML = id === "b-print" ? `<span class="faint">${esc(t)}</span>`
      : t ? `<span class="set">${icon("check")}${esc(t)}</span>` : `<span class="faint">Not set</span>`;
  });
  el.addEventListener("input", stat); el.addEventListener("change", stat); stat();
  el.addEventListener("submit", (e) => {
    e.preventDefault();
    const data = {};
    for (const [k, v] of new FormData(el)) {  // "learning.topic" -> data.learning.topic
      const [a, b] = k.split(".");
      if (b) (data[a] ||= {})[b] = v; else if (!k.startsWith("_")) data[k] = v;
    }
    data.structure = { ...(data.structure || {}), ...structure.value() };
    if (data.structure.sections.length) data.length = "";  // the template sets the length
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

// pages per phase, in order: a thin bar that shows a template's shape at a glance
function phaseBar(sections) {
  const on = sections.filter((x) => x.enabled !== false && Number(x.pages) > 0);
  const runs = [];
  for (const x of on) {
    const ph = x.phase || PHASE_OF[x.kind] || runs.at(-1)?.ph || "play";
    if (runs.at(-1)?.ph === ph) runs.at(-1).n += Number(x.pages); else runs.push({ ph, n: Number(x.pages) });
  }
  return `<div class="pbar">${runs.map((r) => `<i class="ph-${r.ph}" style="flex:${r.n}" title="${PHASES[r.ph]}: ${r.n} ${r.n === 1 ? "page" : "pages"}"></i>`).join("")}</div>`;
}

let kindsCache;
const getKinds = async () => (kindsCache ??= (await api("GET", "/api/templates")).kinds);

// part 3 of the brief: free, or a template, changed for this book only
function structureEditor(el, initial) {
  let kinds = {}, tpls = [], secs = (initial.sections || []).map((x) => ({ ...x }));
  let tplId = initial.template || (secs.length ? "_custom" : "");
  let draftName = "";
  const askLabel = () => {
    const on = !!secs.length;
    $("#tpl-ask-label", el).textContent = on ? "Change this structure, or describe a new one" : "Or describe the structure you want";
    $("#tpl-prompt", el).placeholder = on
      ? "e.g. Put the coloring pages before the games, add a maze, and make the story 24 pages."
      : "e.g. A note to parents, a 20-page story, 10 questions, then 2 coloring pages, a maze and a matching game. Solutions at the end.";
  };
  const host = $("#secs", el);
  const total = () => secs.filter((x) => x.enabled !== false).reduce((n, x) => n + (Number(x.pages) || 0), 0);
  const cards = () => {
    const opts = [{ id: "", name: "Free", description: "Claude plans the pages. Story first; no fixed exercise section." }, ...tpls];
    if (tplId === "_custom") opts.push({ id: "_custom", name: draftName || "This book's own", description: "Made for this book", sections: secs });
    $("#tpls", el).innerHTML = opts.map((t) => {
      const sel = t.id === tplId;
      const ss = t.id === tplId && t.id ? secs : t.sections || [];
      const n = ss.filter((x) => x.enabled !== false).reduce((a, x) => a + (Number(x.pages) || 0), 0);
      return `<label class="tpl-card ${sel ? "on" : ""}"><input type="radio" name="_tpl" value="${esc(t.id)}" ${sel ? "checked" : ""}>
        <span class="row between"><b>${esc(t.name)}</b><span class="faint xs">${t.id ? `${n} pages` : "any length"}</span></span>
        ${t.id ? phaseBar(ss) : `<div class="pbar"><i class="ph-story" style="flex:1"></i></div>`}
        <span class="faint xs">${esc(t.description || (t.audience ? `Ages ${t.audience}` : ""))}</span></label>`;
    }).join("");
    $$("[name=_tpl]", el).forEach((r) => (r.onchange = () => choose(r.value)));
    askLabel();
  };
  const draw = () => {
    const on = !!secs.length;
    $("#tpl-body", el).hidden = !on;
    $("#len-field", el).hidden = on;
    $("#coll-field", el).hidden = !secs.some((x) => x.kind === "collection" && x.enabled !== false);
    $("#tpl-total", el).textContent = on ? `${total()} interior pages, plus front and back cover. Hover a page for what Claude writes there.` : "";
    $("#sec-flow", el).innerHTML = bookFlow(secs, kinds);
    drawActs();
    host.innerHTML = secs.map((x, i) => `
      <div class="secrow ${x.enabled === false ? "off" : ""}" data-i="${i}">
        <input type="checkbox" data-k="enabled" ${x.enabled === false ? "" : "checked"} aria-label="Include ${esc(kinds[x.kind]?.label || x.kind)}">
        <span class="sk-label" title="${esc(kinds[x.kind]?.guide || "")}"><i class="dotph ph-${PHASE_OF[x.kind] || "play"}"></i>${esc(kinds[x.kind]?.label || x.kind)}</span>
        <input class="input" type="number" min="0" max="60" data-k="pages" value="${Number(x.pages) || 0}" aria-label="Pages">
        <input class="input" data-k="title" value="${esc(x.title || "")}" placeholder="Title on the page">
        <input class="input" data-k="note" value="${esc(x.note || "")}" placeholder="Note for Claude">
        <span class="row"><button type="button" class="btn icon ghost" data-mv="-1" aria-label="Move up">↑</button>
          <button type="button" class="btn icon ghost" data-mv="1" aria-label="Move down">↓</button>
          <button type="button" class="btn icon ghost" data-rm aria-label="Remove">${icon("x")}</button></span></div>`).join("");
    $$(".secrow", host).forEach((row) => {
      const i = Number(row.dataset.i);
      $$("[data-k]", row).forEach((inp) => (inp.oninput = () => {
        const k = inp.dataset.k;
        secs[i][k] = k === "enabled" ? inp.checked : k === "pages" ? Number(inp.value) : inp.value;
        if (k !== "title" && k !== "note") { $("#sec-flow", el).innerHTML = bookFlow(secs, kinds); row.classList.toggle("off", secs[i].enabled === false);
          $("#tpl-total", el).textContent = `${total()} interior pages, plus front and back cover.`; cards(); }
      }));
      $$("[data-mv]", row).forEach((b) => (b.onclick = () => {
        const j = i + Number(b.dataset.mv);
        if (j < 0 || j >= secs.length) return;
        [secs[i], secs[j]] = [secs[j], secs[i]]; draw();
      }));
      $("[data-rm]", row).onclick = () => { secs.splice(i, 1); draw(); };
    });
    cards();
  };
  // the games & exercises a structure can have, what each page is, and who makes it
  let actsOpen = false;
  const drawActs = () => {
    const box = $("#acts", el);
    const on = !!secs.length;
    const count = (k) => secs.filter((x) => x.kind === k && x.enabled !== false).reduce((n, x) => n + (Number(x.pages) || 0), 0);
    const added = ACTIVITIES.filter(([k]) => count(k)).length;
    box.innerHTML = `<details class="acts-d" ${actsOpen ? "open" : ""}><summary><span><h4>Games &amp; exercises you can add</h4>${added ? `<span class="set xs">${icon("check")}${added} added</span>` : ""}</span>${icon("chevR", "chev")}</summary>
        <p class="faint xs">${on ? "Add any of these to this book. The answers to every game print on the solutions page automatically."
          : "These come with a structure: pick one above (or describe one), then add games here. A free book gets games Claude invents."}</p></div>
      <div class="act-grid">${ACTIVITIES.map(([k, desc, who]) => {
        const n = count(k);
        return `<div class="act ph-${PHASE_OF[k] || "play"} ${n ? "in" : ""}">${pageSketch(k)}
          <div class="act-t"><b>${esc(kinds[k]?.label || k.replace(/_/g, " "))}</b>
            <span class="xs">${esc(desc)}</span>
            <span class="act-who ${who}">${ACT_WHO[who]}</span>
            <span class="row between"><span class="faint xs">${n ? `${n} page${n > 1 ? "s" : ""} in this book` : ""}</span>
              <button type="button" class="btn sm ghost" data-act="${k}" ${on ? "" : "disabled"}>+ Add</button></span></div></div>`;
      }).join("")}</div></details>`;
    $("details", box).ontoggle = (e) => { actsOpen = e.currentTarget.open; };
    $$("[data-act]", box).forEach((b) => (b.onclick = () => {
      const at = secs.findIndex((x) => PHASE_OF[x.kind] === "end");  // games go before the closing pages
      secs.splice(at < 0 ? secs.length : at, 0, { kind: b.dataset.act, pages: 1, enabled: true });
      tplId = "_custom";
      draw();
      toast(`${kinds[b.dataset.act]?.label || b.dataset.act} added before the closing pages`);
    }));
  };
  const choose = (id) => {
    tplId = id;
    const t = tpls.find((x) => x.id === id);
    if (id !== "_custom") secs = t ? t.sections.map((x) => ({ ...x })) : [];
    if (t?.back_cover && !$("#s-back", el).value) $("#s-back", el).value = t.back_cover;
    if (t?.audience && el.audience && !el.audience.value) el.audience.value = t.audience;
    draw();
  };
  $("#sec-edit", el).onclick = (e) => {
    const ed = $("#sec-editor", el);
    ed.hidden = !ed.hidden;
    e.currentTarget.innerHTML = ed.hidden ? `${icon("edit")}Customize sections` : `${icon("check")}Done`;
  };
  $("#sec-add", el).onchange = (e) => {
    if (!e.target.value) return;
    secs.push({ kind: e.target.value, pages: 1, enabled: true }); e.target.value = ""; draw();
  };
  $("#tpl-go", el).onclick = (e) => {
    const p = $("#tpl-prompt", el).value.trim();
    if (!p) { $("#tpl-prompt", el).focus(); return toast("Write what structure you want first", true); }
    busy(e.currentTarget, "Claude is arranging…", async () => {
      const cur = tpls.find((x) => x.id === tplId);
      const r = await api("POST", "/api/templates/draft", { prompt: p, current: secs.length ? { name: cur?.name || draftName, sections: secs } : null });
      secs = r.sections.map((x) => ({ ...x, enabled: true }));
      draftName = r.name || draftName;
      tplId = "_custom";
      $("#tpl-prompt", el).value = "";
      draw();
      $("#tpl-body", el).scrollIntoView({ block: "nearest", behavior: "smooth" });
      toast(`Built “${draftName || "your structure"}” for this book. Save it as a template to reuse it.`);
    });
  };
  $("#tpl-save", el).onclick = async () => {
    const name = prompt("Name of the template", tpls.find((x) => x.id === tplId)?.name || draftName || "");
    if (!name) return;
    try {
      const t = await api("POST", "/api/templates", { name, sections: secs, back_cover: $("#s-back", el).value || undefined,
        audience: el.audience?.value || undefined });
      tpls = [...tpls.filter((x) => x.id !== t.id), t]; tplId = t.id; draw(); toast(`Saved “${name}”. Every new book can start from it.`);
    } catch (e) { toast(e.message, true); }
  };
  api("GET", "/api/templates").then((r) => {
    kinds = kindsCache = r.kinds; tpls = r.templates;
    if (tplId && tplId !== "_custom" && !tpls.some((t) => t.id === tplId)) tplId = "_custom";
    $("#sec-add", el).innerHTML = `<option value="">+ Add a section…</option>` +
      Object.entries(kinds).map(([k, v]) => `<option value="${k}">${esc(v.label)}</option>`).join("");
    draw();
  }).catch(() => {});
  draw();
  return { value: () => (secs.length ? { template: tplId === "_custom" ? "" : tplId, sections: secs } : { template: "", sections: [] }) };
}

// ---------- book flow: the order of a book's parts, with a small sketch of each kind of page ----------
const PHASES = { intro: "Before the story", story: "The story", learn: "Learning pages", play: "Exercises & games", end: "Closing pages" };
const PHASE_OF = {
  title: "intro", dedication: "intro", parents_note: "intro", story: "story",
  comprehension: "learn", theme_intro: "learn", reference: "learn",
  main_game: "play", coloring: "play", matching: "play", fill_in: "play", odd_one_out: "play", maze: "play",
  observation: "play", guided_drawing: "play", imagination: "play", final_challenge: "play",
  solutions: "end", collection: "end", copyright: "end", the_end: "end", about: "end",
};
// the brief's catalog of games & exercises: [kind, what the page is, who makes it]
const ACTIVITIES = [
  ["main_game", "The main exercise on the story's topic, with room to write.", "app"],
  ["matching", "Two shuffled columns; the child draws a line between partners.", "app"],
  ["fill_in", "Sentences or sums with a blank or a line for the answer.", "app"],
  ["odd_one_out", "Rows of tiles; the child circles the one that doesn't belong.", "app"],
  ["maze", "A maze that always has a way through, the hero at the start.", "app"],
  ["final_challenge", "A last challenge and a certificate for the child's name and date.", "app"],
  ["comprehension", "Ten questions about the story, answered out loud.", "text"],
  ["coloring", "Black-and-white line art of a new scene to color.", "art"],
  ["observation", "A busy picture with a list of things to find in it.", "art"],
  ["guided_drawing", "An instruction and a big empty frame to draw in.", "blank"],
  ["imagination", "The child invents and draws their own scene or character.", "blank"],
];
const ACT_WHO = { app: "Laid out by the app · answers always match", art: "Illustrated", blank: "Blank page to draw", text: "Text page" };
const KIND_LABEL = { title: "Title page", dedication: "Dedication", copyright: "Copyright", the_end: "The End", about: "About the author" };

// 30x40 page sketches: lines in ink, the part that makes the page what it is in accent
function pageSketch(kind) {
  const L = (y, x1 = 6, x2 = 24) => `<line x1="${x1}" y1="${y}" x2="${x2}" y2="${y}"/>`;
  const lines = (y, n, gap = 3, x1 = 6, x2 = 24) => Array.from({ length: n }, (_, i) => L(y + i * gap, x1, i === n - 1 ? x2 - 5 : x2)).join("");
  const head = `<line class="a" x1="9" y1="6" x2="21" y2="6" stroke-width="1.6"/>`;
  const s = {
    cover: `<rect class="af" x="0" y="0" width="30" height="40"/><line class="w" x1="8" y1="9" x2="22" y2="9" stroke-width="2"/><circle class="w" cx="15" cy="24" r="6"/>`,
    title: `<circle class="a" cx="15" cy="15" r="6"/>${L(26, 9, 21)}${L(29, 11, 19)}`,
    copyright: `<circle cx="15" cy="27" r="2.2"/>${lines(31, 2, 2.5, 8, 22)}`,
    dedication: `<path class="a" d="M15 17.5c-3-2.4-4.5-3.8-4.5-5.4a2.2 2.2 0 0 1 4.5-.6 2.2 2.2 0 0 1 4.5.6c0 1.6-1.5 3-4.5 5.4z"/>${L(23, 9, 21)}`,
    parents_note: `${head}${lines(11, 8)}`,
    story: `<rect class="af" x="4" y="4" width="22" height="18" rx="1.5"/><path class="w" d="M4 19l6-6 5 5 3-3 8 7"/><circle class="w" cx="20" cy="9" r="2"/>${lines(27, 3)}`,
    comprehension: `${head}${[0, 1, 2, 3, 4].map((i) => `<circle class="a" cx="7" cy="${12 + i * 5}" r="1.1"/>${L(12 + i * 5, 10, 24)}`).join("")}`,
    theme_intro: `<circle class="a" cx="15" cy="11" r="4.5"/><line class="a" x1="13.5" y1="17" x2="16.5" y2="17"/>${lines(23, 4)}`,
    reference: `${head}<rect x="5" y="11" width="20" height="22" rx="1"/>${L(16.5, 5, 25)}${L(22, 5, 25)}${L(27.5, 5, 25)}<line x1="15" y1="11" x2="15" y2="33"/>`,
    main_game: `${head}${lines(12, 2)}<rect class="a" x="6" y="20" width="18" height="5" rx="1"/><rect class="a" x="6" y="28" width="18" height="5" rx="1"/>`,
    coloring: `${head}<path class="a" d="M15 12l2.2 4.5 5 .7-3.6 3.5.9 5-4.5-2.4-4.5 2.4.9-5-3.6-3.5 5-.7z"/><path class="a" d="M7 35c3-4 6-4 8-1s5 3 8-1"/>`,
    matching: `${head}${[0, 1, 2, 3].map((i) => `<circle class="af" cx="7" cy="${13 + i * 6}" r="1.4"/><circle class="af" cx="23" cy="${13 + i * 6}" r="1.4"/>`).join("")}<path class="a" d="M8.5 13L21.5 25M8.5 19L21.5 13M8.5 25L21.5 31M8.5 31L21.5 19"/>`,
    fill_in: `${head}${[0, 1, 2, 3, 4].map((i) => `${L(13 + i * 5, 6, 14)}<line class="a" x1="16" y1="${13 + i * 5}" x2="24" y2="${13 + i * 5}" stroke-dasharray="1.5 1"/>`).join("")}`,
    odd_one_out: `${head}${[0, 1, 2].map((r) => [0, 1, 2].map((c) => `<circle cx="${8 + c * 7}" cy="${14 + r * 8}" r="2.3"/>`).join("")).join("")}<circle class="a" cx="22" cy="14" r="3.4"/><circle class="a" cx="8" cy="22" r="3.4"/><circle class="a" cx="15" cy="30" r="3.4"/>`,
    maze: `${head}<rect x="5" y="10" width="20" height="25"/><path d="M5 15h10M20 10v10M10 20h10v5M5 25h5M15 30h10M10 25v5"/><path class="a" d="M7.5 10v2.5h10v5h5v10h-5v5h5v5" stroke-dasharray="1.4 1"/>`,
    observation: `${head}<rect x="5" y="10" width="20" height="20" rx="1"/><path d="M5 25l5-5 4 4 4-6 7 7"/><circle class="a" cx="18" cy="17" r="4"/><line class="a" x1="21" y1="20" x2="24.5" y2="23.5" stroke-width="1.6"/>`,
    guided_drawing: `${head}${L(11, 8, 22)}<rect class="a" x="5" y="15" width="20" height="20" rx="3" stroke-dasharray="2 1.5"/><path d="M12 30l7-7 2 2-7 7h-2z"/>`,
    imagination: `${head}${L(11, 8, 22)}<rect class="a" x="5" y="15" width="20" height="20" rx="3" stroke-dasharray="2 1.5"/><path class="a" d="M15 20.5l1.2 2.5 2.8.4-2 2 .5 2.7-2.5-1.3-2.5 1.3.5-2.7-2-2 2.8-.4z"/>`,
    final_challenge: `${head}${lines(11, 2)}<rect class="a" x="5" y="18" width="20" height="16" rx="1.5"/><circle class="af" cx="15" cy="23.5" r="2.4"/>${L(29, 9, 21)}${L(31.5, 11, 19)}`,
    solutions: `${head}${[0, 1, 2, 3, 4].map((i) => `<path class="a" d="M6 ${12.5 + i * 5}l1.3 1.3 2.4-2.6"/>${L(13 + i * 5, 12, 24)}`).join("")}`,
    collection: `${head}${[0, 1, 2].map((i) => `<rect class="${i === 1 ? "af" : "a"}" x="${5 + i * 7}" y="13" width="5.5" height="8" rx=".6"/>`).join("")}${lines(26, 3)}`,
    the_end: `<path class="a" d="M15 13l1.8 3.6 4 .6-2.9 2.8.7 4-3.6-1.9-3.6 1.9.7-4-2.9-2.8 4-.6z"/>${L(29, 10, 20)}`,
    about: `<circle class="a" cx="15" cy="12" r="4"/><path class="a" d="M8.5 22c1.5-3 4-4 6.5-4s5 1 6.5 4"/>${lines(26, 3)}`,
  };
  return `<svg class="psk" viewBox="0 0 30 40" aria-hidden="true"><rect class="pg" x=".5" y=".5" width="29" height="39" rx="1.5"/>${s[kind] || `${head}${lines(11, 7)}`}</svg>`;
}

// sections: [{kind, pages, title?, phase?, enabled?}]. Consecutive sections of one phase share a box.
function bookFlow(sections, kinds = {}, { covers = true, ranges = true } = {}) {
  const on = sections.filter((x) => x.enabled !== false && Number(x.pages) > 0);
  if (!on.length) return "";
  const groups = [];
  let n = 1;
  for (const x of on) {
    const ph = x.phase || PHASE_OF[x.kind] || groups.at(-1)?.phase || "play";
    if (groups.at(-1)?.phase !== ph) groups.push({ phase: ph, items: [], from: n, pages: 0 });
    const g = groups.at(-1);
    g.items.push(x); g.pages += Number(x.pages); n += Number(x.pages);
  }
  const label = (x) => x.title || kinds[x.kind]?.label || KIND_LABEL[x.kind] || x.kind.replace(/_/g, " ");
  const tile = (x) => `<div class="ftile ${x.pages > 1 ? "stack" : ""}" title="${esc(label(x))}${kinds[x.kind]?.guide ? ` · ${esc(kinds[x.kind].guide)}` : ""}">
      ${pageSketch(x.kind)}${x.pages > 1 ? `<span class="fcount">×${x.pages}</span>` : ""}<span class="fname">${esc(label(x))}</span></div>`;
  const cover = (t) => `<div class="fgroup cover"><div class="fhead"><b>${t}</b></div><div class="ftiles"><div class="ftile">${pageSketch("cover")}</div></div></div>`;
  return `<div class="flow">${covers ? cover("Front cover") : ""}${groups.map((g) => `
    <div class="fgroup ph-${g.phase}"><div class="fhead"><b>${PHASES[g.phase]}</b><span>${!ranges ? `${g.pages} ${g.pages === 1 ? "page" : "pages"}` : g.pages === 1 ? `p. ${g.from}` : `p. ${g.from}–${g.from + g.pages - 1}`}</span></div>
      <div class="ftiles">${g.items.map(tile).join("")}</div></div>`).join("")}${covers ? cover("Back cover") : ""}</div>`;
}

// ---------- templates library ----------
// the simple flow: one numbered step per section, in reading order, with its pages
function simpleFlow(sections, kinds = {}) {
  const on = sections.filter((x) => x.enabled !== false && Number(x.pages) > 0);
  if (!on.length) return `<p class="faint small" style="margin:0">No sections yet.</p>`;
  let n = 1;
  const label = (x) => x.title || kinds[x.kind]?.label || KIND_LABEL[x.kind] || x.kind.replace(/_/g, " ");
  const steps = on.map((x, i) => {
    const p = Number(x.pages), rng = p === 1 ? `p. ${n}` : `p. ${n}–${n + p - 1}`;
    n += p;
    return `<li class="sf-step ph-${PHASE_OF[x.kind] || "play"}" title="${esc(kinds[x.kind]?.guide || "")}">
      <span class="sf-n">${i + 1}</span>${pageSketch(x.kind)}
      <span class="sf-t"><b>${esc(label(x))}</b><span>${rng}${p > 1 ? ` · ${p} pages` : ""}</span></span></li>`;
  });
  const used = [...new Set(on.map((x) => PHASE_OF[x.kind] || "play"))];
  return `<div class="sf">${phaseBar(on)}
    <div class="sf-legend">${used.map((ph) => `<span><i class="dotph ph-${ph}"></i>${PHASES[ph]}</span>`).join("")}</div>
    <ol class="sf-steps">${steps.join("")}</ol></div>`;
}

async function templateLibrary(openId) {
  const { templates: list, kinds } = await api("GET", "/api/templates");
  kindsCache = kinds;
  view.innerHTML = `<div class="page">
    <div class="head"><div><h1>Templates</h1><p class="sub">The order of a book's parts and how many pages each gets.
      Pick one in a new book's brief. Edit one here, or describe a new order and Claude builds it.</p></div>
      <button class="btn primary" id="tpl-new">${icon("plus")}New template</button></div>
    <div class="stack" id="tpl-list">${list.map((t) => `
      <div class="card tpl-item" data-id="${esc(t.id)}"><div class="card-b stack" style="gap:12px">
        <div class="row between"><div><h3 style="margin:0">${esc(t.name)}</h3>
          <span class="faint xs">${t.pages} interior pages · ${t.sections.filter((x) => x.enabled !== false && x.pages > 0).length} parts${t.audience ? ` · ages ${esc(t.audience)}` : ""}${t.builtin ? (t.saved ? " · built in, edited" : " · built in") : ""}</span></div>
          <span class="row"><button class="btn sm" data-edit>${icon("edit")}Edit</button>
          ${t.builtin && !t.saved ? "" : `<button class="btn sm ghost" data-del>${icon("trash")}${t.builtin ? "Restore original" : "Remove"}</button>`}</span></div>
        ${t.description ? `<p class="muted small" style="margin:0">${esc(t.description)}</p>` : ""}
        ${simpleFlow(t.sections, kinds)}</div></div>`).join("")}</div></div>`;
  const byId = Object.fromEntries(list.map((t) => [t.id, t]));
  $$(".tpl-item").forEach((card) => {
    const t = byId[card.dataset.id];
    $("[data-edit]", card).onclick = () => templateEditor(card, t, kinds);
    const del = $("[data-del]", card);
    if (del) del.onclick = async () => {
      const restore = t.builtin;
      if (!(await modal({ title: restore ? `Restore ${esc(t.name)}?` : `Remove ${esc(t.name)}?`,
        body: restore ? "Your changes are dropped and the original comes back. Books already written keep their structure."
          : "Books already written keep their structure.", confirm: restore ? "Restore" : "Remove", danger: !restore }))) return;
      try { await api("DELETE", `/api/templates/${encodeURIComponent(t.id)}`); toast(restore ? "Restored" : "Removed"); } catch (e) { toast(e.message, true); }
      templateLibrary();
    };
  });
  $("#tpl-new").onclick = () => {
    if ($("#tpl-list .tpl-item[data-id='']")) return;
    const card = document.createElement("div");
    card.className = "card tpl-item"; card.dataset.id = "";
    $("#tpl-list").prepend(card);
    templateEditor(card, null, kinds);
  };
  if (openId && byId[openId]) $(`.tpl-item[data-id="${CSS.escape(openId)}"]`)?.scrollIntoView({ block: "center" });
}

// edit a template in place: its name, its order (by hand or by asking Claude), then save
function templateEditor(card, t, kinds) {
  const isNew = !t;
  const name = t?.name || "", desc = t?.description || "";
  let secs = (t?.sections || []).map((x) => ({ ...x }));
  const kindOpts = (sel) => Object.entries(kinds).map(([k, v]) => `<option value="${k}" ${k === sel ? "selected" : ""}>${esc(v.label)}</option>`).join("");
  card.classList.add("editing");
  card.innerHTML = `<div class="card-b stack" style="gap:16px">
    <div class="form-grid te-grid">
      <div class="field"><label for="te-name">Name</label><input class="input" id="te-name" value="${esc(name)}" placeholder="e.g. Short activity book"></div>
      <div class="field"><label for="te-desc">Description</label><input class="input" id="te-desc" value="${esc(desc)}" placeholder="One line on what this structure is for"></div></div>
    <div class="te-ask">
      <label for="te-prompt"><b>${icon("sparkle")}${isNew ? "Describe the order you want" : "Tell Claude what to change"}</b></label>
      <textarea class="input" id="te-prompt" rows="2" placeholder="${isNew
        ? "e.g. A note to parents, a 20-page story, 10 questions, then 2 coloring pages, a maze and a matching game. Solutions at the end."
        : "e.g. Put the coloring pages before the games, add a maze, and make the story 24 pages."}"></textarea>
      <div class="row between"><span class="faint xs">Claude rewrites the order below. Nothing is saved until you press Save.</span>
        <button type="button" class="btn sm" id="te-go">${icon("sparkle")}${isNew ? "Build the order" : "Apply"}</button></div></div>
    <div><div class="row between" style="margin-bottom:8px"><b class="small">Flow</b><span class="faint xs" id="te-total"></span></div>
      <div id="te-flow"></div></div>
    <details class="te-hand" ${isNew ? "" : "open"}><summary class="small"><b>Change by hand</b> <span class="faint">· drag to reorder</span></summary>
      <div class="stack" style="gap:6px;margin-top:8px" id="te-rows"></div>
      <select class="input" id="te-add" style="max-width:240px;margin-top:8px"><option value="">+ Add a part…</option>${kindOpts("")}</select></details></div>
    <div class="card-f row between">
      <span class="faint xs">${t?.builtin ? "Saving keeps your own copy. “Restore original” brings back the built-in one." : ""}</span>
      <span class="row"><button type="button" class="btn ghost" id="te-cancel">Cancel</button>
        ${isNew ? "" : `<button type="button" class="btn" id="te-copy">${icon("copy")}Save as new</button>`}
        <button type="button" class="btn primary" id="te-save">${icon("check")}Save</button></span></div>`;
  const total = () => secs.filter((x) => x.enabled !== false).reduce((n, x) => n + (Number(x.pages) || 0), 0);
  const drawFlow = () => {
    $("#te-flow", card).innerHTML = simpleFlow(secs, kinds);
    $("#te-total", card).textContent = secs.length ? `${total()} interior pages, plus covers` : "";
  };
  let dragFrom = null;
  const drawRows = () => {
    $("#te-rows", card).innerHTML = secs.map((x, i) => `
      <div class="te-row ${x.enabled === false ? "off" : ""}" draggable="true" data-i="${i}">
        <span class="te-grip" aria-hidden="true">⋮⋮</span><span class="sf-n">${i + 1}</span>
        <select class="input" data-k="kind" aria-label="Part">${kindOpts(x.kind)}</select>
        <input class="input" type="number" min="0" max="60" data-k="pages" value="${Number(x.pages) || 0}" aria-label="Pages" title="Pages">
        <input class="input" data-k="title" value="${esc(x.title || "")}" placeholder="Title on the page (optional)">
        <span class="row"><button type="button" class="btn icon ghost" data-mv="-1" aria-label="Move up">↑</button>
          <button type="button" class="btn icon ghost" data-mv="1" aria-label="Move down">↓</button>
          <button type="button" class="btn icon ghost" data-rm aria-label="Remove">${icon("x")}</button></span></div>`).join("");
    $$(".te-row", card).forEach((row) => {
      const i = Number(row.dataset.i);
      $$("[data-k]", row).forEach((inp) => (inp.oninput = () => {
        const k = inp.dataset.k;
        secs[i][k] = k === "pages" ? Number(inp.value) : inp.value;
        drawFlow();
      }));
      $$("[data-mv]", row).forEach((b) => (b.onclick = () => move(i, i + Number(b.dataset.mv))));
      $("[data-rm]", row).onclick = () => { secs.splice(i, 1); draw(); };
      row.ondragstart = (e) => { dragFrom = i; row.classList.add("dragging"); e.dataTransfer.effectAllowed = "move"; };
      row.ondragend = () => { dragFrom = null; row.classList.remove("dragging"); };
      row.ondragover = (e) => { if (dragFrom !== null) { e.preventDefault(); row.classList.add("over"); } };
      row.ondragleave = () => row.classList.remove("over");
      row.ondrop = (e) => { e.preventDefault(); row.classList.remove("over"); if (dragFrom !== null) move(dragFrom, i); };
    });
  };
  const move = (i, j) => {
    if (i === j || j < 0 || j >= secs.length) return;
    const [x] = secs.splice(i, 1); secs.splice(j, 0, x); draw();
  };
  const draw = () => { drawFlow(); drawRows(); };
  $("#te-add", card).onchange = (e) => {
    if (!e.target.value) return;
    secs.push({ kind: e.target.value, pages: 1, enabled: true }); e.target.value = ""; draw();
  };
  $("#te-go", card).onclick = (e) => {
    const prompt = $("#te-prompt", card).value.trim();
    if (!prompt) { $("#te-prompt", card).focus(); return toast("Write what order you want first", true); }
    busy(e.currentTarget, "Claude is arranging…", async () => {
      const r = await api("POST", "/api/templates/draft", { prompt, current: secs.length ? { name: $("#te-name", card).value, sections: secs } : null });
      secs = r.sections.map((x) => ({ ...x, enabled: true }));
      if (!$("#te-name", card).value.trim()) $("#te-name", card).value = r.name || "";
      if (!$("#te-desc", card).value.trim()) $("#te-desc", card).value = r.description || "";
      $("#te-prompt", card).value = "";
      draw(); toast("Order updated. Check it, then Save.");
    });
  };
  const save = (asNew) => async (e) => {
    const nm = $("#te-name", card).value.trim();
    if (!nm) { $("#te-name", card).focus(); return toast("Give the template a name", true); }
    if (!secs.some((x) => x.enabled !== false && Number(x.pages) > 0)) return toast("Add at least one part with pages", true);
    if (asNew && t && nm === t.name) { $("#te-name", card).focus(); return toast("Give the copy a different name", true); }
    await busy(e.currentTarget, "Saving…", async () => {
      const body = { ...(t || {}), name: nm, description: $("#te-desc", card).value.trim(), sections: secs };
      delete body.pages; delete body.builtin; delete body.saved;
      if (asNew || isNew) delete body.id;
      if (!body.id && list().includes(slugOf(nm))) throw new Error(`There is already a template called “${nm}”. Pick another name.`);
      const r = await api("POST", "/api/templates", body);
      toast(`Saved “${nm}”`);
      templateLibrary(r.id);
    });
  };
  const slugOf = (s) => s.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 40) || "template";
  const list = () => $$(".tpl-item", document).map((c) => c.dataset.id).filter(Boolean);
  $("#te-save", card).onclick = save(false);
  if (!isNew) $("#te-copy", card).onclick = save(true);
  $("#te-cancel", card).onclick = () => templateLibrary(t?.id);
  voiceify(card);
  draw();
  (isNew ? $("#te-prompt", card) : $("#te-name", card)).focus();
  card.scrollIntoView({ block: "nearest" });
}

// ---------- book wizard ----------
async function bookView(slug, step) {
  const b = await api("GET", `/api/books/${slug}`);
  const st = b.state;
  // "preview" was its own step before it merged into Art & build; old links and saved state land there
  const saved = st.step === "preview" ? "art" : st.step;
  if (step === "preview") step = "art";
  const reached = Math.max(STEPS.findIndex(([k]) => k === saved), b.yaml ? 3 : 0, b.last_build ? 4 : 0, b.last_build === "real" ? 5 : 0);
  step ||= saved || (b.yaml ? "manuscript" : "brief");
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
    const where = "art";
    if (step !== where) $("#step").insertAdjacentHTML("beforebegin", `<div class="job-banner">${note("info",
      `<span class="spin"></span> ${esc(JOB_LABELS[b.job_kind] || "A job")} is running in the background. <a href="#/book/${slug}/${where}">Watch progress</a>`)}</div>`);
  }
  const steps = { brief: stepBrief, questions: stepQuestions, outline: stepOutline, manuscript: stepManuscript,
    art: stepArt, control: stepControl, publish: stepPublish };
  await steps[step]($("#step"), b, slug);
}

const stepHead = (title, sub, right = "") =>
  `<div class="step-head row between"><div><h2>${title}</h2><p>${sub}</p></div>${right}</div>`;

async function stepBrief(host, b, slug) {
  host.innerHTML = stepHead("Brief", "What the book is about. Changing it makes Claude ask its questions again.");
  host.append(await briefForm(slug, b.state.brief || {}, b.sources || []));
}

async function stepQuestions(host, b, slug) {
  const qs = b.state.questions;
  const [styles, toneList] = await Promise.all([qs?.some(isArtQuestion) ? loadArtStyles() : [], qs?.some(isToneQuestion) ? loadTones() : []]);
  if (!qs) {
    host.innerHTML = stepHead("Questions", "Claude asks what it needs to know before outlining.") +
      `<div class="card"><div class="empty"><div class="ico">${icon("sparkle")}</div><p>Claude hasn't asked its questions yet.</p>
       <button class="btn primary" id="ask">${icon("sparkle")}Ask Claude</button></div></div>`;
    $("#ask").onclick = (e) => busy(e.currentTarget, "Thinking…", async () => { await api("POST", `/api/books/${slug}/claude/questions`); route(); });
    return;
  }
  const answers = b.state.answers || {};
  host.innerHTML = stepHead("A few questions", "Only what your brief leaves open. Pick a suggestion or write your own; leave one blank and Claude decides.") + `
    ${briefRecap(b.state.brief || {}, slug)}
    <div class="card"><div class="card-b" id="qs">${qs.map((q, i) => `
      <div class="q" data-id="${esc(q.id)}"><span class="n">${i + 1}</span><div>
        <div class="qt">${esc(q.question)}</div>${q.why ? `<div class="qwhy">${esc(q.why)}</div>` : ""}
        ${styles.length && isArtQuestion(q) ? stylePicker(styles, { value: answers[q.id] || "", label: q.question })
          : toneList.length && isToneQuestion(q) ? tonePicker(toneList, { value: answers[q.id] || "", label: q.question }) : `
        ${q.options?.length ? `<div class="chips">${q.options.map((o) => `<button type="button" class="chip ${answers[q.id] === o ? "on" : ""}">${esc(o)}</button>`).join("")}</div>` : ""}
        <input class="input" aria-label="${esc(q.question)}" value="${esc(answers[q.id] || "")}" placeholder="Your answer">`}</div></div>`).join("")}</div>
      <div class="card-f row between"><a class="btn ghost" href="#/book/${slug}/brief">${icon("edit")}Edit brief</a>
        <button class="btn primary" id="next">${icon("sparkle")}Write the outline</button></div></div>`;
  $$(".q").forEach((q) => {
    const input = $("input", q);
    $$(".chip", q).forEach((c) => (c.onclick = () => { $$(".chip", q).forEach((x) => x.classList.remove("on")); c.classList.add("on"); input.value = c.textContent; }));
    input.oninput = () => $$(".chip", q).forEach((x) => x.classList.toggle("on", x.textContent === input.value));
  });
  voiceify(host);
  wireStylePicker(host);
  $("#next").onclick = (e) => busy(e.currentTarget, "Outlining… about 30 s", async () => {
    const ans = Object.fromEntries($$(".q").map((q) => [q.dataset.id, $("input", q).value.trim()]).filter(([, v]) => v));
    await api("POST", `/api/books/${slug}/claude/outline`, { answers: ans });
    location.hash = `#/book/${slug}/outline`;
  });
}

// what the brief already settles, shown above Claude's questions so they read as the gaps, not a repeat
function briefRecap(br, slug) {
  const L = br.learning || {}, W = br.writing || {};
  const secs = (br.structure?.sections || []).filter((x) => x.enabled !== false);
  const n = secs.reduce((a, x) => a + (Number(x.pages) || 0), 0);
  const items = [
    ["Age", br.audience], ["Language", br.language],
    ["Teaches", L.topic], ["Marking", L.marking && "set"],
    ["Structure", secs.length ? `${n} pages, ${secs.length} sections` : br.length || "free"],
    ["Tone", br.tone], ["Art", br.art], ["Style", W.inspired_by || W.notes],
    ["Characters", (br.cast || []).join(", ")],
  ].filter(([, v]) => v);
  return `<div class="recap"><span class="faint xs">Claude already knows</span>${items.map(([k, v]) =>
    `<span class="rk"><b>${k}</b> ${esc(v)}</span>`).join("")}<a class="xs" href="#/book/${slug}/brief">Edit brief</a></div>`;
}

function stepOutline(host, b, slug) {
  const outline = b.state.outline;
  if (!outline) { host.innerHTML = stepHead("Outline", "") + note("info", `Answer Claude's questions first. <a href="#/book/${slug}/questions">Go to questions</a>`); return; }
  const secs = b.state.brief?.structure?.sections || [];
  host.innerHTML = stepHead("Outline", "The plan for the book. Approve it, ask for changes, or edit it yourself.") + `
    ${secs.length ? `<div class="card" style="margin-bottom:var(--s5)"><div class="card-b"><div id="o-flow">${bookFlow(secs)}</div></div></div>` : ""}
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
  if (secs.length) getKinds().then((k) => ($("#o-flow").innerHTML = bookFlow(secs, k))).catch(() => {});
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

function pageCard(p, i) {
  const txt = esc(p.text).replace(/\[\[(.+?)\]\]/gs, '<mark class="hl">$1</mark>');
  return `<div class="pg" id="pg-${i + 1}"><div class="no"><b>p${String(i + 1).padStart(2, "0")}</b>${p.layout ? `<span class="tag">${esc(p.layout.replace("_", " "))}</span>` : ""}
    <button class="btn sm ghost" data-redopage="${i + 1}" title="Tell Claude what to change on this page">${icon("refresh")}Redo</button></div><div>
    ${p.chapter ? `<div class="chapter">${esc(p.chapter)}</div>` : ""}
    <div class="txt">${txt || (p.panels ? `<span class="muted">${p.panels} comic panels</span>` : `<span class="faint">No text</span>`)}</div>
    ${p.prompt ? `<details class="art"><summary>${icon("image")}<span>${esc(p.prompt)}</span></summary><p>${esc(p.prompt)}</p></details>` : ""}</div></div>`;
}

// a template book reads section by section (parents' note, story, exercises...); a free book page by page
function pagesReader(pages, kinds = kindsCache || {}) {
  if (!pages?.length) return `<p class="muted">No pages to show. Check the YAML for errors.</p>`;
  if (!pages.some((p) => p.kind)) return pages.map(pageCard).join("");
  const runs = [];
  pages.forEach((p, i) => {
    const k = p.kind || "story";
    if (runs.at(-1)?.kind === k) runs.at(-1).idx.push(i); else runs.push({ kind: k, idx: [i] });
  });
  const name = (k) => kinds[k]?.label || k.replace(/_/g, " ");
  const nav = runs.map((r, j) => `<button type="button" class="ms-chip" data-sec="${j}"><i class="dotph ph-${PHASE_OF[r.kind] || "play"}"></i>${esc(name(r.kind))}${r.idx.length > 1 ? `<span>${r.idx.length}</span>` : ""}</button>`).join("");
  return `<nav class="ms-map" aria-label="Sections">${nav}</nav>` + runs.map((r, j) => {
    const ph = PHASE_OF[r.kind] || "play", a = r.idx[0] + 1, z = r.idx.at(-1) + 1;
    return `<section class="ms-sec ph-${ph}" id="sec-${j}"><div class="ms-head">${pageSketch(r.kind)}<div><b>${esc(name(r.kind))}</b>
        <span class="faint xs">${PHASES[ph]} · ${a === z ? `page ${a}` : `pages ${a}–${z}`}</span></div></div>
      ${r.idx.map((i) => pageCard(pages[i], i)).join("")}</section>`;
  }).join("");
}

// clicking a section in the map scrolls to it
function wireReaderMap(root) {
  $$(".ms-chip", root).forEach((t) => (t.onclick = () => $(`#sec-${t.dataset.sec}`, root)?.scrollIntoView({ behavior: "smooth", block: "start" })));
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
          <div><h3>Next: art &amp; build</h3><p class="muted small">See every illustration and its cost, test the look with a pilot, then build the print files.</p></div>
          <a class="btn primary" href="#/book/${slug}/art">Go to art${icon("arrow")}</a></div></div>
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
      showPages(r.pages_view); setValid(null); showLint(); toast("Manuscript saved");
    } catch (err) {
      setValid(err.message);
      if (await modal({ title: "Save with errors?", body: "The YAML doesn't validate. You can save it anyway and keep fixing it, but the book won't build until it's valid.", confirm: "Save anyway" }))
        await api("PUT", `/api/books/${slug}/yaml`, { yaml: $("#yaml").value, save_invalid: true });
    }
  });
  const revise = async (instruction) => {
    const r = await api("POST", `/api/books/${slug}/claude/revise`, { instruction, yaml: $("#yaml").value });
    $("#yaml").value = r.yaml; showPages(r.pages_view); setValid(null);
    showLint();
    toast("Manuscript updated");
  };
  // the prompt check, shown here where it can still be fixed for free, before any art is paid for
  const showLint = async () => {
    const p = await loadPlan(slug);
    if (p.error) { $("#lint").innerHTML = ""; return; }
    const issues = activeLint(slug, p.lint);
    $("#lint").innerHTML = lintHtml(slug, issues, `<div style="margin-top:8px"><button class="btn sm" id="fixlint">${icon("wand")}Fix these with Claude</button></div>`);
    if (issues.length) $("#fixlint").onclick = (e) => busy(e.currentTarget, "Claude is fixing…", () => revise(
      "Fix these prompt-check notes, changing only what each one needs:\n" + activeLint(slug, issues).map((i) => `- ${i.where}: ${i.message}`).join("\n")));
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
  let shown = b.pages_view;
  const showPages = (pv) => { shown = pv; $("#reader").innerHTML = pagesReader(pv); wireReaderMap($("#reader")); wirePages(); };
  showPages(shown);
  if (!kindsCache && shown.some((p) => p.kind)) getKinds().then(() => showPages(shown)).catch(() => {});
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

const lintKey = (i) => `lint|${i.where}|${i.message}`;
const activeLint = (slug, issues) => notIgnored(slug, issues, lintKey);

// only serious problems reach here; each one can be ignored, and nothing shows when all is well
function lintHtml(slug, issues, extra = "") {
  issues = activeLint(slug, issues);
  if (!issues.length) return "";
  return `<div data-ignorable>${note("err", `<b>Prompt check</b><ul>${issues.map((i) =>
    `<li><b>${esc(i.where)}</b> · ${esc(i.message)} ${ignoreBtn(slug, lintKey(i))}</li>`).join("")}</ul>${extra}`)}</div>`;
}

// The built book, one spread at a time: arrows, keys or the slider turn the pages, so a 40-page book
// stays one screen tall. Every spread is in the DOM (lazy, hidden) so the lightbox can still browse them all.
async function spreadViewer(el, slug) {
  const pr = await api("GET", `/api/books/${slug}/proofs`);
  if (!pr.pages.length) { el.innerHTML = ""; return; }
  const v = Date.now(), src = (n) => `/api/books/${slug}/build/proofs/${n}?${v}`;
  const spreads = [[null, pr.pages[0]]];
  for (let i = 1; i < pr.pages.length; i += 2) spreads.push([pr.pages[i], pr.pages[i + 1] || null]);
  const label = (i) => (i === 0 ? "Page 1" : spreads[i][1] ? `Pages ${2 * i}–${2 * i + 1}` : `Page ${2 * i}`);
  let width = 880, at = 0;
  try { width = +localStorage.getItem("zoom") || 880; } catch {}
  el.innerHTML = `<div class="card"><div class="card-h"><div><h3>The book</h3><p>${pr.pages.length} pages as they print. Use ← → to turn the pages.</p></div>
      <div class="seg" id="vmode"><button class="on" data-v="spreads">Pages</button>${pr.cover ? `<button data-v="cover">Cover</button>` : ""}</div></div>
    <div class="viewer" style="--w:${width}px" tabindex="0" aria-label="Book viewer">
      <div id="v-spreads">
        <div class="flip">
          <button class="btn icon flip-nav" id="v-prev" aria-label="Previous pages">${icon("arrow", "flipx")}</button>
          <div class="spreads">${spreads.map((s, i) => `
            <div class="spread ${i === 0 ? "first" : ""}" data-i="${i}" ${i ? "hidden" : ""}>${s.map((p) => (p ? `<img src="${src(p)}" alt="${esc(p)}" loading="lazy">` : `<div class="blank"></div>`)).join("")}</div>`).join("")}</div>
          <button class="btn icon flip-nav" id="v-next" aria-label="Next pages">${icon("arrow")}</button></div>
        <div class="flip-bar">
          <span class="num small" id="v-label"></span>
          <input type="range" id="v-at" min="0" max="${spreads.length - 1}" value="0" aria-label="Spread">
          <span class="faint small num" id="v-of"></span>
          <label class="row small muted flip-zoom">Zoom <input type="range" id="zoom" min="420" max="1200" step="20" value="${width}"></label></div></div>
      <div class="cover-view" id="v-cover" hidden>${pr.cover ? `<img src="${src("cover.png")}" alt="Full cover: back, spine, front">` : ""}</div></div></div>`;
  const viewer = $(".viewer", el);
  const go = (i) => {
    at = Math.max(0, Math.min(spreads.length - 1, i));
    $$(".spread", el).forEach((s) => (s.hidden = +s.dataset.i !== at));
    $("#v-label", el).textContent = label(at);
    $("#v-of", el).textContent = `${at + 1} / ${spreads.length}`;
    $("#v-at", el).value = at;
    $("#v-prev", el).disabled = at === 0; $("#v-next", el).disabled = at === spreads.length - 1;
  };
  $("#v-prev", el).onclick = () => go(at - 1);
  $("#v-next", el).onclick = () => go(at + 1);
  $("#v-at", el).oninput = (e) => go(+e.target.value);
  viewer.addEventListener("keydown", (e) => {
    if (e.target.matches("input")) return;
    if (e.key === "ArrowLeft") { go(at - 1); e.preventDefault(); }
    if (e.key === "ArrowRight") { go(at + 1); e.preventDefault(); }
  });
  $("#zoom", el).oninput = (e) => { viewer.style.setProperty("--w", `${e.target.value}px`); try { localStorage.setItem("zoom", e.target.value); } catch {} };
  $$("#vmode button", el).forEach((b) => (b.onclick = () => {
    $$("#vmode button", el).forEach((x) => x.classList.toggle("on", x === b));
    $("#v-spreads", el).hidden = b.dataset.v !== "spreads"; $("#v-cover", el).hidden = b.dataset.v !== "cover";
  }));
  go(0);
}

// map of the book: intro, story, exercises, closing, in the order they print
function structureCard(structure, slug) {
  if (!structure?.length) return "";
  const play = structure.filter((x) => ["learn", "play"].includes(x.phase || PHASE_OF[x.kind]));
  const n = play.reduce((a, x) => a + x.pages, 0);
  return `<details class="card fold"><summary class="card-h"><div><h3>Book structure</h3>
      <p>${n ? `${n} exercise and learning ${n === 1 ? "page" : "pages"} after the story: ${esc(play.map((x) => x.title || x.kind).join(" · "))}.`
        : `Story only. To add a parents' note, coloring pages, matching games or a maze, pick a template under Book structure in the <a href="#/book/${slug}/brief">brief</a>, then write the book again.`}</p></div></summary>
    <div class="card-b">${bookFlow(structure, {}, { ranges: false })}</div></details>`;
}

// what a slot is called on screen: "Page 12", "Front cover", "Nina"
function slotName(s) {
  const m = /^p(\d+)$/.exec(s.id);
  if (m) return `Page ${+m[1]}`;
  if (s.id === "cover-front") return "Front cover";
  if (s.id === "cover-back") return "Back cover";
  const t = s.id.replace(/^char-/, "").replace(/[-_]+/g, " ");
  return t.charAt(0).toUpperCase() + t.slice(1);
}
const isPageSlot = (s) => /^p\d+$/.test(s.id);
const isFrontSlot = (s) => s.kind === "character" || /^cover-/.test(s.id);

// Every illustration as a small tile, with one inspector beside the grid for the selected image:
// big preview, the problems found, quality and Redo. Forty pages stay a compact grid, not a long list.
function artGallery(el, slug, ctx, { slots, filters = true, title = "Illustrations", sub = "" }) {
  const issuesOf = (id) => notIgnored(slug, ctx.review.get(id)?.issues || [], (i) => `art|${id}|${i}`);
  const state = (s) => (!s.has_art ? "missing" : issuesOf(s.id).length ? "bad" : "ok");
  let filter = "all";
  let sel = slots.some((s) => s.id === ctx.sel) ? ctx.sel : (slots.find((s) => state(s) === "bad") || slots.find((s) => s.has_art) || slots[0])?.id;
  const thumb = (s) => `/api/books/${slug}/build/thumbs/${s.id}.jpg?${ctx.v}`;
  const full = (s) => `/api/books/${slug}/build/art/${s.id}.png?${ctx.v}`;
  const tile = (s) => `<button type="button" class="gal-t ${state(s)} ${s.id === sel ? "on" : ""}" data-sel="${esc(s.id)}" title="${esc(slotName(s))}">
      <span class="gal-i">${s.has_art ? `<img src="${thumb(s)}" alt="" loading="lazy" onerror="this.onerror=null;this.src='${full(s)}'">` : icon("image")}</span>
      <span class="gal-n">${state(s) === "bad" ? `<i class="dot err"></i>` : ""}${esc(slotName(s))}${s.quality === "high" ? `<em>HQ</em>` : ""}</span></button>`;
  const group = (name, list) => list.length ? `<div class="gal-g"><div class="gal-h">${name}<span class="faint">${list.length}</span></div>
      <div class="gal-grid">${list.map(tile).join("")}</div></div>` : "";
  const inspector = () => {
    const s = slots.find((x) => x.id === sel);
    if (!s) return `<div class="insp empty faint small">Pick an image to see it here.</div>`;
    const iss = issuesOf(s.id), i = slots.indexOf(s);
    return `<div class="insp">
      <div class="insp-top"><button class="btn sm icon ghost" data-step="-1" ${i ? "" : "disabled"} aria-label="Previous image">${icon("arrow", "flipx")}</button>
        <div class="insp-t"><b>${esc(slotName(s))}</b><span class="faint xs">${esc(s.kind.replace(/_/g, " "))}${s.characters.length ? ` · ${esc(s.characters.join(", "))}` : ""}</span></div>
        <button class="btn sm icon ghost" data-step="1" ${i < slots.length - 1 ? "" : "disabled"} aria-label="Next image">${icon("arrow")}</button></div>
      <div class="insp-img">${s.has_art ? `<img src="${thumb(s)}" data-full="${full(s)}" alt="${esc(slotName(s))}" onerror="this.onerror=null;this.src='${full(s)}'">`
        : `<div class="insp-none">${icon("image")}<span>Not drawn yet</span></div>`}</div>
      ${iss.length ? `<div data-ignorable>${note("err", `<b>${iss.length === 1 ? "Needs a fix" : `${iss.length} things to fix`}</b><ul>${iss.map((x) => `<li>${esc(x)} ${ignoreBtn(slug, `art|${s.id}|${x}`)}</li>`).join("")}</ul>`)}</div>` : ""}
      <label class="insp-q"><span><b class="small">High quality</b><span class="faint xs">~${money(ctx.p.high_cost_usd)} instead of ~${money(ctx.p.base_cost_usd)}${s.has_art ? ", applies on the next redraw" : ""}</span></span>
        <span class="switch"><input type="checkbox" data-high="${esc(s.id)}" ${s.quality === "high" ? "checked" : ""} aria-label="High quality for ${esc(slotName(s))}"><i></i></span></label>
      ${s.has_art ? `<button class="btn" data-redo="${esc(s.id)}">${icon("refresh")}Redo this image</button>`
        : `<p class="faint xs">Drawn by Generate all art, ~${money(s.cost_usd)}.</p>`}</div>`;
  };
  const draw = () => {
    const counts = { bad: slots.filter((s) => state(s) === "bad").length, missing: slots.filter((s) => state(s) === "missing").length };
    if ((filter === "bad" && !counts.bad) || (filter === "missing" && !counts.missing)) filter = "all";
    const shown = slots.filter((s) => filter === "all" || state(s) === filter);
    const fronts = shown.filter(isFrontSlot), pages = shown.filter((s) => !isFrontSlot(s));
    const seg = filters && (counts.bad || counts.missing) ? `<div class="seg" id="gal-f">
        <button data-f="all" class="${filter === "all" ? "on" : ""}">All ${slots.length}</button>
        ${counts.bad ? `<button data-f="bad" class="${filter === "bad" ? "on" : ""}">Need a fix ${counts.bad}</button>` : ""}
        ${counts.missing ? `<button data-f="missing" class="${filter === "missing" ? "on" : ""}">Not drawn ${counts.missing}</button>` : ""}</div>` : "";
    el.innerHTML = `<div class="card-h"><div><h3>${title}</h3>${sub ? `<p>${sub}</p>` : ""}</div>${seg}</div>
      <div class="card-b gal">
        <div class="gal-list">${group("Characters &amp; cover", fronts)}${group("Pages", pages)}${shown.length ? "" : `<p class="faint small">Nothing here.</p>`}</div>
        ${inspector()}</div>`;
    $$("[data-sel]", el).forEach((b) => (b.onclick = () => { sel = ctx.sel = b.dataset.sel; draw(); }));
    $$("[data-f]", el).forEach((b) => (b.onclick = () => { filter = b.dataset.f; draw(); }));
    $$("[data-step]", el).forEach((b) => (b.onclick = () => { const i = slots.findIndex((s) => s.id === sel) + +b.dataset.step; if (slots[i]) { sel = ctx.sel = slots[i].id; draw(); } }));
    $$("[data-redo]", el).forEach((b) => (b.onclick = () => ctx.redo(b.dataset.redo, b)));
    $$("[data-high]", el).forEach((c) => (c.onchange = async () => {
      try {
        const np = await api("PUT", `/api/books/${slug}/high`, { slots: [c.dataset.high], on: c.checked });
        ctx.setPlan(np);
        np.slots.forEach((n) => { const s = slots.find((x) => x.id === n.id); if (s) Object.assign(s, n); });
        toast(`${slotName({ id: c.dataset.high })} → ${c.checked ? "high" : np.quality} · book now ~${money(np.estimate_usd)}`);
        draw();
      } catch (e) { c.checked = !c.checked; toast(e.message, true); }
    }));
    // an ignored problem may leave the image clean: redraw once the global Ignore handler has run
    $$("[data-ignore]", el).forEach((b) => b.addEventListener("click", () => setTimeout(draw)));
  };
  if (!slots.length) { el.hidden = true; return; }
  el.hidden = false;
  draw();
}

async function stepArt(host, b, slug) {
  let p = await loadPlan(slug);
  if (p.error) { host.innerHTML = stepHead("Art & build", "") + note("err", `${esc(p.error)}<br><a href="#/book/${slug}/manuscript">Fix the manuscript</a>`); return; }
  const ctx = { p, review: new Map(), v: Date.now(), setPlan: (np) => { p = ctx.p = np; $$(".est").forEach((e) => (e.textContent = money(np.estimate_usd))); drawSteps(); } };
  let built = b.last_build, preflight = null, running = false, tab = null, pilotN = 3;
  const chars = () => p.slots.filter((s) => s.kind === "character").length;
  const done = () => p.slots.filter((s) => s.has_art).length;
  const missing = () => p.slots.filter((s) => !s.has_art);
  const missingCost = () => missing().reduce((a, s) => a + s.cost_usd, 0);
  // the optional pilot: character sheets, the front cover and the first pages, to check the look cheaply
  const pilotSlots = () => [...p.slots.filter((s) => s.kind === "character" || s.id === "cover-front"), ...p.slots.filter(isPageSlot).slice(0, pilotN)];
  const pilotCost = () => pilotSlots().filter((s) => !s.has_art).reduce((a, s) => a + s.cost_usd, 0);
  const auto = () => (missing().length ? "art" : "build");

  host.innerHTML = stepHead("Art & build", "Draw the illustrations, then build the print files.",
    `<div class="art-sum"><b class="num">${p.slots.length}</b> illustrations<br><span class="faint">~<span class="est">${money(p.estimate_usd)}</span> in total</span></div>`) + `
    <div class="stack">
      <ol class="artflow" id="flow" role="tablist" aria-label="Art steps"></ol>
      ${lintHtml(slug, p.lint)}
      ${jobPanel("Working…")}
      <div class="stack" id="panel"></div>
    </div>`;

  const steps = () => {
    const left = missing().length, pf = built === "real" && preflight;
    return [
      { k: "art", n: 1, t: "Illustrations", done: !left, s: `${done()} of ${p.slots.length} drawn` },
      { k: "build", n: 2, t: "Print files", done: !!pf?.ok, locked: left > 0,
        s: left ? `Waiting for ${left} image${left > 1 ? "s" : ""}` : pf ? (pf.ok ? "Preflight passed" : "Preflight failed") : built === "mock" ? "Placeholder build only" : "Ready to build" },
    ];
  };
  function drawSteps() {
    const list = steps();
    $("#flow").innerHTML = list.map((x) => `<li class="${x.done ? "done" : ""} ${x.k === tab ? "current" : ""} ${x.locked ? "locked" : ""}">
      <button type="button" role="tab" aria-selected="${x.k === tab}" data-tab="${x.k}">
        <span class="dot">${x.done ? icon("check") : x.n}</span>
        <span class="tx"><span class="k">Step ${x.n}</span><b>${x.t}</b><span class="s">${esc(x.s)}</span></span></button></li>`).join("");
    $$("[data-tab]", $("#flow")).forEach((btn) => (btn.onclick = () => show(btn.dataset.tab)));
  }
  const show = (k) => { tab = k; drawSteps(); drawPanel(); };
  const next = (k, label) => `<button class="btn primary" data-go="${k}">${label}${icon("arrow")}</button>`;
  const actionCard = (title, body, actions, extra = "") => `<div class="card act"><div class="act-b"><h3>${title}</h3><p>${body}</p></div><div class="act-a">${actions}</div>${extra}</div>`;

  function drawPanel() {
    const panel = $("#panel");
    const left = missing().length;
    if (tab === "art") {
      const pct = Math.round((done() / p.slots.length) * 100);
      // optional: try the look on a few pages before paying for the rest (only worth it while pages are missing)
      const pilotLeft = pilotSlots().some((s) => !s.has_art);
      const pilot = left && pilotLeft ? `<div class="act-opt"><span class="badge plain">Optional</span>
          <span class="small">Check the look first: characters, cover and the first</span>
          <input class="input num" id="pp" type="number" min="1" max="10" value="${pilotN}" aria-label="Pages to try">
          <span class="small">pages</span><span class="faint small" id="pp-cost">~${money(pilotCost())}</span>
          <button class="btn sm" id="pilot">${icon("eye")}Try these first</button></div>` : "";
      panel.innerHTML = actionCard(left ? "Draw the illustrations" : "Every illustration is drawn",
        `${left ? `${left} image${left > 1 ? "s" : ""} left, about <b>${money(missingCost())}</b>. ` : ""}All at <b>${esc(p.quality)}</b> quality (~${money(p.base_cost_usd)} each). Each image is generated once and only redrawn when you press Redo.
         <span class="act-p"><span class="progress ${left ? "" : "done"}"><i style="width:${Math.max(pct, 2)}%"></i></span><span class="num small">${done()} / ${p.slots.length}</span></span>`,
        left ? `<button class="btn primary" id="all">${icon("sparkle")}Generate ${left === p.slots.length ? "all art" : `${left} missing`}</button>`
          : next("build", "Next: print files"), pilot) + `
        <div class="card gallery" id="gal"></div>
        ${structureCard(p.structure, slug)}`;
      if (pilot) {
        $("#pp").oninput = (e) => { pilotN = Math.max(1, Math.min(10, +e.target.value || 1)); $("#pp-cost").textContent = `~${money(pilotCost())}`; };
        $("#pilot").onclick = async (e) => {
          const btn = e.currentTarget;
          if (await cost("Try the look first?", `Character sheets, the front cover and the first ${pilotN} page${pilotN > 1 ? "s" : ""}: about <b>${money(pilotCost())}</b>.`))
            run(btn, "pilot", { pages: pilotN }, "Generating pilot…", chars() + 1 + pilotN);
        };
      }
      artGallery($("#gal"), slug, ctx, { slots: p.slots.map((s) => ({ ...s })), title: "Illustrations",
        sub: `Click an image to inspect it. Switch on <b>High quality</b> for images that deserve it. <span class="faint">${esc(p.model)}</span>` });
      $("#all")?.addEventListener("click", async (e) => {
        const btn = e.currentTarget;
        if (await cost("Generate all illustrations?", `${left} missing image${left > 1 ? "s" : ""}, about <b>${money(missingCost())}</b>.`))
          run(btn, "art", {}, "Generating art…", p.slots.length);
      });
    } else {
      panel.innerHTML = (left ? note("info", `Building needs every illustration. ${left} still missing. <a href="#" data-go="art">Go to illustrations</a>`) : "") +
        actionCard("Build the print files",
          `Lays out interior.pdf and cover.pdf with the real art and checks them against KDP's rules (trim, bleed, margins, fonts, cover size).
           ${built === "mock" ? `<br><span class="faint">The last build used placeholder art.</span>` : ""}`,
          `<button class="btn ${built === "real" ? "" : "primary"}" id="build" ${left ? "disabled" : ""}>${icon("file")}${built === "real" ? "Build again" : "Build &amp; preflight"}</button>
           ${built === "real" && preflight?.ok ? `<a class="btn primary" href="#/book/${slug}/control">Next: control &amp; correction${icon("arrow")}</a>` : ""}`) + `
        <div id="pf"></div><div id="viewer"></div>`;
      if (preflight && built === "real") showPreflight(preflight);
      if (built === "real") spreadViewer($("#viewer"), slug);
      $("#build").onclick = (e) => run(e.currentTarget, "build", {}, "Building print files…", 0);
    }
    $$("[data-go]", panel).forEach((a) => (a.onclick = (e) => { e.preventDefault(); show(a.dataset.go); }));
    if (running) jobButtons().forEach((x) => (x.disabled = true));
  }

  const showPreflight = (r) => {
    const warns = notIgnored(slug, r.warnings, (w) => `pf|${w}`);
    // a problem that names an image ("p002: lettering too close…") gets its own Redo, the problem as the note
    const fix = (msg) => {
      const m = /^([\w-]+):\s*(.*)$/.exec(msg);
      const s = m && p.slots.find((x) => x.id === m[1]);
      if (!s) return { text: esc(msg), btn: "" };
      const why = m[2].replace(/\s*-\s*redo it before uploading\.?$/i, "");
      return { text: `<b>${esc(slotName(s))}</b> · ${esc(why)}`,
        btn: `<button class="btn sm pf-redo" data-pfredo="${esc(s.id)}" data-why="${esc(why)}">${icon("refresh")}Redo</button>` };
    };
    const line = (cls, ic, msg, extra = "") => { const f = fix(msg); return `<li class="${cls}">${icon(ic)}<span>${f.text}</span>${f.btn}${extra}</li>`; };
    $("#pf").innerHTML = `<div class="card"><div class="card-h"><h3>Preflight</h3>${r.ok ? `<span class="badge ok">Passed</span>` : `<span class="badge err">Failed</span>`}</div>
      <div class="card-b"><ul class="checklist">
        ${r.errors.map((e) => line("e", "x", e)).join("")}
        ${warns.map((w) => line("w", "alert", w, ignoreBtn(slug, `pf|${w}`))).join("")}
        ${r.ok ? `<li class="o">${icon("check")}<span>${r.pages} pages · ${esc(r.trim)} · fonts embedded · bleed, margins and cover size match KDP</span></li>` : ""}</ul>
        ${warns.length > 1 ? `<div style="margin-top:8px"><button class="btn sm ghost" id="pf-ignore-all">Ignore all</button></div>` : ""}
        ${[...r.errors, ...warns].some((e) => fix(e).btn) ? `<p class="faint xs" style="margin-top:8px">After redrawing, press Build again to check the new images.</p>` : ""}</div></div>`;
    $("#pf-ignore-all")?.addEventListener("click", () => {
      const s = ignoredSet(slug); warns.forEach((w) => s.add(`pf|${w}`));
      try { localStorage.setItem(ignoreStore(slug), JSON.stringify([...s])); } catch {}
      showPreflight(r);
    });
    $$("[data-pfredo]", $("#pf")).forEach((btn) => (btn.onclick = () => ctx.redo(btn.dataset.pfredo, btn, btn.dataset.why)));
  };
  const loadReview = async () => {
    const r = await api("GET", `/api/books/${slug}/review`).catch(() => ({ slots: [] }));
    ctx.review = new Map(r.slots.map((s) => [s.id, s]));
    ctx.v = Date.now();
  };
  const loadPreflight = async () => {
    preflight = await api("GET", `/api/books/${slug}/build/preflight.json`).catch(() => null);
  };
  const refresh = async () => {
    const np = await loadPlan(slug);
    if (!np.error) p = ctx.p = np;
    await loadReview();
  };

  const jobButtons = () => [...["#pilot", "#all", "#build", "#pp"].map((q) => $(q)).filter(Boolean), ...$$("[data-redo], [data-pfredo]")];
  const follow = async (job, kind, label, total) => {
    running = true; jobButtons().forEach((x) => (x.disabled = true));
    try {
      const j = await watchJob(job, label, total);
      if (j.status !== "done") toast("The job stopped. See the log.", true);
      if (kind === "build" && j.status === "done") built = "real";
      if (j.result?.preflight) preflight = j.result.preflight;
      // reload the plan so the new images show; retry once, since a failed reload would leave the old picture
      for (let i = 0; i < 3; i++) {
        try { const np = await loadPlan(slug); if (np.error) throw new Error(np.error); p = ctx.p = np; await loadReview(); break; }
        catch { await new Promise((r) => setTimeout(r, 800)); }
      }
      if (j.status === "done") toast(`${label.replace(/…$/, "")}: done`);
      return j;
    } finally {
      running = false;
      if (host.isConnected) { drawSteps(); drawPanel(); }
    }
  };
  const run = async (btn, kind, body, label, total) => busy(btn, label, async () => {
    const { job } = await api("POST", `/api/books/${slug}/jobs/${kind}`, { ...body, force: !activeLint(slug, p.lint).length });
    return follow(job, kind, label, total);
  });
  const cost = (title, body) => modal({ title, body: `${body}<br><br>This uses the OpenAI image API and costs real money.`, confirm: "Generate" });
  ctx.redo = async (id, btn, prefill = "") => {
    const slot = p.slots.find((s) => s.id === id);
    const isHigh = slot?.quality === "high";
    const v = await modal({ title: `Redo ${slotName({ id })}`, confirm: "Redo image",
      body: `Draws this image once more with your correction: about ${money(isHigh ? p.high_cost_usd : p.base_cost_usd)}.`,
      fields: `<div class="field"><label for="m-note">What should change?</label>
        <textarea class="input" id="m-note" name="note" rows="3" required placeholder="Pip smaller, facing left, softer light. Spell 'wiggles' with two g's.">${esc(prefill)}</textarea></div>
        <label class="check"><input type="checkbox" name="high" ${isHigh ? "checked" : ""}> High quality (~${money(p.high_cost_usd)} instead of ~${money(p.base_cost_usd)})</label>` });
    if (!v) return;
    if (!!v.high !== isHigh) p = ctx.p = await api("PUT", `/api/books/${slug}/high`, { slots: [id], on: !!v.high });
    run(btn, "regen", { slots: [id], note: (v.note || "").trim() || null }, `Redrawing ${slotName({ id })}…`, 1);
  };

  await Promise.all([loadReview(), built === "real" ? loadPreflight() : null]);
  if (!host.isConnected) return;
  // a job still running on the server (e.g. after a page refresh) opens the step it belongs to
  tab = { pilot: "art", art: "art", regen: "art", build: "build" }[b.job_kind] || auto();
  drawSteps(); drawPanel();
  if (b.job) follow(b.job, b.job_kind, `${JOB_LABELS[b.job_kind] || "Working"}…`, 0);
}

// ---------- control & correction: Claude proofreads the built book, page by page ----------
const FIX_LABEL = { image: "Redraw the picture", text: "Fix the words", layout: "Fix the page layout" };

async function stepControl(host, b, slug) {
  const head = stepHead("Control & correction", "Claude reads every page of the built book, lists the real problems and writes the fix for each one.");
  if (b.last_build !== "real") {
    host.innerHTML = head + note("info", `Build the book first: the check reads the finished pages. <a href="#/book/${slug}/art">Go to Art &amp; build</a>`);
    return;
  }
  let report = (await api("GET", `/api/books/${slug}/control`)).report;
  // The queue: fixes wait here and run one after another (a book runs one job at a time). When it empties the
  // book is rebuilt and read again, because the check reads the built pages.
  const queue = [];                 // [{ id, prompt }]
  let working = null, phase = null; // phase: null | "fix" | "build" | "check"
  host.innerHTML = head + `<div class="stack"><div class="ctl-sticky">${jobPanel("Working…")}<div id="ctl-head"></div></div><div class="stack" id="ctl"></div></div>`;
  const png = (n) => `/api/books/${slug}/build/proofs/page-${String(n).padStart(3, "0")}.png`;
  const stat = (id) => (working === id ? "working" : queue.some((q) => q.id === id) ? "queued" : null);
  const reload = async () => { report = (await api("GET", `/api/books/${slug}/control`)).report; };
  const locked = () => phase === "build" || phase === "check";
  const live = () => host.isConnected;

  function issueHtml(i) {
    const s = stat(i.id);
    let body;
    if (i.status === "applied") body = `<span class="badge ok">Fixed</span>`;
    else if (s === "working") body = `<div class="ctl-state"><span class="spin"></span>Fixing…</div>`;
    else if (s === "queued") body = `<div class="ctl-state">Waiting in the queue <button class="btn sm ghost" data-unq="${i.id}">Remove</button></div>`;
    else body = `<label class="ctl-pick" ${report.issues.filter((x) => x.page === i.page && x.status !== "ignored").length > 1 ? "" : "hidden"}><input type="checkbox" data-pick="${i.id}" checked> Include in “Apply selected”</label>
      <textarea class="input" rows="3" data-prompt="${i.id}" aria-label="The fix">${esc(i.prompt)}</textarea>
      <div class="row gap2"><button class="btn primary sm" data-apply="${i.id}">${icon(i.fix === "image" ? "sparkle" : "check")}Apply fix${i.cost_usd ? ` · ~${money(i.cost_usd)}` : ""}</button>
        <button class="btn sm ghost" data-skip="${i.id}" ${phase === "check" ? "disabled" : ""}>Ignore</button></div>`;
    return `<div class="ctl-issue ${i.status} ${s ? "is-" + s : ""}" id="iss-${i.id}">
      <div class="row gap2"><span class="badge ${i.fix === "image" ? "accent" : "plain"}">${FIX_LABEL[i.fix]}</span></div>
      <p class="ctl-problem">${esc(i.problem)}</p>
      ${i.replace_with ? `<p class="ctl-swap">${i.current ? `<s>${esc(i.current)}</s> → ` : ""}<b>${esc(i.replace_with)}</b></p>` : ""}${body}</div>`;
  }

  // only the issue (and its page) that changed is redrawn, so nothing else on the screen moves
  function refreshIssue(id) {
    const el = $(`#iss-${id}`, host), i = report?.issues.find((x) => x.id === id);
    if (!el || !i) return;
    el.outerHTML = issueHtml(i);
    voiceify($(`#iss-${id}`, host));
    const card = $(`#iss-${id}`, host).closest(".ctl-card");
    card.classList.toggle("loading", !!card.querySelector(".is-working"));
    refreshPage(card);
  }
  // the page's own button: apply the ticked fixes of that page at once (shown when it has two or more to do)
  function refreshPage(card) {
    const btn = $("[data-pageapply]", card);
    if (!btn) return;
    const open = $$("[data-pick]", card), picked = open.filter((c) => c.checked).length;
    btn.hidden = open.length < 2;
    btn.disabled = !picked;
    btn.innerHTML = `${icon("sparkle")}Apply selected (${picked})`;
  }
  const refreshAll = () => report?.issues.forEach((i) => refreshIssue(i.id));

  const todoList = () => (report?.issues || []).filter((i) => i.status === "open" && !stat(i.id));

  function drawHead() {
    const box = $("#ctl-head", host);
    if (!report) { box.innerHTML = ""; return; }
    const open = report.issues.filter((i) => i.status !== "ignored");
    const todo = open.filter((i) => i.status === "open").length;
    const free = todoList().length, busyNow = phase || queue.length || working;
    const line = phase === "build" ? `<span class="spin"></span>Rebuilding the book…`
      : phase === "check" ? `<span class="spin"></span>Reading every page again…`
      : busyNow ? `<span class="spin"></span>Fixing: ${queue.length + (working ? 1 : 0)} left`
      : open.length ? `<b>${todo} to fix</b>${open.length > todo ? ` · ${open.length - todo} fixed` : ""}` : `<b>No problems found</b>`;
    box.innerHTML = `<div class="card"><div class="card-b row between">
      <div class="row gap2">${line}<span class="faint small"> · ${report.pages} pages read</span></div>
      <div class="row gap2">
        ${free > 1 ? `<button class="btn" id="ignore-all" ${phase === "check" ? "disabled" : ""}>Ignore all (${free})</button>` : ""}
        ${free > 1 ? `<button class="btn primary" id="apply-all">${icon("sparkle")}Apply all (${free})</button>` : ""}
        ${report.rebuild && !busyNow ? `<button class="btn primary" id="rebuild">${icon("file")}Rebuild the book</button>` : ""}
        <button class="btn" id="check" ${busyNow ? "disabled" : ""}>${icon("refresh")}Check again</button>
        ${!todo && !report.rebuild && !busyNow ? `<a class="btn primary" href="#/book/${slug}/publish">Next: publish${icon("arrow")}</a>` : ""}</div></div></div>`;
  }

  function draw() {
    const box = $("#ctl", host);
    if (!report) {
      $("#ctl-head", host).innerHTML = "";
      box.innerHTML = `<div class="card act"><div class="act-b"><h3>Check the book</h3>
        <p>Claude looks at every page for real mistakes: spelling, cut or crowded text, pictures that contradict the words. It changes nothing by itself.</p></div>
        <div class="act-a"><button class="btn primary" id="check">${icon("eye")}Check every page</button></div></div>`;
      return;
    }
    drawHead();
    const pages = [...new Set(report.issues.filter((i) => i.status !== "ignored").map((i) => i.page))];
    box.innerHTML = pages.map((n) => `<div class="card ctl-card"><div class="card-b ctl-page">
      <a class="ctl-img" href="${png(n)}" target="_blank" rel="noopener"><img src="${png(n)}?${Math.round(report.checked)}" alt="Page ${n}" loading="lazy"><span class="ctl-load"><span class="spin"></span></span></a>
      <div class="stack"><div class="row between"><h3>Page ${n}</h3><button class="btn sm primary" data-pageapply="${n}" hidden></button></div>${report.issues.filter((i) => i.page === n && i.status !== "ignored").map(issueHtml).join("")}</div></div></div>`).join("");
    voiceify(box);
    refreshAll();
  }

  // "Check again" always reads the latest book: it is built first, then every page is read.
  async function check(btn) {
    if (pumping) return;
    pumping = true;
    try {
      if (report) { phase = "build"; drawHead(); }
      const { job } = await api("POST", `/api/books/${slug}/jobs/build`, {});
      const r = await watchJob(job, "Building print files…", 0);
      if (r?.status === "failed") throw new Error("The book could not be built, so it was not checked.");
      if (report) { phase = "check"; drawHead(); }
      await busy(btn, "Reading the pages…", async () => { report = (await api("POST", `/api/books/${slug}/control/check`)).report; });
      remap();
    } catch (e) {
      toast(e.message, true);
    } finally {
      phase = null; pumping = false;
      if (live()) { if (!report) { try { await reload(); } catch {} } draw(); }
    }
  }

  async function applyOne(it) {
    const i = report.issues.find((x) => x.id === it.id);
    const r = await api("POST", `/api/books/${slug}/control/${it.id}/apply`, { prompt: it.prompt });
    if (r.job) await watchJob(r.job, `Redrawing ${i.slot}…`, 1);
  }

  let pumping = false;
  async function pump() {
    if (pumping) return;
    pumping = true;
    try {
      while (live()) {
        let did = false;
        while (queue.length && live()) {
          const it = queue.shift();
          working = it.id; phase = "fix"; refreshIssue(it.id); drawHead();
          try { await applyOne(it); did = true; } catch (e) { toast(e.message, true); }
          working = null;
          await reload();
          if (live()) { refreshIssue(it.id); drawHead(); }
        }
        if (!did || !live()) break;
        // the queue is done: build the book again, then read it again. Fixes asked for meanwhile wait in the queue.
        phase = "build"; drawHead(); refreshAll();
        const { job } = await api("POST", `/api/books/${slug}/jobs/build`, {});
        await watchJob(job, "Building print files…", 0);
        phase = "check"; drawHead();
        report = (await api("POST", `/api/books/${slug}/control/check`)).report;
        remap();
        phase = null; draw();
        if (!queue.length) break;
      }
    } catch (e) {
      toast(e.message, true);
    } finally {
      working = null; phase = null; pumping = false;
      if (live()) { try { await reload(); } catch {} draw(); }
    }
  }

  const enqueue = (id) => {
    const el = $(`[data-prompt="${id}"]`, host), i = report.issues.find((x) => x.id === id);
    queue.push({ id, prompt: (el?.value || i.prompt).trim(), page: i.page, fix: i.fix, problem: i.problem });
    refreshIssue(id); drawHead(); pump();
  };
  // a new check numbers its issues again: queued fixes follow their problem (same page, same kind of fix)
  function remap() {
    let lost = 0;
    for (const q of queue.splice(0)) {
      const cands = report.issues.filter((i) => i.status === "open" && i.page === q.page && i.fix === q.fix && !queue.some((x) => x.id === i.id));
      const m = cands.find((i) => i.problem === q.problem) || (cands.length === 1 ? cands[0] : null);
      if (m) queue.push({ ...q, id: m.id }); else lost++;
    }
    if (lost) toast(`${lost} queued fix${lost > 1 ? "es were" : " was"} dropped: the new check no longer shows ${lost > 1 ? "them" : "it"}.`);
  }
  const imageCost = (list) => list.reduce((a, i) => a + (i.fix === "image" ? i.cost_usd || 0 : 0), 0);
  const redrawNote = (list) => `${list.filter((i) => i.fix === "image").length} picture${list.filter((i) => i.fix === "image").length > 1 ? "s" : ""} will be redrawn: about ${money(imageCost(list))}.<br><br>This uses the OpenAI image API and costs real money.`;

  host.addEventListener("change", (e) => { const c = e.target.closest("[data-pick]"); if (c) refreshPage(c.closest(".ctl-card")); });
  host.addEventListener("click", async (e) => {
    const t = e.target.closest("button");
    if (!t || !live()) return;
    if (t.id === "check") return check(t);
    if (t.id === "rebuild") {
      if (pumping) return;
      pumping = true; phase = "build"; drawHead();
      try { const { job } = await api("POST", `/api/books/${slug}/jobs/build`, {}); await watchJob(job, "Building print files…", 0); }
      catch (err) { toast(err.message, true); }
      finally { pumping = false; phase = null; await reload(); draw(); }
      return;
    }
    if (t.dataset.skip) {   // the issue goes away at once; the page card goes with its last issue
      const id = t.dataset.skip;
      try { await api("PUT", `/api/books/${slug}/control/${id}`, { status: "ignored" }); }
      catch (err) { return toast(err.message, true); }
      const i = report.issues.find((x) => x.id === id);
      if (i) i.status = "ignored";
      const el = $(`#iss-${id}`, host), card = el?.closest(".ctl-card");
      el?.remove();
      if (card && !card.querySelector(".ctl-issue")) card.remove(); else if (card) refreshPage(card);
      return drawHead();
    }
    if (t.dataset.unq) { queue.splice(queue.findIndex((q) => q.id === t.dataset.unq), 1); refreshIssue(t.dataset.unq); return drawHead(); }
    if (t.dataset.apply) {
      const i = report.issues.find((x) => x.id === t.dataset.apply);
      if (i.fix === "image" && !(await modal({ title: "Redraw this picture?", body: redrawNote([i]), confirm: "Redraw" }))) return;
      return enqueue(i.id);
    }
    if (t.dataset.pageapply) {
      const card = t.closest(".ctl-card");
      const list = $$("[data-pick]", card).filter((c) => c.checked).map((c) => report.issues.find((x) => x.id === c.dataset.pick));
      if (!list.length) return;
      if (list.some((i) => i.fix === "image") && !(await modal({ title: `Apply ${list.length} fixes on page ${t.dataset.pageapply}?`, body: redrawNote(list), confirm: "Apply" }))) return;
      return list.forEach((i) => enqueue(i.id));
    }
    if (t.id === "ignore-all") {
      const list = todoList();
      if (!list.length || !(await modal({ title: `Ignore all ${list.length} problems?`, body: "They are hidden now and stay hidden on every re-check.", confirm: "Ignore all" }))) return;
      t.disabled = true;
      try {
        for (const i of list) { await api("PUT", `/api/books/${slug}/control/${i.id}`, { status: "ignored" }); i.status = "ignored"; }
      } catch (err) { toast(err.message, true); }
      return draw();
    }
    if (t.id === "apply-all") {
      const list = todoList();
      const body = list.some((i) => i.fix === "image") ? redrawNote(list) : "The words and layout will be fixed.";
      if (!(await modal({ title: `Apply all ${list.length} fixes?`, body: `${body}<br><br>They run one after another, then the book is rebuilt and checked again.`, confirm: "Apply all" }))) return;
      list.forEach((i) => enqueue(i.id));
    }
  });
  draw();
}

// Download formats on the Publish step: [file, title, kind, what it's for, icon]
const FORMATS = {
  print: { title: "Print", sub: "The two files Amazon KDP asks for when you publish a paperback.", items: [
    ["interior.pdf", "Interior", "PDF · print", "Every page with bleed, at print resolution.", "book"],
    ["cover.pdf", "Cover", "PDF · print", "Back, spine and front in one wraparound sheet.", "layers"]] },
  screen: { title: "Read on screen", sub: "Trimmed to the page edge, padding pages left out, small enough to email.", items: [
    ["reading.pdf", "Reading PDF", "PDF · pages", "Cover, then one page after another. For tablets, email or selling as a download.", "file"],
    ["spreads.pdf", "Spreads PDF", "PDF · spreads", "Two pages side by side, as the open book looks. For reading on a laptop or a TV.", "eye"]] },
  images: { title: "Images", sub: "For your shop page, social posts and the eBook cover.", items: [
    ["cover.jpg", "Front cover", "JPG · 300 dpi", "The front cover alone, full size. Use it as the Kindle cover, on your website or in ads.", "image"],
    ["pages.zip", "All pages", "ZIP of JPGs", "The cover and every page as an image, numbered in reading order.", "grid"]] },
};

async function stepPublish(host, b, slug) {
  const built = b.last_build === "real";
  const listing = b.state.listing;
  let paper = "premium_color", trim = "8.5x8.5";
  const m = b.yaml?.match(/^paper:\s*(\S+)/m); if (m) paper = m[1];
  const t = b.yaml?.match(/^trim:\s*['"]?([\d.x]+)/m); if (t) trim = t[1];
  const ready = !!b.files?.["interior.pdf"];
  const fmt = ([name, title, kind, what, ic]) => {
    const print = name.endsWith(".pdf") && FORMATS.print.items.some(([n]) => n === name);
    const href = print ? `/api/books/${slug}/build/${name}` : `/api/books/${slug}/export/${name}`;
    const size = print ? b.files?.[name] : b.exports?.[name];
    const on = print ? !!size : ready && (name !== "cover.jpg" || !!b.files?.["cover.pdf"]);
    return `<div class="fmt ${on ? "" : "off"}">
      <div class="fmt-top"><span class="fmt-ic">${icon(ic)}</span><span><b>${title}</b><span class="fmt-kind">${kind}</span></span></div>
      <p>${what}</p>
      <div class="fmt-f"><span class="faint xs num">${on ? (size ? bytes(size) : "") : "not built"}</span>
        <a class="btn sm" ${on ? `href="${href}" download` : `aria-disabled="true"`}>${icon("download")}Download</a></div></div>`;
  };
  const group = (key) => { const g = FORMATS[key]; return `<section class="pub-group">
      <div class="pub-gh"><h3>${g.title}</h3><p>${g.sub}</p></div>
      <div class="fmts">${g.items.map(fmt).join("")}</div>
      
    </section>`; };

  host.innerHTML = stepHead("Publish", "Download the book in the format you need, or make the same book in another language.") + `
    <div class="stack">
      ${built ? (b.preflight?.ok ? note("ok", "Ready to publish. Every file below comes from the same finished book.") : "")
        : note("warn", `${b.last_build === "mock" ? "These files use placeholder art. Don't upload or share them." : "Nothing built yet."} <a href="#/book/${slug}/art">Go to Art &amp; build</a>`)}
      ${(() => {
        const pf = b.preflight, warns = built && pf ? notIgnored(slug, pf.warnings, (w) => `pf|${w}`) : [];
        if (!built || !pf || !(pf.errors.length || warns.length)) return "";
        return `<div data-ignorable>${note(pf.errors.length ? "err" : "warn", `<b>Check before uploading</b><ul>${pf.errors.map((e) => `<li>${esc(e)}</li>`).join("")}${
          warns.map((w) => `<li>${esc(w)} ${ignoreBtn(slug, `pf|${w}`)}</li>`).join("")}</ul>`)}</div>`;
      })()}
      <div class="split pub">
        <div class="stack">
          ${group("print")}${group("screen")}${group("images")}
          <a class="file everything" href="/api/books/${slug}/download.zip"><span class="fi">${icon("download")}</span>
            <span><b>Everything in one .zip</b><span>Print PDFs, Amazon listing and book.yaml</span></span>${icon("arrow")}</a>
          <div class="card"><div class="card-h"><div><h3>Amazon listing</h3><p>Description, keywords, categories and AI disclosure, ready to paste into KDP.</p></div>
            <button class="btn ${listing ? "" : "primary"} sm" id="gen">${icon("sparkle")}${listing ? "Regenerate" : "Draft with Claude"}</button></div>
            <div class="card-b" id="listing">${listing ? listingHtml(listing) : `<p class="muted">Claude reads the finished book and drafts every field KDP asks for.</p>`}</div></div>
        </div>
        <aside class="sticky">${editionsCard(b, slug)}</aside>
      </div>
    </div>`;
  wireEditions(b, slug);
  wireCopy();
  $("#gen").onclick = (e) => busy(e.currentTarget, "Writing…", async () => {
    const st = await api("POST", `/api/books/${slug}/listing`);
    $("#listing").innerHTML = listingHtml(st.listing); wireCopy();
  });
}

// "Same book, another language": the same art, the same text translated, as its own book
function editionsCard(b, slug) {
  const ed = b.editions || { translations: [] };
  // new languages are always made from the original, so a translation can start one as soon as the original is built
  const built = ed.origin ? ["ready", "preflight failed"].includes(ed.origin.status) : b.last_build === "real";
  const here = langOf(b.yaml?.match(/^language:\s*['"]?([^'"\n]+)/m)?.[1]);
  const source = ed.origin || { slug, title: b.title, language: here };
  const made = new Set([source.language, ...ed.translations.map((e) => e.language)].map((l) => l.toLowerCase()));
  const row = (e) => `<a class="ed ${e.slug === slug ? "here" : ""}" href="#/book/${e.slug}/${e.status === "ready" ? "publish" : "art"}">
      <span class="ed-lang">${esc(e.language)}</span><span class="ed-t">${esc(e.title)}</span>
      ${e.slug === slug ? `<span class="faint xs">this book</span>` : badge(e.status)}</a>`;
  return `<div class="card tr-card"><div class="card-h"><div><h3>${icon("globe")}Another language</h3></div></div>
    <div class="card-b stack">
      <p class="small">The whole book again in another language: <b>the same art</b> and <b>the same text</b>, translated by Claude and laid out as its own book.</p>
      ${built ? `<div class="stack tight">
          <span class="label">Translate “${esc(source.title)}” into</span>
          ${LANGS.some((l) => !made.has(l.toLowerCase())) ? `<div class="tr-langs" id="tr-chips">${LANGS.filter((l) => !made.has(l.toLowerCase()))
            .map((l) => `<button class="btn" data-lang="${l}">${icon("globe")}${LANG_NATIVE[l]}</button>`).join("")}</div>`
            : `<p class="muted small">This book is already in all ${LANGS.length} languages.</p>`}
          <span class="faint xs">Pictures with no words in them are reused as they are. Only pictures with the words drawn into them are drawn again.</span>
        </div>` : `<p class="muted small">Finish the art and build this book first. Then you can translate it.</p>`}
      ${ed.origin || ed.translations.length ? `<div class="stack tight"><span class="label">Editions</span>
        <div class="eds">${row({ ...source, status: source.status || b.status })}${ed.translations.map(row).join("")}</div></div>` : ""}
    </div></div>`;
}

function wireEditions(b, slug) {
  const source = b.editions?.origin?.slug || slug;
  $$("#tr-chips [data-lang]").forEach((c) => (c.onclick = () => runTranslate(source, c.dataset.lang, c)));
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
          ["Preflight passes with real art", "Never upload a build with placeholder art. Art & build must show Preflight passed."],
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
          ${field("openai_api_key", "OpenAI API key", { secret: true, ph: "sk-…", hint: "Required to generate the illustrations.", full: true })}
          ${field("image_model", "Image model")}
          ${field("image_quality", "Default quality", { select: [["low", "low · ~$0.01"], ["medium", "medium · ~$0.05 (recommended)"], ["high", "high · ~$0.21"]], hint: "Per image. Mark single images as high in the Art & build step." })}
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
      <div class="setup-actions"><a href="#" id="skip" class="small faint">Skip for now</a>
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
      <div>${icon(s.openai_api_key ? "check" : "alert")} Illustrations: ${s.openai_api_key ? "OpenAI connected" : `not connected yet, so no art can be generated. <a href="#/setup/2">Connect</a>`}</div>
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

// ---------- updates (installed Windows app only: the server says whether it's enabled) ----------
async function checkForUpdate() {
  const done = sessionStorage.getItem("mb-updated-to");
  let u;
  try { u = await api("GET", "/api/update"); } catch { return; }
  if (done) {
    sessionStorage.removeItem("mb-updated-to");
    if (u.current === done) toast(`MosiBooks is updated to version ${done}`);
    else toast("The update didn't install. Your books are fine; try again later.", true);
    return;
  }
  if (!u.enabled || !u.available || sessionStorage.getItem("mb-update-later") === u.latest) return;
  const notes = (u.notes || "").trim();
  const ok = await modal({ title: `MosiBooks ${u.latest} is ready`,
    body: `You have version ${esc(u.current)}. Updating to version ${esc(u.latest)} takes a minute or two. Your books and settings stay as they are.`
      + (notes ? `</p><p class="update-notes" dir="auto">${esc(notes)}` : ""),
    confirm: `Update to ${u.latest}` });
  if (!ok) { sessionStorage.setItem("mb-update-later", u.latest); return; }
  runUpdate(u.latest);
}

async function runUpdate(target) {
  const root = document.getElementById("modal-root");
  const show = (title, text, spin = true) => {
    root.innerHTML = `<div class="backdrop"><div class="modal" role="alertdialog" aria-modal="true" aria-labelledby="u-t" aria-live="polite">
      <div class="mb"><h2 id="u-t">${spin ? '<span class="spin"></span> ' : ""}${esc(title)}</h2><p>${esc(text)}</p></div></div></div>`;
  };
  show(`Downloading version ${target}`, "Keep this page open. MosiBooks will restart by itself.");
  try {
    await api("POST", "/api/update/apply");
  } catch (e) { root.innerHTML = ""; toast(e.message, true); return; }
  sessionStorage.setItem("mb-updated-to", target);
  show(`Installing version ${target}`, "MosiBooks is closing, installing the new version and starting again. This page reloads by itself.");
  const alive = () => fetch("/api/auth/status", { cache: "no-store" }).then((r) => r.ok, () => false);
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const t0 = Date.now();
  while (await alive() && Date.now() - t0 < 30000) await wait(1000);   // until the old app has stopped
  while (Date.now() - t0 < 15 * 60000) {
    await wait(2000);
    if (await alive()) { location.reload(); return; }
  }
  show("The update is taking too long", "Close this page, then open MosiBooks from the desktop icon.", false);
}
checkForUpdate();
