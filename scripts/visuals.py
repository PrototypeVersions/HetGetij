"""Render sourced geography and explicitly supplied chart data as static SVG.

Two kinds of map: a Netherlands map built from CBS province outlines (type "nl"),
and the Natural Earth world map for stories that reach beyond the country (type "map")."""
import html, json, math
from pathlib import Path

DATA = json.loads((Path(__file__).parent/'data/world-110m.json').read_text())
NL = json.loads((Path(__file__).parent/'data/provinces-2026.topojson').read_text())
ESC = lambda value: html.escape(str(value), quote=True)

def geographic_polygons():
    scale = DATA['transform']['scale']; translate = DATA['transform']['translate']
    arcs = []
    for arc in DATA['arcs']:
        x = y = 0; points = []
        for dx, dy in arc:
            x += dx; y += dy
            points.append((x*scale[0]+translate[0], y*scale[1]+translate[1]))
        arcs.append(points)
    def ring(indices):
        result = []
        for index in indices:
            points = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
            result.extend(points if not result else points[1:])
        return result
    countries = []
    for geometry in DATA['objects']['countries']['geometries']:
        polygons = [geometry['arcs']] if geometry['type']=='Polygon' else geometry['arcs']
        countries.append((str(geometry.get('id','')).zfill(3), [[ring(indices) for indices in poly] for poly in polygons]))
    return countries

COUNTRIES = geographic_polygons()
COUNTRY_IDS = {code for code,_ in COUNTRIES}

