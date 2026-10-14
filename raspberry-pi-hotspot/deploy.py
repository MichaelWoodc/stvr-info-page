"""Copy the main parody site and hotspot config to a Raspberry Pi over SSH."""
import argparse
import getpass
import os
import re
import hashlib
import tarfile
import tempfile
import time
from pathlib import Path
import paramiko
import requests

parser = argparse.ArgumentParser()
parser.add_argument('--host', default='192.168.1.151')
parser.add_argument('--user', default='science')
parser.add_argument('--install', action='store_true', help='Also apply hotspot configuration')
args = parser.parse_args()
password = os.environ.get('AIRBNB_PI_PASSWORD') or getpass.getpass('Pi SSH password: ')
folder = Path(__file__).resolve().parent
repo = folder.parent
client = paramiko.SSHClient()
client.load_system_host_keys()
# First connection prompts for trust rather than changing global SSH settings.
client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
client.connect(args.host, username=args.user, password=password, timeout=20)
stage = '/home/' + args.user + '/airbnb-wifi-deploy'

def run(command):
    _, stdout, stderr = client.exec_command(command, get_pty=True)
    for line in iter(stdout.readline, ''):
        print(line, end='', flush=True)
    error = stderr.read().decode()
    if error:
        print(error, end='')
    if stdout.channel.recv_exit_status():
        raise RuntimeError('Remote command failed')

run('mkdir -p ' + stage + '/site')
with client.open_sftp() as sftp:
    def upload(path, target, site_html=False):
        parent = str(Path(target).parent).replace('\\', '/')
        parts = parent.split('/')
        current = ''
        for part in parts:
            if not part:
                continue
            current += '/' + part
            try:
                sftp.mkdir(current)
            except OSError:
                pass
        if site_html:
            # The published site lives in /dist/; the Pi serves it at /.
            text = path.read_text(encoding='utf-8').replace('../slideshow-timer.js', 'slideshow-timer.js')
            with sftp.file(target, 'w') as out:
                out.write(text.encode('utf-8'))
        else:
            last_report = [0]
            def file_progress(sent, total):
                if total > 5 * 1048576 and (time.monotonic() - last_report[0] > 10 or sent == total):
                    print(f'{path.name}: {sent//1048576}/{total//1048576} MB transferred', flush=True)
                    last_report[0] = time.monotonic()
            sftp.put(str(path), target, callback=file_progress)

    files = list((repo / 'dist').rglob('*'))
    for path in files:
        if path.is_file():
            relative = path.relative_to(repo / 'dist').as_posix()
            # Download folders hold full-size sources. Only optimized videos ship.
            if relative.startswith('assets/whitefield/') and len(path.relative_to(repo / 'dist').parts) > 3:
                subfolder = path.relative_to(repo / 'dist').parts[2]
                if subfolder not in {'videos', 'shooting', 'lawn_damage', 'bedbug_pictures'}:
                    continue
            if path.suffix == '.mkv' or path.name.endswith('.partial.mp4'):
                continue
            upload(path, stage + '/site/' + path.relative_to(repo / 'dist').as_posix(), path.suffix == '.html')
    # Keep fonts local without altering the public site's source CSS.
    css = (repo / 'dist/style.css').read_text(encoding='utf-8')
    font_url = re.search(r"@import url\('([^']+)'\);", css).group(1)
    fonts = folder / 'fonts'
    fonts.mkdir(exist_ok=True)
    font_css_path = fonts / 'fonts.css'
    if not font_css_path.exists():
        response = requests.get(font_url, headers={'User-Agent': 'Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36'}, timeout=30)
        response.raise_for_status()
        font_css = response.text
        for url in set(re.findall(r'https://fonts\.gstatic\.com/[^)\s]+', font_css)):
            name = hashlib.sha256(url.encode()).hexdigest()[:16] + Path(url).suffix
            response = requests.get(url, timeout=30); response.raise_for_status()
            (fonts / name).write_bytes(response.content)
            font_css = font_css.replace(url, name)
        font_css_path.write_text(font_css, encoding='utf-8')
    for path in fonts.iterdir():
        if path.is_file():
            upload(path, stage + '/site/fonts/' + path.name)
    css = re.sub(r"@import url\('[^']+'\);", "@import url('fonts/fonts.css');", css, count=1)
    with sftp.file(stage + '/site/style.css', 'w') as out:
        out.write(css.encode('utf-8'))
    # The linked Cozy Corner pages and their photographs/PDFs are local too.
    app = (repo / 'dist/app.js').read_text(encoding='utf-8').replace(
        'https://michaelwoodc.github.io/stvr-info-page/owners/', '/owners/')
    with sftp.file(stage + '/site/app.js', 'w') as out:
        out.write(app.encode('utf-8'))
    upload(repo / 'slideshow-timer.js', stage + '/site/slideshow-timer.js')
    for path in folder.iterdir():
        if path.suffix in {'.conf', '.nft', '.service', '.sh', '.link'}:
            upload(path, stage + '/' + path.name)
    owner_hash = hashlib.sha256()
    for path in sorted((repo / 'owners').rglob('*')):
        if path.is_file():
            owner_hash.update(path.relative_to(repo).as_posix().encode())
            owner_hash.update(hashlib.sha256(path.read_bytes()).digest())
    digest = owner_hash.hexdigest()
    try:
        with sftp.file(stage + '/owners.sha256') as marker:
            owners_current = marker.read().decode().strip() == digest
    except OSError:
        owners_current = False
    if not owners_current:
        with tempfile.TemporaryDirectory(prefix='airbnb-pi-') as temp:
            archive = Path(temp) / 'owners.tar.gz'
            print('Packaging linked information pages and assets...', flush=True)
            with tarfile.open(archive, 'w:gz', compresslevel=1) as tar:
                tar.add(repo / 'owners', arcname='owners')
            last_report = [0]
            def progress(sent, total):
                if time.monotonic() - last_report[0] > 10 or sent == total:
                    print(f'Linked assets: {sent//1048576}/{total//1048576} MB transferred', flush=True)
                    last_report[0] = time.monotonic()
            sftp.put(str(archive), stage + '/owners.tar.gz', callback=progress)
