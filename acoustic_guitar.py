"""A nylon-string acoustic guitar, synthesised from nothing but maths.

Each string is a Karplus-Strong loop: a burst of noise (the pluck) circulates
in a delay line one pitch-period long, and a gentle filter in the loop makes
it lose its highs and die away like a real string. The summed strings then
pass through a few resonances (the wooden body) and a short reverb (the room).

Standard library only.
"""

import math
import random
import wave
from array import array

# Open-string pitches in Hz. String 6 is the low E, string 1 the high E.
OPEN_STRINGS = {6: 82.41, 5: 110.00, 4: 146.83, 3: 196.00, 2: 246.94, 1: 329.63}


class Guitar:
    def __init__(self, sample_rate=44100, seed=7):
        self.sr = sample_rate
        self.rng = random.Random(seed)
        self.events = {s: [] for s in OPEN_STRINGS}  # per string: (time, fret, velocity)

    # ---- playing -----------------------------------------------------------

    def pluck(self, time, string, fret=0, velocity=0.8):
        """Pluck `string` (6 = low E ... 1 = high E) at `fret`, at `time` seconds."""
        self.events[string].append((time, fret, velocity))

    def mute(self, time, string=None):
        """Rest a finger on a string (or on all of them) to stop it ringing."""
        for s in [string] if string else OPEN_STRINGS:
            self.events[s].append((time, None, 0.0))

    def slide(self, time, string, fret, glide=0.09):
        """Slide the fretting finger to `fret`, arriving at `time`. The note keeps ringing."""
        self.events[string].append((time, fret, None, glide))

    # ---- sound -------------------------------------------------------------

    def render(self, dry=False):
        """Return the performance as a list of float samples (mono)."""
        sr = self.sr
        notes = []  # (start sample, end sample, fade samples, freq, velocity, slides)
        for string, events in self.events.items():
            events = sorted(events, key=lambda e: e[0])
            slides = {}  # pluck index -> [(sample offset, freq)], one step per fret passed
            at = at_fret = None
            for i, event in enumerate(events):
                time, fret = event[0], event[1]
                if event[2] is not None:
                    at, at_fret = (i, fret) if fret is not None else (None, None)
                elif at is not None and fret != at_fret:
                    step = 1 if fret > at_fret else -1
                    passed = range(at_fret + step, fret + step, step)
                    for j, f in enumerate(passed):
                        t = time - event[3] * (len(passed) - 1 - j) / len(passed)
                        offset = max(1, int((t - events[at][0]) * sr))
                        slides.setdefault(at, []).append((offset, OPEN_STRINGS[string] * 2 ** (f / 12)))
                    at_fret = fret
            cuts = [(i, e) for i, e in enumerate(events) if e[2] is not None]  # plucks and mutes end a note; slides don't
            for i, (index, (time, fret, velocity)) in enumerate(cuts):
                if fret is None:
                    continue
                freq = OPEN_STRINGS[string] * 2 ** (fret / 12)
                ring = _decay_time(freq)
                end, fade = time + ring, 0.008
                if i + 1 < len(cuts) and cuts[i + 1][1][0] < end:
                    end = cuts[i + 1][1][0]
                    # a muting finger damps more softly than a fresh pluck
                    fade = 0.035 if cuts[i + 1][1][1] is None else 0.008
                moves = slides.get(index, [])
                notes.append((int(time * sr), int(end * sr), int(fade * sr), freq, velocity, moves))

        length = max(n[1] + n[2] for n in notes) + int(0.4 * sr)
        out = [0.0] * length
        for note in notes:
            self._string(out, *note)

        if not dry:
            out = _body(out, sr)
            out = _room(out, sr)
        peak = max(abs(x) for x in out) or 1.0
        gain = 10 ** (-1 / 20) / peak  # normalise to -1 dBFS
        return [x * gain for x in out]

    def write_wav(self, path):
        samples = self.render()
        pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in samples))
        with wave.open(path, "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(self.sr)
            f.writeframes(pcm.tobytes())
        return len(samples) / self.sr

    def _string(self, out, start, end, fade, freq, velocity, slides=()):
        """One plucked note: Karplus-Strong with exact (fractional) tuning."""
        sr = self.sr
        damp = 0.5  # loop low-pass mix; also delays the loop by `damp` samples

        def tune(freq):
            period = sr / freq
            n = int(period - damp - 0.1)
            frac = period - damp - n  # leftover delay, handled by an all-pass
            loss = 0.001 ** (1 / (freq * _decay_time(freq)))  # per-trip gain for a -60 dB decay
            return n, (1 - frac) / (1 + frac), loss

        n, c, loss = tune(freq)
        buf = self._pluck_shape(n, velocity)
        slides = dict(slides)
        count = end - start + fade
        fade_from = count - fade
        prev = ap_in = ap_out = 0.0
        i = 0
        for k in range(count):
            if k in slides:
                # the finger moved a fret: squeeze the same wave into a shorter (or longer) ring
                old, m = buf[i:] + buf[:i], n
                n, c, loss = tune(slides[k])
                buf = []
                for j in range(n):
                    x = j * m / n
                    a = int(x)
                    buf.append(old[a] + (x - a) * (old[(a + 1) % m] - old[a]))
                i = 0
            d = buf[i]
            lp = loss * ((1 - damp) * d + damp * prev)  # highs fade faster than lows
            prev = d
            ap_out = c * lp + ap_in - c * ap_out  # fine-tunes the pitch
            ap_in = lp
            buf[i] = ap_out
            out[start + k] += d if k < fade_from else d * (count - k) / fade
            i += 1
            if i == n:
                i = 0

    def _pluck_shape(self, n, velocity):
        """The string's initial shape: soft noise, like a fingertip on nylon."""
        rng = self.rng
        noise = [rng.uniform(-1, 1) for _ in range(n)]
        bright = 0.22 + 0.5 * velocity  # harder plucks are brighter
        for _ in range(2):
            y = noise[-1]
            for i in range(n):
                y += bright * (noise[i] - y)
                noise[i] = y
        # plucking a fifth of the way along the string cancels every 5th harmonic
        gap = max(1, int(0.2 * n))
        shape = [noise[i] - 0.9 * noise[i - gap] for i in range(n)]
        mean = sum(shape) / n
        shape = [x - mean for x in shape]
        peak = max(abs(x) for x in shape) or 1.0
        return [x * velocity / peak for x in shape]


def _decay_time(freq):
    """Seconds for a string to ring down: bass strings sustain longer."""
    return 4.5 * (82.41 / freq) ** 0.4


def _resonance(x, sr, freq, q):
    """Band-pass biquad: one resonant mode of the guitar body."""
    w = 2 * math.pi * freq / sr
    alpha = math.sin(w) / (2 * q)
    a0 = 1 + alpha
    b0, a1, a2 = alpha / a0, -2 * math.cos(w) / a0, (1 - alpha) / a0
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, s in enumerate(x):
        v = b0 * (s - x2) - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, s, y1, v
        y[i] = v
    return y


def _body(x, sr):
    """Strings alone sound thin; the body adds warmth around 100-400 Hz."""
    air = _resonance(x, sr, 105, 5)   # air inside the body
    top = _resonance(x, sr, 210, 6)   # the soundboard
    mid = _resonance(x, sr, 400, 5)
    return [d + 0.9 * a + 0.7 * t + 0.4 * m for d, a, t, m in zip(x, air, top, mid)]


def _room(x, sr, wet=0.12):
    """A small room: four echoing delays, smeared by two all-passes."""
    n = len(x)
    rev = [0.0] * n
    for ms, feedback in ((29.7, 0.78), (37.1, 0.76), (41.1, 0.74), (43.7, 0.72)):
        size = int(ms * sr / 1000)
        buf = [0.0] * size
        i = 0
        for k in range(n):
            d = buf[i]
            buf[i] = x[k] + feedback * d
            rev[k] += d
            i += 1
            if i == size:
                i = 0
    for ms in (5.0, 1.7):
        size = int(ms * sr / 1000)
        buf = [0.0] * size
        i = 0
        for k in range(n):
            d = buf[i]
            v = rev[k] + 0.7 * d
            buf[i] = v
            rev[k] = d - 0.7 * v
            i += 1
            if i == size:
                i = 0
    return [d + wet * 0.25 * r for d, r in zip(x, rev)]
