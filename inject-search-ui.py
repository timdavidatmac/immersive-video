#!/usr/bin/env python3
"""
inject-search-ui.py
Injects the site-wide search input + Fuse.js script into all four site pages.
Run once after building search-index.json.
Safe to re-run — checks if already injected before modifying.
"""
import re, os

REPO = "/Users/timdavid/Documents/Enchanté/Immersive-newsletter/GitHub-immersive-video/immersive-video"

# Search input HTML — goes inside the site-header-inner div, after <nav>
SEARCH_HTML = '''
      <!-- ── Site-wide search ── -->
      <div class="site-search" role="search" aria-label="Site-wide search">
        <input
          type="search"
          class="site-search-input"
          id="site-search-input"
          placeholder="Search…"
          aria-label="Search all content"
          autocomplete="off"
          spellcheck="false"
        >
        <div class="site-search-results" id="site-search-results" role="listbox" aria-live="polite"></div>
      </div>'''

# Fuse.js CDN + search logic — goes before </body>
# The path prefix adjusts based on whether the file is in newsletters/ or root
def search_js(path_prefix=''):
    return f'''
  <!-- ── Site-wide search JS ── -->
  <script src="https://cdn.jsdelivr.net/npm/fuse.js@7.0.0/dist/fuse.min.js"></script>
  <script>
  (function() {{
    const input  = document.getElementById('site-search-input');
    const box    = document.getElementById('site-search-results');
    if (!input || !box) return;

    let fuse = null;

    function loadIndex() {{
      fetch('{path_prefix}search-index.json')
        .then(r => r.json())
        .then(data => {{
          fuse = new Fuse(data, {{
            keys: [
              {{ name: 'title',   weight: 0.6 }},
              {{ name: 'body',    weight: 0.3 }},
              {{ name: 'section', weight: 0.1 }},
            ],
            threshold: 0.35,
            includeScore: true,
            minMatchCharLength: 2,
          }});
        }});
    }}

    // Load index on first focus
    input.addEventListener('focus', function onFocus() {{
      if (!fuse) loadIndex();
      input.removeEventListener('focus', onFocus);
    }}, {{ once: true }});

    input.addEventListener('input', function() {{
      const q = this.value.trim();
      if (!q || !fuse) {{ close(); return; }}
      const results = fuse.search(q, {{ limit: 10 }});
      if (!results.length) {{
        box.innerHTML = '<div class="search-no-results">No results found</div>';
        box.classList.add('active');
        return;
      }}
      box.innerHTML = results.map(r => {{
        const item = r.item;
        const base = '{path_prefix}';
        const url  = base + item.url;
        return `<a class="search-result-item" href="${{url}}">
          <span class="search-result-title">${{item.title}}</span>
          <span class="search-result-meta">
            <span class="search-result-page">${{item.page}}</span>
            ${{item.section}}
          </span>
        </a>`;
      }}).join('');
      box.classList.add('active');
    }});

    // Close on outside click
    document.addEventListener('click', function(e) {{
      if (!input.contains(e.target) && !box.contains(e.target)) close();
    }});

    // Keyboard: Escape to close
    input.addEventListener('keydown', function(e) {{
      if (e.key === 'Escape') {{ close(); input.blur(); }}
    }});

    function close() {{
      box.classList.remove('active');
      box.innerHTML = '';
    }}
  }})();
  </script>'''

FILES = [
    ('index.html',                      ''),
    ('creators.html',                   ''),
    ('usecases.html',                   ''),
    ('newsletters/index.html',          '../'),
]

for fname, prefix in FILES:
    fpath = os.path.join(REPO, fname)
    with open(fpath, 'r', encoding='utf-8') as f:
        content = f.read()

    changed = False

    # Inject search HTML after </nav> if not already present
    if 'site-search-input' not in content:
        content = content.replace('    </div>\n  </header>', SEARCH_HTML + '\n    </div>\n  </header>', 1)
        changed = True

    # Inject JS before </body> if not already present
    if 'site-search-input' not in content or 'fuse.min.js' not in content:
        content = content.replace('</body>', search_js(prefix) + '\n</body>', 1)
        changed = True

    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"{'updated' if changed else 'skipped (already injected)'}: {fname}")

print("Done.")
