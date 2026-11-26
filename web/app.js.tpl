/* Demo walidatora importu ERP: cały plik jako arkusz, obok panel z przebiegiem, podsumowaniem i szczegółami.
   Strona czyta wyłącznie zapisane wyniki z data/ (scripts/export_web.py): bez backendu i bez kluczy.
   "Pokaż wynik walidacji" odtwarza prawdziwy zapis przebiegu narzędzia, oznaczony jako nagranie. */
"use strict";

const REPLAY_MS = 3400;
const reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
/* telefon i tablet: bez przewijania wewnątrz okna, krótka lista wierszy, otwarty wiersz na cały ekran */
const narrow = window.matchMedia("(max-width: 1023px)");
const SHORT_LIST = 12;
const nf = new Intl.NumberFormat("pl-PL");
const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => [...root.querySelectorAll(sel)];
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const STATUS = {
  ready: { cls: "st--ready", short: "Gotowy", long: "Gotowy do importu" },
  review: { cls: "st--review", short: "Do weryfikacji", long: "Do ręcznej weryfikacji" },
  skipped: { cls: "st--skip", short: "Pominięty", long: "Pominięty duplikat" },
  queued: { cls: "st--queued", short: "W kolejce", long: "W kolejce" },
};
const LOG_ICON = { ok: "✓", warn: "!", error: "!", review: "?", step: "→" };

/* etap wiersza: 0 = jak w pliku, 1 = po regułach (czeka na AI), 2 = wynik końcowy */
const state = { cache: new Map(), file: "01", data: null, filter: "all", selected: null, stage: {}, flash: new Set(),
  busy: false, done: false, repo: null };

function plural(n, one, few, many) {
  const d = n % 10, h = n % 100;
  const w = n === 1 ? one : d >= 2 && d <= 4 && (h < 12 || h > 14) ? few : many;
  return `${nf.format(n)} ${w}`;
}
const word = (n, one, few, many) => plural(n, one, few, many).replace(/^\S+\s/, "");
const pct = (x) => `${Math.round(x * 100)}%`;
const secs = (s) => `${new Intl.NumberFormat("pl-PL", { minimumFractionDigits: 1, maximumFractionDigits: 1 }).format(s)} s`;
const when = (iso) => new Date(iso).toLocaleDateString("pl-PL", { day: "numeric", month: "long", year: "numeric" });

async function load(id) {
  if (!state.cache.has(id)) {
    const res = await fetch(`data/${id}.json`, { cache: "no-cache" });
    if (!res.ok) throw new Error(`data/${id}.json: HTTP ${res.status}`);
    state.cache.set(id, await res.json());
  }
  return state.cache.get(id);
}

/* --- liczby i filtr ------------------------------------------------------------------------ */

const stageOf = (r) => state.stage[r.row] ?? 0;

function counts(data) {
  const c = { rows_in: data.rows.length, ready: 0, review: 0, skipped: 0, fixed_rows: 0 };
  for (const r of data.rows) {
    if (stageOf(r) === 2) c[r.status] += 1;
    if (stageOf(r) >= 1 && r.fixed) c.fixed_rows += 1;
  }
  return c;
}

function renderStats(bump = []) {
  const c = counts(state.data);
  $("#stats").classList.toggle("is-idle", !state.done && !state.busy);
  for (const el of $$("[data-stat]")) {
    const key = el.dataset.stat;
    const text = nf.format(c[key]);
    if (el.textContent !== text) {
      el.textContent = text;
      if (bump.includes(key) && !reduced.matches) {
        const btn = el.closest(".stat");
        btn.classList.remove("is-bump"); void btn.offsetWidth; btn.classList.add("is-bump");
      }
    }
  }
  for (const btn of $$("#stats .stat")) {
    btn.setAttribute("aria-pressed", String(btn.dataset.filter === state.filter));
    btn.setAttribute("aria-disabled", String(!state.done));
  }
}

const inFilter = (r) => !state.done || state.filter === "all" || (state.filter === "fixed" ? r.fixed : r.status === state.filter);

/* --- arkusz -------------------------------------------------------------------------------- */

