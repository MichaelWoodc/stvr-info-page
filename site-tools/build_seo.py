"""Generate search metadata, canonical URLs, sitemap, and static page content."""
import functools
import html
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import re
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
PUBLIC = 'https://michaelwoodc.github.io/stvr-info-page/'
PAGES = {
    'index.html': (
        'Patrick Forelli Vacation Rentals | Savannah GA Airbnb & Vrbo',
        'Independent neighbor commentary on Patrick Forelli vacation rentals in Savannah, GA. Airbnb and Vrbo guest reviews, property photos, videos and reports.',
        'whitefield/whitefieldbed_bug_bordello.jpg'),
    'bed-bug-bordello.html': (
        'Bed Bug Bordello | Patrick Forelli, Savannah GA Rental Reviews',
        'Bed Bug Bordello: guest reviews and neighbor commentary about Patrick Forelli vacation rentals in Savannah, GA, including Airbnb, Vrbo, photos and videos.',
        'whitefield/whitefieldbed_bug_bordello.jpg'),
    'garland-gta.html': (
        'Garland GTA | Patrick Forelli, Savannah GA Vacation Rentals',
        'Garland GTA: independent neighbor commentary about Patrick Forelli vacation rentals in Savannah, GA, with Airbnb and Vrbo context, trash photos and parody artwork.',
        'garland/garland_gta.jpg'),
}
def write_utf8(path, text):
    text = text.replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n')
    path.write_bytes(text.encode('utf-8'))

CONTEXT = 'Independent neighbor commentary on vacation rentals associated with Patrick Forelli in Savannah, GA, including Airbnb and Vrbo guest reviews.'

def canonical(name):
    return PUBLIC + 'dist/' + ('' if name == 'index.html' else name)

for folder in ['dist', 'parody-site-alternative/dist']:
    app = ROOT / folder / 'app.js'
    text = app.read_text(encoding='utf-8')
    titles = {'home':PAGES['index.html'][0], 'whitefield':PAGES['bed-bug-bordello.html'][0], 'garland':PAGES['garland-gta.html'][0]}
    text = re.sub(r'^document\.title=.*$', 'document.title='+json.dumps(titles)+'[page];', text, count=1, flags=re.M)
    text = text.replace('<p class="intro">${description}</p>', '<p class="intro">${description}</p><p class="site-context">'+CONTEXT+'</p>') if 'class="site-context"' not in text else text
    write_utf8(app, text)
    css = ROOT / folder / 'style.css'
    text = css.read_text(encoding='utf-8')
    if '.site-context{' not in text:
        text += '\n.site-context{font-size:13px;max-width:650px;color:#58645c}\n'
    write_utf8(css, text)
    for name, (title, description, image) in PAGES.items():
        path = ROOT / folder / name
        text = path.read_text(encoding='utf-8')
        text = re.sub(r'<title>.*?</title>', '<title>'+html.escape(title)+'</title>', text, flags=re.S)
        text = re.sub(r'<meta name="description"[^>]*>', '<meta name="description" content="'+html.escape(description, quote=True)+'">', text)
        text = re.sub(r'\n?<!-- SEO metadata -->.*?<!-- /SEO metadata -->\n?', '', text, flags=re.S)
        url = canonical(name)
        image_url = PUBLIC + 'dist/assets/' + image
        schema = {
            '@context':'https://schema.org', '@type':'WebPage', 'name':title,
            'description':description, 'url':url, 'inLanguage':'en-US',
            'isPartOf':{'@type':'WebSite','name':"The Neighbor's Travel Guide",'url':PUBLIC+'dist/'},
            'about':[{'@type':'Person','name':'Patrick Forelli'}, {'@type':'Place','name':'Savannah, Georgia'}],
        }
        metadata = '\n<!-- SEO metadata -->\n'+ '\n'.join([
            '<link rel="canonical" href="'+url+'">',
            '<meta name="robots" content="index,follow,max-image-preview:large">',
            '<meta property="og:type" content="website">',
            '<meta property="og:site_name" content="The Neighbor\'s Travel Guide">',
            '<meta property="og:title" content="'+html.escape(title, quote=True)+'">',
            '<meta property="og:description" content="'+html.escape(description, quote=True)+'">',
            '<meta property="og:url" content="'+url+'">',
            '<meta property="og:image" content="'+image_url+'">',
            '<meta property="og:image:alt" content="Supplied vacation rental parody artwork for Savannah, GA">',
            '<meta name="twitter:card" content="summary_large_image">',
            '<script type="application/ld+json">'+json.dumps(schema, ensure_ascii=False).replace('<','\\u003c')+'</script>',
        ])+'\n<!-- /SEO metadata -->\n'
        text = text.replace('</head>', metadata+'</head>')
        write_utf8(path, text)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass
    def copyfile(self, source, output):
        try:
            super().copyfile(source, output)
        except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
            pass

