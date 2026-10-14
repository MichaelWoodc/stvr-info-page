"""Create GitHub-sized H.264/AAC videos without changing downloaded originals."""
import hashlib
import json
from pathlib import Path
import subprocess

root = Path(__file__).resolve().parent.parent
assets = root / 'dist/assets/whitefield'
output = assets / 'videos'
output.mkdir(exist_ok=True)
items = [
    ('Airbnb Brawl', 'airbnb-brawl', 'Sunday morning fight'),
    ('Bullets hit nearby homes in short term vacation rental shooting', 'bullets-hit-nearby-homes', 'Shooting · bullets hit nearby homes'),
    ('Chatham Co. Police investigating after nearly 40 shots fired from rental property', 'police-investigation', 'Shooting · police investigation'),
    ('‘Inches Away’; Savannah neighbors react to bullets flying through windows in Airbnb shootout', 'neighbors-react', 'Shooting · neighbors react'),
    ('Grinder  Pump Overflowing', 'grinder-pump-overflow', 'Grinder pump overflow'),
    ('8-5-26 grinder pump still overflowing', 'grinder-pump-august-5', 'Grinder pump still overflowing · August 5, 2026'),
    ('8611 Whitefield Ave Grinder Pump Failure - Guest Notices Toilet Paper', 'guest-notices-pump-failure', 'Guest notices grinder pump failure'),
    ('ancrest nvr with sewer overlay', 'nvr-sewer-overlay', 'NVR footage with sewer overlay'),
]
manifest = []
for folder, slug, title in items:
    sources = [p for p in (assets / folder).iterdir() if p.suffix.lower() in {'.mp4', '.mkv'}]
    if len(sources) != 1:
        raise RuntimeError('Expected one source video in ' + folder)
    source = sources[0]
    data = json.loads(subprocess.check_output(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'json', str(source)]))
    duration = float(data['format']['duration'])
    target = output / (slug + '.mp4')
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    stamp = output / (slug + '.json')
    config = {'source_sha256': source_hash, 'settings': 'h264-720p-crf26-80MiB-aac64-v1'}
    if not target.exists() or not stamp.exists() or json.loads(stamp.read_text()) != config:
        # Limit video bitrate so even the longest clip stays well below 100 MiB.
        rate = min(1500, int(80 * 1024 * 1024 * 8 / duration / 1000 - 80))
        temporary = output / (slug + '.partial.mp4')
        command = ['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', str(source),
                   '-map', '0:v:0', '-map', '0:a:0?', '-vf', 'scale=1280:720:force_original_aspect_ratio=decrease:force_divisible_by=2,fps=30',
                   '-c:v', 'libx264', '-preset', 'fast', '-crf', '26', '-maxrate', str(rate)+'k', '-bufsize', str(rate*2)+'k',
                   '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '64k', '-movflags', '+faststart', str(temporary)]
        print('Encoding: '+title, flush=True)
        subprocess.run(command, check=True)
        if temporary.stat().st_size >= 95 * 1024 * 1024:
            raise RuntimeError('Encoded video exceeds size target: '+slug)
        temporary.replace(target)
        stamp.write_text(json.dumps(config, indent=2)+'\n')
    manifest.append({'title': title, 'file': slug+'.mp4', 'bytes': target.stat().st_size, 'duration': duration})
    print(f'{slug}: {target.stat().st_size/1048576:.1f} MiB', flush=True)
(output / 'manifest.json').write_text(json.dumps(manifest, indent=2)+'\n')