/* Co pokazuje komórka na danym etapie: wartość z pliku albo wynik walidacji i jego kolor. */
function cellView(r, c) {
  const stage = stageOf(r);
  const shown = c.source === "AI" ? stage >= 2 : stage >= 1;
  if (!shown) return { text: c.before, cls: [], title: "", tag: "" };
  if (c.state === "changed") {
/*{{etykieta_zrodla}}*/
    return { text: c.after, cls: ["is-fix"], title: `W pliku: ${c.before.trim() || "(puste)"}, zmiana: ${c.source}`, tag };
  }
  if (c.state === "error") {
    const issue = r.issues.find((i) => i.field === c.label && i.severity === "critical");
    return { text: c.before || "(puste)", cls: ["is-todo"], title: issue ? issue.title : "do poprawy", tag: "" };
  }
  if (c.state === "warning") {
    const issue = r.issues.find((i) => i.field === c.label && i.severity === "warning");
    return { text: c.after || c.before, cls: ["is-warn"], title: issue ? issue.title : "", tag: "" };
  }
  return { text: c.after, cls: [], title: "", tag: "" };
}

function cellHtml(r, c) {
  const v = cellView(r, c);
  if (c.key === "price") v.cls.push("is-num");
  if (c.key === "ean") v.cls.push("is-mono");
  return `<td class="${v.cls.join(" ")}"${v.title ? ` title="${esc(v.title)}"` : ""}>${esc(v.text)}${tagHtml(v.tag)}</td>`;
}

function tagHtml(tag) {
  if (!tag) return "";
/*{{etykieta_zrodla_2}}*/
}

function statusHtml(r) {
  const stage = stageOf(r);
  if (stage === 0) return '<td class="sheet__st"></td>';
  const st = STATUS[stage === 2 ? r.status : "queued"];
  return `<td class="sheet__st"><span class="st ${st.cls}">${st.short}</span></td>`;
}

function rowHtml(r, i) {
  const name = cellView(r, r.cells[0]);
  const current = state.selected === r.row ? ' aria-current="true"' : "";
  const flash = state.flash.has(r.row) ? ` class="is-new" style="--i:${Math.min(i, 24)}"` : "";
  const st = stageOf(r) === 2 ? r.status : stageOf(r) === 1 ? "queued" : "";
  return `<tr data-row="${r.row}"${st ? ` data-st="${st}"` : ""}${flash}${current}>
    <th scope="row" class="sheet__n">${r.row}</th>
    <td class="sheet__name ${name.cls.join(" ")}"${name.title ? ` title="${esc(name.title)}"` : ""}><button type="button" class="sheet__open" data-row="${r.row}" title="${esc(name.text.trim())}"${state.done ? "" : ' tabindex="-1"'}>${esc(name.text.trim() || "(brak nazwy)")}</button>${tagHtml(name.tag)}</td>
    ${r.cells.slice(1).map((c) => cellHtml(r, c)).join("")}
    ${statusHtml(r)}</tr>`;
}

function renderSheet() {
  let rows = state.data.rows.filter(inFilter);
  const total = rows.length;
  const cut = narrow.matches && !state.expanded && total > SHORT_LIST + 3;
  if (cut) rows = rows.slice(0, SHORT_LIST);
  $("#rows").innerHTML = rows.length ? rows.map(rowHtml).join("")
/*{{kolspan}}*/
  $("#sheet").classList.toggle("is-done", state.done);
  state.flash.clear();
  const more = $("#sheet-more");
  more.hidden = !cut;
  if (cut) $("button", more).textContent = `Pokaż wszystkie wiersze (${total})`;
}

/* na telefonie i tablecie otwarty wiersz to okno na cały ekran (#row-sheet, poza oknem narzędzia,
   więc przykrywa też nawigację); panel pod spodem zostaje z podsumowaniem */
const sheetOpen = () => !$("#row-sheet").hidden;
function setOverlay(on) {
  const box = $("#row-sheet");
  box.hidden = !on;
  document.documentElement.classList.toggle("has-overlay", on);
  if (on) { box.scrollTop = 0; $(".rd__back", box)?.focus({ preventScroll: true }); }
  else box.innerHTML = "";
}

