"""A four-string electric bass, synthesised from nothing but maths.

The strings are the same Karplus-Strong loops as the guitar, an octave lower.
What makes it electric is everything around them: no hollow body, a magnetic
pickup that hears the string's speed at one spot, a tone knob, and an amp
that squashes the loud peaks.

Standard library only.
"""

import math
import random

from mixer import normalise, write_wav

# Open-string pitches in Hz. String 4 is the low E, string 1 the G.
OPEN_STRINGS = {4: 41.20, 3: 55.00, 2: 73.42, 1: 98.00}

PLUCK_AT = 0.22   # fingers pluck this far along the string from the bridge
PICKUP_AT = 0.16  # where the pickup sits


class Bass:
    def __init__(self, sample_rate=44100, seed=3, tone=1300, drive=1.6):
        self.sr = sample_rate
        self.rng = random.Random(seed)
        self.tone = tone    # tone knob: highs above this (Hz) are rolled off
        self.drive = drive  # how hard the amp is pushed
        self.events = {s: [] for s in OPEN_STRINGS}  # per string: (time, fret, velocity)

    # ---- playing -----------------------------------------------------------

    def pluck(self, time, string, fret=0, velocity=0.8):
        """Pluck `string` (4 = low E ... 1 = G) at `fret`, at `time` seconds."""
        self.events[string].append((time, fret, velocity))

    def mute(self, time, string=None):
        """Rest a finger on a string (or on all of them) to stop it ringing."""
        for s in [string] if string else OPEN_STRINGS:
            self.events[s].append((time, None, 0.0))

    # ---- sound -------------------------------------------------------------

    def render(self, dry=False):
        """Return the performance as a list of float samples (mono)."""
        sr = self.sr
        notes = []  # (start sample, end sample, fade samples, freq, velocity)
        for string, events in self.events.items():
            events = sorted(events, key=lambda e: e[0])
            for i, (time, fret, velocity) in enumerate(events):
                if fret is None:
                    continue
                freq = OPEN_STRINGS[string] * 2 ** (fret / 12)
                end, fade = time + _decay_time(freq), 0.01
                if i + 1 < len(events) and events[i + 1][0] < end:
                    end = events[i + 1][0]
                    fade = 0.04 if events[i + 1][1] is None else 0.01
                notes.append((int(time * sr), int(end * sr), int(fade * sr), freq, velocity))

        length = max(n[1] + n[2] for n in notes) + int(0.2 * sr)
        out = [0.0] * length
        for note in notes:
            self._string(out, *note)

        if not dry:
            out = _low_pass(out, sr, self.tone)
            out = _amp(out, self.drive)
        return normalise(out)

    def write_wav(self, path):
        return write_wav(path, self.render(), sample_rate=self.sr)

    def _string(self, out, start, end, fade, freq, velocity):
        """One plucked note: Karplus-Strong with exact (fractional) tuning."""
        period = self.sr / freq
        n = int(period - 0.5 - 0.1)
        frac = period - 0.5 - n  # leftover delay, handled by an all-pass
        c = (1 - frac) / (1 + frac)
        loss = 0.001 ** (1 / (freq * _decay_time(freq)))  # per-trip gain for a -60 dB decay

        buf = self._pluck_shape(n, velocity)
        gap = max(1, int(PICKUP_AT * n))
        count = end - start + fade
        fade_from = count - fade
        prev = ap_in = ap_out = 0.0
        i = 0
        for k in range(count):
            d = buf[i]
            # the pickup hears the wave pass twice, once each way: some overtones cancel
            heard = d - 0.7 * buf[i - gap]
            lp = loss * 0.5 * (d + prev)  # highs fade faster than lows
            prev = d
            ap_out = c * lp + ap_in - c * ap_out  # fine-tunes the pitch
            ap_in = lp
            buf[i] = ap_out
            out[start + k] += heard if k < fade_from else heard * (count - k) / fade
            i += 1
            if i == n:
                i = 0

    def _pluck_shape(self, n, velocity):
        """A finger pulls the string into a triangle and lets go.

        A pickup hears speed, not position, and the speed of a released
        triangle is a two-level step. A little noise is the fingertip.
        """
        rng = self.rng
        edge = max(1, int(PLUCK_AT * n))
        shape = [(1 / PLUCK_AT if j < edge else -1 / (1 - PLUCK_AT)) + 0.25 * rng.uniform(-1, 1)
                 for j in range(n)]
        bright = 0.04 + 0.22 * velocity  # harder plucks are brighter
        y = shape[-1]
        for _ in range(2):
            for j in range(n):
                y += bright * (shape[j] - y)
                shape[j] = y
        mean = sum(shape) / n
        shape = [x - mean for x in shape]
        peak = max(abs(x) for x in shape) or 1.0
        return [x * velocity / peak for x in shape]


def _decay_time(freq):
    """Seconds for a string to ring down: heavy steel strings sustain for ages."""
    return 7.0 * (41.20 / freq) ** 0.4


def _low_pass(x, sr, freq, q=0.7):
    """The tone knob: a low-pass biquad."""
    w = 2 * math.pi * freq / sr
    alpha = math.sin(w) / (2 * q)
    a0 = 1 + alpha
    b1 = (1 - math.cos(w)) / a0
    b0 = b1 / 2
    a1, a2 = -2 * math.cos(w) / a0, (1 - alpha) / a0
    y = [0.0] * len(x)
    x1 = x2 = y1 = y2 = 0.0
    for i, s in enumerate(x):
        v = b0 * (s + x2) + b1 * x1 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, s, y1, v
        y[i] = v
    return y


def _amp(x, drive):
    """A valve amp rounds off loud peaks, which adds warmth and growl."""
    peak = max(abs(s) for s in x) or 1.0
    return [math.tanh(drive * s / peak) for s in x]


if __name__ == "__main__":
    from pathlib import Path

    bass = Bass()
    # a walk up the E string and back down the others
    line = [(4, 0), (4, 3), (4, 5), (3, 2), (3, 3), (3, 5), (2, 2), (2, 5), (1, 2), (1, 4), (2, 5), (3, 5), (4, 5), (4, 0)]
    for i, (string, fret) in enumerate(line):
        t = 0.05 + i * 0.4
        bass.mute(t)
        bass.pluck(t, string, fret, 0.8)
    bass.mute(0.05 + len(line) * 0.4 + 1.5)
    out = Path(__file__).with_name("electric_bass.wav")
    print(f"{out.name}: {bass.write_wav(str(out)):.1f}s")
