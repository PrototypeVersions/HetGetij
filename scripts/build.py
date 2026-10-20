#!/usr/bin/env python3
"""Build Het Getij's static publication. Python standard library only.

Het Getij is a daily briefing on the Netherlands. Internally the national section keeps the
section key "world" and provinces are "regions", so the data format matches The Signal's."""
import html, json, math, re, shutil, hashlib, sys
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse
from xml.sax.saxutils import escape as xml_escape
from visuals import COUNTRY_IDS, NL_BOUNDS, prepare_visuals

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'dist'
BASE = 'https://prototypeversions.github.io/HetGetij'
NAME = 'Het Getij'
e = lambda s: html.escape(str(s), quote=True)
SITE = {}
ASSET_VERSION = hashlib.sha256(((ROOT/'assets/style.css').read_text() + (ROOT/'assets/app.js').read_text()).encode()).hexdigest()[:12]

def validate_image(image):
    asset = image['asset']
    assert re.fullmatch(r'assets/(?:[a-zA-Z0-9_-]+/)*[a-zA-Z0-9_-]+\.(jpg|jpeg|png|webp|svg)', asset), 'Unsafe image path'
    assert (ROOT / asset).is_file(), f'Missing image: {asset}'
    assert image['alt'].strip() and image['credit'].strip(), 'Images need alt text and credit'

def load_site():
    path = ROOT / 'data/site.json'
    site = json.loads(path.read_text()) if path.exists() else {}
    user = site.get('newsletter', {}).get('username', '')
    code = site.get('analytics', {}).get('goatcounter', '')
    assert not user or re.fullmatch(r'[A-Za-z0-9_-]{1,64}', user), 'Newsletter username must be letters, numbers, - or _'
    assert not code or re.fullmatch(r'[a-z0-9-]{1,63}', code), 'GoatCounter code must be lowercase letters, numbers or -'
    return site

def newsletter_user(): return SITE.get('newsletter', {}).get('username', '')
def analytics_code(): return SITE.get('analytics', {}).get('goatcounter', '')

def signup_form(where):
    user = newsletter_user()
    if not user: return ''
    return (f'<form class="signup signup-{where}" action="https://buttondown.com/api/emails/embed-subscribe/{e(user)}" method="post">'
            f'<label for="signup-{where}">Get each morning’s edition by email</label>'
            f'<div class="signup-row"><input type="email" id="signup-{where}" name="email" placeholder="you@example.com" autocomplete="email" required>'
            f'<input type="hidden" name="embed" value="1"><button type="submit">Sign up</button></div>'
            f'<p class="signup-note">One email a day, free. Unsubscribe any time. Your address is held by Buttondown and used only to send the edition.</p></form>')

FIELDS = ('AI', 'Tech', 'Science', 'Health', 'Space', 'Energy', 'Water', 'Climate')

def validate(edition):
    date.fromisoformat(edition['date'])
    assert isinstance(edition['number'], int) and edition['number'] > 0
    cutoff = datetime.fromisoformat(edition['cutoff'].replace('Z', '+00:00'))
    assert cutoff.tzinfo is not None, 'Cutoff must include a timezone'
    assert len(edition['stories']) >= 1, 'An edition needs verified stories'
    ids = set()
    for s in edition['stories']:
        assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s['id']), 'Unsafe story slug'
        assert s['id'] not in ids, 'Duplicate story id'
        ids.add(s['id'])
        assert s['section'] in ('world', 'more', 'ai', 'frontiers', 'still')
        if s.get('field'): assert s['field'] in FIELDS, f'field must be one of {FIELDS}'
        if s['section'] == 'frontiers': assert s.get('field'), 'Frontiers stories need a field tag'
        if 'hook' in s: assert isinstance(s['hook'], str) and s['hook'].strip()
        required = ('title', 'body', 'whatChanged', 'eventDate', 'category', 'region', 'status')
        if s['section'] != 'more': required += ('whyMatters', 'uncertainty', 'watchNext')
        for field in required:
            assert isinstance(s.get(field), str) and s[field].strip(), f'Missing {field}'
        for field in ('whyMatters', 'uncertainty', 'watchNext'):
            if field in s: assert isinstance(s[field], str) and s[field].strip(), f'Empty {field}'
        assert s['sources'], 'Every story needs sources'
        for source in s['sources']:
            assert urlparse(source['url']).scheme == 'https' and urlparse(source['url']).netloc
            assert source['title'] and source['publisher'] and source['publishedAt']
        if s.get('image'): validate_image(s['image'])
        if 'report' in s:
            assert isinstance(s['report'], list) and s['report'], 'report must be a list of sections'
            for section in s['report']:
                assert isinstance(section.get('heading'), str) and section['heading'].strip(), 'Report sections need a heading'
                assert isinstance(section.get('paragraphs'), list) and section['paragraphs'], 'Report sections need paragraphs'
                assert all(isinstance(x, str) and x.strip() for x in section['paragraphs'])
        for update in s.get('updates', []):
            stamp = datetime.fromisoformat(update['at'].replace('Z', '+00:00'))
            assert stamp.tzinfo is not None, 'Update times need a timezone'
            assert isinstance(update.get('text'), str) and update['text'].strip(), 'Updates need text'
            for source in update.get('sources', []):
                assert urlparse(source['url']).scheme == 'https' and source['title'] and source['publisher'] and source['publishedAt']
        if 'keyFacts' in s:
            assert isinstance(s['keyFacts'], list) and 2 <= len(s['keyFacts']) <= 6, 'keyFacts needs 2 to 6 items'
            assert all(isinstance(x, str) and x.strip() for x in s['keyFacts'])
        if s.get('threadId'): assert re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', s['threadId']), 'Unsafe thread slug'
        for field in ('threadTitle','threadSummary'):
            if field in s: assert isinstance(s[field],str) and s[field].strip()
        if s.get('visual'):
            visual=s['visual']
            assert visual['type'] in ('map','bars','nl')
            assert visual['title'] and visual['alt'] and visual['caption']
            if visual['type']=='nl':
                assert all(x in REGION_SLUGS for x in visual.get('provinces',[])), 'nl map provinces must use province slugs'
                w,so,ea,no=NL_BOUNDS
                for point in s.get('locations',[]):
                    assert w-1<=point['lon']<=ea+1 and so-1<=point['lat']<=no+1, f"{point['label']} is outside the Netherlands map"
            elif visual['type']=='map':
                west,south,east,north=visual['bounds']
                assert -180<=west<east<=180 and -90<=south<north<=90
                assert all(str(code) in COUNTRY_IDS for code in visual.get('countries',[])), 'Unknown country code'
                for point in visual.get('labels',[]):
                    assert west<=point['lon']<=east and south<=point['lat']<=north and point['label']
            else:
                assert visual['sourceUrl'] in [x['url'] for x in s['sources']], 'Chart must cite a story source'
                assert visual['measure'] and visual['unit'] and 1<=len(visual['values'])<=4
                assert all(isinstance(x['value'],(int,float)) and math.isfinite(x['value']) and x['value']>=0 and x['label'] for x in visual['values'])
    for s in edition['stories']:
        if 'regions' in s:
            assert isinstance(s['regions'], list) and all(x in REGION_SLUGS for x in s['regions']), 'Story regions must use the twelve province slugs'
    if 'regions' in edition:
        assert isinstance(edition['regions'], dict) and all(k in REGION_SLUGS for k in edition['regions']), 'Unknown province key'
        for entry in edition['regions'].values():
            if 'summary' in entry: assert isinstance(entry['summary'], str) and entry['summary'].strip()
            for b in entry.get('briefs', []):
                for field in ('title', 'text', 'eventDate'):
                    assert isinstance(b.get(field), str) and b[field].strip(), f'Province briefs need {field}'
                assert b.get('sources'), 'Province briefs need sources'
                for source in b['sources']:
                    assert urlparse(source['url']).scheme == 'https' and source['title'] and source['publisher'] and source['publishedAt']
    if edition.get('updatedAt'):
        assert datetime.fromisoformat(edition['updatedAt'].replace('Z', '+00:00')).tzinfo is not None, 'updatedAt needs a timezone'
        assert edition.get('updatedLabel'), 'updatedAt needs a readable updatedLabel'
    assert edition['watch'], 'Missing watch list'
    if 'note' in edition: assert isinstance(edition['note'], str) and edition['note'].strip(), 'note must be text; omit it when there is nothing unusual to say'
    if edition.get('leadStoryId'):
        assert edition['leadStoryId'] in ids, 'Lead must reference an edition story'
        assert lead_story(edition)['section'] in ('world', 'ai', 'frontiers'), 'The lead must be a national (world) or Frontiers story'
    rc = edition.get('realityCheck')
    if rc:
        assert rc.get('title') and rc.get('text') and urlparse(rc.get('url', '')).scheme == 'https', 'realityCheck needs title, text and an https url'
    if edition.get('cover'):
        cover = edition['cover']
        assert cover['storyId'] in ids, 'Cover must reference an edition story'
        assert cover['storyId'] == lead_story(edition)['id'], 'Cover must match the selected lead'
        validate_image(cover)
    for s in edition['stories']:
        for point in s.get('locations', []):
            assert -180 <= point['lon'] <= 180 and -90 <= point['lat'] <= 90
            assert point['label']

