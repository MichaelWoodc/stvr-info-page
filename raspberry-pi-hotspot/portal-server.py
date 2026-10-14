"""Local visitor counter, timestamped visit log, and guestbook storage."""
import csv
from contextlib import contextmanager
from datetime import datetime, timezone
import io
import json
import logging
import os
from pathlib import Path
import sqlite3
import queue
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from uuid import UUID

DATABASE = Path(os.environ.get('STATE_DIRECTORY', '/var/lib/airbnb-portal')) / 'portal.sqlite3'
DATABASE.parent.mkdir(parents=True, exist_ok=True)
bell_queue = queue.Queue(maxsize=20)

def ring_worker():
    while True:
        bell_queue.get()
        try:
            device = os.environ.get('PORTAL_AUDIO_DEVICE', 'plughw:CARD=Headphones,DEV=0')
            subprocess.run(['/usr/bin/aplay','-q','-D',device,str(Path(__file__).with_name('doorbell.wav'))], check=True, timeout=10)
            logging.info('Visitor doorbell played through the headphone output')
        except (OSError, subprocess.SubprocessError):
            logging.exception('Could not play visitor doorbell')
        finally:
            bell_queue.task_done()

threading.Thread(target=ring_worker, daemon=True).start()

def ring():
    if os.environ.get('PORTAL_BELL_ENABLED', '1') == '1':
        try:
            bell_queue.put_nowait(True)
        except queue.Full:
            logging.warning('Doorbell queue full; visit was still recorded')

@contextmanager
def connect():
    db = sqlite3.connect(DATABASE, timeout=15)
    db.row_factory = sqlite3.Row
    try:
        with db:
            yield db
    finally:
        db.close()

with connect() as db:
    db.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS visits (
            session_id TEXT PRIMARY KEY, visitor_id TEXT NOT NULL,
            visited_at TEXT NOT NULL, page TEXT NOT NULL, hotspot TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS guestbook (
            submission_id TEXT PRIMARY KEY, visitor_id TEXT NOT NULL,
            submitted_at TEXT NOT NULL, name TEXT NOT NULL, message TEXT NOT NULL,
            hotspot TEXT NOT NULL);
    ''')

def identifier(value):
    return str(UUID(value))

def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')

def network(address):
    if address.startswith('10.42.'):
        return 'Airbnb-wifi'
    if address.startswith('10.43.'):
        return 'cozy-corner-rentals-wifi'
    return 'Management LAN'

def counts(db):
    row = db.execute('SELECT COUNT(DISTINCT visitor_id) AS visitors, COUNT(*) AS visits FROM visits').fetchone()
    return dict(row)

class Handler(BaseHTTPRequestHandler):
    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def reply(self, status, data, content_type='application/json; charset=utf-8'):
        payload = json.dumps(data).encode() if isinstance(data, (dict, list)) else data.encode()
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(payload)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, *_):
        pass  # SQLite is the durable visit log; do not duplicate addresses in logs.

    def do_GET(self):
        path = self.path.split('?', 1)[0]
        if path == '/api/stats':
            with connect() as db:
                self.reply(200, counts(db))
        elif path == '/admin':
            self.reply(200, Path(__file__).with_name('portal-admin.html').read_text(), 'text/html; charset=utf-8')
        elif path == '/admin/data':
            with connect() as db:
                result = counts(db)
                result['recent_visits'] = [dict(r) for r in db.execute('SELECT visited_at,page,hotspot FROM visits ORDER BY visited_at DESC LIMIT 200')]
                result['guestbook'] = [dict(r) for r in db.execute('SELECT submitted_at,name,message,hotspot FROM guestbook ORDER BY submitted_at DESC LIMIT 200')]
                self.reply(200, result)
        elif path in {'/admin/visits.csv', '/admin/guestbook.csv'}:
            table = 'visits' if path.endswith('visits.csv') else 'guestbook'
            columns = ['visited_at','page','hotspot'] if table == 'visits' else ['submitted_at','name','message','hotspot']
            output = io.StringIO(newline='')
            writer = csv.writer(output)
            writer.writerow(columns)
            with connect() as db:
                for row in db.execute('SELECT '+','.join(columns)+' FROM '+table+' ORDER BY '+columns[0]+' DESC'):
                    # Preserve stored responses, while preventing spreadsheet formulas in exports.
                    writer.writerow(["'"+value if value.startswith(('=', '+', '-', '@')) else value for value in row])
            self.reply(200, output.getvalue(), 'text/csv; charset=utf-8')
        else:
            self.reply(404, {'error':'Not found'})

    def do_POST(self):
        if self.path not in {'/api/visit', '/api/guestbook'}:
            return self.reply(404, {'error':'Not found'})
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 8192:
                return self.reply(413, {'error':'Submission is too large.'})
            data = json.loads(self.rfile.read(length))
            visitor = identifier(data['visitor_id'])
            hotspot = network(self.headers.get('X-Real-IP', ''))
            with connect() as db:
                if self.path == '/api/visit':
                    session = identifier(data['session_id'])
                    page = str(data.get('page', '/'))[:200]
                    if not page.startswith('/') or any(ord(c) < 32 for c in page):
                        raise ValueError('Invalid page')
                    # Management previews do not inflate the hotspot visitor count.
                    inserted = False
                    timestamp = now()
                    if hotspot != 'Management LAN':
                        inserted = db.execute('INSERT OR IGNORE INTO visits VALUES (?,?,?,?,?)', (session, visitor, timestamp, page, hotspot)).rowcount > 0
                    db.commit()
                    if inserted:
                        logging.info('Visitor session recorded: %s at %s', hotspot, timestamp)
                        ring()
                    self.reply(200, counts(db))
                else:
                    submission = identifier(data['submission_id'])
                    name = str(data.get('name', '')).strip()
                    message = str(data.get('message', '')).strip()
                    if not name or not message or len(name) > 80 or len(message) > 2000:
                        return self.reply(400, {'error':'Enter a name (up to 80 characters) and a message (up to 2,000 characters).'})
                    recent = db.execute("SELECT COUNT(*) FROM guestbook WHERE visitor_id=? AND submitted_at>=strftime('%Y-%m-%dT%H:%M:%S','now','-10 minutes')", (visitor,)).fetchone()[0]
                    if recent >= 5:
                        return self.reply(429, {'error':'Please wait before leaving another message.'})
                    db.execute('INSERT OR IGNORE INTO guestbook VALUES (?,?,?,?,?,?)', (submission,visitor,now(),name,message,hotspot))
                    db.commit()
                    self.reply(201, {'saved':True})
        except (ValueError, TypeError, KeyError, UnicodeError):
            self.reply(400, {'error':'Please check the submission and try again.'})
        except sqlite3.Error:
            self.reply(503, {'error':'Could not save right now. Please try again.'})

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    ThreadingHTTPServer(('127.0.0.1', 8090), Handler).serve_forever()
