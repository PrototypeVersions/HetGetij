# Het Getij editorial instructions

This guide describes the site exactly as it is built today. The scheduled morning and evening runs follow it to the letter, so keep it current whenever the site changes.

## Promise
The publication is named **Het Getij** ("the tide"). Use the full name in reader-facing copy. The repository is `PrototypeVersions/HetGetij`. It is a sister publication to The Signal and shares its design and data format, but it covers the Netherlands only. The site is currently written in English; when it switches to Dutch, every reader-facing string in the data must be Dutch.

One daily edition about consequential changes in the Netherlands: national politics, the economy, public services and society, all twelve provinces, and Dutch science, technology, health, energy and water. Aim for about five full national stories, five to eight shorter “More that changed” items, two to four Frontiers items, a continuing-priority (Still matters) item when justified, and one to three briefs for every province. Look hard for news in every province, including the quieter ones (Zeeland, Drenthe, Flevoland, Limburg): use the regional broadcasters (RTV Noord, Omrop Fryslân, RTV Drenthe, RTV Oost, Omroep Flevoland, Omroep Gelderland, RTV Utrecht, NH Nieuws, Omroep West, Rijnmond, Omroep Zeeland, Omroep Brabant, L1), regional papers and local news sites, as well as NOS, NL Times and DutchNews.nl. International news belongs only when it directly concerns the Netherlands. Publish fewer items when evidence is weak. Relevance, human consequence, novelty and evidence guide selection. Include consequential positive developments when supported; do not equate significance with crime or conflict.

## Research and comparison
Read the most recent files in `data/editions/` before researching, and list the existing story threads with `python3 scripts/build.py --threads` (see Story threads). Reuse a stable story ID for the same continuing event and state the actual change relative to prior reporting. Search current reporting broadly and open the sources. Check event dates inside articles; search freshness alone is not sufficient. Do not infer that no news found means nothing happened. Cite the original source behind syndicated reporting and do not count repeats as independent evidence.

Primary documents verify what an institution says or does, not automatically every underlying claim. Distinguish company claims, independent replication and availability. Prefer two genuinely independent accounts for contested factual claims. A single primary announcement is allowed if clearly attributed and its limits stated. Flag unresolved contradictions, exclude unsupported claims, and never fill a quiet day with invented stories. Respect source quotation and summary limits; use original concise prose and direct URLs.

## Page layout
The home page runs in this order:

1. **The day, in view**: the edition's `opening`.
2. **The Netherlands / In focus** (“Across the country”): `section: "world"` stories as full cards, about five. The section key stays `world` for compatibility; it means national stories.
3. **More that changed**: `section: "more"` items as short rows.
4. **Frontiers**: `section: "frontiers"` items as cards, followed by the optional Reality check card.
5. **The country, by province**: a map with twelve numbered provinces, each with its own page (see Provinces).
6. **Still matters** (`section: "still"`) and **What we’re watching** (`watch`).
7. An optional `note` (only on unusual days), then the closing “You’re caught up” section.

There is no separate lead block or cover. The `leadStoryId` story is shown first, as a larger card, inside its own section. Order the `stories` array as the page shows them: world, then more, then frontiers, then still.

## Schema
Use the most recent edition as the schema reference.

**Top level:** `date` (Europe/Amsterdam edition date), `number` (previous + 1), `cutoff` (actual UTC timestamp of the research cutoff), `cutoffLabel` (readable Amsterdam time, e.g. `6:40 AM CEST`, or `CET` in winter), `opening`, `leadStoryId`, `stories`, `watch`, `regions`, and optionally `realityCheck`, `note`, `corrections`, `updatedAt` and `updatedLabel`.

- `opening`: a 30–50 word factual synthesis of the day's main developments. Avoid invented causal connections.
- `leadStoryId`: the most consequential development of the day. It must be a national (`world`) or Frontiers story; a `more` or `still` story cannot lead.
- `watch`: three items with `title` and `text`, each tied to a dated or concrete thing to watch.
- `realityCheck` (optional): `title`, `text`, `url`. It appears as the last Frontiers card, labelled Reality check. Include one only when a prominent claim in the news genuinely needs testing against the evidence; it must be sourced and separate claims from demonstrations. Omit it on other days.
- `note` (optional): omit on ordinary days. Include it only when readers need to know something unusual, in one or two plain sentences: for example that the edition was published in the evening because the morning run failed, that a major story is still developing and key facts may change, or that a usual section is missing.
- Do not add `cover`, a markets strip or daily market quotes. `realityCheck` is supported but rarely needed.