def write(path, content):
    target = OUT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding='utf-8')

def pretty(d):
    return date.fromisoformat(d).strftime('%B %d, %Y').replace(' 0', ' ')

def event_label(text):
    """Readable event dates: 2026-10-17 -> October 17, 2026; 2026-10-17 / 2026-10-18 -> October 17–18, 2026."""
    iso = r'(\d{4})-(\d{2})-(\d{2})'
    def same_month(m):
        y1, m1, d1, y2, m2, d2 = m.groups()
        if (y1, m1) == (y2, m2): return date(int(y1), int(m1), 1).strftime('%B') + f' {int(d1)}–{int(d2)}, {y1}'
        return pretty(f'{y1}-{m1}-{d1}') + ' – ' + pretty(f'{y2}-{m2}-{d2}')
    text = re.sub(iso + r'\s*/\s*' + iso, same_month, text)
    return re.sub(iso, lambda m: pretty(m.group(0)), text)

def source_links(s):
    return '<div class="sources-inline">' + ''.join(f'<a href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">{e(x["publisher"])} ↗</a>' for x in s['sources']) + '</div>'

def evidence(s):
    return ''.join(f'<div class="evidence"><a href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">{e(x["title"])} ↗</a><small>{e(x["publisher"])} · {e(x["publishedAt"])}{" · "+e(x["kind"]) if x.get("kind") else ""}</small></div>' for x in s['sources'])


CORRECTED = set()

def correction_items(edition, story_id):
    return [c for c in edition.get('corrections', []) if c['storyId'] == story_id]

def correction_body(c):
    when = pretty(c['date']) if re.fullmatch(r'\d{4}-\d{2}-\d{2}', c['date']) else c['date']
    return (f'<span class="eyebrow">Correction · {e(when)}</span>'
            f'<p><strong>An earlier version said:</strong> “{e(c["original"])}”</p>'
            f'<p><strong>It now says:</strong> {e(c["replacement"])}</p>'
            f'<p class="correction-why">{e(c["reason"])}</p>')

def corrections(edition, story_id):
    """Corrections appear with the story they correct, at the end of its page."""
    return ''.join(f'<aside class="correction-box" id="correction">{correction_body(c)}</aside>' for c in correction_items(edition, story_id))

def corrected_tag(s, prefix):
    return f'<a class="corrected-tag" href="{prefix}stories/{e(s["id"])}/#correction">Corrected</a>' if s['id'] in CORRECTED else ''


def story_image(s, prefix, link=False):
    image = s.get('image')
    if not image: return ''
    img = f'<img src="{prefix}{e(image["asset"])}" alt="{e(image["alt"])}" width="1200" height="800" loading="lazy" decoding="async">'
    if link: img = f'<a href="{prefix}stories/{s["id"]}/">{img}</a>'
    visual=s.get('visual',{})
    credit=e(image['credit'])
    if visual.get('type')=='nl': credit=f'{e(visual["caption"])} · Province outlines: CBS / Kadaster'
    elif visual.get('type')=='map': credit=f'{e(visual["caption"])} · <a href="https://www.naturalearthdata.com/" target="_blank" rel="noopener noreferrer">Natural Earth ↗</a>'
    elif visual.get('type')=='bars': credit=f'{e(visual["caption"])} <a href="{e(visual["sourceUrl"])}" target="_blank" rel="noopener noreferrer">Source ↗</a>'
    return f'<figure class="story-art visual-{e(visual.get("type","art"))}">{img}<figcaption>{credit}</figcaption></figure>'

def thread_key(s): return s.get('threadId',s['id'])

def update_label(u):
    return u.get('label') or 'Evening update'

def updates_inline(s):
    ups = s.get('updates', [])
    if not ups: return ''
    return '<div class="story-updates">' + ''.join(f'<p><strong>{e(update_label(u))}</strong> {e(u["text"])}</p>' for u in ups) + '</div>'

def update_time(u):
    label = update_label(u)
    return label.split('·', 1)[1].strip() if '·' in label else ''

def updated_tag(s, prefix):
    ups = s.get('updates', [])
    if not ups: return ''
    when = update_time(ups[-1])
    return f'<div class="updated-row">{updated_link(s, prefix)}</div>'

def updated_link(s, prefix):
    ups = s.get('updates', [])
    if not ups: return ''
    when = update_time(ups[-1])
    return f'<a class="corrected-tag updated-tag" href="{prefix}stories/{e(s["id"])}/#updates">Updated{" " + e(when) if when else ""}</a>'

def row_tags(s, prefix):
    tags = corrected_tag(s, prefix) + updated_link(s, prefix)
    return f'<div class="updated-row">{tags}</div>' if tags else ''

def updates_full(s):
    ups = s.get('updates', [])
    if not ups: return ''
    items = ''
    for u in ups:
        src = ''.join(f'<div class="evidence"><a href="{e(x["url"])}" target="_blank" rel="noopener noreferrer">{e(x["title"])} ↗</a><small>{e(x["publisher"])} · {e(x["publishedAt"])} · {e(x.get("kind","reporting"))}</small></div>' for x in u.get('sources', []))
        items += f'<div class="update-item"><span class="eyebrow">{e(update_label(u))}</span><p>{e(u["text"])}</p>{src}</div>'
    return f'<section class="article-updates" id="updates" aria-label="Updates"><h2>Since this morning</h2>{items}</section>'

def report_words(s):
    words = len(s['body'].split())
    for section in s.get('report', []): words += sum(len(p.split()) for p in section['paragraphs'])
    return words

