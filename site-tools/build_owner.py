"""Extract the supplied Facebook photo posts and refresh the owner section.

Run with the existing Python environment (BeautifulSoup required).
Original offline captures and separately supplied photographs are untouched.
"""
import base64
import html
import json
from pathlib import Path
import re
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / 'dist'
PHOTOS = DIST / 'assets/owner/photos'
posts = {}
for capture in sorted(PHOTOS.glob('*.html')):
    soup = BeautifulSoup(capture.read_text(encoding='utf-8'), 'html.parser')
    for image in soup.find_all('img', alt='No photo description available.'):
        src = image.get('src', '')
        if not src.startswith('data:image/jpeg;base64,'):
            continue
        parent = image
        for _ in range(25):
            parent = parent.parent
            if parent is None:
                break
            if 'Shared with Public' not in parent.get_text(' ', strip=True):
                continue
            link = parent.find('a', href=re.compile(r'/photo/\?fbid='))
            if link is None:
                break
            photo_id = parse_qs(urlparse(link['href']).query)['fbid'][0]
            # The message container preserves the author's paragraphs and punctuation.
            message = parent.find(attrs={'data-ad-preview': 'message'})
            if message is None:
                raise ValueError(f'No caption container for {photo_id}')
            caption = message.get_text(' ', strip=True)
            caption = re.sub(r'\s*See less$', '', caption)
            filename = f'facebook-{photo_id}.jpg'
            (PHOTOS / filename).write_bytes(base64.b64decode(src.split(',', 1)[1]))
            posts[photo_id] = (filename, caption)
            break

assert len(posts) == 6, f'Expected six photo posts, found {len(posts)}'
cards = []
for i, (photo_id, (filename, caption)) in enumerate(posts.items(), 1):
    image_path = 'assets/owner/photos/' + filename
    label = f'Humans of Patrick · photo {i}'
    cards.append(f'''<figure class="owner-card">
<button class="image-button" data-image="{image_path}" data-caption="{label}" aria-label="Enlarge {label}"><img loading="lazy" src="{image_path}" alt="Photograph accompanying Humans of Patrick post {i}"></button>
<figcaption><blockquote>{html.escape(caption)}</blockquote><p class="source">— <cite>Humans of Patrick</cite> · <a href="https://www.facebook.com/photo/?fbid={photo_id}" target="_blank" rel="noopener noreferrer">Original Facebook photo ↗</a></p></figcaption></figure>''')
section = '''<section id="about-owner" aria-labelledby="owner-heading">
<div class="eyebrow">Behind the brochure / The owner edition</div>
<h2 id="owner-heading">About the owner</h2>
<p class="intro">The brochure has a photo album. Meet the Patrick of <a href="https://www.facebook.com/humansofpatrick/" target="_blank" rel="noopener noreferrer">Humans of Patrick</a>, in the page’s own words.</p>
<p class="note">Photos and quoted captions below come from the supplied offline copies of the Humans of Patrick Facebook page, saved October 17, 2026. They are presented as the page’s humorous posts, not verified biographical statements or independently authenticated quotations by Patrick Forelli. No affiliation or endorsement is implied.</p>
<div class="owner-gallery">''' + '\n'.join(cards) + '</div></section>'

from owner_editorial import biggerpockets_section
editorial = biggerpockets_section(ROOT)
section = section.replace('id="about-owner"', 'id="facebook-album"').replace('About the owner</h2>', 'The Facebook photo album</h2>')
content = '<section class="owner-intro" id="about-owner"><div class="eyebrow">The Neighbor’s Travel Guide / Move fast. Break the peace.</div><h1>The tech-bro / frat-bro guide<br>to investing Mom &amp; Dad’s money.</h1><p class="intro">Disrupt the neighborhood. Scale the portfolio. Send Mom &amp; Dad the pitch deck. An unauthorized, satirical owner’s manual inspired by Patrick Forelli’s own forum posts.</p><a class="button" href="#forum-files">Read the forum files ↓</a><a class="button secondary" href="#facebook-album">Visit the photo album ↓</a><p class="source">About the owner · An independent parody. The tech-bro / frat-bro persona is our caricature; quotes are sourced and punchlines are ours.</p></section>' + editorial + section
app_path = DIST / 'app.js'
app = app_path.read_text(encoding='utf-8')
app = re.sub(r'^const ownerSection=.*;\n', '', app, flags=re.M)
app = 'const ownerSection=()=>'+json.dumps(content, ensure_ascii=False)+';\n'+app
app = app.replace("const page=path.includes('bed-bug-bordello')", "const page=path.includes('about-owner')?'owner':path.includes('bed-bug-bordello')")
app = app.replace("${page==='home'?home()+ownerSection():", "${page==='owner'?ownerSection():page==='home'?home():")
app = app.replace('index.html#about-owner', 'about-owner.html')
app = app.replace('document.title={', 'document.title={"owner":"About the owner | Patrick Forelli · The Neighbor’s Travel Guide",') if '"owner":"About the owner' not in app else app
app_path.write_text(app, encoding='utf-8')
for name in ['index.html', 'bed-bug-bordello.html', 'garland-gta.html']:
    path = DIST / name
    text = path.read_text(encoding='utf-8').replace('index.html#about-owner', 'about-owner.html')
    if name == 'index.html':
        text = re.sub(r'<section id="about-owner".*?</section>', '', text, flags=re.S)
    path.write_text(text, encoding='utf-8')
# Use the established page shell, retaining a full static version for no-JS readers.
text = (DIST / 'index.html').read_text(encoding='utf-8')
text = re.sub(r'<main>.*?</main>', '<main>'+content+'</main>', text, flags=re.S)
text = re.sub(r'<title>.*?</title>', '<title>About the owner | Patrick Forelli · The Neighbor’s Travel Guide</title>', text)
text = text.replace('https://michaelwoodc.github.io/stvr-info-page/dist/"', 'https://michaelwoodc.github.io/stvr-info-page/dist/about-owner.html"')
text = re.sub(r'<script type="application/ld\+json">.*?</script>', '', text, flags=re.S)
text = text.replace('Independent neighbor commentary on Patrick Forelli vacation rentals in Savannah, GA. Airbnb and Vrbo guest reviews, property photos, videos and reports.', 'A satirical owner’s manual featuring sourced Patrick Forelli BiggerPockets excerpts and the Humans of Patrick photo album.')
text = text.replace('content="Patrick Forelli Vacation Rentals | Savannah GA Airbnb &amp; Vrbo"', 'content="About the owner | Patrick Forelli · The Neighbor’s Travel Guide"')
(DIST / 'about-owner.html').write_text(text, encoding='utf-8')
print(f'Refreshed separate owner page: 7 verified forum stories and {len(posts)} photo posts.')
