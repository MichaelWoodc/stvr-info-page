"""Generate a short, original ding-dong WAV for the Pi's headphone jack."""
import math
from pathlib import Path
import struct
import wave

rate = 44100
samples = []
for frequency, duration in [(660, .65), (0, .10), (523.25, .85), (0, .10)]:
    for i in range(int(rate * duration)):
        t = i / rate
        envelope = min(1, t / .008) * math.exp(-4.5 * t) * min(1, (duration-t)/.015)
        value = .25 * envelope * (math.sin(2*math.pi*frequency*t) + .20*math.sin(4*math.pi*frequency*t)) if frequency else 0
        samples.append(struct.pack('<h', round(max(-1, min(1, value))*32767)))
output = Path(__file__).with_name('doorbell.wav')
with wave.open(str(output), 'wb') as audio:
    audio.setnchannels(1); audio.setsampwidth(2); audio.setframerate(rate)
    audio.writeframes(b''.join(samples))
print('Generated '+str(output), flush=True)
