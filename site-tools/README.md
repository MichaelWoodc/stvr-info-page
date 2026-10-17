# Search metadata and static page generation

The separate `dist/about-owner.html` page combines sourced BiggerPockets excerpts
with the Humans of Patrick album. Run `python site-tools/build_owner.py` to
rebuild it from the saved pages in `dist/patricia` and `dist/assets/owner/photos`.
It checks every forum excerpt against a post attributed to Patrick Forelli,
retains source links and post dates, and keeps editorial satire separate from
quotes. Run it after `build_seo.py` when rebuilding both. Original captures stay
unchanged; the owner page includes complete static content for readers without JS.

Run `python site-tools/build_seo.py` after editing either site's app.js. Requires
Python Playwright and installed Edge. The script opens visible Edge, writes
page-specific titles/descriptions, canonical and social-sharing tags, WebPage
structured data, and renders the page content into its initial HTML so it can
be read without JavaScript. Existing scripts still provide slideshow controls.

Canonical URLs point to the main GitHub Pages site; the alternative pages point
to the corresponding main pages. The root redirect and Cozy Corner info page
also receive descriptive titles and canonical links. `sitemap.xml` lists the
main pages and the linked info page. The script does not submit the sitemap to
Google Search Console or guarantee search ranking changes.

The wording identifies this as independent neighbor commentary, includes
Patrick Forelli, Savannah GA, vacation rentals, Airbnb and Vrbo, and avoids
adding business affiliations or fabricated review ratings to structured data.

Implementation references:

- [Google: titles and descriptions](https://developers.google.com/search/docs/fundamentals/get-started-developers)
- [Google: JavaScript SEO](https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics)
- [Google: canonical URLs](https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls)