function setStage(rows, stage) {
  for (const r of rows) {
    if (stageOf(r) < stage) { state.stage[r.row] = stage; state.flash.add(r.row); }
  }
}

/* --- panel: przycisk, zapis przebiegu, podsumowanie, szczegóły wiersza ---------------------------- */

function renderCta(data) {
  setOverlay(false);
  $("#open").innerHTML = `<div class="cta ui ui-cta">
    <p class="cta__file">${esc(data.file)}, ${plural(data.rows.length, "wiersz", "wiersze", "wierszy")}</p>
    <p class="cta__title">Tak wygląda plik przed walidacją</p>
    <button type="button" class="cta__btn" id="run"><svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7-4.5z"/></svg><span>Pokaż wynik walidacji</span></button>
    <p class="cta__hint">Odtwarza zapis prawdziwego przebiegu, około 3 sekund.</p>
  </div>`;
}

function renderSummary(data) {
  setOverlay(false);
  const s = data.summary;
  const fixes = Object.entries(data.fixes_by_field || {});
  const mode = data.run.mode === "ai" ? "tryb AI" : "tryb bez AI";
  const groups = (data.review_groups || []).map((g) => `<li><p>${esc(g.title)}</p><div class="sum__rows">
      ${g.rows.map((n) => `<button type="button" data-goto="${n}" aria-label="Wiersz ${n}">${n}</button>`).join("")}</div></li>`).join("");
  $("#open").innerHTML = `<div class="sum ui ui-sum">
    <h3 class="sum__title">Gotowe do importu: ${nf.format(s.ready)} z ${plural(s.rows_in, "wiersza", "wierszy", "wierszy")}</h3>
    <p class="sum__lead">${plural(s.review, "wiersz czeka", "wiersze czekają", "wierszy czeka")} na człowieka.${s.skipped ? ` ${plural(s.skipped, "zduplikowany wiersz pominięty", "zduplikowane wiersze pominięte", "zduplikowanych wierszy pominiętych")}.` : ""}</p>
/*{{zrodla}}*/
    <div class="sum__box"><h4>Poprawione automatycznie: ${plural(s.fixes, "zmiana", "zmiany", "zmian")} w ${plural(s.fixed_rows, "wierszu", "wierszach", "wierszach")}, w tym ${nf.format(s.from_sources)} z kartoteki i cennika</h4>
      <ul class="sum__fixes">${fixes.map(([k, n]) => `<li><span>${esc(k)}</span><b>${nf.format(n)}</b></li>`).join("")}</ul></div>
    ${groups ? `<div class="sum__box sum__box--todo"><h4>Do ręcznej weryfikacji, według powodu</h4><ul class="sum__groups">${groups}</ul></div>` : ""}
    <p class="sum__hint">Kliknij wiersz w arkuszu albo jego numer powyżej, żeby zobaczyć wartości przed i po.</p>
    <p class="sum__meta">${esc(data.file)}, nagranie z ${when(data.run.recorded_at)}, ${mode}, ${secs(data.run.duration_s)}</p>
  </div>`;
  $("#open").scrollTop = 0;
}

function verdict(r) {
  const fixes = r.cells.filter((c) => c.state === "changed" && c.key !== "category").length;
  if (r.status === "skipped") return `Pominięty: identyczny z wierszem ${r.duplicate_of}, więc w imporcie byłby tym samym produktem drugi raz.`;
  if (r.data_error) {
    const n = r.issues.filter((i) => i.severity === "critical").length;
    return `Do ręcznej weryfikacji: ${plural(n, "wartość wymaga", "wartości wymagają", "wartości wymaga")} poprawy. Po poprawce wiersz trafia do importu, reszta jego danych jest już gotowa.`;
  }
  if (r.status === "review") return "Do ręcznej weryfikacji: narzędzie nie zgaduje, więc decyzję podejmuje człowiek.";
/*{{werdykt}}*/
    : r.ai ? ` Nowy produkt: kategorię przypisało AI z pewnością ${pct(r.ai.confidence)}.` : "";
  return `Trafia do pliku importu${fixes ? ` po ${plural(fixes, "poprawce", "poprawkach", "poprawkach")}` : " bez zmian"}.${how}`;
}

