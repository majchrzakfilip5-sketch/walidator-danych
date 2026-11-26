<!doctype html>
<html lang="pl" data-type="software" data-radius="soft" data-ground="sage" data-buttons="solid" data-motion>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<!--{{meta_title}}-->
<meta property="og:type" content="website">
<!--{{meta_og}}-->
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="assets/favicon.svg" type="image/svg+xml">
<meta name="theme-color" content="#f7f9f8">
<!--{{meta_canonical}}-->
<meta name="site-kind" content="software">
<meta name="page-type" content="software">
<!-- Fonty: Epilogue i JetBrains Mono (OFL), hostowane lokalnie, z polskimi znakami (latin-ext). -->
<link rel="preload" href="assets/fonts/epilogue-latin-wght-normal.woff2" as="font" type="font/woff2" crossorigin>
<style>
@font-face { font-family: "Epilogue"; font-style: normal; font-display: block; font-weight: 100 900; src: url("assets/fonts/epilogue-latin-ext-wght-normal.woff2") format("woff2-variations"); unicode-range: U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF; }
@font-face { font-family: "Epilogue"; font-style: normal; font-display: block; font-weight: 100 900; src: url("assets/fonts/epilogue-latin-wght-normal.woff2") format("woff2-variations"); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
@font-face { font-family: "JetBrains Mono"; font-style: normal; font-display: swap; font-weight: 100 800; src: url("assets/fonts/jetbrains-mono-latin-ext-wght-normal.woff2") format("woff2-variations"); unicode-range: U+0100-02BA,U+02BD-02C5,U+02C7-02CC,U+02CE-02D7,U+02DD-02FF,U+0304,U+0308,U+0329,U+1D00-1DBF,U+1E00-1E9F,U+1EF2-1EFF,U+2020,U+20A0-20AB,U+20AD-20C0,U+2113,U+2C60-2C7F,U+A720-A7FF; }
@font-face { font-family: "JetBrains Mono"; font-style: normal; font-display: swap; font-weight: 100 800; src: url("assets/fonts/jetbrains-mono-latin-wght-normal.woff2") format("woff2-variations"); unicode-range: U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD; }
</style>
<link rel="stylesheet" href="assets/system.css">
<link rel="stylesheet" href="assets/ui/cards.css">
<link rel="stylesheet" href="assets/motion/motion.css">
<link rel="stylesheet" href="assets/backgrounds/backgrounds.css">
<link rel="stylesheet" href="assets/layout/layout.css">
<style>
:root {
  --p-bg: #f7f9f8; --p-surface: #ebf0ee; --p-ink: #06525c; --p-muted: #2f737d;
  --p-accent: #06525c; --p-accent-ink: #f7f9f8; --p-action: #06525c; --p-action-ink: #f7f9f8;
  --p-inv-bg: #06525c; --p-inv-surface: #205d66; --p-inv-ink: #f7f9f8; --p-inv-muted: #c1d0d2;
  --p-inv-accent: #f7f9f8; --p-inv-accent-ink: #06525c; --p-inv-action: #f7f9f8; --p-inv-action-ink: #06525c;
  --font-display: "Epilogue", system-ui, sans-serif;
  --font-text: "Epilogue", system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, "SFMono-Regular", Menlo, Consolas, monospace;
  --display-weight: 400;
  --display-tracking: -0.035em;
  --display-tracking-xl: -0.045em;
  --ly-scale: 0.97;
}
</style>
<link rel="stylesheet" href="assets/ui/base.css">
<link rel="stylesheet" href="assets/ui/window/fragment.css">
<link rel="stylesheet" href="assets/icons/icon.css">
<link rel="stylesheet" href="assets/diagrams/diagram.css">
<link rel="stylesheet" href="app.css">
<script>document.documentElement.classList.add('m-enter');setTimeout(()=>document.documentElement.classList.add('m-enter-done'),700)</script>
<script src="assets/backgrounds/backgrounds.js"></script>
</head>
<body>
<!-- type: software (narzędzie do walidacji danych, demo na stronie portfolio, wersja krótka)
     deal: hero collage, nav nav-centre, footer footer-dark (kontakt), buttons solid, mark wordmark,
           palette teal-on-paper (spokojny papier i morski akcent: arkusze, dane, porządek),
           type epilogue + JetBrains Mono, radius soft, ground sage, effect grain-gradient (hero) -->
<header class="nav nav--centre">
  <div class="wrap nav__bar">
    <a class="skip-link" href="#top">Przejdź do treści</a>
<!--{{nav_logo}}-->
    <nav class="nav__links" aria-label="Główna">
      <div class="nav__item"><a class="nav__link" href="#wynik">Wynik</a></div>
      <div class="nav__item"><a class="nav__link" href="#jak-dziala">Działanie</a></div>
      <div class="nav__item"><a class="nav__link" href="#kontakt">Kontakt</a></div>
<!--{{repo_link}}-->
    </nav>
    <div class="nav__actions">
      <a class="btn btn--primary" href="#wynik" data-run>Pokaż wynik walidacji</a>
    </div>
    <button class="nav__toggle" type="button" aria-expanded="false" aria-label="Menu">
      <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true"><path d="M2 5h14M2 13h14" stroke="currentColor" stroke-width="1.6" stroke-linecap="round"/></svg>
    </button>
  </div>
</header>

<main id="top">
  <!-- HERO (collage): słowa po lewej, okno narzędzia na tle z efektem po prawej, karta z wynikiem na jego rogu.
       Liczby i wiersze pliku 01 wpisuje scripts/export_web.py. -->
  <section class="hero hero--collage" data-enter aria-labelledby="hero-h">
    <div class="wrap"><div class="hero-text grid hero__grid">
      <div class="hero__text span-5">
<!--{{hero}}-->
        <div class="btn-row">
          <a class="btn btn--primary" href="#wynik" data-run>Pokaż wynik walidacji<svg class="m-arrow" viewBox="0 0 12 12" aria-hidden="true"><path class="m-arrow__stem" d="M1 6h8"/><path class="m-arrow__head" d="M4.5 2.5 8 6l-3.5 3.5"/></svg></a>
<!--{{repo_link_2}}-->
        </div>
        <p class="hero__proof">Liczby, EAN i ceny sprawdza kod, AI dostaje tylko nazwę i opis nowego produktu.</p>
      </div>
      <div class="hero__art span-6 start-7" data-fx="grain-gradient" data-fx-seed="7" data-fx-still role="img"
           aria-label="Okno walidatora z wierszami pliku: poprawione formaty, wiersze do weryfikacji i karta z wynikiem przebiegu">
        <div class="ly-piece ly-piece--main" aria-hidden="true">
          <div class="ui ui-panel ui-win" data-ui-still>
            <div class="ui-win__bar">
              <span class="ui-dots"><i></i><i></i><i></i></span>
              <span class="ui-win__crumb">Walidator <i>/</i> <b data-fact="file">01_plik_brudny.xlsx</b></span>
              <span class="ui-spacer"></span>
            </div>
            <div class="ui-win__body">
              <nav class="ui-win__side">
                <span class="ui-win__nav is-on">Wszystkie<em data-fact="rows_in">40</em></span>
<!--{{podglad_liczby}}-->
                <span class="ui-win__nav">Poprawione<em data-fact="fixed_rows">40</em></span>
                <span class="ui-win__label">Pliki</span>
                <span class="ui-win__nav"><span class="ui-win__hash">01</span>Brudny</span>
                <span class="ui-win__nav"><span class="ui-win__hash">02</span>Bardzo brudny</span>
              </nav>
              <div class="ui-win__main">
                <ul class="ui-win__rows hero-rows">
                <!-- hero-rows -->
<!--{{podglad_wiersze}}-->
                <!-- /hero-rows -->
                </ul>
              </div>
            </div>
          </div>
        </div>
        <div class="ly-piece ly-piece--note ui ui-panel result-card" aria-hidden="true">
          <div class="result-card__head"><b>Wynik walidacji</b><span class="st st--ready">Zapisano</span></div>
<!--{{karta_wyniku}}-->
        </div>
      </div>
    </div></div>
  </section>

  <!-- APP-FRAME: cały plik jako arkusz, obok panel: przycisk, zapis przebiegu, podsumowanie albo szczegóły wiersza.
       Zmiana pliku pokazuje surowy arkusz i przycisk; walidację uruchamia dopiero przycisk (app.js). -->
  <section class="section" id="wynik" aria-labelledby="wynik-h">
    <div class="wrap">
      <div class="grid">
        <h2 class="span-5" id="wynik-h">Cały plik przed i po walidacji</h2>
        <div class="span-6 start-7 stack-4 app-intro">
          <p>Arkusz pokazuje plik tak, jak przyszedł. Po walidacji zielone komórki to poprawki narzędzia, a bursztynowe czekają na człowieka. Kliknij wiersz, żeby zobaczyć szczegóły.</p>
          <a class="link" data-download="input" href="downloads/01/01_plik_brudny.xlsx" download>Pobierz plik wejściowy</a>
        </div>
      </div>
      <div class="ui ui-panel app fill" id="app" role="region" aria-label="Okno walidatora: arkusz pliku i panel z wynikiem">
        <div class="app__bar">
          <span class="ui-dots" aria-hidden="true"><i></i><i></i><i></i></span>
          <div class="app__files" role="radiogroup" aria-label="Plik przykładowy" id="files">
            <button type="button" role="radio" aria-checked="true" data-file="01">01 Brudny</button>
            <button type="button" role="radio" aria-checked="false" data-file="02">02 Bardzo brudny</button>
          </div>
          <span class="ui-spacer"></span>
          <div class="app__dl" aria-label="Pliki wynikowe">
            <a data-download="csv" href="downloads/01/clean_import.csv" download><span class="t-wide">CSV do importu</span><span class="t-narrow" aria-hidden="true">CSV</span></a>
            <a data-download="review" href="downloads/01/manual_review.xlsx" download>Weryfikacja</a>
            <a data-download="errors" href="downloads/01/error_report.xlsx" download>Raport</a>
          </div>
        </div>
        <div class="app__stats is-idle" role="group" aria-label="Filtr wierszy" id="stats">
          <button type="button" class="stat" data-filter="all" aria-pressed="true"><span class="stat__n" data-stat="rows_in" data-fact="rows_in">40</span><span class="stat__l">Wejście</span></button>
          <button type="button" class="stat stat--ready" data-filter="ready" aria-pressed="false"><span class="stat__n" data-stat="ready">0</span><span class="stat__l"><span class="t-wide">Gotowe do importu</span><span class="t-narrow" aria-hidden="true">Gotowe</span></span></button>
          <button type="button" class="stat stat--review" data-filter="review" aria-pressed="false"><span class="stat__n" data-stat="review">0</span><span class="stat__l"><span class="t-wide">Do ręcznej weryfikacji</span><span class="t-narrow" aria-hidden="true">Weryfikacja</span></span></button>
          <button type="button" class="stat stat--fixed" data-filter="fixed" aria-pressed="false"><span class="stat__n" data-stat="fixed_rows">0</span><span class="stat__l"><span class="t-wide">Poprawione automatycznie</span><span class="t-narrow" aria-hidden="true">Poprawione</span></span></button>
        </div>
        <div class="app__sheet" id="sheet-wrap">
          <table class="sheet ui ui-sheet" id="sheet">
            <caption class="sr-only">Wiersze pliku. Przed walidacją wartości z pliku, po walidacji wynik każdej komórki.</caption>
            <thead><tr>
              <th scope="col" class="sheet__n" title="Numer wiersza w pliku">Nr</th><th scope="col" class="sheet__name">Nazwa</th><th scope="col">EAN</th>
<!--{{kolumny_tabeli}}-->
              <th scope="col">Kategoria</th><th scope="col" class="sheet__st">Wynik</th>
            </tr></thead>
            <tbody id="rows"></tbody>
          </table>
        </div>
        <div class="app__more" id="sheet-more" hidden><button type="button" class="more__btn">Pokaż wszystkie wiersze</button></div>
        <div class="app__pane" id="open">
          <div class="cta ui ui-cta">
            <p class="cta__file" data-cta-file>01_plik_brudny.xlsx, 40 wierszy</p>
            <p class="cta__title">Tak wygląda plik przed walidacją</p>
            <button type="button" class="cta__btn" id="run">
              <svg viewBox="0 0 16 16" aria-hidden="true"><path d="M5 3.5v9l7-4.5z"/></svg>
              <span>Pokaż wynik walidacji</span>
            </button>
            <p class="cta__hint">Odtwarza zapis prawdziwego przebiegu, około 3 sekund.</p>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- SPLIT-TEXT-LEFT ze schematem: plik, reguły i AI, trzy wyjścia z liczbami pliku 01 (wpisuje je
       scripts/export_web.py). Schemat płynie w pętli, póki jest na ekranie; nie zatrzymuje się pod kursorem. -->
  <section class="section" id="jak-dziala" aria-labelledby="jak-dziala-h">
    <div class="wrap">
      <div class="grid">
        <div class="span-5 split-copy">
          <h2 id="jak-dziala-h">Jak działa walidacja</h2>
<!--{{opis_regul}}-->
          <ul class="facts">
<!--{{lista_regul}}-->
            <li>Kolumny i format pliku importu ustawia się w konfiguracji, bez zmian w kodzie.</li>
          </ul>
<!--{{repo_link_3}}-->
        </div>
        <div class="frame frame--split span-6 start-7 frame--diagram">
<!--{{diagram}}-->
        </div>
      </div>
    </div>
  </section>
</main>

<footer class="footer footer--dark ground-inverse contact" id="kontakt" aria-labelledby="kontakt-h">
  <div class="wrap">
    <div class="contact__grid">
      <h2 class="contact__name" id="kontakt-h">Filip Majchrzak</h2>
      <ul class="contact__list">
        <li><span class="contact__k">Telefon</span><a href="tel:+48788524622">+48 788 524 622</a></li>
        <li><span class="contact__k">E-mail</span><a href="mailto:majchrzakfilip5@gmail.com">majchrzakfilip5@gmail.com</a></li>
<!--{{repo_link_4}}-->
      </ul>
    </div>
    <div class="footer__legal">
      <span>&copy; 2026 Filip Majchrzak</span>
<!--{{nota_marki}}-->
    </div>
  </div>
</footer>

<!-- telefon i tablet: otwarty wiersz jako okno na cały ekran, ponad nawigacją (app.js) -->
<div class="row-sheet ui" id="row-sheet" role="dialog" aria-modal="true" aria-label="Szczegóły wiersza" hidden></div>

<nav class="actionbar" aria-label="Szybkie akcje">
  <a class="btn btn--primary" href="#wynik" data-run>Pokaż wynik walidacji</a>
</nav>

<script type="module" src="assets/system.js"></script>
<script type="module" src="assets/motion/motion.js"></script>
<script type="module" src="assets/layout/layout.js"></script>
<script type="module" src="assets/diagrams/mount.js"></script>
<script type="module" src="app.js"></script>
</body>
</html>
