"""Prepare complete Downloads videos for the offline Pi; never trim or resize."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

root = Path(__file__).resolve().parent
downloads = Path.home() / 'Downloads'
output = root / 'full-videos'
output.mkdir(exist_ok=True)
items = [
    ('Airbnb Brawl', 'airbnb-brawl', 'BuSnI4De5Sk'),
    ('Bullets hit nearby homes in short term vacation rental shooting', 'bullets-hit-nearby-homes', 'r2nPxOJlNd0'),
    ('Chatham Co. Police investigating after nearly 40 shots fired from rental property', 'police-investigation', 'LxeWDLwMIno'),
    ('â€˜Inches Awayâ€™; Savannah neighbors react to bullets flying through windows in Airbnb shootout', 'neighbors-react', 'E4NYwe-brgI'),
    ('Grinder  Pump Overflowing', 'grinder-pump-overflow', '0qKOywS4RWo'),
    ('8-5-26 grinder pump still overflowing', 'grinder-pump-august-5', 'USQtHn8AiHo'),
    ('8611 Whitefield Ave Grinder Pump Failure - Guest Notices Toilet Paper', 'guest-notices-pump-failure', 'obECa0K9oss'),
    ('ancrest nvr with sewer overlay', 'nvr-sewer-overlay', '9YM11YvgE54'),
]
manifest = []
for folder, slug, youtube_id in items:
    sources = [p for p in (downloads / folder).iterdir() if p.suffix.lower() in {'.mp4','.mkv'}]
    if len(sources) != 1:
        raise RuntimeError('Expected one original video in Downloads/'+folder)
    source = sources[0]
    if slug == 'airbnb-brawl':
        source = root.parent / 'dist/assets/whitefield/Airbnb Brawl/zoomed and subtitled.mp4'
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    target = output / (('airbnb-brawl-zoomed' if slug == 'airbnb-brawl' else slug)+'.mp4')
    stamp = output / (slug+'.json')
    expected = {'source_sha256':source_hash,'settings':'zoomed-fight-preserve-all-frames-aac-v3' if slug == 'airbnb-brawl' else 'original-mp4-or-full-resolution-h264-crf18-no-trim-v1'}
    if not target.exists() or not stamp.exists() or json.loads(stamp.read_text()) != expected:
        if slug == 'airbnb-brawl':
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),'-map','0:v:0','-map','0:a:0?','-vf','setpts=PTS-STARTPTS,tpad=start_mode=clone:start_duration=0.2','-fps_mode','passthrough','-c:v','libx264','-preset','fast','-crf','18','-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',str(target)],check=True)
        elif source.suffix.lower() == '.mp4':
            shutil.copy2(source, target)
            assert hashlib.sha256(target.read_bytes()).hexdigest() == source_hash
        else:
            temporary = output / (slug+'.partial.mp4')
            print('Converting entire MKV at original resolution and frame timing: '+folder, flush=True)
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(source),
                            '-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','fast','-crf','18',
                            '-pix_fmt','yuv420p','-fps_mode','passthrough','-c:a','copy','-movflags','+faststart',str(temporary)],check=True)
            temporary.replace(target)
        stamp.write_text(json.dumps(expected,indent=2)+'\n',encoding='utf-8')
    probe = json.loads(subprocess.check_output(['ffprobe','-v','error','-show_entries','format=duration:stream=codec_name,width,height,start_time','-of','json',str(target)]))
    manifest.append({'youtube_id':youtube_id,'file':target.name,'source_sha256':source_hash,
                     'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'duration':float(probe['format']['duration'])})
    print(f'{slug}: complete video, {target.stat().st_size/1048576:.1f} MiB',flush=True)
(output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-i',str(output/'airbnb-brawl-zoomed.mp4'),'-frames:v','1',
                '-vf','scale=640:-2',str(output/'airbnb-brawl-poster.jpg')],check=True)