/* Diff na poziomie slow: podswietla wylacznie to, co sie naprawde zmienilo.
   Bez tego drobna poprawka wyglada, jakby obok przekreslonej wartosci wpisano
   prawie to samo. Najdluzszy wspolny podciag slow, reszta to zmiany. */
function slowaDiff(a, b) {
  const A = String(a).split(/(\s+)/), B = String(b).split(/(\s+)/);
  const n = A.length, m = B.length;
  const dp = Array.from({ length: n + 1 }, () => new Uint16Array(m + 1));
  for (let i = n - 1; i >= 0; i--) {
    for (let j = m - 1; j >= 0; j--) {
      dp[i][j] = A[i] === B[j] ? dp[i + 1][j + 1] + 1 : Math.max(dp[i + 1][j], dp[i][j + 1]);
    }
  }
  const zA = new Array(n).fill(false), zB = new Array(m).fill(false);
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (A[i] === B[j]) { i++; j++; }
    else if (dp[i + 1][j] >= dp[i][j + 1]) zA[i++] = true;
    else zB[j++] = true;
  }
  while (i < n) zA[i++] = true;
  while (j < m) zB[j++] = true;
  const zloz = (cz, zm) => cz.map((t, k) => (zm[k] && t.trim() ? `<mark>${esc(t)}</mark>` : esc(t))).join("");
  return [zloz(A, zA), zloz(B, zB)];
}


function diffCells(c, issues) {
  const before = c.before === "" ? `<div class="diff__v is-empty">(puste)</div>` : null;
  const fieldIssue = issues.find((i) => i.field === c.label && i.severity !== "fixed");
  const src = c.source ? `<span class="diff__src${c.source === "AI" ? " diff__src--ai" : ""}">${esc(c.source)}</span>` : "";
  if (c.state === "error") {
    // wartość do poprawy nie jest przekreślona: narzędzie jej nie zmieniło
    return `${before || `<div class="diff__v is-bad">${esc(c.before)}</div>`}
      <div class="diff__v is-err">${esc(fieldIssue ? fieldIssue.title : "do poprawy")}</div>`;
  }
  if (c.state === "warning") {
    return `${before || `<div class="diff__v">${esc(c.before)}</div>`}
      <div class="diff__v is-warn">${esc(c.after || c.before)}${fieldIssue ? ` <span>(${esc(fieldIssue.title.toLowerCase())})</span>` : ""}</div>`;
  }
  if (c.state === "changed") {
    const [przed, po] = slowaDiff(c.before, c.after);
    return `${before || `<div class="diff__v is-del">${przed}</div>`}
      <div class="diff__v is-add">${po}${src}</div>`;
  }
  return `${before || `<div class="diff__v">${esc(c.before)}</div>`}
    <div class="diff__v${c.after === "" ? " is-empty" : ""}">${c.after === "" ? "(puste)" : esc(c.after)}</div>`;
}

