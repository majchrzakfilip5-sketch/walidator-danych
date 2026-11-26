SELECT kategoria,
       COUNT(*)                        AS liczba_produktow,
       COUNT(DISTINCT nazwa)           AS liczba_modeli,
       ROUND(AVG(cena_netto_pln), 2)   AS srednia_cena_netto
FROM produkty
WHERE import_id = :import_id
GROUP BY kategoria
ORDER BY liczba_produktow DESC, kategoria;