**Every story:** `id` (stable safe slug), `section`, `title`, `category`, `region` (readable label such as `National`, `Drenthe · Hoogeveen` or `North Holland · Amsterdam`), `regions` (see Provinces), `status` (`Major development`, `Meaningful update`, `This week`, `Research result` or `Still matters`), `eventDate`, `body`, `whatChanged`, `sources`, and `threadId` with `threadTitle` and `threadSummary` (see Story threads).

- `eventDate`: ISO dates such as `2026-10-17` or a range `2026-10-16 / 2026-10-18`; the site shows them as October 16–18, 2026.
- Each source has `publisher`, `title`, exact `url`, `publishedAt` (state undated when appropriate) and `kind` (for example primary, reporting, company announcement, analysis). No tool citation syntax belongs in JSON.

**National (World), Frontiers and Still stories** also need `body` (70–100 words), `whyMatters`, `uncertainty`, `watchNext`, `keyFacts` and `report` (see Full reports). Frontiers stories also need `field` and may have `hook`.

**More that changed items** (`section: "more"`) need `whatChanged` (one sentence, shown under the headline) and `body` (two to four sentences, shown when the reader opens “More”). `whyMatters`, `uncertainty`, `watchNext`, `keyFacts`, `report`, `visual` and `image` are optional; if an item has a `report`, the site links its full report. A story that moves from World to More keeps its id and thread.

## Full reports
Every national, Frontiers and Still story has a full report on its own page.

- `keyFacts`: three to five short, sourced facts (one line each) that a reader could quote. Numbers, dates, names.
- `report`: two to four sections, each `{"heading": "...", "paragraphs": ["...", "..."]}`, 200–450 words in total. Typical headings: what happened, the response or reaction, background or context, what comes next. Write original, concise prose; do not copy sentences from sources. Every claim must be supported by a listed source. Attribute contested claims and give both sides when accounts conflict. Do not repeat `whatChanged` and `whyMatters` word for word; the report adds detail and context.

On cards, the top story shows its summary, What changed and Why it matters; other World cards show What changed, with Why it matters, Still uncertain, What to watch and sources in a dropdown. Story pages end with one “Our assessment” box (What changed, Why it matters, Still uncertain, Watch next).

All public text should be reader-facing, not workflow instructions. Dates must be precise and relative weekdays resolved. Avoid unsupported probabilities, invented measurements, unverifiable counts of reviewed sources, and fabricated human review labels.

## Frontiers
Frontiers covers Dutch science, technology and innovation, and developments that change the country's future: AI and digital sovereignty, chips and the tech sector, health and medicine, energy and the power grid, water and climate, space. Prefer Dutch research, companies, institutions and policy; international developments belong only with a clear Dutch angle. Do not force a daily number: publish only material changes with adequate evidence. Distinguish a preprint, peer-reviewed result, trial stage, regulatory approval and real-world deployment; do not turn an early result into a promise.

Use `section: "frontiers"` and a `field` of `AI`, `Tech`, `Science`, `Health`, `Space`, `Energy`, `Water` or `Climate`. The field describes the subject; `category` describes the specific development. The optional `hook` is one concise, supportable sentence shown under “Why it matters” on the card; without it the card uses `whyMatters`. Keep it proportionate. Frontiers cards show the image, field, headline and hook, and link to the full report.

## Provinces
The “The country, by province” map has twelve numbered provinces, each with its own page at `regions/<slug>/`. Numbered north to south, the slugs are `groningen`, `friesland`, `drenthe`, `overijssel`, `flevoland`, `gelderland`, `utrecht`, `north-holland`, `south-holland`, `zeeland`, `north-brabant` and `limburg`.

1. Give every story a `regions` list of the provinces it is really about, e.g. `["drenthe"]` for a story in Hoogeveen, or several when a national decision names projects in several provinces. A national story with no particular place gets `[]`.
2. Add a top-level `regions` object with an entry for each of the twelve slugs: `{"summary": "One or two plain sentences on the province today.", "briefs": [ ... ]}`.
3. `briefs` are extra provincial items that are not on the main page: one to three per province. Each is `{"title", "text", "eventDate", "sources"}`, where `text` is two to four sentences of paraphrased, sourced facts and `sources` uses the normal source fields. Open and read every source; do not rely on search snippets. Prefer the last 48 hours, and look hard before leaving a province empty. Do not repeat a main-page story as a brief. If nothing clears the bar, leave `briefs` empty and the site says so; never pad.

