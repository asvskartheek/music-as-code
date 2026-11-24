"""A drum kit, synthesised from nothing but maths.

Drums have no strings to loop. Each one is a recipe of two ingredients:
a tone that drops in pitch (the skin) and shaped noise (wires, sticks, metal).

Standard library only.
"""

import math
import random

from acoustic_guitar import _room
from mixer import normalise, write_wav

PIECES = ("kick", "snare", "rim", "hat", "open_hat", "tom_hi", "tom_lo", "ride")
CHOKES = ("hat", "open_hat")  # closing the hi-hat stops an open one ringing

# Six clashing square waves: the classic recipe for something that sounds like metal.
METAL = (205.3, 304.4, 369.6, 522.7, 540.0, 800.0)


class Drums:
    def __init__(self, sample_rate=44100, seed=9):
        self.sr = sample_rate
        self.rng = random.Random(seed)
        self.hits = []  # (time, piece, velocity)

    # ---- playing -----------------------------------------------------------

    def hit(self, time, piece, velocity=0.8):
        """Strike `piece` (see PIECES) at `time` seconds."""
        assert piece in PIECES, piece
        self.hits.append((time, piece, velocity))

    # ---- sound -------------------------------------------------------------

    def render(self, dry=False):
        """Return the performance as a list of float samples (mono)."""
        sr = self.sr
        hits = sorted(self.hits)
        length = int((hits[-1][0] + 2.5) * sr)
        low = [0.0] * length   # kick and toms stay dry so the low end stays tight
        rest = [0.0] * length  # everything else sits in the room

        for i, (time, piece, velocity) in enumerate(hits):
            start = int(time * sr)
            if piece == "kick":
                self._skin(low, start, velocity, pitch=47, drop=95, drop_time=0.028, ring=0.11, click=0.35)
            elif piece == "tom_hi":
                self._skin(low, start, 0.7 * velocity, pitch=150, drop=70, drop_time=0.04, ring=0.12, click=0.2)
            elif piece == "tom_lo":
                self._skin(low, start, 0.75 * velocity, pitch=98, drop=50, drop_time=0.05, ring=0.16, click=0.2)
            elif piece == "snare":
                self._snare(rest, start, 0.7 * velocity)
            elif piece == "rim":
                self._rim(rest, start, 0.5 * velocity)
            elif piece == "ride":
                self._metal(rest, start, 0.22 * velocity, ring=0.45, seconds=2.2, cutoff=4500, scale=1.37)
            else:
                seconds, ring = (0.14, 0.022 + 0.015 * velocity) if piece == "hat" else (0.9, 0.22)
                nxt = next((t for t, p, _ in hits[i + 1:] if p in CHOKES), None)
                if nxt is not None:
                    seconds = min(seconds, nxt - time)
                self._metal(rest, start, 0.24 * velocity, ring=ring, seconds=seconds, cutoff=7000)

        if not dry:
            rest = _room(rest, sr, wet=0.3)
        return normalise([a + b for a, b in zip(low, rest)])

    def write_wav(self, path):
        return write_wav(path, self.render(), sample_rate=self.sr)

    def _skin(self, out, start, velocity, pitch, drop, drop_time, ring, click):
        """Kick or tom: a sine that starts high and falls as the skin relaxes, plus the beater's click."""
        sr, rng = self.sr, self.rng
        count = min(int(ring * 7 * sr), len(out) - start)
        phase = y = 0.0
        for k in range(count):
            t = k / sr
            phase += 2 * math.pi * (pitch + drop * velocity * math.exp(-t / drop_time)) / sr
            s = math.sin(phase) * math.exp(-t / ring)
            if t < 0.006:
                y += 0.3 * (rng.uniform(-1, 1) - y)
                s += click * velocity * y * (1 - t / 0.006)
            out[start + k] += velocity * s

    def _snare(self, out, start, velocity):
        """Two skin tones plus the hiss of the wires underneath."""
        sr, rng = self.sr, self.rng
        count = min(int(0.4 * sr), len(out) - start)
        high = _HighPass(sr, 1800)
        for k in range(count):
            t = k / sr
            skin = (math.sin(2 * math.pi * 186 * t) + 0.6 * math.sin(2 * math.pi * 332 * t)) * math.exp(-t / 0.045)
            wires = high(rng.uniform(-1, 1)) * math.exp(-t / (0.05 + 0.05 * velocity))
            out[start + k] += velocity * (0.6 * skin + 0.9 * wires)

    def _rim(self, out, start, velocity):
        """Cross-stick: the stick laid across the snare and tapped on the rim. Short, woody."""
        sr, rng = self.sr, self.rng
        count = min(int(0.12 * sr), len(out) - start)
        for k in range(count):
            t = k / sr
            wood = math.sin(2 * math.pi * 1720 * t) * math.exp(-t / 0.009)
            shell = 0.5 * math.sin(2 * math.pi * 465 * t) * math.exp(-t / 0.022)
            tick = rng.uniform(-1, 1) * (1 - t / 0.002) if t < 0.002 else 0.0
            out[start + k] += velocity * (wood + shell + 0.6 * tick)

    def _metal(self, out, start, velocity, ring, seconds, cutoff, scale=1.0):
        """Hi-hat or cymbal: clashing square waves and noise, with everything low filtered away."""
        sr, rng = self.sr, self.rng
        count = min(int(seconds * sr), len(out) - start)
        fade = min(count, int(0.012 * sr))
        steps = [f * scale / sr for f in METAL]
        phases = [rng.random() for _ in METAL]
        hp1, hp2 = _HighPass(sr, cutoff), _HighPass(sr, cutoff)
        for k in range(count):
            s = 0.0
            for j, step in enumerate(steps):
                p = phases[j] + step
                if p >= 1.0:
                    p -= 1.0
                phases[j] = p
                s += 1.0 if p < 0.5 else -1.0
            s = hp2(hp1(s / 3 + 0.8 * rng.uniform(-1, 1))) * math.exp(-k / sr / ring)
            if k >= count - fade:
                s *= (count - k) / fade
            out[start + k] += velocity * s


class _HighPass:
    """One-pole high-pass: keeps only what changes fast."""

    def __init__(self, sr, freq):
        rc = 1 / (2 * math.pi * freq)
        self.a = rc / (rc + 1 / sr)
        self.x = self.y = 0.0

    def __call__(self, x):
        self.y = self.a * (self.y + x - self.x)
        self.x = x
        return self.y


if __name__ == "__main__":
    from pathlib import Path

    drums = Drums()
    step = 0.15  # a sixteenth at 100 bpm
    for bar in range(2):
        for s in range(16):
            t = 0.05 + (bar * 16 + s) * step
            if s % 2 == 0:
                drums.hit(t, "open_hat" if s == 14 else "hat", 0.6 if s % 4 == 0 else 0.4)
            if s in (0, 7, 10):
                drums.hit(t, "kick", 0.85)
            if s in (4, 12) and (bar, s) != (1, 12):  # the fill takes over the last beat
                drums.hit(t, "snare", 0.8)
    end = 0.05 + 32 * step
    for s, piece in enumerate(("snare", "tom_hi", "tom_hi", "tom_lo")):
        drums.hit(end - (4 - s) * step, piece, 0.8)
    drums.hit(end, "kick", 0.9)
    drums.hit(end, "ride", 0.9)
    out = Path(__file__).with_name("drum_kit.wav")
    print(f"{out.name}: {drums.write_wav(str(out)):.1f}s")