def read_label(s):
    return f'{max(1, math.ceil(report_words(s) / 220))} min read' if s.get('report') else 'Summary'

def key_facts(s):
    if not s.get('keyFacts'): return ''
    return '<aside class="key-facts" aria-label="Key facts"><span class="eyebrow">Key facts</span><ul>' + ''.join(f'<li>{e(x)}</li>' for x in s['keyFacts']) + '</ul></aside>'

def full_report(s):
    if not s.get('report'): return ''
    parts = ''.join(f'<h2>{e(sec["heading"])}</h2>' + ''.join(f'<p>{e(p)}</p>' for p in sec['paragraphs']) for sec in s['report'])
    return f'<section class="full-report" id="full-report" aria-label="Full report">{parts}</section>'

def thread_link(s,prefix): return f'{prefix}threads/{thread_key(s)}/'

def lead_story(edition):
    if edition.get('leadStoryId'):
        return next(s for s in edition['stories'] if s['id'] == edition['leadStoryId'])
    return next((s for s in edition['stories'] if s['section'] == 'world'), edition['stories'][0])

def frontier_card(s, n, prefix, lead=False):
    return f'''<article class="story-card frontier-card{' lead' if lead else ''}" id="{e(s['id'])}" data-section="frontiers">
    {story_image(s,prefix,True)}<div class="kicker"><span class="eyebrow">{e(s.get('field','AI'))} / {e(s['category'])}</span><span class="number">{n:02}</span></div>
    <h3><a href="{prefix}stories/{s['id']}/">{e(s['title'])}</a></h3>
    <div class="frontier-hook"><span class="eyebrow">Why it matters</span><p>{e(s.get('hook',s['whyMatters']))}</p></div>{row_tags(s,prefix)}
    <div class="card-foot"><span class="badge">Editorial assessment</span><a class="card-more" href="{prefix}stories/{s['id']}/" aria-label="Full report: {e(s['title'])}">Full report <span>→</span></a></div></article>'''

def card(s, n, prefix, lead=False):
    kicker = f'<div class="kicker"><span class="eyebrow">{("Top story · " if lead else "")+e(s["region"])} / {e(s["category"])}</span><span class="number">{n:02}</span></div>'
    title = f'<h3><a href="{prefix}stories/{s["id"]}/">{e(s["title"])}</a></h3>'
    change = f'<div class="change"><p><strong>What changed</strong><br>{e(s["whatChanged"])}</p></div>'
    context = f'<div class="context"><p><strong>Why it matters · our assessment</strong><br>{e(s["whyMatters"])}</p></div>'
    details = f'<details class="card-details"><summary>Uncertainty &amp; sources</summary><div class="context"><p><strong>Still uncertain</strong><br>{e(s["uncertainty"])}</p><p><strong>What to watch</strong><br>{e(s["watchNext"])}</p>{source_links(s)}</div></details>'
    foot = f'<div class="card-foot"><a class="card-thread" href="{thread_link(s,prefix)}" aria-label="Follow this story: {e(s["title"])}">Follow</a><a class="card-more" href="{prefix}stories/{s["id"]}/" aria-label="Full report: {e(s["title"])}">Full report <span>→</span></a></div>'
    if lead:
        return (f'<article class="story-card lead" id="{e(s["id"])}" data-section="{e(s["section"])}"><div class="lead-top">{story_image(s, prefix, True)}'
                f'<div class="lead-copy">{kicker}{title}<p class="summary">{e(s["body"])}</p></div></div>'
                f'<div class="lead-bottom"><div>{change}</div><div>{context}{details}{row_tags(s, prefix)}{foot}</div></div></article>')
    folded = f'<details class="card-details"><summary>Why it matters, uncertainty &amp; sources</summary><div class="context"><p><strong>Why it matters · our assessment</strong><br>{e(s["whyMatters"])}</p><p><strong>Still uncertain</strong><br>{e(s["uncertainty"])}</p><p><strong>What to watch</strong><br>{e(s["watchNext"])}</p>{source_links(s)}</div></details>'
    return f'<article class="story-card" id="{e(s["id"])}" data-section="{e(s["section"])}">{story_image(s, prefix, True)}<div class="card-body">{kicker}{title}{change}{folded}{row_tags(s, prefix)}{foot}</div></article>'

def more_item(s, n, prefix):
    report = f'<a class="card-more" href="{prefix}stories/{s["id"]}/" aria-label="Full report: {e(s["title"])}">Full report <span>→</span></a>' if s.get('report') else ''
    return f'''<article class="more-item" id="{e(s['id'])}"><span class="more-number">{n:02}</span><div class="more-copy"><span class="eyebrow">{e(s['region'])} / {e(s['category'])}</span><h3>{e(s['title'])}</h3><p class="more-dek">{e(s['whatChanged'])}</p><details class="more-details"><summary>More</summary>{''.join(f'<p class="more-update"><strong>{e(update_label(u))}</strong> {e(u["text"])}</p>' for u in s.get('updates', []))}<p>{e(s['body'])}</p>{source_links(s)}</details>{row_tags(s, prefix)}{report}</div></article>'''

def reality_card(rc):
    return f'''<article class="story-card frontier-card reality-card"><div class="kicker"><span class="eyebrow">Reality check / A claim, tested</span></div><h3>{e(rc['title'])}</h3><div class="frontier-hook"><span class="eyebrow">What the evidence does and doesn’t show</span><p>{e(rc['text'])}</p></div><div class="card-foot"><span class="badge">Editorial assessment</span><a class="card-more" href="{e(rc['url'])}" target="_blank" rel="noopener noreferrer">Read the research <span>↗</span></a></div></article>'''