function renderDetail(r) {
  const st = STATUS[r.status];
  const warnings = r.issues.filter((i) => i.severity === "warning");
  const fixed = r.issues.filter((i) => i.severity === "fixed").length;
/*{{kartoteka}}*/
  const ai = r.ai ? `<div class="rd__box"><h4>Ocena AI nowego produktu (tylko nazwa i opis)</h4>
      <div class="rd__ai"><b>${esc(r.ai.category)}</b><span class="rd__conf">pewność ${pct(r.ai.confidence)}</span><span class="rd__conf">segment ${esc(r.ai.segment)}</span></div>
      <p class="rd__why">„${esc(r.ai.reasoning)}”</p></div>` : "";
  const todo = r.reasons.length ? `<div class="rd__box rd__box--todo"><h4>Do sprawdzenia przez człowieka</h4><ul class="rd__issues">
      ${r.reasons.map((x) => `<li><p>${esc(x)}</p></li>`).join("")}</ul></div>` : "";
  const notes = warnings.length || fixed ? `<div class="rd__box"><h4>Co jeszcze zrobiło narzędzie</h4><ul class="rd__issues">
      ${warnings.map((i) => `<li><p>${esc(i.title)} <span>(${esc(i.field)}${i.detail ? `: ${esc(i.detail)}` : ""})</span></p></li>`).join("")}
      ${fixed ? `<li class="is-fixed"><p>${plural(fixed, "poprawka automatyczna", "poprawki automatyczne", "poprawek automatycznych")} <span>(opisane w raporcie)</span></p></li>` : ""}
    </ul></div>` : "";
  const target = narrow.matches ? $("#row-sheet") : $("#open");
  target.innerHTML = `<article class="rd ui ui-rd">
    <button type="button" class="rd__back" data-back>${narrow.matches ? "Zamknij" : "Podsumowanie pliku"}</button>
    <div class="rd__meta"><span>Wiersz ${r.row}</span><span>${esc(r.sku || "bez SKU")}</span><span class="st ${st.cls}">${st.long}</span></div>
    <h3 class="rd__title">${esc(r.name)}</h3>
    <p class="rd__verdict">${esc(verdict(r))}</p>
    <div class="diff" role="table" aria-label="Wartości z pliku i po walidacji">
      <div class="diff__h diff__h--k" role="columnheader">Pole</div><div class="diff__h" role="columnheader">W pliku</div><div class="diff__h" role="columnheader">Po walidacji</div>
      ${r.cells.map((c) => `<div class="diff__k" role="rowheader">${esc(c.label)}</div>${diffCells(c, r.issues)}`).join("")}
    </div>
    ${todo}${master}${ai}${notes}
  </article>`;
  if (narrow.matches) setOverlay(true);
  else $("#open").scrollTop = 0;
}

function select(rowNo, focus = false) {
  if (!state.done || state.busy) return;
  const r = state.data.rows.find((x) => x.row === rowNo);
  if (!r) return;
  if (!inFilter(r)) { state.filter = "all"; renderSheet(); renderStats(); }
  state.selected = rowNo;
  $$("#rows tr[data-row]").forEach((tr) => {
    if (Number(tr.dataset.row) === rowNo) tr.setAttribute("aria-current", "true");
    else tr.removeAttribute("aria-current");
  });
  renderDetail(r);
  const tr = $(`#rows tr[data-row="${rowNo}"]`);
  if (tr) {
    // przewiń tylko arkusz, nie całą stronę
    const wrap = $("#sheet-wrap"), head = $("#sheet thead").offsetHeight;
    if (tr.offsetTop - head < wrap.scrollTop) wrap.scrollTop = tr.offsetTop - head;
    else if (tr.offsetTop + tr.offsetHeight > wrap.scrollTop + wrap.clientHeight) wrap.scrollTop = tr.offsetTop + tr.offsetHeight - wrap.clientHeight;
    if (focus) $(".sheet__open", tr)?.focus({ preventScroll: true });
  }
}

function backToSummary() {
  state.selected = null;
  $$("#rows tr[aria-current]").forEach((tr) => tr.removeAttribute("aria-current"));
  if (sheetOpen()) setOverlay(false);          // telefon: pod oknem nadal jest podsumowanie
  else renderSummary(state.data);
}

/* --- zapis przebiegu ------------------------------------------------------------------------- */

function logLine(e, isNew) {
  // "[1/3] Reguły walidacji..." z CLI: numer kroku jako plakietka
  const text = esc(e.text).replace(/^\[(\d\/\d)\]\s*/, '<span class="rl__step">$1</span>');
  return `<li class="rl rl--${esc(e.kind)}${isNew ? " is-new" : ""}"><span class="rl__t">${e.t == null ? "" : e.t.toFixed(2).replace(".", ",") + " s"}</span>`
    + `<span class="rl__i" aria-hidden="true">${LOG_ICON[e.kind] || ""}</span><span class="rl__x">${text}</span></li>`;
}

