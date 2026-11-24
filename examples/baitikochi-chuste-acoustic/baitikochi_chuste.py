"""A fingerpicked acoustic backing for "Baitikochi Chuste" (Agnyaathavaasi,
music by Anirudh Ravichander): the first minute of the song, chords only.

The chords follow the recording's own clock. CHART below is the song's
repeating loop, F#m (4 beats) -> C#m (2) -> Bm (2), placed on the beat grid a
chord-detection chart gives for the official lyrical video (89.95 BPM, loop
landing on beat 41 = 27.3 s). Three independent transcriptions agree on the
i - v - iv loop in F# minor. None of it was checked by ear: if a change lands
early or late, move FIRST_LOOP_BEAT or edit CHART.

Run:  python3 baitikochi_chuste.py   ->  baitikochi_chuste.wav
"""

import random
import sys
import wave
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acoustic_guitar import Guitar  # noqa: E402

BPM = 89.95                 # the recording's beat, as detected
BEAT = 60 / BPM
SIXTEENTH = BEAT / 4
LENGTH = 62                 # seconds

# Shapes as (string, fret), low string first. String 6 is the low E.
SHAPES = {
    "F#m": [(6, 2), (5, 4), (4, 4), (3, 2), (2, 2), (1, 2)],
    "C#m": [(5, 4), (4, 6), (3, 6), (2, 5), (1, 4)],
    "Bm":  [(5, 2), (4, 4), (3, 4), (2, 3), (1, 2)],
}

LOOP = [("F#m", 4), ("C#m", 2), ("Bm", 2)]   # (chord, beats)
FIRST_LOOP_BEAT = 1                           # 41 on the recording, minus five loops

# Picking pattern for one beat, in sixteenths: which string of the shape to
# pick. "bass" is the lowest string, "alt" the next one up; numbers are strings.
PATTERN = [
    ["bass", 3, 2, 1],     # odd beats: thumb on the root, fingers roll up
    ["alt", 3, 2, 3],      # even beats: thumb moves up a string
]


def chart():
    """[(beat, chord)] for the whole minute."""
    changes, beat = [], FIRST_LOOP_BEAT
    while beat * BEAT < LENGTH:
        for name, beats in LOOP:
            changes.append((beat, name))
            beat += beats
    return [c for c in changes if c[0] * BEAT < LENGTH - 1]


CHART = chart()


def play(guitar):
    human = random.Random(5)
    for i, (beat, name) in enumerate(CHART):
        shape = dict(SHAPES[name])
        strings = sorted(shape, reverse=True)          # low string first
        bass, alt = strings[0], strings[1]
        end = CHART[i + 1][0] if i + 1 < len(CHART) else beat + 2
        for string in set(range(1, 7)) - set(shape):   # stop strings the new chord doesn't use
            guitar.mute(beat * BEAT - 0.01, string)
        for b in range(beat, end):
            for step, pick in enumerate(PATTERN[(b - beat) % 2]):
                string = {"bass": bass, "alt": alt}.get(pick, pick)
                t = b * BEAT + step * SIXTEENTH + human.uniform(-0.006, 0.006)
                thumb = pick in ("bass", "alt")
                touch = (0.86 if thumb else 0.6) + (0.06 if step == 0 and b == beat else 0)
                guitar.pluck(max(0.0, t), string, shape[string], touch + human.uniform(-0.05, 0.05))


def write_wav(path, samples, sample_rate):
    pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in samples))
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())


def render():
    """The backing track, exactly LENGTH seconds, with a short fade at the end."""
    guitar = Guitar(seed=7)
    play(guitar)
    sr = guitar.sr
    samples = (guitar.render() + [0.0] * (LENGTH * sr))[: LENGTH * sr]
    fade = int(1.5 * sr)
    for i in range(fade):
        samples[-1 - i] *= i / fade
    return samples, sr


if __name__ == "__main__":
    samples, sr = render()
    out = Path(__file__).with_name("baitikochi_chuste.wav")
    write_wav(out, samples, sr)
    print(f"{out.name}: {len(samples) / sr:.1f}s, {len(CHART)} chord changes")