def shell(content, edition, title='Het Getij — The Netherlands, considered. Once a day.', prefix='./', canonical='', payload=True, description='A daily briefing on the Netherlands: national news, all twelve provinces, and Dutch science and technology. What changed, why it matters, and the evidence behind it.'):
    stamp = date.fromisoformat(edition['date']).strftime('%A, %d %B %Y')
    metadata = dict(edition={'date': edition['date'], 'cutoff': edition['cutoff'], 'number': edition['number']}, latest=EDITIONS[-1]['date'], prefix=prefix)
    serialized = json.dumps(metadata, ensure_ascii=False).replace('<', '\\u003c')
    return f'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{e(title)}</title><meta name="description" content="{e(description)}"><meta name="theme-color" content="#09131d"><link rel="canonical" href="{BASE}/{canonical}"><meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(description)}"><meta property="og:site_name" content="Het Getij"><meta property="og:type" content="website"><meta property="og:url" content="{BASE}/{canonical}"><meta property="og:image" content="{BASE}/assets/og-image.png"><meta property="og:image:width" content="1200"><meta property="og:image:height" content="630"><meta property="og:image:alt" content="Het Getij. The Netherlands, considered. Once a day."><meta name="twitter:card" content="summary_large_image"><meta name="twitter:title" content="{e(title)}"><meta name="twitter:description" content="{e(description)}"><meta name="twitter:image" content="{BASE}/assets/og-image.png">{f'<script data-goatcounter="https://{analytics_code()}.goatcounter.com/count" async src="https://gc.zgo.at/count.js"></script>' if analytics_code() else ''}<link rel="icon" type="image/svg+xml" href="{prefix}assets/getij.svg?v={ASSET_VERSION}"><link rel="stylesheet" href="{prefix}assets/style.css?v={ASSET_VERSION}"><link rel="alternate" type="application/rss+xml" title="Het Getij editions" href="{prefix}feed.xml"></head>
    <body><a class="skip" href="#main">Skip to the briefing</a><div class="progress" aria-hidden="true"></div><header class="wrap"><div class="topline eyebrow"><span class="status"><i class="status-dot"></i> An independent daily briefing</span><span>{e(stamp)}</span><span class="timezone">A Dutch perspective</span></div><div class="masthead"><a class="wordmark" href="{prefix}" aria-label="Het Getij home"><span class="wordmark-the">Het</span><span>Getij</span></a><div class="masthead-note"><p>The Netherlands, considered.<br><em>Once a day.</em></p><div class="edition-stamp"><span>Nº</span><strong>{edition['number']:03}</strong><small>The daily edition</small></div></div></div><nav class="navigation" aria-label="Main navigation"><div class="navlinks"><a href="{prefix}#edition">Today</a><a href="{prefix}#frontiers">Frontiers</a><a class="regions-nav" href="{prefix}#regions">Provinces</a><a class="archive-nav" href="{prefix}archive/">Archive</a><a class="about-nav" href="{prefix}about/">Our approach</a></div><div class="nav-actions"><button class="catchup" data-dialog="catchup-dialog">Catch me up ↗</button></div></nav></header>
    {content}
    <footer class="footer"><div class="wrap"><a class="footer-brand" href="{prefix}"><span>Het</span> Getij</a><p>Evidence-linked. Open to correction.</p><div class="footer-links"><a href="{prefix}about/">Our approach</a><a href="{prefix}archive/">Archive</a><a href="{prefix}corrections/">Corrections</a></div></div></footer>
    <dialog id="catchup-dialog" aria-labelledby="catchup-title"><button class="close" aria-label="Close dialog">×</button><div class="eyebrow">The thread, picked up</div><h2 id="catchup-title">How long were you away?</h2><p id="catchup-welcome" hidden></p><div class="cu-choices" role="group" aria-label="Time away"><button data-days="1">Since yesterday</button><button data-days="3">Last 3 days</button><button data-days="7">Last week</button><button data-days="14">Last 2 weeks</button><button data-days="30">Last month</button><button data-days="new">I’m new here</button></div><p class="cu-longer">Away for longer? <a href="{prefix}archive/">Browse the archive →</a></p><div id="catchup-results" aria-live="polite"></div></dialog>
    <div class="toast" role="status" hidden></div><script id="signal-data" type="application/json">{serialized}</script><script src="{prefix}assets/app.js?v={ASSET_VERSION}" defer></script></body></html>'''

# The twelve provinces, numbered north to south. (slug, name, pin lon, pin lat, label dx, label dy, anchor)
REGIONS = [
    ('groningen', 'Groningen', 6.72, 53.24, 0, 30, 'middle'),
    ('friesland', 'Friesland', 5.78, 53.08, 0, 30, 'middle'),
    ('drenthe', 'Drenthe', 6.60, 52.86, 0, 30, 'middle'),
    ('overijssel', 'Overijssel', 6.42, 52.42, 0, 30, 'middle'),
    ('flevoland', 'Flevoland', 5.58, 52.53, 0, -24, 'middle'),
    ('gelderland', 'Gelderland', 6.02, 52.07, 0, 30, 'middle'),
    ('utrecht', 'Utrecht', 5.20, 52.06, 0, 30, 'middle'),
    ('north-holland', 'North Holland', 4.82, 52.62, -24, 5, 'end'),
    ('south-holland', 'South Holland', 4.45, 51.98, -24, 5, 'end'),
    ('zeeland', 'Zeeland', 3.82, 51.50, 0, 30, 'middle'),
    ('north-brabant', 'North Brabant', 5.15, 51.56, 0, 30, 'middle'),
    ('limburg', 'Limburg', 5.92, 51.22, 24, 5, 'start'),
]
REGION_SLUGS = [r[0] for r in REGIONS]

def story_regions(s):
    """Provinces a story belongs to. Only explicit tags count: national stories often have no single province."""
    return list(s.get('regions', []))

def region_items(edition):
    data = edition.get('regions', {})
    out = []
    for number, (slug, name, lon, lat, dx, dy, anchor) in enumerate(REGIONS, 1):
        stories = [(i, s) for i, s in enumerate(edition['stories'], 1) if slug in story_regions(s)]
        entry = data.get(slug, {})
        out.append(dict(slug=slug, name=name, number=number, lon=lon, lat=lat, dx=dx, dy=dy, anchor=anchor, stories=stories,
                        briefs=entry.get('briefs', []), summary=entry.get('summary', '')))
    return out

def region_count(r): return len(r['stories']) + len(r['briefs'])

def count_label(r):
    n = region_count(r)
    return f'{n} item{"s" if n != 1 else ""}'

def region_panel(r, prefix, active):
    name = e(r['name'])
    stories = ''.join(f'<li><a href="{prefix}stories/{e(s["id"])}/"><span>{i:02}</span><b>{e(s["title"])}</b></a></li>' for i, s in r['stories']) \
        or f'<li class="region-empty">No {name} story made today’s main edition.</li>'
    briefs = ''.join(f'<li><a href="regions/{r["slug"]}/#brief-{n}"><span>+</span><b>{e(b["title"])}<small>{e(b["sources"][0]["publisher"])} · {e(b["eventDate"])}</small></b></a></li>' for n, b in enumerate(r['briefs'], 1)) \
        or '<li class="region-empty">No further development cleared our bar today.</li>'
    summary = f'<p class="region-summary">{e(r["summary"])}</p>' if r['summary'] else ''
    hidden = '' if active else ' hidden'
    return (f'<div class="region-panel" id="region-panel-{r["slug"]}" data-panel="{r["slug"]}"{hidden}>'
            f'<span class="eyebrow">Province {r["number"]:02} · {count_label(r)}</span><h3>{name}</h3>{summary}'
            f'<h4>In today’s edition</h4><ul class="region-list">{stories}</ul>'
            f'<h4>More from {name} <small>Beyond the main edition</small></h4><ul class="region-list region-briefs">{briefs}</ul>'
            f'<a class="atlas-read" href="regions/{r["slug"]}/">All {name} news <span>→</span></a></div>')

def atlas(edition, prefix='./'):
    from visuals import nl_project
    W, H = 520, 620
    regions = region_items(edition)
    pins = ''
    for r in regions:
        x, y = nl_project(r['lon'], r['lat'], W, H)
        lx, ly = x + r['dx'], y + r['dy']
        pins += (f'<a href="regions/{r["slug"]}/" class="region-pin" data-region="{r["slug"]}" aria-label="{e(r["name"])}: {count_label(r)}">'
                 f'<circle class="halo" cx="{x:.1f}" cy="{y:.1f}" r="19"/><circle class="dot" cx="{x:.1f}" cy="{y:.1f}" r="13"/>'
                 f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle">{r["number"]:02}</text>'
                 f'<text class="region-name" x="{lx:.1f}" y="{ly:.1f}" text-anchor="{r["anchor"]}">{e(r["name"])} · {region_count(r)}</text></a>')
    chips = ''.join(f'<a href="regions/{r["slug"]}/" class="region-chip" data-region="{r["slug"]}"><span>{r["number"]:02}</span>{e(r["name"])}<small>{region_count(r)}</small></a>' for r in regions)
    panels = ''.join(region_panel(r, prefix, i == 0) for i, r in enumerate(regions))
    return (f'<section class="atlas atlas-nl" id="regions" aria-labelledby="atlas-heading"><div class="atlas-top"><div class="eyebrow">The observatory / Provinces</div>'
            f'<span class="atlas-instruction">Choose a province for more news ↘</span></div><div class="atlas-layout"><div class="atlas-map">'
            f'<h2 id="atlas-heading">The country, <em>by province.</em></h2>'
            f'<p class="atlas-lede">Twelve provinces, numbered from north to south. Choose one to see today’s stories from there, plus local news that didn’t make the main edition.</p>'
            f'<svg viewBox="0 0 {W} {H}" role="group" aria-label="Map of the Netherlands with twelve numbered provinces"><defs><pattern id="atlas-grid" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="#263c50" stroke-width=".6"/></pattern></defs>'
            f'<rect width="{W}" height="{H}" fill="url(#atlas-grid)"/><image href="{prefix}assets/visuals/nl-overview.svg" width="{W}" height="{H}"/>{pins}</svg>'
            f'<nav class="region-chips" aria-label="Provinces">{chips}</nav>'
            f'<p class="atlas-caption">Numbers show items for each province · province outlines: CBS / Kadaster</p></div>'
            f'<aside class="atlas-detail" aria-live="polite">{panels}</aside></div></section>')

def region_page(r, edition, prefix):
    CORRECTED.clear(); CORRECTED.update(c['storyId'] for c in edition.get('corrections', []))
    name = e(r['name'])
    stories = ''.join(
        f'<article class="region-story"><span class="eyebrow">{e(s["region"])} / {i:02}</span><h3><a href="{prefix}stories/{e(s["id"])}/">{e(s["title"])}</a></h3>'
        f'<p>{e(s["whatChanged"])}</p>{row_tags(s, prefix)}<a class="card-more" href="{prefix}stories/{e(s["id"])}/">Full report <span>→</span></a></article>'
        for i, s in r['stories']) or f'<p class="region-empty">No {name} story made this edition’s main report.</p>'
    briefs = ''.join(
        f'<article class="region-brief" id="brief-{n}"><h3>{e(b["title"])}</h3><p class="source-note">{e(b["eventDate"])}</p><p>{e(b["text"])}</p>{source_links(b)}</article>'
        for n, b in enumerate(r['briefs'], 1)) or '<p class="region-empty">No further development cleared our bar today.</p>'
    switch = ''.join(f'<a href="../{x["slug"]}/"{" aria-current=" + chr(34) + "page" + chr(34) if x["slug"] == r["slug"] else ""}><span>{x["number"]:02}</span>{e(x["name"])}</a>' for x in region_items(edition))
    summary = f'<p class="article-summary">{e(r["summary"])}</p>' if r['summary'] else ''
    return (f'<main class="wrap" id="main"><article class="article-page region-page"><a class="article-back" href="../../#regions">← All provinces</a>'
            f'<div class="eyebrow">Province {r["number"]:02} / {e(pretty(edition["date"]))}</div><h1>{name}</h1>{summary}'
            f'<nav class="region-switch" aria-label="Other provinces">{switch}</nav>'
            f'<h2>In today’s edition</h2><div class="region-stories">{stories}</div>'
            f'<h2>More from {name}</h2><p class="source-note">These developments did not make the main edition. Each is summarized from the linked reporting; follow the sources for the full story.</p>'
            f'{briefs}</article></main>')

def home(edition, prefix='./', archived=False):
    CORRECTED.clear(); CORRECTED.update(c['storyId'] for c in edition.get('corrections', []))
    stories = edition['stories']
    num = {s['id']: i for i, s in enumerate(stories, 1)}
    lead = lead_story(edition)
    lead_first = lambda items: sorted(items, key=lambda s: s['id'] != lead['id'])
    world = lead_first([s for s in stories if s['section'] == 'world'])
    more = [s for s in stories if s['section'] == 'more']
    ai = lead_first([s for s in stories if s['section'] in ('ai', 'frontiers')])
    still = [s for s in stories if s['section'] == 'still']
    count = len(world) + len(more) + len(ai)
    words = sum(len(' '.join(s.get(k, '') for k in ('body', 'whatChanged', 'whyMatters', 'uncertainty')).split()) for s in stories) + sum(len(w['text'].split()) for w in edition['watch'])
    minutes = max(3, math.ceil(words / 200))
    archive_note = f'<div class="latest-link">You’re reading an archived edition. <a href="{prefix}"><u>Read the latest →</u></a></div>' if archived else ''
    rc = edition.get('realityCheck')
    still_html = ''.join(f'''<article class="still-card" id="{s['id']}">{story_image(s,prefix,True)}<span class="eyebrow">{e(s['region'])}</span><h3><a href="{prefix}stories/{s['id']}/">{e(s['title'])}</a></h3><p>{e(s['body'])}</p>{row_tags(s, prefix)}<a class="card-more" href="{prefix}stories/{s['id']}/" aria-label="Full report: {e(s['title'])}">Full report <span>→</span></a></article>''' for s in still)
    watch = ''.join(f'<div class="watch-item"><span>{i:02}</span><div><h3>{e(w["title"])}</h3><p>{e(w["text"])}</p></div></div>' for i, w in enumerate(edition['watch'], 1))
    world_cards = ''.join(card(s, num[s['id']], prefix, s['id'] == lead['id']) for s in world)
    more_items = ''.join(more_item(s, num[s['id']], prefix) for s in more)
    ai_cards = ''.join(frontier_card(s, num[s['id']], prefix, s['id'] == lead['id']) for s in ai) + (reality_card(rc) if rc else '')
    return archive_note + f'''<main id="main" class="wrap">
    <section class="issue-intro" id="edition"><div><div class="eyebrow">The daily edition / {edition['number']:03}</div><h2>{e(pretty(edition['date']))}</h2></div><div class="edition-meta"><span>{count} developments</span><span>≈ {minutes} min read</span><span>Updated {e(edition['updatedLabel'] if edition.get('updatedAt') else edition['cutoffLabel'])}</span></div></section><div class="stale-note" id="stale-note" hidden></div><div class="welcome-back" id="welcome-back" hidden><span></span><button class="textlink" data-dialog="catchup-dialog">Catch up on what changed →</button></div>
    <section class="opening-note" aria-label="Today in brief"><span class="eyebrow">The day, in view</span><p>{e(edition['opening'])}</p></section>
    <section class="world-grid-section" {"hidden" if not world_cards else ""}><div class="section-title"><div><span class="eyebrow">The Netherlands / In focus</span><h2>Across the <em>country.</em></h2></div></div><div class="story-grid world-grid" aria-label="National developments">{world_cards}</div></section>
    <section class="more-section" id="more" {"hidden" if not more_items else ""}><div class="section-title"><div><span class="eyebrow">The Netherlands / Also today</span><h2>More that <em>changed.</em></h2></div><span class="section-number">{len(more):02} more</span></div><div class="more-list">{more_items}</div></section>
    <section class="ai-section" id="frontiers" {"hidden" if not ai_cards else ""}><span id="ai-frontier" aria-hidden="true"></span><div class="section-head"><div><div class="eyebrow">Tech · Science · Health · Energy · Water</div><h2><em>Frontiers.</em></h2></div><p>Dutch work that could change the future.<br>And the evidence behind it.</p></div><div class="story-grid">{ai_cards}</div></section>
    {atlas(edition,prefix)}
    <div class="below"><section><div class="eyebrow">Beyond the news cycle</div><h2><em>Still</em> matters.</h2>{still_html or '<p>No continuing-priority entry in this edition.</p>'}</section><section><div class="eyebrow">The next signals</div><h2>What we’re watching.</h2>{watch}</section></div>
    {f'<aside class="edition-note-box" aria-label="A note on this edition"><span class="eyebrow">A note on this edition</span><p>{e(edition["note"])}</p></aside>' if edition.get('note') else ''}
    <section class="endnote"><div class="endnote-mark" aria-hidden="true">✳</div><div><h2>You’re caught up.<br><em>Go live your day.</em></h2><p>One considered edition. A natural place to stop.</p>{signup_form('endnote')}</div><div class="endnote-actions"><button class="textlink" id="share-edition">Share this edition ↗</button><a class="textlink" href="{prefix}archive/">Past stories and editions →</a></div></section></main>'''

def thread_sections(threads, prefix):
    latest = max(h[-1][0]['date'] for h in threads.values())
    def recent(h): return (date.fromisoformat(latest) - date.fromisoformat(h[-1][0]['date'])).days <= 7
    def row(slug, history):
        edition, story = history[-1]
        n = len(history)
        return f'<article class="thread-index-card"><div class="eyebrow">{e(story.get("field",story["category"]))}</div><h2><a href="{prefix}threads/{slug}/">{e(story.get("threadTitle",story["title"]))} <span>↗</span></a></h2><p>{e(story.get("threadSummary",story["whatChanged"]))}</p><div class="thread-meta">{n} report{"s" if n!=1 else ""} · Updated {e(pretty(edition["date"]))}</div></article>'
    order = lambda item: (-len(item[1]), item[1][-1][0]['date'] < latest, item[1][-1][0]['date'])
    active = sorted([x for x in threads.items() if recent(x[1])], key=order)
    earlier = sorted([x for x in threads.items() if not recent(x[1]) and len(x[1]) >= 3], key=lambda item: item[1][-1][0]['date'], reverse=True)
    shown, folded = active[:12], active[12:]
    html = ''.join(row(*x) for x in shown)
    more = ''
    if folded: more += f'<details class="thread-more"><summary>{len(folded)} more active {"story" if len(folded)==1 else "stories"}</summary><div class="thread-index">{"".join(row(*x) for x in folded)}</div></details>'
    if earlier: more += f'<details class="thread-more"><summary>Earlier stories · {len(earlier)} followed over several reports</summary><div class="thread-index">{"".join(row(*x) for x in earlier)}</div></details>'
    return f'<div class="thread-index">{html}</div>{more}'

def assessment_box(s):
    rows = f'<div><dt>What changed</dt><dd>{e(s["whatChanged"])}</dd></div>'
    if s.get('whyMatters'): rows += f'<div><dt>Why it matters</dt><dd>{e(s["whyMatters"])}</dd></div>'
    if s.get('uncertainty'): rows += f'<div><dt>Still uncertain</dt><dd>{e(s["uncertainty"])}</dd></div>'
    if s.get('watchNext'): rows += f'<div><dt>Watch next</dt><dd>{e(s["watchNext"])}</dd></div>'
    label = 'Our assessment' if s.get('whyMatters') else 'What changed'
    note = '<p class="assessment-note">“Why it matters” and “Watch next” are editorial judgments; the rest is drawn from the sources below.</p>' if s.get('whyMatters') else ''
    if not s.get('whyMatters') and not s.get('uncertainty') and not s.get('watchNext'):
        return f'<section class="assessment-box single" id="assessment" aria-label="What changed"><span class="eyebrow">What changed</span><p>{e(s["whatChanged"])}</p></section>'
    return f'<section class="assessment-box" id="assessment" aria-label="{label}"><span class="eyebrow">{label}</span><dl>{rows}</dl>{note}</section>'

def assessment_block(story):
    parts = ''
    if story.get('whyMatters'): parts += f'<p><strong>Why it matters · our assessment</strong><br>{e(story["whyMatters"])}</p>'
    if story.get('uncertainty'): parts += f'<p><strong>Still uncertain</strong><br>{e(story["uncertainty"])}</p>'
    return f'<div class="context">{parts}</div>' if parts else ''

def thread_page(history):
    edition,current=history[-1]
    timeline=''
    newest=date.fromisoformat(edition['date'])
    full=[(x,s) for x,s in history if (newest-date.fromisoformat(x['date'])).days<14]
    older=[(x,s) for x,s in history if (newest-date.fromisoformat(x['date'])).days>=14]
    for published,story in reversed(full):
        timeline+=f'''<article class="thread-update"><div class="thread-date"><a href="../../editions/{published['date']}/#{story['id']}">{e(pretty(published['date']))}</a><span>{e(story['status'])}</span></div><h2><a href="../../stories/{story['id']}/">{e(story['title'])} ↗</a></h2><div class="change"><p><strong>What changed</strong><br>{e(story['whatChanged'])}</p></div>{updates_inline(story)}{assessment_block(story)}<details class="thread-sources"><summary>Sources & evidence ({len(story['sources'])})</summary>{evidence(story)}</details></article>'''
    months={}
    for published,story in reversed(older): months.setdefault(published['date'][:7],[]).append((published,story))
    for month,items in months.items():
        label=date.fromisoformat(month+'-01').strftime('%B %Y')
        rows=''.join(f'<div class="archive-row"><div><a href="../../editions/{x["date"]}/#{s["id"]}">{e(pretty(x["date"]))}</a><h3><a href="../../stories/{s["id"]}/">{e(s["title"])}</a></h3><p>{e(s["whatChanged"])}</p></div></div>' for x,s in items)
        timeline+=f'<details class="thread-month"><summary>{label} · {len(items)} report{"s" if len(items)!=1 else ""}</summary>{rows}</details>'
    return f'''<main class="wrap" id="main"><article class="article-page thread-page"><a class="article-back" href="../../archive/#stories">← All stories</a><span class="eyebrow">The story, in context</span><h1>{e(current.get('threadTitle',current['title']))}</h1><p class="article-summary">{e(current.get('threadSummary',current['whatChanged']))}</p><div class="thread-meta">{len(history)} report{'s' if len(history)!=1 else ''} · First tracked {e(pretty(history[0][0]['date']))} · Updated {e(pretty(edition['date']))}</div><h2 class="timeline-heading" id="timeline">The story so far</h2><div class="thread-timeline">{timeline}</div><p class="source-note">Dated editions preserve what was reported at the time. New developments are added here as the story continues.</p></article></main>'''

def article(s, edition, history):
    thread_history=THREADS.get(thread_key(s),history)
    recent_reports=list(reversed(thread_history))[:10]
    timeline=''.join(f'<div class="archive-row"><div><a href="../../editions/{x["date"]}/#{item["id"]}">{pretty(x["date"])}</a><h3>{e(item["title"])}</h3><p>{e(item["whatChanged"])}</p></div></div>' for x,item in recent_reports)
    if len(thread_history)>10: timeline+=f'<p class="source-note"><a href="{thread_link(s,"../../")}">See all {len(thread_history)} reports in this story →</a></p>'
    return f'''<main class="wrap" id="main"><article class="article-page"><a class="article-back" href="../../">← Back to the latest edition</a><div class="eyebrow">{e(s['region'])} / {e(s['category'])}</div><h1>{e(s['title'])}</h1><p class="source-note">Published in Het Getij on {pretty(edition['date'])} · Event: {e(event_label(s['eventDate']))} · {e(read_label(s))}{(' · <a href="#updates">Updated ' + e(update_time(s['updates'][-1])) + '</a>') if s.get('updates') else ''}{' · <a href="#correction">Corrected</a>' if correction_items(edition, s['id']) else ''}</p><div class="article-thread"><span>Part of <a href="{thread_link(s,'../../')}">{e(s.get('threadTitle',s['title']))}</a></span><a href="{thread_link(s,'../../')}">Follow the thread →</a></div>{story_image(s,"../../")}<p class="article-summary">{e(s['body'])}</p>{key_facts(s)}{full_report(s)}{assessment_box(s)}{updates_full(s)}{corrections(edition,s["id"])}<h2 id="sources-evidence">Sources & evidence</h2>{evidence(s)}<h2 id="story-history">The story so far</h2>{timeline}<p class="source-note">Each dated edition preserves what we reported at the time. Corrections are recorded explicitly.</p></article></main>'''

ABOUT_TEMPLATE = '''<main class="wrap" id="main"><article class="article-page"><div class="eyebrow">The editorial promise</div><h1>Attention is finite.<br><em>Spend it well.</em></h1><p class="article-summary">Het Getij is an independent daily briefing on the Netherlands. It follows what changed in national life, in each of the twelve provinces, and in Dutch science and technology, in one daily edition.</p>{signup}<h2>Change, with context</h2><p>We ask what is new, how strong the evidence is, and what the development could change for people in the Netherlands. A quieter day can mean a shorter edition. A long-running issue, such as housing or nitrogen, can deserve attention even when there is no fresh headline.</p><h2>Every province, every day</h2><p>The province map covers all twelve provinces, from Groningen to Limburg. Each one shows its stories from the edition plus local news that did not make the main page, drawn from the regional broadcasters and newspapers that cover it. If nothing important happened somewhere, we say so.</p><h2>Evidence before certainty</h2><p>Every item links to its sources. We prioritize primary documents, official statements and established reporting, seek independent corroboration, and distinguish an announcement from a demonstrated result. Sources repeating the same original account are not independent confirmation. Company research is labeled as such.</p><h2>Facts and judgments</h2><p>The report and “What changed” describe available evidence. “Why it matters” and “Watch next” are editorial assessments. We show uncertainties instead of manufacturing precise importance scores or unsupported probabilities.</p><h2>A publication with a memory</h2><p>Daily editions are retained in the archive. Continuing stories use stable identifiers so their developments can be followed across editions. The first edition starts that record; it does not invent a past.</p><h2>How each edition is produced</h2><p>Each morning, the edition is researched and assembled from the linked reporting, and each evening it is updated where stories have moved, with context, evidence limitations, and a clear point at which to stop. Follow those sources for their full reporting.</p><h2>Corrections belong in the open</h2><p>If a claim is wrong, we correct it and record what changed. We do not silently erase mistakes from the historical record. <a href="https://github.com/PrototypeVersions/HetGetij/issues/new?labels=correction&amp;title=Correction%3A%20" target="_blank" rel="noopener noreferrer">Report an error on GitHub ↗</a> · <a href="../corrections/">See every correction →</a></p><h2>Images as editorial interpretation</h2><p>Our original illustrations use simple visual metaphors for each story. They are labeled as illustrations, not photographs of the reported events, and are not evidence for the reporting. Maps locate the reporting; charts show sourced figures; illustrations provide a visual interpretation.</p><h2>Your reading stays yours</h2><p>{privacy}</p><h2>Read at your own pace</h2><p>{signup_note}Every main story has a full report with key facts, background, sources and a dated timeline, and shorter items under More that changed open with a tap; Follow opens the whole thread across editions. Provinces gathers each part of the country in one place.</p></article></main>'''

def about_page():
    privacy = 'There is no advertising. '
    if analytics_code():
        privacy += 'We count visits with GoatCounter, a privacy-friendly service that uses no cookies, collects no personal data and does not follow you across sites; it tells us which pages are read, not who reads them. '
    else:
        privacy += 'There are no analytics scripts. '
    if newsletter_user():
        privacy += 'If you sign up for email, Buttondown holds your address and uses it only to send the edition; you can unsubscribe from any email. '
    privacy += 'Catch-up is based on the edition you select. Google Fonts supplies the typography; source links take you to their respective publishers. Your browser and hosting provider may retain ordinary access logs.'
    signup_note = 'The edition can also come to your inbox each morning. ' if newsletter_user() else ''
    return ABOUT_TEMPLATE.replace('{privacy}', privacy).replace('{signup_note}', signup_note).replace('{signup}', signup_form('about'))

if __name__ == '__main__':
    if '--threads' in sys.argv:
        found = {}
        for path in sorted((ROOT/'data/editions').glob('*.json')):
            x = json.loads(path.read_text())
            for s in x['stories']:
                key = s.get('threadId', s['id'])
                entry = found.setdefault(key, {'title': s.get('threadTitle', s['title']), 'reports': 0, 'first': x['date']})
                entry['reports'] += 1; entry['last'] = x['date']
                if s.get('threadTitle'): entry['title'] = s['threadTitle']
        print('threadId | title | reports | first seen | last seen')
        for key, v in sorted(found.items(), key=lambda kv: kv[1]['last'], reverse=True):
            print(f"{key} | {v['title']} | {v['reports']} | {v['first']} | {v['last']}")
        sys.exit(0)
    SITE.update(load_site())
    EDITIONS = [json.loads(p.read_text()) for p in sorted((ROOT/'data/editions').glob('*.json'))]
    assert EDITIONS, 'No editions to publish'
    newest_date = date.fromisoformat(EDITIONS[-1]['date'])
    for edition in EDITIONS:
        if (newest_date - date.fromisoformat(edition['date'])).days <= 1:
            validate(edition)  # today's and yesterday's editions must pass every current rule
        else:
            try: validate(edition)
            except (AssertionError, KeyError, ValueError) as problem:
                print(f'Note: older edition {edition["date"]} does not meet a current rule ({problem}); published as it was.')
    assert len({x['date'] for x in EDITIONS}) == len(EDITIONS)
    if OUT.exists(): shutil.rmtree(OUT)
    OUT.mkdir()
    shutil.copytree(ROOT/'assets',OUT/'assets')
    for edition in EDITIONS: prepare_visuals(edition,OUT)
    latest = EDITIONS[-1]
    THREADS = {}
    for edition in EDITIONS:
        for story in edition['stories']: THREADS.setdefault(thread_key(story),[]).append((edition,story))
    write('index.html',shell(home(latest),latest))
    for edition in EDITIONS:
        write(f'editions/{edition["date"]}/index.html',shell(home(edition,'../../',True),edition,f'Het Getij — {pretty(edition["date"])}','../../',f'editions/{edition["date"]}/'))
    index = {}
    for edition in EDITIONS:
        for s in edition['stories']: index.setdefault(s['id'],[]).append((edition,s))
    for edition in EDITIONS:
        for r in region_items(edition):
            title=f'{r["name"]} — Het Getij'
            about=r['summary'] or f'News from {r["name"]} in Het Getij.'
            if edition is latest: write(f'regions/{r["slug"]}/index.html',shell(region_page(r,edition,'../../'),edition,title,'../../',f'regions/{r["slug"]}/',description=about))
            write(f'editions/{edition["date"]}/regions/{r["slug"]}/index.html',shell(region_page(r,edition,'../../../../'),edition,title,'../../../../',f'editions/{edition["date"]}/regions/{r["slug"]}/',description=about))
    write('threads/index.html','<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Stories — Het Getij</title><link rel="canonical" href="'+BASE+'/archive/"><meta http-equiv="refresh" content="0; url=../archive/#stories"></head><body><p><a href="../archive/#stories">Stories have moved to the archive →</a></p></body></html>')
    for slug,history in THREADS.items():
        current=history[-1][1]
        write(f'threads/{slug}/index.html',shell(thread_page(history),latest,current.get('threadTitle',current['title'])+' — Het Getij','../../',f'threads/{slug}/'))
    for slug,history in index.items():
        edition,s = history[-1]
        write(f'stories/{slug}/index.html',shell(article(s,edition,history),edition,s['title']+' — Het Getij','../../',f'stories/{slug}/',description=s['body']))
    by_month = {}
    for x in reversed(EDITIONS): by_month.setdefault(x['date'][:7], []).append(x)
    rows = ''.join(f'<details class="archive-month"{" open" if i == 0 else ""}><summary>{date.fromisoformat(month + "-01").strftime("%B %Y")} · {len(items)} edition{"s" if len(items) != 1 else ""}</summary>' + ''.join(f'<div class="archive-row"><a href="../editions/{x["date"]}/">{pretty(x["date"])}</a><span>Edition {x["number"]:03} · {len(x["stories"])} stories ↗</span></div>' for x in items) + '</details>' for i, (month, items) in enumerate(by_month.items()))
    archive_html = (f'<main class="wrap" id="main"><div class="eyebrow" style="margin-top:45px">The record, kept</div><h1 class="archive-title">A country in chapters.</h1>'
                    f'<p>Follow a story from the start, or open any day’s edition as it was published.</p><nav class="archive-jump" aria-label="Archive sections"><a href="#stories">By story</a><a href="#editions">By date</a></nav>'
                    f'<section id="stories" class="archive-block"><div class="section-title"><div><span class="eyebrow">The longer view</span><h2>Stories, <em>followed.</em></h2></div></div><p class="archive-lede">The most followed stories come first. Each opens a dated timeline of everything we have reported on it.</p>{thread_sections(THREADS, "../")}</section>'
                    f'<section id="editions" class="archive-block"><div class="section-title"><div><span class="eyebrow">Every edition</span><h2>Day by <em>day.</em></h2></div></div><div class="archive-list">{rows}</div></section></main>')
    write('archive/index.html',shell(archive_html,latest,'The archive — Het Getij','../','archive/'))
    log_by_month = {}
    for x in reversed(EDITIONS):
        titles = {s['id']: s['title'] for s in x['stories']}
        for c in reversed(x.get('corrections', [])):
            title = titles.get(c['storyId'], c['storyId'])
            log_by_month.setdefault(x['date'][:7], []).append(f'<article class="correction-entry"><h2><a href="../stories/{e(c["storyId"])}/">{e(title)}</a></h2><p class="source-note">Edition of {e(pretty(x["date"]))}</p><div class="correction-box">{correction_body(c)}</div></article>')
    log_html = ''.join(f'<details class="archive-month"{" open" if i == 0 else ""}><summary>{date.fromisoformat(month + "-01").strftime("%B %Y")} · {len(items)} correction{"s" if len(items) != 1 else ""}</summary>{"".join(items)}</details>' for i, (month, items) in enumerate(log_by_month.items()))
    report_link = '<a href="https://github.com/PrototypeVersions/HetGetij/issues/new?labels=correction&amp;title=Correction%3A%20" target="_blank" rel="noopener noreferrer">Report an error on GitHub ↗</a>'
    corrections_html = (f'<main class="wrap" id="main"><article class="article-page"><div class="eyebrow">The record, corrected</div><h1>Corrections.</h1>'
                        f'<p class="article-summary">When we get something wrong, we fix it and say so. Each correction also appears at the end of the story it corrects.</p>'
                        f'<p>{report_link}</p>{log_html or "<p>No corrections have been needed so far.</p>"}</article></main>')
    write('corrections/index.html',shell(corrections_html,latest,'Corrections — Het Getij','../','corrections/'))
    write('about/index.html',shell(about_page(),latest,'Our approach — Het Getij','../','about/'))
    recent = [x for x in EDITIONS if (date.fromisoformat(latest['date']) - date.fromisoformat(x['date'])).days <= 35]
    def slim(x):
        lead = lead_story(x)['id']
        out = []
        for s in x['stories']:
            item = {'id': s['id'], 'h': thread_key(s), 'ht': s.get('threadTitle', s['title']), 't': s['title'], 'w': s['whatChanged'], 's': s['section']}
            if s.get('threadSummary'): item['hs'] = s['threadSummary']
            if s['id'] == lead: item['l'] = 1
            if s.get('updates'): item['u'] = s['updates'][-1]['text']
            out.append(item)
        return {'date': x['date'], 'stories': out}
    write('data/catchup.json', json.dumps({'first': EDITIONS[0]['date'], 'latest': latest['date'], 'editions': [slim(x) for x in recent]}, ensure_ascii=False, separators=(',', ':')))
    def feed_item(x):
        stamp = datetime.fromisoformat(x['cutoff'].replace('Z', '+00:00')).strftime('%a, %d %b %Y %H:%M:%S +0000')
        link = f'{BASE}/editions/{x["date"]}/'
        groups = [('Across the Netherlands', ('world',)), ('More that changed', ('more',)), ('Frontiers', ('ai', 'frontiers')), ('Still matters', ('still',))]
        body = f'<p>{e(x["opening"])}</p>'
        for label, sections in groups:
            picks = [s for s in x['stories'] if s['section'] in sections]
            if picks: body += f'<h3>{label}</h3><ul>' + ''.join(f'<li><a href="{BASE}/stories/{s["id"]}/">{e(s["title"])}</a>. {e(s["whatChanged"])}</li>' for s in picks) + '</ul>'
        body += f'<p><a href="{link}">Read the full edition →</a></p>'
        return f'<item><title>{xml_escape("Het Getij — "+pretty(x["date"]))}</title><link>{link}</link><guid isPermaLink="true">{link}</guid><pubDate>{stamp}</pubDate><description><![CDATA[{body}]]></description></item>'
    items=''.join(feed_item(x) for x in list(reversed(EDITIONS))[:30])
    write('feed.xml',f'<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>Het Getij</title><link>{BASE}/</link><description>A daily briefing on what changed in the Netherlands.</description><language>en</language>{items}</channel></rss>')
    paths=['','archive/','about/','corrections/']+[f'threads/{slug}/' for slug in THREADS]+[f'stories/{s}/' for s in index]+[f'editions/{x["date"]}/' for x in EDITIONS]+[f'regions/{slug}/' for slug in REGION_SLUGS]
    write('sitemap.xml','<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join(f'<url><loc>{BASE}/{x}</loc></url>' for x in paths)+'</urlset>')
    write('robots.txt',f'User-agent: *\nAllow: /\nSitemap: {BASE}/sitemap.xml\n')
    write('.nojekyll','')
    write('404.html',shell('<main class="wrap article-page" id="main"><h1>This page hasn’t made the edition.</h1><p><a href="/HetGetij/">Return to Het Getij →</a></p></main>',latest,'Page not found — Het Getij','/HetGetij/'))
    print(f'Built {len(EDITIONS)} edition(s), {len(index)} story pages and {len(paths)} indexed pages.')