def svg_shell(title, description, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 800" role="img" aria-labelledby="title desc"><title id="title">{ESC(title)}</title><desc id="desc">{ESC(description)}</desc><rect width="1200" height="800" fill="#0b1825"/>{body}</svg>'''

def map_svg(story, visual):
    west,south,east,north = visual['bounds']
    cosine = math.cos(math.radians((south+north)/2))
    factor = min(1080/((east-west)*cosine), 580/(north-south))
    left = (1200-(east-west)*cosine*factor)/2
    top = 112+(580-(north-south)*factor)/2
    def project(lon,lat): return (left+(lon-west)*cosine*factor, top+(north-lat)*factor)
    def path(ring): return 'M'+' L'.join(f'{x:.2f},{y:.2f}' for x,y in (project(lon,lat) for lon,lat in ring))+' Z'
    body = '<defs><clipPath id="map-area"><rect x="25" y="90" width="1150" height="625"/></clipPath></defs><g clip-path="url(#map-area)">'
    step = 30 if east-west>120 else (10 if east-west>40 else 5)
    for lon in range(math.ceil(west/step)*step, math.floor(east/step)*step+1, step):
        x1,y1=project(lon,south);x2,y2=project(lon,north)
        body+=f'<path d="M{x1:.1f},{y1:.1f}L{x2:.1f},{y2:.1f}" stroke="#20364a" stroke-width="1"/>'
    for lat in range(math.ceil(south/step)*step, math.floor(north/step)*step+1, step):
        x1,y1=project(west,lat);x2,y2=project(east,lat)
        body+=f'<path d="M{x1:.1f},{y1:.1f}L{x2:.1f},{y2:.1f}" stroke="#20364a" stroke-width="1"/>'
    focus = set(visual.get('countries',[]))
    for code,polygons in COUNTRIES:
        parts = []
        for poly in polygons:
            points = [point for ring in poly for point in ring]
            if not points: continue
            if max(p[0] for p in points)<west or min(p[0] for p in points)>east or max(p[1] for p in points)<south or min(p[1] for p in points)>north: continue
            parts.extend(path(ring) for ring in poly)
        if parts:
            active = code in focus
            body+=f'<path d="{" ".join(parts)}" fill="{"#31516a" if active else "#152a3b"}" stroke="{"#f0954a" if active else "#59758c"}" stroke-width="{"1.8" if active else ".9"}" fill-rule="evenodd"/>'
    body+='</g>'
    for label in visual.get('labels',[]):
        x,y=project(label['lon'],label['lat']); water=label.get('kind')=='water'
        body+=f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" fill="{"#8ba9c3" if water else "#b9cfe2"}" font-family="Georgia,serif" font-size="{36 if water else 32}" font-style="{"italic" if water else "normal"}">{ESC(label["label"])}</text>'
    for point in story.get('locations',[]):
        if not (west<=point['lon']<=east and south<=point['lat']<=north): continue
        x,y=project(point['lon'],point['lat']); anchor='end' if x>860 else 'start'; offset=-15 if anchor=='end' else 15
        body+=f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#f0954a" fill-opacity=".15"/><circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#f6ad6c" stroke="#09131d" stroke-width="2"/><text x="{x+offset:.1f}" y="{y-15:.1f}" text-anchor="{anchor}" fill="#d8e7f5" stroke="#0b1825" stroke-width="5" paint-order="stroke" font-family="Arial,sans-serif" font-size="30">{ESC(point.get("mapLabel",point["label"]))}</text>'
    body+=f'<text x="54" y="62" fill="#f0954a" font-family="Arial,sans-serif" font-size="22" letter-spacing="3">{ESC(visual["title"].upper())}</text><path d="M54 738H1146" stroke="#2b4052"/><circle cx="62" cy="768" r="5" fill="#f0954a"/><text x="80" y="775" fill="#9fb5c9" font-family="Arial,sans-serif" font-size="18">Approximate reporting locations · country outlines simplified</text>'
    return svg_shell(visual['title'],visual['alt'],body)

def bar_svg(visual):
    values=visual['values']; ceiling=math.ceil(max(v['value'] for v in values)/5)*5
    if ceiling==0: ceiling=1
    body=f'<text x="70" y="90" fill="#c5d9f1" font-family="Georgia,serif" font-size="48">{ESC(visual["title"])}</text>'
    for i in range(4):
        value=ceiling*i/3; y=630-value/ceiling*395
        body+=f'<path d="M100 {y:.1f}H1110" stroke="#2b4052"/><text x="82" y="{y+7:.1f}" text-anchor="end" fill="#9fb5c9" font-family="Arial,sans-serif" font-size="20">{value:g}{ESC(visual["unit"])}</text>'
    width=min(240,700/len(values)); stride=940/len(values)
    for i,item in enumerate(values):
        x=130+i*stride+(stride-width)/2;height=item['value']/ceiling*395;y=630-height
        color='#f0954a' if i==len(values)-1 else '#668aa7'
        body+=f'<rect x="{x:.1f}" y="{y:.1f}" width="{width:.1f}" height="{height:.1f}" fill="{color}"/><text x="{x+width/2:.1f}" y="{y-23:.1f}" text-anchor="middle" fill="#d8e7f5" font-family="Georgia,serif" font-size="60">{item["value"]:g}{ESC(visual["unit"])}</text><text x="{x+width/2:.1f}" y="678" text-anchor="middle" fill="#b9cfe2" font-family="Arial,sans-serif" font-size="40">{ESC(item["label"])}</text>'
    body+=f'<text x="70" y="753" fill="#9fb5c9" font-family="Arial,sans-serif" font-size="28">{ESC(visual["measure"])}</text>'
    return svg_shell(visual['title'],visual['alt'],body)

# ---------------------------------------------------------------- Netherlands
PROVINCE_SLUGS = {'Groningen': 'groningen', 'Fryslân': 'friesland', 'Drenthe': 'drenthe', 'Overijssel': 'overijssel',
                  'Flevoland': 'flevoland', 'Gelderland': 'gelderland', 'Utrecht': 'utrecht', 'Noord-Holland': 'north-holland',
                  'Zuid-Holland': 'south-holland', 'Zeeland': 'zeeland', 'Noord-Brabant': 'north-brabant', 'Limburg': 'limburg'}

def province_polygons():
    scale = NL['transform']['scale']; translate = NL['transform']['translate']
    arcs = []
    for arc in NL['arcs']:
        x = y = 0; points = []
        for dx, dy in arc:
            x += dx; y += dy
            points.append((x*scale[0]+translate[0], y*scale[1]+translate[1]))
        arcs.append(points)
    def ring(indices):
        result = []
        for index in indices:
            points = arcs[index] if index >= 0 else list(reversed(arcs[~index]))
            result.extend(points if not result else points[1:])
        return result
    out = []
    for g in list(NL['objects'].values())[0]['geometries']:
        polygons = [g['arcs']] if g['type'] == 'Polygon' else g['arcs']
        out.append((PROVINCE_SLUGS[g['properties']['statnaam']], [[ring(r) for r in poly] for poly in polygons]))
    return out

PROVINCES = province_polygons()
NL_BOUNDS = (3.3, 50.72, 7.25, 53.58)  # west, south, east, north
NL_COS = math.cos(math.radians(52.2))

def nl_project(lon, lat, width, height, bounds=NL_BOUNDS, pad=0):
    west, south, east, north = bounds
    f = min((width-2*pad)/((east-west)*NL_COS), (height-2*pad)/(north-south))
    left = (width-(east-west)*NL_COS*f)/2; top = (height-(north-south)*f)/2
    return left+(lon-west)*NL_COS*f, top+(north-lat)*f

def nl_overview_svg(width=520, height=620):
    paths = ''
    for slug, polys in PROVINCES:
        d = ' '.join('M'+' L'.join(f'{x:.1f},{y:.1f}' for x, y in (nl_project(lon, lat, width, height) for lon, lat in r))+' Z' for poly in polys for r in poly)
        paths += f'<path data-province="{slug}" d="{d}"/>'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}"><title>The Netherlands by province</title>'
            f'<g fill="#1c3449" stroke="#6f8aa1" stroke-width=".9" stroke-linejoin="round" fill-rule="evenodd">{paths}</g></svg>')

