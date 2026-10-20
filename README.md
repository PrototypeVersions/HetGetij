# Het Getij

Een dagelijks overzicht van Nederland: wat er veranderde in het land, in elk van de twaalf provincies en in de Nederlandse wetenschap en techniek, met voor elk hoofdverhaal een volledig verslag, bronnen en een gedateerde tijdlijn. Een zusterpublicatie van [The Signal](https://prototypeversions.github.io/Signal/), gebouwd op hetzelfde ontwerp en hetzelfde dataformaat.

Site: https://prototypeversions.github.io/HetGetij/

## Hoe het werkt

- **Edities** (`data/editions/JJJJ-MM-DD.json`): één per dag, gedateerd in Amsterdamse tijd, volledig in het Nederlands. Elke editie heeft ongeveer vijf landelijke verhalen, kortere berichten onder ‘Wat er nog veranderde’, de Voorhoede (techniek, wetenschap, gezondheid, energie, water), een onderwerp dat belangrijk blijft, een lijst met waar we op letten, en per provincie een samenvatting met lokaal nieuws.
- **Bouw** (`scripts/build.py`, standaard-Python): controleert de data en schrijft de statische site naar `dist/`: de voorpagina, een pagina per verhaal en per provincie, tijdlijnen per verhaal, het archief, correcties, de feed en de gegevens voor Bijpraten.
- **Kaarten** (`scripts/visuals.py`): de provinciekaart en de kaarten bij verhalen komen uit de provinciegrenzen van CBS / Kadaster; kaarten over het buitenland gebruiken Natural Earth. Zie `scripts/data/README.md`.
- **Illustraties** (`assets/editions/JJJJ-MM-DD/*.svg`): eenvoudige eigen tekeningen bij verhalen.
- **Publicatie**: elke push naar `main` start `.github/workflows/pages.yml`, die de site bouwt en op GitHub Pages zet.

[`EDITORIAL.md`](EDITORIAL.md) is de redactionele handleiding die de dagelijkse edities volgen.

## Lokaal draaien

```
python3 scripts/build.py              # controleren en dist/ bouwen
python3 scripts/build.py --threads    # lijst van verhaallijnen
python3 -m http.server -d dist        # bekijken op http://localhost:8000
```