function renderLogShell(data) {
  setOverlay(false);
  const mode = data.run.mode === "ai" ? "tryb AI" : "tryb bez AI";
  $("#open").innerHTML = `<div class="rlog ui ui-log"><div class="rlog__head"><b>Zapis przebiegu narzędzia</b>
    <span>${esc(data.file)}, nagranie z ${when(data.run.recorded_at)}, ${mode}, rzeczywisty czas ${secs(data.run.duration_s)}</span></div>
    <ol class="rlog__lines" id="rlog"></ol></div>`;
}

function schedule(log) {
  const d = log.map((e, i) => (i ? Math.max(e.t - log[i - 1].t, 0) : 0));
  const total = d.reduce((a, b) => a + b, 0) || 1;
  const base = (REPLAY_MS * 0.5) / log.length;
  return d.map((x) => base + (REPLAY_MS * 0.5 * x) / total);
}

function setBusy(busy) {
  state.busy = busy;
  $("#app").classList.toggle("is-busy", busy);
  $$("#files [data-file]").forEach((b) => b.setAttribute("aria-disabled", String(busy)));
}

function resetFile(data) {
  state.data = data;
  state.done = false;
  state.filter = "all";
  state.selected = null;
  state.stage = {};
  state.expanded = false;
  renderSheet(); renderStats(); renderDownloads(data);
  $("#sheet-wrap").scrollTop = 0;
}

async function replay() {
  if (state.busy) return;
  setBusy(true);
  try {
    const data = await load(state.file);
    resetFile(data);
    renderLogShell(data);
    const list = $("#rlog");
    const pane = $("#open");
    const direct = data.rows.filter((r) => !r.to_ai);      // kartoteka, błąd w danych albo duplikat
    const toAi = data.rows.filter((r) => r.to_ai);
    const isBatch = (t) => /^partia \d+\/\d+/.test(t);
    const batches = Math.max(1, data.log.filter((e) => isBatch(e.text)).length);
    const per = Math.ceil(toAi.length / batches);
    let batch = 0;
    const delays = reduced.matches ? data.log.map(() => 0) : schedule(data.log);
    const wait = () => logLine({ kind: "wait", text: "oczekiwanie na odpowiedź modelu" }, true);

    for (let i = 0; i < data.log.length; i += 1) {
      const e = data.log[i];
      list.querySelector(".rl--wait")?.remove();
      list.insertAdjacentHTML("beforeend", logLine(e, !reduced.matches));
      if (e.kind === "ok" && /poprawk/.test(e.text) && batch === 0) {
        // reguły: formaty poprawione w całym arkuszu naraz, wiersze czekają na AI
        setStage(data.rows, 1); renderSheet(); renderStats(["fixed_rows"]);
      }
      if (e.kind === "step" && e.text.startsWith("[2/3]")) {
        // AI nie jest potrzebne dla produktów z kartoteki, duplikatów i wierszy z błędem w danych: mają już wynik
        setStage(data.rows, 1); setStage(direct, 2); renderSheet(); renderStats(["ready", "review", "fixed_rows"]);
        if (data.run.mode === "ai" && toAi.length) list.insertAdjacentHTML("beforeend", wait());
      }
      if (isBatch(e.text) || e.text.startsWith("tryb mock")) {
        const chunk = e.text.startsWith("tryb mock") ? toAi : toAi.slice(batch * per, (batch + 1) * per);
        batch += 1;
        setStage(chunk, 2); renderSheet(); renderStats(["ready", "review"]);
        if (data.run.mode === "ai" && batch < batches) list.insertAdjacentHTML("beforeend", wait());
      }
      pane.scrollTop = pane.scrollHeight;
      if (delays[i + 1]) await sleep(delays[i + 1]);
    }
    setStage(data.rows, 2);
    await sleep(reduced.matches ? 0 : 700);
    state.done = true;
    renderSheet(); renderStats();
    renderSummary(data);
    const s = data.summary;
    announce(`Wynik dla pliku ${data.file}: ${s.rows_in} wierszy, ${s.ready} gotowych do importu, ${s.review} do ręcznej weryfikacji.`);
  } catch (err) {
    showError(err);
  } finally {
    setBusy(false);
  }
}