def nl_map_svg(story, visual):
    focus = set(visual.get('provinces', []))
    points = [p for p in story.get('locations', [])]
    # frame: the whole country, or the focus provinces plus a margin
    if visual.get('zoom') and focus:
        pts = [pt for slug, polys in PROVINCES if slug in focus for poly in polys for r in poly for pt in r] + [(p['lon'], p['lat']) for p in points]
        west, east = min(p[0] for p in pts), max(p[0] for p in pts); south, north = min(p[1] for p in pts), max(p[1] for p in pts)
        mx, my = max(.25, (east-west)*.18), max(.15, (north-south)*.18)
        bounds = (west-mx, south-my, east+mx, north+my)
    else:
        bounds = NL_BOUNDS
    W, H = 1200, 800
    proj = lambda lon, lat: nl_project(lon, lat, 1100, 600, bounds)
    shift = lambda xy: (xy[0]+50, xy[1]+112)
    body = '<defs><clipPath id="map-area"><rect x="25" y="90" width="1150" height="625"/></clipPath></defs><g clip-path="url(#map-area)">'
    for slug, polys in PROVINCES:
        d = ' '.join('M'+' L'.join(f'{x:.1f},{y:.1f}' for x, y in (shift(proj(lon, lat)) for lon, lat in r))+' Z' for poly in polys for r in poly)
        on = slug in focus
        body += f'<path d="{d}" fill="{"#31516a" if on else "#152a3b"}" stroke="{"#f0954a" if on else "#59758c"}" stroke-width="{"2.2" if on else "1"}" stroke-linejoin="round" fill-rule="evenodd"/>'
    body += '</g>'
    for label in visual.get('labels', []):
        x, y = shift(proj(label['lon'], label['lat'])); water = label.get('kind') == 'water'
        body += f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="middle" fill="{"#8ba9c3" if water else "#b9cfe2"}" font-family="Georgia,serif" font-size="{30 if water else 28}" font-style="{"italic" if water else "normal"}">{ESC(label["label"])}</text>'
    for point in points:
        x, y = shift(proj(point['lon'], point['lat']))
        if not (25 <= x <= 1175 and 90 <= y <= 715): continue
        anchor = point.get('anchor') or ('end' if x > 860 else 'start'); offset = -15 if anchor == 'end' else 15
        ly = y - 15 + point.get('labelDy', 0)
        body += (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="12" fill="#f0954a" fill-opacity=".15"/><circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="#f6ad6c" stroke="#09131d" stroke-width="2"/>'
                 f'<text x="{x+offset:.1f}" y="{ly:.1f}" text-anchor="{anchor}" fill="#d8e7f5" stroke="#0b1825" stroke-width="5" paint-order="stroke" font-family="Arial,sans-serif" font-size="28">{ESC(point.get("mapLabel", point["label"]))}</text>')
    body += (f'<text x="54" y="62" fill="#f0954a" font-family="Arial,sans-serif" font-size="22" letter-spacing="3">{ESC(visual["title"].upper())}</text><path d="M54 738H1146" stroke="#2b4052"/>'
             f'<circle cx="62" cy="768" r="5" fill="#f0954a"/><text x="80" y="775" fill="#9fb5c9" font-family="Arial,sans-serif" font-size="18">Approximate reporting locations · province outlines: CBS / Kadaster</text>')
    return svg_shell(visual['title'], visual['alt'], body)

def prepare_visuals(edition, out):
    nl=out/'assets/visuals/nl-overview.svg'
    if not nl.exists():
        nl.parent.mkdir(parents=True,exist_ok=True); nl.write_text(nl_overview_svg())
    overview=out/'assets/visuals/world-overview.svg'
    if not overview.exists():
        paths=''
        for _,polygons in COUNTRIES:
            for poly in polygons:
                d=' '.join('M'+' L'.join(f'{(lon+180)*2.2:.1f},{(84-lat)*2.45:.1f}' for lon,lat in ring)+' Z' for ring in poly)
                paths+=f'<path d="{d}"/>'
        overview.parent.mkdir(parents=True,exist_ok=True)
        overview.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 355"><title>World overview, Natural Earth geography</title><g fill="#1c3449" stroke="#6f8aa1" stroke-width=".5" fill-rule="evenodd">{paths}</g></svg>')
    for story in edition['stories']:
        visual=story.get('visual')
        if not visual: continue
        kind=visual['type']; svg=nl_map_svg(story,visual) if kind=='nl' else map_svg(story,visual) if kind=='map' else bar_svg(visual)
        asset=f'assets/visuals/{edition["date"]}/{story["id"]}.svg'
        target=out/asset;target.parent.mkdir(parents=True,exist_ok=True);target.write_text(svg)
        story['image']={'asset':asset,'alt':visual['alt'],'credit':'Map data: CBS / Kadaster' if kind=='nl' else 'Map data: Natural Earth' if kind=='map' else visual['caption']}
