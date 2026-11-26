# Walidator danych produktowych

Silnik walidacji plików produktowych przed importem + powłoka strony demo.
Jedno repo obsługuje wiele wdrożeń: kod jest wspólny, a treść i dane są w profilach.

## Zasada

**W tym repo nie ma żadnych danych przykładowych.** Ani plików wejściowych,
ani wyników, ani treści konkretnego klienta. Repo zawiera działający kod
i powłokę strony. Dane demo żyją w profilu, poza repo.

## Układ

```
walidator/     silnik: reguły, parsery, kartoteka, cennik, warstwa AI
config/        mapping.example.yaml - wzór mapowania kolumn
scripts/
  export_web.py    przebieg walidacji -> dane dla strony
  build_site.py    powłoka + profil -> gotowa strona
tests/         testy silnika
web/           powłoka strony (szablony .tpl + wspólne assets)
```

Profil klienta (osobny katalog, poza repo):

```
profil-<nazwa>/
  tresc.json           teksty i liczby wstawiane w szablony
  mapping.yaml         mapowanie kolumn dla tego klienta
  generate_samples.py  generator danych przykładowych
  data/                dane demo wczytywane przez stronę
  downloads/           pliki do pobrania
  share.jpg            obrazek podglądu linku
```

## Zbudowanie strony

```
python scripts/build_site.py ../profil-przyklad dist-przyklad
```

Powłoka to trzy szablony (`index.html`, `app.js`, `app.css`) z nazwanymi
slotami. Slot wygląda tak: `<!--{{hero}}-->` w HTML, `/*{{kolspan}}*/`
w JS i CSS. Wartości slotów przychodzą z `tresc.json` profilu, więc dwa
wdrożenia mogą różnić się tekstem, liczbą kolumn i brandingiem,
dzieląc całą resztę.
