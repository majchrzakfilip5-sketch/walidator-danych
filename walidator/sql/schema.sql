-- Docelowa baza produktów (SQLite). Import aktualizuje istniejące SKU (upsert).

CREATE TABLE IF NOT EXISTS importy (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    plik_zrodlowy   TEXT    NOT NULL,
    data_importu    TEXT    NOT NULL,
    liczba_wierszy  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS produkty (
    sku             TEXT    PRIMARY KEY,
    ean             TEXT    NOT NULL CHECK (length(ean) = 13),
    nazwa           TEXT    NOT NULL,
    rozmiar         TEXT,                   -- opcjonalne: ma odziez i obuwie, nie ma zywnosc
    kolor           TEXT,                   -- jw.
    waga_g          INTEGER NOT NULL CHECK (waga_g > 0),
    cena_netto_pln  NUMERIC NOT NULL CHECK (cena_netto_pln > 0),
    data_dostawy    TEXT    NOT NULL,
    kategoria       TEXT    NOT NULL,
    segment         TEXT    NOT NULL,
    import_id       INTEGER NOT NULL REFERENCES importy(id)
);

CREATE INDEX IF NOT EXISTS idx_produkty_ean ON produkty(ean);
CREATE INDEX IF NOT EXISTS idx_produkty_kategoria ON produkty(kategoria);