## Story threads
Every story, including `more` items, has a `threadId` (a stable topic slug named for the situation, not the day's headline, e.g. `russia-ukraine-security`), a `threadTitle` (short reader-facing topic) and a `threadSummary` (one factual sentence explaining the ongoing situation).

Before creating a new thread, run `python3 scripts/build.py --threads` to list every existing thread with its title, number of reports and the dates it was first and last seen. If a development belongs to a situation already listed, reuse that `threadId`, even if the thread has not appeared for weeks. Create a new thread only for a genuinely new situation. Several stories, including several in one edition, may share a thread.

The site builds a dated timeline page for each thread at `threads/<threadId>/` and lists the stories in the archive under “By story”. Never invent past entries, claim historical coverage that does not exist, or backfill unsourced context.

## Visuals
Use the site palette: midnight navy (#09131d), pale ice blue, slate and Dutch orange (#f0954a). Choose a visual because it explains the particular story. Maps locate reporting, charts show sourced comparisons, and illustrations help when a simple visual metaphor is understandable. In practice most World stories should use a built-in map or chart. Frontiers stories usually get an illustration. `more` items show no image on the home page.

**Maps and charts** are rendered by the build from structured `visual` data; they need no uploaded image. Most stories use the Netherlands map (`type: "nl"`), drawn from CBS / Kadaster province outlines in `scripts/data/provinces-2026.topojson`; stories that reach abroad can use the world map (`type: "map"`), drawn from Natural Earth geography in `scripts/data/world-110m.json`. Do not invent country outlines, boundaries, paths or coordinates. Locations are approximate reporting locations. Never imply an entire country is affected when evidence concerns a particular area; country highlighting means context, not an incident footprint. Do not add attack paths, territorial-control claims or trade flows without sourced data.

For a Netherlands map use:
```
"visual": {
  "type": "nl", "title": "Hoogeveen, Drenthe",
  "provinces": ["drenthe"], "zoom": true,
  "alt": "Describe the highlighted province and the marked places.",
  "caption": "Drenthe · approximate locations"
}
```
`provinces` are highlighted; `zoom: true` frames the highlighted provinces and markers instead of the whole country. Markers come from the story's `locations` (`{label, lon, lat}`, optional `mapLabel`, `anchor` of `start` or `end`, and `labelDy` in map units to move a label that would overlap another).

For a world map use:
```
"visual": {
  "type": "map", "title": "Romania & the Black Sea",
  "bounds": [18, 38, 44, 52], "countries": ["642"],
  "labels": [{"label": "Black Sea", "lon": 35, "lat": 44, "kind": "water"}],
  "alt": "Describe the highlighted places and the location uncertainty.",
  "caption": "Romania and its neighbors · approximate reporting location"
}
```
Bounds are west, south, east, north. `countries` contains three-digit country IDs present in the bundled data, for example Romania 642, Brazil 076, United States 840, Russia 643. Verify names, IDs, bounds and labels; do not guess. `labels` is optional. Markers come from the story's `locations`, a list of `{label, lon, lat}` with an optional shorter `mapLabel`; include only relevant, well-established reporting locations, and omit them when location is immaterial or uncertain.

For a simple comparison chart use `visual` with `type: "bars"`, `title`, `measure`, `unit`, one to four `values` (each with `label` and a nonnegative numeric `value`), `alt`, `caption` and `sourceUrl`, which must match one of the story's sources. Supply actual units, denominators and dates or periods; disclose missing baselines rather than inventing them. Compare like quantities. Do not turn uncertainty into a measured number. Bar axes start at zero.

**Illustrations** must visibly match their story. Before drawing one, write down in a single sentence the concrete thing from the story it shows: an object, place, mechanism or action a reader would recognize from the headline (solar panels for solar export controls; an elliptic curve and a clock for curve seeds recovered from timestamps; doorways for outside evaluators getting inside access). If you cannot name such a thing, use a map or chart, or omit the visual; never fall back on a generic abstract shape. Check the finished image against its headline: a reader who sees only the picture and the headline should see the connection.

Draw a fresh, simple, story-specific composition as an original self-contained SVG: one strong object or a few shapes, quiet negative space, no lettering or fake data, no scripts, external references or third-party imagery. Avoid generic robots and metaphors that need a paragraph to explain. Never depict fictional documentary scenes, officials, identifiable victims or scientific plots. Image generation, paid APIs, credentials and stock purchases are not part of the daily run. Save the file as `assets/editions/YYYY-MM-DD/<story-id>.svg` in the same commit as the edition and reference it as `image: {"asset": "...", "alt": "...", "credit": "Editorial illustration"}`. The alt text states what is shown and how it connects to the story. Keep files under 250 KB. Do not put generated map or chart paths into the JSON: the build creates them. Real news photography requires a verified source and reuse rights. If no useful visual can be produced, omit it and say so in the run report.

## Publication (morning run)
Editions are produced each morning by a scheduled Claude (Opus 5.5) task and published directly; there is no draft or manual review step. The task:

1. Clones or pulls `PrototypeVersions/HetGetij` and reads this file, README.md and the most recent editions.
2. Works out today's edition date in Europe/Amsterdam. If `data/editions/<date>.json` already exists, it stops and reports.
3. Runs `python3 scripts/build.py --threads`, researches with web search (opening and reading the actual articles), and writes `data/editions/<date>.json` following this guide, with briefs for every province.
4. Runs `python3 scripts/build.py` and fixes any validation error in the data. It never edits application code, styles, workflows, `data/site.json`, README.md or this file, and never edits past editions except to add a `corrections` entry.
5. Commits and pushes to `main` with the message `Edition <N>: <date>`. The push triggers the Actions workflow, which validates and deploys to GitHub Pages.
6. Reports a short summary: the lead story, the items included, provinces left without briefs, anything left out because it could not be verified, and any problem.

If sources or access are insufficient, publish fewer items rather than weaker ones; if a usable edition cannot be produced, leave the latest edition in place and report the problem. Do not send email or social posts.

## Evening update
A second scheduled task runs each evening and updates that day's edition in place. It does not create a second edition.

1. Read today's edition, recent editions and this guide. If today's edition does not exist (the morning run failed), produce a full edition instead, following the morning steps, and say in `note` that it was published in the evening.
2. Research what has happened since the morning `cutoff` for every story in the edition, every dated item in `watch`, and any major new development.
3. For each story that materially moved, append to its `updates` list: `{"at": "<ISO time with zone>", "label": "Evening update · 6:55 PM CEST", "text": "One to three sentences on what changed since this morning.", "sources": [ ...normal source fields... ]}`. On the home page the story gets a small “Updated” tag (the time comes from the part of `label` after “·”); the update text itself appears on the story’s page in a “Since this morning” box after the “Our assessment” box, and inside the “More” dropdown for More that changed items. Do not rewrite the morning's `title`, `body`, `whatChanged` or `report` unless they contain an error, in which case add a `corrections` entry. You may add a short paragraph to the end of a `report` section when the update needs more space, and update `keyFacts` when a figure has changed (state the time).
4. Add at most two new stories (national or More that changed), only for major new developments, in the normal schema. Change `leadStoryId` only if a new development clearly outranks the morning lead.
5. Refresh a province's `summary` if the picture changed, and add a province brief for a major local development that does not warrant a main story.
6. Set `updatedAt` (ISO time with zone) and `updatedLabel` (e.g. `6:55 PM CEST`). Leave `cutoff` as the morning value. Rewrite `opening` only if the day's picture changed.
7. Run `python3 scripts/build.py`, then commit and push to `main` with the message `Edition <N> evening update: <date>`.
8. Report which stories were updated, any new stories, and anything left out because it could not be verified. If nothing material happened, still set `updatedAt` and say so.

## Corrections and the record
A correction is only for something we published that was wrong when we published it: a wrong fact, figure, name, date or attribution. News that arrives later is not a correction; it goes in the story's `updates` (evening) or in the next edition. Do not correct wording, style or emphasis.

For a real error, fix the text and add a `corrections` object to that edition with `storyId`, `date` (ISO), `original` (the wrong sentence, quoted exactly), `replacement` (the corrected sentence) and `reason` (one plain sentence on what was wrong and how we know). Do not silently rewrite published claims. The site shows a small “Corrected” tag on the story's card, the full correction at the end of the story's page, and every correction, grouped by month, on the Corrections page. Past editions are kept as published in the archive. The build checks today's and yesterday's editions against every rule here; older editions are published as they were, even if a rule has since changed.