if not owners_current:
    run('tar -xzf ' + stage + '/owners.tar.gz -C ' + stage + '/site')
    with client.open_sftp() as sftp:
        with sftp.file(stage + '/owners.sha256', 'w') as marker:
            marker.write(digest + '\n')
# Internal links and locally available legacy videos stay on the Pi as well.
run("python3 - <<'PY'\nfrom pathlib import Path\nimport re\nroot=Path('" + stage + "/site')\nvideos={'r2nPxOJlNd0':'bullets-hit-nearby-homes.mp4','E4NYwe-brgI':'neighbors-react.mp4','LxeWDLwMIno':'police-investigation.mp4'}\nfor p in (root/'owners').rglob('*.html'):\n s=p.read_text(encoding='utf-8',errors='replace').replace('https://michaelwoodc.github.io/stvr-info-page/owners/','/owners/')\n def embed(m):\n  hit=re.search(r'embed/([^?\\\"]+)',m.group(0));name=videos.get(hit.group(1)) if hit else None\n  if name:return '<video controls playsinline preload=\"metadata\" style=\"width:100%;max-width:900px\" src=\"/assets/whitefield/videos/'+name+'\"></video>'\n  return '<p>This older linked video was not included in the supplied local video files.</p>'\n s=re.sub(r'<iframe[^>]*src=\"https://www.youtube.com/embed/[^\"]*\"[^>]*>.*?</iframe>',embed,s,flags=re.S)\n p.write_text(s,encoding='utf-8')\nPY")
print('Uploaded site and configuration.', flush=True)
if args.install:
    run('cd ' + stage + ' && sudo -n sh install.sh')
else:
    run('sudo -n cp -au ' + stage + '/site/. /var/www/airbnb-wifi/ && sudo -n chmod -R a+rX /var/www/airbnb-wifi')
client.close()
