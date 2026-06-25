#!/usr/bin/env python3
"""
build-search-index.py
Generates search-index.json for the Imagination Ave site-wide search.

Sources:
  - catalog.json         → catalog entries (title, description, note, genre)
  - creators.html        → tools, cameras, learning resources, dev sessions
  - usecases.html        → enterprise, education, healthcare use cases
  - newsletters/*.html   → article headings and summaries

Output: search-index.json in the repo root

Run after any content update:
  python3 build-search-index.py

The index is consumed by Fuse.js in the site header search UI.
Each entry: { id, title, section, page, url, body }
"""

import json, re, unicodedata, os
from html.parser import HTMLParser

REPO = os.path.dirname(os.path.abspath(__file__))

def strip_tags(html):
    return re.sub(r'<[^>]+>', '', html).strip()

def clean(text):
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300]

def slugify(text):
    text = text.lower().strip()
    text = unicodedata.normalize('NFKD', text).encode('ascii','ignore').decode()
    text = re.sub(r'[^\w\s-]','',text)
    text = re.sub(r'[\s_]+','-',text)
    return re.sub(r'-+','-',text).strip('-')[:60]

index = []

# ── 1. catalog.json ──────────────────────────────────────────
def walk_catalog(data, section_label=''):
    if isinstance(data, dict):
        # Entry object
        if 'title' in data and 'id' in data:
            entry_id = data.get('id','')
            title = data.get('title','')
            body = ' '.join(filter(None,[
                data.get('description',''),
                data.get('note',''),
                data.get('genre',''),
            ]))
            url = f"index.html#entry-{entry_id}"
            index.append({
                'id': f"catalog-{entry_id}",
                'title': title,
                'section': section_label or 'Catalog',
                'page': 'Immersive Video',
                'url': url,
                'body': clean(body),
            })
            # Recurse into episodes
            for ep in data.get('episodes', []):
                if ep.get('status') == 'pending': continue
                ep_title = ep.get('title','')
                index.append({
                    'id': f"catalog-{entry_id}-{slugify(ep_title)}",
                    'title': f"{title} — {ep_title}",
                    'section': section_label or 'Catalog',
                    'page': 'Immersive Video',
                    'url': url,
                    'body': clean(ep.get('guest','') + ' ' + ep.get('date','')),
                })
        else:
            for k, v in data.items():
                lbl = data.get('label', section_label)
                walk_catalog(v, lbl)
    elif isinstance(data, list):
        for item in data:
            walk_catalog(item, section_label)

with open(os.path.join(REPO, 'catalog.json')) as f:
    catalog = json.load(f)

# Walk viewer section (Immersive Video page)
walk_catalog(catalog.get('viewer', {}))
viewer_count = len(index)
print(f"catalog.json viewer: {viewer_count} entries")

# Walk spatial_apps section separately — points to spatial-apps.html
spatial = catalog.get('spatial_apps', {})
for entry in spatial.get('entries', []):
    entry_id = entry.get('id', '')
    title = entry.get('title', '')
    body = ' '.join(filter(None, [entry.get('note',''), entry.get('description','')]))
    index.append({
        'id': f"spatial-{entry_id}",
        'title': title,
        'section': 'Spatial Apps',
        'page': 'Spatial Apps',
        'url': f"spatial-apps.html#spatial-{entry_id}",
        'body': clean(body),
    })
print(f"catalog.json spatial_apps: {len(index) - viewer_count} entries")

# ── 2. Static pages (creators.html, usecases.html) ───────────
def extract_static_entries(filepath, page_name):
    with open(filepath) as f:
        html = f.read()
    entries = []
    # Find all <li id="..."> blocks
    pattern = r'<li\s+id="([^"]+)"[^>]*>(.*?)</li>'
    for m in re.finditer(pattern, html, re.DOTALL):
        anchor_id = m.group(1)
        block = m.group(2)
        # Get entry-name
        name_m = re.search(r'class="entry-name"[^>]*>(.*?)</[ap]>', block, re.DOTALL)
        title = strip_tags(name_m.group(1)) if name_m else ''
        # Get entry-note
        note_m = re.search(r'class="entry-note"[^>]*>(.*?)</span>', block, re.DOTALL)
        body = clean(strip_tags(note_m.group(1))) if note_m else ''
        if not title:
            continue
        # Determine section from context (look for nearest preceding h2)
        pos = m.start()
        section_m = re.findall(r'<h[23][^>]*id="[^"]*"[^>]*>(.*?)</h[23]>', html[:pos], re.DOTALL)
        section = strip_tags(section_m[-1]) if section_m else page_name
        entries.append({
            'id': f"page-{anchor_id}",
            'title': title,
            'section': section,
            'page': page_name,
            'url': f"{os.path.basename(filepath)}#{anchor_id}",
            'body': body,
        })
    return entries

creators = extract_static_entries(os.path.join(REPO,'creators.html'), 'Create')
usecases = extract_static_entries(os.path.join(REPO,'usecases.html'), 'Use Cases')
index.extend(creators)
index.extend(usecases)
print(f"creators.html: {len(creators)} entries")
print(f"usecases.html: {len(usecases)} entries")

# ── 3. Newsletter pages ───────────────────────────────────────
NL_DIR = os.path.join(REPO, 'newsletters')
nl_files = [
    ('immersive_newsletter_may15_2026.html',  'May 2026'),
    ('immersive_newsletter_june2026.html',    'June 2026'),
    ('immersive_newsletter_wwdc26.html',      'WWDC26 Special'),
]
nl_count = 0
for fname, label in nl_files:
    fpath = os.path.join(NL_DIR, fname)
    if not os.path.exists(fpath): continue
    with open(fpath) as f:
        html = f.read()
    # Match article headings with id
    for m in re.finditer(r'<(?:h2|p)\s[^>]*id="(article-[^"]+)"[^>]*>(.*?)</(?:h2|p)>', html, re.DOTALL):
        anchor_id = m.group(1)
        title = strip_tags(m.group(2))
        if not title: continue
        # Grab the next ~400 chars of text as body
        pos = m.end()
        snippet = strip_tags(html[pos:pos+600])
        index.append({
            'id': f"nl-{slugify(label)}-{anchor_id}",
            'title': title,
            'section': label,
            'page': 'Newsletter',
            'url': f"newsletters/{fname}#{anchor_id}",
            'body': clean(snippet),
        })
        nl_count += 1
print(f"newsletters: {nl_count} entries")

# ── Write output ─────────────────────────────────────────────
out_path = os.path.join(REPO, 'search-index.json')
with open(out_path, 'w', encoding='utf-8') as f:
    json.dump(index, f, ensure_ascii=False, separators=(',',':'))
print(f"\nWrote {len(index)} total entries to search-index.json ({os.path.getsize(out_path)//1024}KB)")
