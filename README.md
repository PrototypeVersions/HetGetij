# Het Getij

A daily briefing on the Netherlands: what changed nationally, in each of the twelve provinces, and in Dutch science and technology, with a full report, sources and a dated timeline for every main story. A sister publication to [The Signal](https://prototypeversions.github.io/Signal/), built on the same design and data format.

Live site: https://prototypeversions.github.io/HetGetij/

## How it works

- **Editions** (`data/editions/YYYY-MM-DD.json`): one per day, dated in Europe/Amsterdam. Each has about five national stories, shorter "More that changed" items, Frontiers (tech, science, health, energy, water), a Still matters item, a watch list, and a summary plus local briefs for every province.
- **Build** (`scripts/build.py`, standard-library Python): validates the data and writes the static site to `dist/`: the front page, a page per story, a page per province, thread timelines, the archive, corrections, the feed and the catch-up data.
- **Maps** (`scripts/visuals.py`): the province map and story maps are drawn from CBS / Kadaster province outlines; maps that reach abroad use Natural Earth. See `scripts/data/README.md`.
- **Illustrations** (`assets/editions/YYYY-MM-DD/*.svg`): simple original pictures for Frontiers items.
- **Publishing**: every push to `main` runs `.github/workflows/pages.yml`, which builds and deploys to GitHub Pages.

[`EDITORIAL.md`](EDITORIAL.md) is the editorial guide the daily editions follow.

## Running locally

```
python3 scripts/build.py              # validate and build dist/
python3 scripts/build.py --threads    # list story threads
python3 -m http.server -d dist        # preview at http://localhost:8000
```
