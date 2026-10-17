"""Sourced parody copy. Every excerpt is checked against its saved author post."""
from datetime import date
import html
import json
from pathlib import Path
import re

def biggerpockets_section(root):
    from bs4 import BeautifulSoup
    records = []
    def walk(value, title):
        if isinstance(value, dict):
            author = value.get('author', {})
            if isinstance(author, dict) and author.get('name') == 'Patrick Forelli' and value.get('dateCreated'):
                records.append({**value, 'thread_title': title})
            for item in value.values():
                walk(item, title)
        elif isinstance(value, list):
            for item in value:
                walk(item, title)
    for path in (root / 'dist/patricia').glob('*.html'):
        soup = BeautifulSoup(path.read_text(encoding='utf-8'), 'html.parser')
        title = soup.title.get_text().split(' (10_17_2026')[0]
        canonical = soup.find('link', rel='canonical')
        for script in soup.select('script[type="application/ld+json"]'):
            data = json.loads(script.get_text())
            entity = data.get('mainEntity', {}) if isinstance(data, dict) else {}
            thread_title = entity.get('headline', title) if isinstance(entity, dict) else title
            walk(data, thread_title)

    # Title, source URL fragment, exact excerpts, context, original satirical commentary.
    items = [
        ('The damage deposit gets a sequel.', '1180531-remove-collections', [
            'I want to buy another one but my credit score recently tanked due to a collections filing from a property I rented.',
            'I have since paid the collections.',
            'I rented a property with a few friends for a year and after move out we were charged with over 6000 $ in B.S damages including 5k to repaint all the interior walls of the home due to a few minor marks.'
        ], 'He described the charges as unfair and said an attempted small-claims case was dismissed. This is his account of disputed move-out charges, not a finding that he or his friends caused the alleged damage.',
         'A five-star getaway for the credit score: check in at 740, check out at 640. The souvenir apparently stayed longer than the guests.'),
        ('Bank of Mom & Dad: the expansion pack.', '1180364-investment-property', [
            'I dont have the upfront cash to purchase another for a down payment but my parents are interested in financing my down payment with a 5% interest rate.',
            'Is an LLC a secure, 100 % fool proof method to protect my parents assets?'
        ], 'The post asks about possible financing structures. It does not establish that the proposed loan closed.',
         'Introducing Bank of Mom & Dad: because “self-made” sounds better when you leave out the down payment. Mom and Dad supply the capital; three letters—LLC—are apparently interviewing for the job of protecting the family fortune.'),
        ('Please hold all family-finance reviews.', '1180572-leverage-investors', [
            'My parents have plenty of money and most of it is sitting in low risk investments such as money market accounts getting 4.5% interest.',
            'Please hold the advice about investing with family members.',
            'I understand everyone has their own opinions and preferences but please hold off judgement.'
        ], 'In the same post, he requested feedback on loan financing and LLC asset protection while asking readers to withhold advice about investing with relatives.',
         'Welcome to the advice forum. Please leave the advice in the designated advice-free area.'),
        ('The family home enters the group project.', '410916-subject-to', [
            'We were exploring taking out a primary mortgage on their home to take out 350k in cash at about a 6% interest rate, and I take out a loan from them at an equal rate or slightly higher (maybe 6.5%).',
            'They are cutting me a good deal and I am grateful.'
        ], 'He described an idea being explored with his parents, not a completed mortgage or purchase.',
         'Some family group chats plan Thanksgiving. This one appears to have a capital stack.'),
        ('The expertise comes with a preferred return.', '1173079-lp-gp-deal-structure', [
            'I am providing the industry knowledge and skill behind the investment.',
            'If the investment under performs, I am at fault, and if the investment over performs, I deserve the credit.'
        ], 'He proposed contributing 20–30% of the upfront investment plus furnishing and management work, and asked whether his preferred profit split was reasonable.',
         'The brochure now offers an executive suite: bring most of the cash and enjoy a complimentary presentation on the value of expertise.'),
        ('Regulations: some assembly required.', '970179-savannah-georgia', [
            "I'm looking to invest in a STR in savannah, but I'm confused with the regulations.",
            "It seems that most areas are not zoned for STR's and most permits are taken."
        ], 'This is a historical forum question about regulations. It does not establish the permit status of any property.',
         'Before choosing your adventure, please locate the instruction manual. The zoning chapter has fewer pool photos.'),
        ('The business plan has a question mark.', '1126514-llc-for-funding', [
            "I'm looking to purchase an airbnb with a 2nd home loan.",
            'Is it feasible/ legal to buy the property with a 2nd home loan, occupy the residence for 14 days, create an LLC management company to manage my property on airbnb, and leverage 15k in 0 % interest through business credit cards.'
        ], 'He asked whether a proposed arrangement was feasible or legal. Forum replies expressed differing views; this page makes no finding about a mortgage or its terms.',
         'Our itinerary includes fourteen days at the house, eighteen months of promotional APR, and one very busy question mark.'),
    ]
    normalize = lambda text: re.sub(r'\s+', ' ', text).strip()
    cards = []
    for number, (title, fragment, quotes, context, joke) in enumerate(items, 1):
        candidates = [r for r in records if fragment in r.get('url', '') and all(normalize(q) in normalize(r.get('articleBody', r.get('text', ''))) for q in quotes)]
        if not candidates:
            raise ValueError(f'Cannot verify exact author excerpts for {title}')
        source = candidates[0]
        url = source['url']
        posted = date.fromisoformat(source['dateCreated'][:10]).strftime('%B %d, %Y').replace(' 0', ' ')
        def format_quote(quote):
            return html.escape(quote).replace('My parents have plenty of money', '<strong>My parents have plenty of money</strong>')
        excerpts = ''.join(f'<blockquote cite="{html.escape(url, quote=True)}"><p>“{format_quote(q)}”</p></blockquote>' for q in quotes)
        cards.append(f'''<article class="owner-story"><p class="eyebrow">Chapter {number:02d} / BiggerPockets</p><h3>{html.escape(title)}</h3>
<p class="owner-joke"><span class="editorial-label">Travel guide commentary</span>{html.escape(joke)}</p>
<div class="owner-excerpts"><p class="editorial-label">From the post · Patrick Forelli</p>{excerpts}</div>
<p class="source"><a href="{html.escape(url, quote=True)}" target="_blank" rel="noopener noreferrer">Read “{html.escape(source['thread_title'])}” on BiggerPockets ↗</a> · Posted {posted}</p>
<p class="note">{html.escape(context)}</p></article>''')
    return '''<section id="forum-files"><div class="eyebrow">The investor origin story</div><h2>Bigger pockets.<br>Longer footnotes.</h2><p class="intro">A self-guided tour of financing questions, family capital, and a credit report with a plot twist.</p><p class="note">Excerpts attributed to Patrick Forelli’s BiggerPockets account in the supplied pages saved October 17, 2026. Quoted wording is preserved; separate excerpts omit intervening text. The commentary is original satire. Historical posts describe the author’s claims and proposals, not independently verified outcomes.</p><div class="owner-stories">''' + ''.join(cards) + '</div></section>'