/* zmiana pliku: surowy arkusz i przycisk; walidację uruchamia dopiero przycisk */
async function chooseFile(id) {
  if (state.busy) return;
  state.file = id;
  $$("#files [data-file]").forEach((b) => b.setAttribute("aria-checked", String(b.dataset.file === id)));
  try {
    const data = await load(id);
    resetFile(data);
    renderCta(data);
  } catch (err) {
    showError(err);
  }
}

function renderDownloads(data) {
  for (const a of $$("[data-download]")) {
    const href = data.downloads[a.dataset.download];
    if (href) { a.href = href; a.setAttribute("download", href.split("/").pop()); }
  }
}

/* --- pomocnicze ----------------------------------------------------------------------------- */

function announce(text) {
  let el = $("#sr-live");
  if (!el) {
    el = document.createElement("p");
    el.id = "sr-live"; el.className = "sr-only"; el.setAttribute("aria-live", "polite");
    document.body.append(el);
  }
  el.textContent = text;
}

function showError(err) {
  const msg = location.protocol === "file:"
    ? "Strona jest otwarta prosto z dysku, więc przeglądarka blokuje wczytanie wyników. Uruchom w folderze web polecenie python -m http.server 8000 i otwórz http://localhost:8000."
    : `Nie udało się wczytać zapisanych wyników (${err.message}). Odśwież stronę.`;
  $("#open").innerHTML = `<div class="rd ui ui-rd"><p class="rd__verdict" style="margin:0">${esc(msg)}</p></div>`;
}

async function setupRepo() {
  try {
    const index = await (await fetch("data/index.json", { cache: "no-cache" })).json();
    state.repo = index.repo_url;
  } catch { /* linki zostają domyślne */ }
  if (!state.repo) return;
  $$("[data-repo]").forEach((a) => { a.href = state.repo; });
}

async function init() {
  setupRepo();
  $("#files").addEventListener("click", (e) => { const b = e.target.closest("[data-file]"); if (b) chooseFile(b.dataset.file); });
  $("#files").addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight"].includes(e.key) || state.busy) return;
    const btns = $$("#files [data-file]"); const i = btns.findIndex((b) => b.dataset.file === state.file);
    const next = btns[(i + (e.key === "ArrowRight" ? 1 : btns.length - 1)) % btns.length];
    next.focus(); chooseFile(next.dataset.file);
  });
  $("#open").addEventListener("click", (e) => {
    if (e.target.closest("#run")) replay();
    else if (e.target.closest("[data-back]")) backToSummary();
    else { const g = e.target.closest("[data-goto]"); if (g) select(Number(g.dataset.goto)); }
  });
  $("#stats").addEventListener("click", (e) => {
    const b = e.target.closest("[data-filter]"); if (!b || !state.done || state.busy) return;
    state.filter = b.dataset.filter; renderSheet(); renderStats();
    $("#sheet-wrap").scrollTop = 0;
  });
  $("#rows").addEventListener("click", (e) => { const tr = e.target.closest("tr[data-row]"); if (tr) select(Number(tr.dataset.row)); });
  $("#rows").addEventListener("keydown", (e) => {
    if (!["ArrowDown", "ArrowUp"].includes(e.key) || !state.done) return;
    const btns = $$("#rows .sheet__open"); const i = btns.indexOf(document.activeElement); if (i < 0) return;
    e.preventDefault();
    const next = btns[Math.min(btns.length - 1, Math.max(0, i + (e.key === "ArrowDown" ? 1 : -1)))];
    select(Number(next.dataset.row), true);
  });
  $("#sheet-more").addEventListener("click", () => { state.expanded = true; renderSheet(); });
  $("#row-sheet").addEventListener("click", (e) => { if (e.target.closest("[data-back]")) backToSummary(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape" && sheetOpen()) backToSummary(); });
  narrow.addEventListener("change", () => { if (state.data) renderSheet(); if (!narrow.matches && sheetOpen()) setOverlay(false); });
  // "Pokaż wynik walidacji" w nawigacji, hero i pasku na telefonie: skok do okna i odtworzenie zapisu
  $$("a[data-run]").forEach((a) => a.addEventListener("click", () => setTimeout(replay, reduced.matches ? 0 : 450)));

  await chooseFile(state.file);
}

init();
