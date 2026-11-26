/* Page CSS: tylko to, co siedzi wewnątrz wizualizacji i czego zestaw nie ma.
   Dwa wyniki wiersza: gotowy do importu (zieleń) albo do ręcznej weryfikacji (bursztyn).
   W arkuszu: zielona komórka = poprawka narzędzia, bursztynowa = wartość do sprawdzenia przez człowieka. */

:root {
  --ok-ink: #17663e;  --ok-bg: #e6f4ec;  --ok-ring: #c3e3d0;  --ok-text: #124d30;
  --bad-ink: #a3261c; --bad-bg: #fcebea;
  --wait-ink: #8a5300; --wait-bg: #fdf2dc; --wait-ring: #f1d9a6; --wait-text: #6b4100;
}

/* --- chip wyniku ----------------------------------------------------------------------------- */
.st {
  display: inline-flex; align-items: center; gap: 6px; height: 24px; padding: 0 9px; border-radius: 999px;
  font: 500 12.5px/1 var(--font-text); white-space: nowrap;
  color: var(--u-muted, #555); box-shadow: inset 0 0 0 1px var(--u-line-2, rgb(0 0 0 / .15));
}
.st::before { content: ""; width: 6px; height: 6px; border-radius: 50%; background: currentColor; flex: none; }
.st.st--ready, .ui-win__st.st--ready { color: var(--ok-ink); background: var(--ok-bg); box-shadow: inset 0 0 0 1px var(--ok-ring); }
.st.st--review, .ui-win__st.st--review { color: var(--wait-ink); background: var(--wait-bg); box-shadow: inset 0 0 0 1px var(--wait-ring); }
.st.st--skip { color: var(--u-muted); background: var(--u-fill-2); }
.st.st--queued { color: var(--u-soft); }
.st.st--queued::before { background: none; width: 8px; height: 8px; border: 1.5px solid color-mix(in oklab, currentColor 30%, transparent); border-top-color: currentColor; animation: ui-spin 800ms linear infinite; }

/* --- hero: okno z wierszami pliku i karta z wynikiem ------------------------------------- */
.hero__art .ui-win { width: 100%; }
.hero__art .ui-win__body { min-height: 0; }
.hero__art .ui-win__main { padding-right: var(--ly-cut-room, 48px); }
@media (max-width: 639px) {
  .hero__art .ui-win__side { display: none; }
  .hero__art .ui-win__body { grid-template-columns: minmax(0, 1fr); }
  .hero__proof { display: none; }          /* telefon: hero mieści się w jednym ekranie */
}
/* wiersz w dwóch liniach: nazwa nad tym, co się stało; status po prawej */
.hero-rows .ui-win__row { grid-template-columns: 26px minmax(0, 1fr) auto; grid-template-rows: auto auto; row-gap: 2px; height: auto; min-height: 58px; padding-block: 9px; }
.hero-rows .ui-avatar { grid-row: 1 / 3; font: 500 11px/1 var(--font-mono); }
.hero-rows .ui-win__who { grid-column: 2; grid-row: 1; font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hero-rows .ui-win__sub { grid-column: 2; grid-row: 2; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.hero-rows .ui-win__st { grid-column: 3; grid-row: 1 / 3; }
.hero-rows .ui-win__age { display: none; }
.hero__art > .ly-piece--note { left: var(--s-6); bottom: var(--s-6); width: 312px; z-index: 2; }
.result-card { padding: 14px 16px 10px; font-size: 13px; }
.result-card__head { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding-bottom: 8px; }
.result-card__head b { font-weight: 500; font-size: 14px; }
.result-card__line { display: flex; align-items: center; gap: 10px; padding: 8px 0; border-top: 1px solid var(--u-line); color: var(--u-text-2); }
.result-card__line i { width: 18px; height: 18px; border-radius: 50%; flex: none; display: grid; place-items: center; background: var(--ok-bg); color: var(--ok-ink); font: 600 11px/1 var(--font-text); font-style: normal; }
.result-card__line b { font-weight: 500; color: var(--u-ink); }
@media (max-width: 1023px) { .hero__art > .ly-piece--note { left: var(--s-4); bottom: var(--s-4); width: 280px; } }

/* --- okno aplikacji: pasek, liczby, arkusz i panel ----------------------------------------- */
#wynik .app-intro p { color: var(--ink); }
.app-intro .link { justify-self: start; }
.app.ui {
  display: grid; grid-template-columns: minmax(0, 1fr) 340px; grid-template-rows: auto auto minmax(0, 1fr);
  margin-top: var(--s-7); background: var(--u-bg); border: 1px solid var(--u-border); border-radius: var(--u-r);
  box-shadow: var(--u-shadow); overflow: hidden; overflow: clip;
}
.app__bar {
  grid-column: 1 / -1; display: flex; align-items: center; gap: 14px; min-height: 56px; padding: 8px 12px 8px 16px;
  border-bottom: 1px solid var(--u-line); background: var(--u-fill);
}
.app__files { display: inline-flex; gap: 2px; padding: 3px; border-radius: 10px; background: var(--u-fill-2); }
.app__files button {
  height: 34px; padding: 0 14px; border: 0; border-radius: 8px; background: none; cursor: pointer;
  font: 500 13.5px/1 var(--font-text); color: var(--u-muted); white-space: nowrap;
}
.app__files button:hover { color: var(--u-ink); background: color-mix(in oklab, var(--u-bg) 60%, transparent); }
.app__files button[aria-checked="true"] { background: var(--u-bg); color: var(--u-ink); box-shadow: var(--u-shadow-sm); }
.app__files button[aria-disabled="true"] { cursor: progress; }
.app__dl { display: flex; flex-wrap: wrap; gap: 6px; }
.app__dl a {
  display: inline-flex; align-items: center; gap: 6px; height: 32px; padding: 0 10px; border-radius: 8px;
  font: 500 13px/1 var(--font-text); color: var(--u-ink); text-decoration: none; box-shadow: inset 0 0 0 1px var(--u-line-2); background: var(--u-bg);
}
.app__dl a::before { content: ""; width: 10px; height: 10px; flex: none;
  background: currentColor; -webkit-mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10'%3E%3Cpath d='M5 1v5.5M2.5 4.5 5 7l2.5-2.5M1.5 9h7' fill='none' stroke='%23000' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat;
  mask: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 10 10'%3E%3Cpath d='M5 1v5.5M2.5 4.5 5 7l2.5-2.5M1.5 9h7' fill='none' stroke='%23000' stroke-width='1.4' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E") center / contain no-repeat; }
.app__dl a:hover { background: var(--u-fill); }

/* krótkie etykiety na telefonie; pełna nazwa zostaje dla czytnika ekranu */
.t-narrow { display: none; }

.app__stats { grid-column: 1 / -1; display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); border-bottom: 1px solid var(--u-line); }
.stat {
  position: relative; display: grid; gap: 6px; justify-items: start; padding: 14px 20px 12px; border: 0;
  border-right: 1px solid var(--u-line); background: none; text-align: left; cursor: pointer; color: var(--u-ink);
}
.stat:last-child { border-right: 0; }
.stat:hover { background: var(--u-fill); }
.stat[aria-disabled="true"] { cursor: default; }
.stat[aria-disabled="true"]:hover { background: none; }
.stat__n { font: 500 34px/1 var(--font-display); letter-spacing: -0.035em; font-variant-numeric: tabular-nums; transition: color 300ms var(--u-ease); }
.stat__l { font-size: 13px; line-height: 16px; color: var(--u-muted); }
.stat--ready .stat__n { color: var(--ok-ink); }
.stat--review .stat__n { color: var(--wait-ink); }
.app__stats.is-idle .stat:not([data-filter="all"]) .stat__n { color: var(--u-soft); }
.stat[aria-pressed="true"]:not([aria-disabled="true"]) { background: var(--u-fill); }
.stat[aria-pressed="true"]:not([aria-disabled="true"])::after { content: ""; position: absolute; inset: auto 0 -1px; height: 2px; background: var(--u-ink); }
.stat--ready[aria-pressed="true"]::after { background: var(--ok-ink); }
.stat--review[aria-pressed="true"]::after { background: var(--wait-ink); }
.stat.is-bump .stat__n { animation: stat-bump 420ms var(--u-spring); }
@keyframes stat-bump { 0% { transform: translateY(4px); opacity: .4; } 100% { transform: none; opacity: 1; } }

/* arkusz: cały plik, nagłówek i kolumna nazw zostają na miejscu przy przewijaniu */
.app__sheet { position: relative; min-width: 0; min-height: 0; overflow: auto; overscroll-behavior: contain; border-right: 1px solid var(--u-line); }
/*{{szerokosc_tabeli}}*/
.sheet th, .sheet td { height: 38px; padding: 0 10px; border-bottom: 1px solid var(--u-line); border-right: 1px solid var(--u-line); text-align: left;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; background: var(--u-bg); transition: background-color 400ms var(--u-ease), color 400ms var(--u-ease); }
.sheet thead th { position: sticky; top: 0; z-index: 2; height: 34px; background: var(--u-fill); font: 500 12px/1 var(--font-text); color: var(--u-muted); }
.sheet th:last-child, .sheet td:last-child { border-right: 0; }
/*{{szerokosci_kolumn}}*/
.sheet thead th:nth-child(3) { width: 150px; }
/*{{szerokosci_kolumn_2}}*/
.sheet .sheet__n { position: sticky; left: 0; z-index: 1; width: 44px; text-align: center; font: 500 12px/1 var(--font-mono); color: var(--u-muted); background: var(--u-fill); }
.sheet thead .sheet__n { z-index: 3; }
.sheet .sheet__name { position: sticky; left: 44px; z-index: 1; box-shadow: 1px 0 0 var(--u-line); }
.sheet tr[data-st="ready"] > .sheet__n { box-shadow: inset 3px 0 0 var(--ok-ink); color: var(--ok-ink); }
.sheet tr[data-st="review"] > .sheet__n { box-shadow: inset 3px 0 0 var(--wait-ink); color: var(--wait-ink); }
.sheet tr[data-st="skipped"] > .sheet__n { box-shadow: inset 3px 0 0 var(--u-line-2); }
/* kolumna Wynik zostaje przy prawej krawędzi, gdy arkusz jest szerszy niż okno (laptopy) */
@media (min-width: 640px) {
  .sheet .sheet__st { position: sticky; right: 0; z-index: 1; box-shadow: -1px 0 0 var(--u-line); }
  .sheet thead .sheet__st { z-index: 3; }
}
.sheet thead .sheet__name { z-index: 3; }
.sheet .sheet__st { width: 120px; }
.sheet .is-num { text-align: right; font-variant-numeric: tabular-nums; }
.sheet .is-mono { font-family: var(--font-mono); font-size: 12px; }
.sheet td.is-fix { background: var(--ok-bg); color: var(--ok-text); }
.sheet td.is-todo { background: var(--wait-bg); color: var(--wait-text); box-shadow: inset 0 0 0 1px var(--wait-ring); }
.sheet td.is-warn { background: #fef8ec; color: var(--wait-text); }
.sheet__open { display: inline-block; max-width: 100%; padding: 0; border: 0; background: none; font: inherit; color: var(--u-ink); text-align: left;
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis; vertical-align: middle; cursor: default; }
.sheet td.is-fix .sheet__open { color: var(--ok-text); }
.sheet td.is-todo .sheet__open { color: var(--wait-text); }
.sheet__name:has(.sheet__ai) .sheet__open { max-width: calc(100% - 34px); }
.sheet__ai { display: inline-block; margin-left: 6px; padding: 2px 4px; border-radius: 4px; vertical-align: 2px;
  font: 600 9px/1 var(--font-text); letter-spacing: .02em; color: var(--u-bg); background: var(--u-ink); }
.sheet__ai--erp { color: var(--ok-ink); background: var(--u-bg); box-shadow: inset 0 0 0 1px var(--ok-ring); }
.sheet .st { height: 22px; padding: 0 8px; font-size: 12px; }
.sheet__empty { padding: 32px 20px !important; text-align: center !important; color: var(--u-muted); white-space: normal !important; }
/* po walidacji wiersz da się otworzyć */
.sheet.is-done tbody tr { cursor: pointer; }
.sheet.is-done .sheet__open { cursor: pointer; }
.sheet.is-done tbody tr:hover > :is(th, td):not(.is-fix, .is-todo, .is-warn) { background: var(--u-fill); }
.sheet tbody tr[aria-current="true"] > * { box-shadow: inset 0 2px 0 var(--u-ink), inset 0 -2px 0 var(--u-ink); }
.sheet tbody tr[aria-current="true"] > .sheet__n { box-shadow: inset 3px 0 0 var(--u-ink), inset 0 2px 0 var(--u-ink), inset 0 -2px 0 var(--u-ink); color: var(--u-ink); }
/* fala zmian w trakcie odtwarzania: każda komórka zapala się mocniej i gaśnie do swojego koloru */
.sheet tr.is-new > td.is-fix { animation: cell-fix 900ms var(--u-ease) both; animation-delay: calc(var(--i, 0) * 22ms); }
.sheet tr.is-new > td.is-todo { animation: cell-todo 900ms var(--u-ease) both; animation-delay: calc(var(--i, 0) * 22ms); }
.sheet tr.is-new > td.sheet__st .st { animation: st-in 360ms var(--u-ease) both; animation-delay: calc(var(--i, 0) * 22ms); }
@keyframes cell-fix { 0% { background: var(--u-bg); color: var(--u-text-2); } 35% { background: #bfe6cf; } 100% { background: var(--ok-bg); } }
@keyframes cell-todo { 0% { background: var(--u-bg); color: var(--u-text-2); } 35% { background: #f8dfa8; } 100% { background: var(--wait-bg); } }
@keyframes st-in { from { opacity: 0; transform: scale(.92); } to { opacity: 1; transform: none; } }

.app > .app__pane { position: relative; min-width: 0; min-height: 0; overflow: auto; overscroll-behavior: contain;
  -webkit-mask-image: linear-gradient(#000 calc(100% - 32px), transparent); mask-image: linear-gradient(#000 calc(100% - 32px), transparent); }
.app > .app__pane > :last-child { padding-bottom: 40px; }

/* panel na starcie i po zmianie pliku: duży przycisk */
.cta { display: grid; place-content: center; justify-items: center; gap: 14px; min-height: 100%; padding: 28px 24px; text-align: center; }
.cta__file { margin: 0; font: 500 12px/1.4 var(--font-mono); color: var(--u-muted); }
.cta__title { margin: -4px 0 4px; max-width: 24ch; font: var(--display-weight) var(--t-lead)/1.3 var(--font-display); letter-spacing: -0.01em; color: var(--u-ink); }
.cta__btn {
  display: inline-flex; align-items: center; gap: 10px; height: 52px; padding: 0 26px; border: 0; border-radius: 12px; cursor: pointer;
  background: var(--u-ink); color: var(--u-bg); font: 500 16px/1 var(--font-text);
  box-shadow: 0 10px 24px -10px color-mix(in oklab, var(--u-ink) 70%, transparent);
  transition: transform 160ms var(--u-ease), box-shadow 160ms var(--u-ease);
}
.cta__btn:hover { transform: translateY(-1px); box-shadow: 0 14px 28px -10px color-mix(in oklab, var(--u-ink) 75%, transparent); }
.cta__btn:active { transform: translateY(1px); }
.cta__btn svg { width: 14px; height: 14px; fill: currentColor; }
.cta__hint { margin: 0; max-width: 34ch; font-size: 13.5px; line-height: 20px; color: var(--u-muted); }

/* panel po odtworzeniu: podsumowanie całego pliku */
.sum { display: grid; align-content: start; gap: 14px; padding: 20px 22px 28px; }
.sum__meta { margin: 4px 0 0; padding-top: 12px; border-top: 1px solid var(--u-line); font: 500 11.5px/1.5 var(--font-mono); color: var(--u-muted); }
.sum__title { margin: 0; font: var(--display-weight) var(--t-lead)/1.25 var(--font-display); letter-spacing: -0.01em; color: var(--u-ink); }
.sum__lead { margin: -6px 0 0; font-size: 14px; line-height: 20px; color: var(--u-ink); }
.sum__sources { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin: 0; }
.sum__sources span { display: grid; gap: 2px; padding: 10px 12px; border-radius: 10px; box-shadow: inset 0 0 0 1px var(--u-line);
  font-size: 12.5px; line-height: 17px; color: var(--u-muted); }
.sum__sources b { font: 500 20px/1.1 var(--font-display); color: var(--u-ink); }
.sum__box { display: grid; gap: 4px; padding: 12px 14px; border-radius: 10px; background: var(--u-fill); }
.sum__box h4, .rd__box h4 { margin: 0 0 4px; font: 500 13px/17px var(--font-text); color: var(--u-muted); }
.sum__box--todo { background: var(--wait-bg); }
/*{{blok_ai}}*/
.sum__box--todo h4 { color: var(--wait-text); }
.sum__fixes, .sum__groups { display: grid; margin: 0; padding: 0; list-style: none; }
.sum__fixes li { display: flex; justify-content: space-between; gap: 12px; padding: 6px 0; border-top: 1px solid var(--u-line); font-size: 13.5px; color: var(--u-ink); }
.sum__fixes li:first-child, .sum__groups li:first-child { border-top: 0; }
.sum__fixes b { font: 500 13px/20px var(--font-mono); color: var(--ok-ink); }
.sum__groups li { display: grid; gap: 6px; padding: 8px 0; border-top: 1px solid var(--wait-ring); }
.sum__groups p { margin: 0; font-size: 13.5px; line-height: 19px; color: var(--wait-text); }
.sum__rows { display: flex; flex-wrap: wrap; gap: 4px; }
.sum__rows button { min-width: 32px; height: 28px; padding: 0 7px; border: 0; border-radius: 7px; cursor: pointer;
  background: var(--u-bg); box-shadow: inset 0 0 0 1px var(--wait-ring); font: 500 12px/1 var(--font-mono); color: var(--wait-text); }
.sum__rows button:hover { background: #fffaf0; box-shadow: inset 0 0 0 1px var(--wait-ink); }
.sum__hint { margin: 0; font-size: 13px; line-height: 19px; color: var(--u-muted); }

/* panel: otwarty wiersz, wartość z pliku i po walidacji */
.rd { display: grid; gap: 18px; padding: 16px 22px 28px; }
.rd__back { justify-self: start; display: inline-flex; align-items: center; gap: 8px; height: 30px; padding: 0 10px; border: 0; border-radius: 8px;
  background: var(--u-fill); font: 500 13px/1 var(--font-text); color: var(--u-ink); cursor: pointer; }
.rd__back::before { content: ""; width: 6px; height: 6px; border-left: 1.5px solid currentColor; border-bottom: 1.5px solid currentColor; transform: rotate(45deg); margin-left: 2px; }
.rd__back:hover { background: var(--u-fill-2); }
.rd__meta { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; font: 500 12.5px/1 var(--font-mono); color: var(--u-muted); }
.rd__title { margin: -6px 0 0; font: var(--display-weight) var(--t-lead)/1.3 var(--font-display); letter-spacing: -0.01em; color: var(--u-ink); }
.rd__verdict { margin: -8px 0 0; font-size: 14px; line-height: 20px; color: var(--u-ink); }
.diff { display: grid; grid-template-columns: 96px minmax(0, 1fr) minmax(0, 1fr); border: 1px solid var(--u-line); border-radius: 10px; overflow: hidden; font-size: 13px; line-height: 18px; }
.diff > * { padding: 8px 10px; border-top: 1px solid var(--u-line); min-width: 0; }
.diff > .diff__h { border-top: 0; background: var(--u-fill); font-size: 12.5px; color: var(--u-muted); }
.diff__k { color: var(--u-muted); }
.diff__v { font-family: var(--font-mono); font-size: 12.5px; white-space: pre-wrap; overflow-wrap: anywhere; color: var(--u-text-2); }
.diff__v.is-empty { font-family: var(--font-text); font-style: italic; color: var(--u-muted); }
.diff__v.is-del { background: var(--bad-bg); color: #7a1d16; text-decoration: line-through; text-decoration-color: color-mix(in oklab, var(--bad-ink) 55%, transparent); }
.diff__v.is-add { background: var(--ok-bg); color: var(--ok-text); }
/* Zmieniony fragment w porownaniu przed/po: ciemniejszy slad w kolorze swojego tla. */
.diff__v mark { background: color-mix(in oklab, currentColor 20%, transparent); color: inherit;
  border-radius: 3px; padding: 0 2px; text-decoration: inherit; }
.diff__v.is-bad { color: var(--bad-ink); }
.diff__v.is-err { background: var(--wait-bg); color: var(--wait-text); font-family: var(--font-text); }
.diff__v.is-warn { background: var(--wait-bg); color: var(--wait-text); }
.diff__src { display: inline-flex; align-items: center; height: 18px; margin-left: 8px; padding: 0 7px; border-radius: 999px; vertical-align: 1px;
  font: 500 11px/1 var(--font-text); text-decoration: none; color: var(--u-ink); box-shadow: inset 0 0 0 1px var(--u-line-2); background: var(--u-bg); }
.diff__src--ai { background: var(--u-ink); color: var(--u-bg); box-shadow: none; }
.rd__box { display: grid; gap: 6px; padding: 14px 16px; border-radius: 10px; background: var(--u-fill); font-size: 13.5px; line-height: 20px; }
.rd__box--todo { background: var(--wait-bg); }
.rd__box--todo h4 { color: var(--wait-text); }
.rd__ai { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 12px; }
.rd__ai b { font-weight: 500; font-size: 15px; }
.rd__conf { font: 500 13px/1 var(--font-mono); }
.rd__why { color: var(--u-text-2); }
.rd__issues { display: grid; gap: 8px; margin: 0; padding: 0; list-style: none; }
.rd__issues li { display: grid; grid-template-columns: 12px minmax(0, 1fr); gap: 10px; font-size: 13.5px; line-height: 20px; }
.rd__issues li::before { content: ""; width: 8px; height: 8px; margin-top: 6px; border-radius: 50%; background: var(--wait-ink); }
.rd__issues li.is-fixed::before { background: var(--ok-ink); }
.rd__issues span { color: var(--u-muted); }

/* panel w trakcie: zapis przebiegu */
.rlog { display: grid; align-content: start; min-height: 100%; background: var(--u-fill); }
.rlog__head { display: flex; flex-wrap: wrap; align-items: center; gap: 6px 12px; padding: 14px 18px; border-bottom: 1px solid var(--u-line); background: var(--u-bg); }
.rlog__head b { font-weight: 500; font-size: 14px; }
.rlog__head span { font-size: 12.5px; color: var(--u-muted); }
.rlog__lines { margin: 0; padding: 12px 16px 20px; list-style: none; font: 12px/21px var(--font-mono); }
.rl { display: grid; grid-template-columns: 44px 14px minmax(0, 1fr); gap: 8px; align-items: start; color: var(--u-text-2); }
.rl.is-new { animation: rl-in 240ms var(--u-ease); }
@keyframes rl-in { from { opacity: 0; transform: translateY(3px); } to { opacity: 1; transform: none; } }
.rl__t { text-align: right; color: var(--u-soft); font-variant-numeric: tabular-nums; }
.rl__i { display: grid; place-items: center; height: 21px; font-family: var(--font-text); font-size: 12px; }
.rl__x { overflow-wrap: anywhere; }
.rl--step .rl__x { color: var(--u-ink); font-weight: 600; }
.rl__step { display: inline-block; margin-right: 8px; padding: 0 6px; border-radius: 5px; background: var(--u-ink); color: var(--u-bg); font-weight: 500; }
.rl--info .rl__x { padding-left: 12px; }
.rl--ok .rl__i { color: var(--ok-ink); }
.rl--warn .rl__i, .rl--review .rl__i, .rl--error .rl__i { color: var(--wait-ink); }
.rl--done .rl__x { color: var(--u-ink); font-weight: 500; }
.rl--wait .rl__x { color: var(--u-soft); padding-left: 12px; }
.rl--wait .rl__i::before { content: ""; width: 8px; height: 8px; border-radius: 50%; border: 1.5px solid color-mix(in oklab, var(--u-ink) 25%, transparent); border-top-color: var(--u-ink); animation: ui-spin 800ms linear infinite; }

@media (min-width: 1024px) {
  #wynik .app.fill { min-height: 540px; }
}
@media (min-width: 1024px) and (max-width: 1439px) {
  .app.ui { grid-template-columns: minmax(0, 1fr) 300px; }
  .sum, .rd { padding-inline: 18px; }
}
@media (min-width: 1024px) and (max-height: 860px) {
  .app.ui { margin-top: var(--s-6); }
  .app__bar { min-height: 48px; padding-block: 6px; }
  .stat { gap: 4px; padding: 10px 20px 9px; }
  .stat__n { font-size: 28px; }
}
@media (min-width: 1024px) and (max-width: 1279px) {
  .stat__n { font-size: 30px; }
  .app__dl a { padding: 0 8px; }
}
.app__more { display: none; }
.more__btn { height: 44px; padding: 0 20px; border: 0; border-radius: 10px; cursor: pointer; background: var(--u-bg);
  box-shadow: inset 0 0 0 1px var(--u-line-2); font: 500 14px/1 var(--font-text); color: var(--u-ink); }
@media (max-width: 1023px) {
  /* dotyk (telefon, tablet): żadnego przewijania w pionie wewnątrz okna, wszystko przewija się razem ze stroną.
     Panel (przycisk, przebieg, podsumowanie) stoi nad tabelą, otwarty wiersz to karta na cały ekran. */
  #wynik .app.fill { flex: none; height: auto; }
  .app.ui { grid-template-columns: minmax(0, 1fr); grid-template-rows: none; }
  .app__bar { flex-wrap: wrap; }
  .app > .app__pane { order: 1; max-height: none; overflow: visible; -webkit-mask-image: none; mask-image: none;
    border-bottom: 1px solid var(--u-line); }
  .app > .app__pane > :last-child { padding-bottom: 24px; }
  .app__sheet { order: 2; overflow-x: auto; overflow-y: hidden; overscroll-behavior: auto; border-right: 0; }
  .app__more:not([hidden]) { order: 3; display: flex; justify-content: center; padding: 14px; border-top: 1px solid var(--u-line); }
  .cta { min-height: 0; }
  html.has-overlay, html.has-overlay body { overflow: hidden; }
}
/* otwarty wiersz na telefonie i tablecie: okno na cały ekran ponad nawigacją i dolnym paskiem */
.row-sheet { position: fixed; inset: 0; z-index: 2000; overflow-y: auto; overscroll-behavior: contain; background: var(--u-bg); }
.row-sheet[hidden] { display: none; }
.row-sheet > .rd { max-width: 720px; margin: 0 auto; padding-bottom: 48px; }
.row-sheet .rd__back { position: sticky; top: 10px; z-index: 2; height: 40px; padding: 0 14px;
  background: var(--u-bg); box-shadow: inset 0 0 0 1px var(--u-line-2), var(--u-shadow-sm); }
@media (max-width: 639px) {
  .app__bar { padding: 10px 12px; gap: 10px; }
  .app__bar .ui-dots, .app__bar .ui-spacer { display: none; }
  .app__files { width: 100%; }
  .app__files button { flex: 1; height: 44px; padding: 0 6px; font-size: 13px; }
  .app__dl { width: 100%; }
  .app__dl a { flex: 1; justify-content: center; height: 40px; padding: 0 6px; }
  .t-wide { position: absolute; width: 1px; height: 1px; margin: -1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
  .t-narrow { display: inline; }
  .stat { gap: 4px; padding: 10px 10px 9px; }
  .stat__n { font-size: 26px; }
  .stat__l { font-size: 12px; }
/*{{szerokosc_tabeli_2}}*/
  .sheet .sheet__n { width: 40px; }
  .sheet .sheet__name { left: 40px; }
  .sheet { font-size: 12.5px; }
  .sheet thead th.sheet__name { width: 168px; }
  .rd, .sum { padding-inline: 16px; }
  .cta { padding: 24px 16px; }
  .diff { grid-template-columns: minmax(0, 1fr) minmax(0, 1fr); }
  .diff > .diff__k { grid-column: 1 / -1; padding-bottom: 0; border-top: 1px solid var(--u-line); background: var(--u-fill); }
  .diff > .diff__h--k { display: none; }
  .rl { grid-template-columns: 38px 14px minmax(0, 1fr); gap: 6px; }
  .rlog__lines { padding-inline: 12px; }
}

/* --- jak działa: tekst i schemat -------------------------------- */
.split-copy { display: grid; gap: var(--s-5); align-content: start; }
.split-copy .link { justify-self: start; }
.facts { display: grid; margin: 0; padding: 0; list-style: none; }
.facts li { padding: 12px 0; border-bottom: 1px solid var(--line); font-size: 16px; line-height: 1.5; color: var(--ink); }
.frame--diagram { background: var(--g-alt, var(--surface)); }
.frame--diagram > .dg { position: absolute; inset: 0; }
@media (min-width: 1024px) { #jak-dziala .frame--split { --ratio: 88%; } }

/* --- stopka: kontakt ------------------------------------------------------------------------ */
.contact__grid { display: grid; grid-template-columns: minmax(0, 1fr) auto; align-items: end; gap: var(--s-6) var(--s-8); }
.contact__name { margin: 0; font: var(--display-weight) clamp(32px, 4vw, 52px)/1.05 var(--font-display); letter-spacing: var(--display-tracking); color: var(--ink); }
.footer .contact__list { display: grid; gap: 10px; margin: 0; padding: 0; list-style: none; font-size: 16px; }
.contact__list li { display: grid; grid-template-columns: 72px auto; align-items: baseline; gap: var(--s-4); }
.contact__k { font-size: 13px; color: var(--muted); }
.contact__list a { color: var(--ink); text-decoration: underline; text-decoration-color: color-mix(in oklab, currentColor 35%, transparent); text-underline-offset: 4px; }
.contact__list a:hover { text-decoration-color: currentColor; }
.contact .footer__legal { margin-top: var(--s-7); }
@media (max-width: 767px) { .contact__grid { grid-template-columns: minmax(0, 1fr); align-items: start; } }
/* telefon: dolny pasek z przyciskiem nie zasłania ostatniej linii stopki */
@media (max-width: 639px) { .contact { padding-bottom: calc(var(--s-6) + 84px); } }