server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT)))
threading.Thread(target=server.serve_forever, daemon=True).start()
try:
    with sync_playwright() as p:
        browser = p.chromium.launch(channel='msedge', headless=False)
        context = browser.new_context()
        context.route('**/*', lambda route: route.continue_() if route.request.url.startswith('http://127.0.0.1:') else route.abort())
        page = context.new_page()
        for folder in ['dist', 'parody-site-alternative/dist']:
            for name in PAGES:
                page.goto(f'http://127.0.0.1:{server.server_port}/{folder}/{name}', wait_until='domcontentloaded')
                page.wait_for_selector('#app main')
                if name == 'bed-bug-bordello.html':
                    page.wait_for_function('document.querySelector("#review-text").textContent!=="Loading supplied text…"')
                    assert page.locator('#reviews h2').inner_text() == 'What guests are saying.'
                rendered = page.locator('#app').inner_html()
                path = ROOT / folder / name
                text = path.read_text(encoding='utf-8')
                begin = text.index('<div id="app">') + len('<div id="app">')
                end = text.index('<dialog id="viewer">', begin)
                text = text[:begin] + rendered + '</div>' + text[end:]
                write_utf8(path, text)
                print('Metadata and static content generated: '+folder+'/'+name, flush=True)
        browser.close()
finally:
    server.shutdown()

root_index = ROOT / 'index.html'
text = root_index.read_text(encoding='utf-8')
text = re.sub(r'<title>.*?</title>', '<title>'+html.escape(PAGES['index.html'][0])+'</title>', text, flags=re.S)
if 'rel="canonical"' not in text:
    text = text.replace('</head>', '<link rel="canonical" href="'+PUBLIC+'dist/"></head>')
write_utf8(root_index, text)

owner = ROOT / 'owners/cozy_corner_rentals/cozy_corner_rentals.html'
text = owner.read_text(encoding='utf-8')
title = 'Patrick Forelli & Cozy Corner Rentals | Savannah GA Airbnb & Vrbo'
text = re.sub(r'<title>.*?</title>', '<title>'+html.escape(title)+'</title>', text, flags=re.S)
if 'rel="canonical"' not in text:
    text = text.replace('</head>', '<link rel="canonical" href="'+PUBLIC+'owners/cozy_corner_rentals/cozy_corner_rentals.html"><meta name="description" content="Neighbor-created reports and guest-review material concerning Patrick Forelli, Cozy Corner Rentals, and vacation rentals in Savannah, GA on Airbnb and Vrbo."></head>')
write_utf8(owner, text)

urls = [canonical(name) for name in PAGES] + [PUBLIC+'owners/cozy_corner_rentals/cozy_corner_rentals.html']
sitemap = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'+'\n'.join('  <url><loc>'+html.escape(url)+'</loc></url>' for url in urls)+'\n</urlset>\n'
write_utf8(ROOT / 'sitemap.xml', sitemap)
print('Canonical sitemap generated.', flush=True)
