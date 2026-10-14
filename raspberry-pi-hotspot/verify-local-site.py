"""Visible Edge verification with every external browser request blocked."""
import argparse
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='192.168.1.151')
args = parser.parse_args()
blocked = set()
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel='msedge', headless=False)
    context = browser.new_context()
    def restrict(route):
        if urlparse(route.request.url).hostname == args.host:
            route.continue_()
        else:
            blocked.add(route.request.url)
            route.abort()
    context.route('**/*', restrict)
    page = context.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://' + args.host + '/bed-bug-bordello.html#videos')
    page.wait_for_selector('video')
    assert page.locator('iframe').count() == 0
    assert page.locator('video').count() == 8
    page.wait_for_function('Array.from(document.querySelectorAll("video")).every(v=>v.readyState>=1)', timeout=60000)
    for index in range(8):
        video = page.locator('video').nth(index)
        video.evaluate('(v)=>{v.muted=true;return v.play()}')
        page.wait_for_function('(i)=>document.querySelectorAll("video")[i].currentTime>0.1', arg=index, timeout=20000)
        video.evaluate('(v)=>v.pause()')
        print('Local playback verified: ' + video.get_attribute('src'), flush=True)
    page.goto('http://' + args.host + '/garland-gta.html')
    page.wait_for_selector('#property-slideshow img')
    assert page.locator('#property-slideshow img').evaluate('(img)=>img.complete&&img.naturalWidth>0')
    assert not errors, errors
    assert not blocked, sorted(blocked)
    print('All eight videos play; Garland photos load; no external requests or JavaScript errors.', flush=True)
    browser.close()
