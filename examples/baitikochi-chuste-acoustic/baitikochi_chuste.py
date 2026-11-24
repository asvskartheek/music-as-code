"""A one-minute acoustic take on "Baitikochi Chuste" (Agnyaathavaasi, music by
Anirudh Ravichander), for two guitars:

  chords  - a strummed rhythm guitar
  melody  - a fingerpicked guitar carrying the tune on the top two strings

Each layer is rendered on its own guitar, then the two are mixed into one file.

Key (F# minor), tempo (166 BPM) and chord set (F#m7, C#m7, Bm7) come from
published transcriptions; the melody's pitches from a published sargam
notation. The rhythm of the melody and which chord sits under which bar are
this arrangement's own guesses, so fix them in the tables below if they are off.

Run:  python3 baitikochi_chuste.py   ->  baitikochi_chuste.wav
      python3 baitikochi_chuste.py --layers   also writes chords.wav, melody.wav
"""

import random
import sys
import wave
from array import array
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from acoustic_guitar import OPEN_STRINGS, Guitar  # noqa: E402

TEMPO = 166
EIGHTH = 60 / TEMPO / 2     # 8 eighths per bar
BAR = 8 * EIGHTH
CHORD_LEVEL = 0.5           # rhythm guitar sits under the melody

# ---- chords ------------------------------------------------------------------

# Shapes as (string, fret), low string first. String 6 is the low E.
SHAPES = {
    "F#m7": [(6, 2), (5, 4), (4, 2), (3, 2), (2, 2)],
    "C#m7": [(5, 4), (4, 6), (3, 4), (2, 5)],
    "Bm7":  [(5, 2), (4, 4), (3, 2), (2, 3)],
}
TONES = {  # pitch classes, used only for the sanity check
    "F#m7": {"F#", "A", "C#", "E"},
    "C#m7": {"C#", "E", "G#", "B"},
    "Bm7":  {"B", "D", "F#", "A"},
}

# Strum pattern for one bar: (eighth, direction, touch)
STRUM = [(0, "down", 0.80), (2, "down", 0.58), (3, "up", 0.48),
         (5, "up", 0.50), (6, "down", 0.62), (7, "up", 0.45)]

# ---- sections ----------------------------------------------------------------
# chords: one name per bar, or "X Y" for two half-bars.
# melody: (eighth from the section start, note, length in eighths)

INTRO = {
    "chords": ["F#m7", "C#m7", "Bm7", "Bm7"],
    "melody": [],
}

HOOK = {
    "chords": ["F#m7", "Bm7", "F#m7", "C#m7 F#m7"],
    "melody": [
        (0, "C#5", 1), (1, "B4", 1), (2, "A4", 1), (3, "G#4", 1), (4, "F#4", 2), (6, "C#5", 2),
        (8, "F#4", 1), (9, "A4", 1), (10, "B4", 2), (12, "B4", 1), (13, "C#5", 1), (14, "F#4", 2),
        (16, "C#5", 1), (17, "B4", 1), (18, "A4", 1), (19, "G#4", 1), (20, "F#4", 1), (21, "C#5", 1),
        (22, "F#4", 1), (23, "A4", 1), (24, "B4", 2),
        (26, "B4", 1), (27, "C#5", 1), (28, "F#4", 4),
    ],
}

HUM = {
    "chords": ["F#m7", "C#m7", "Bm7", "C#m7"],
    "melody": [
        (0, "A4", 4), (4, "G#4", 4), (8, "E4", 4), (12, "F#4", 4),
        (16, "A4", 4), (20, "B4", 4), (24, "C#5", 8),
    ],
}

VERSE = {
    "chords": ["F#m7", "Bm7", "F#m7", "Bm7", "F#m7", "C#m7", "F#m7", "Bm7 F#m7"],
    "melody": [
        (0, "F#4", 1), (1, "F#4", 1), (2, "C#5", 2), (4, "E4", 1), (5, "F#4", 1), (6, "A4", 2),
        (8, "F#4", 1), (9, "A4", 1), (10, "B4", 6),
        (16, "F#4", 1), (17, "F#4", 1), (18, "C#5", 2), (20, "F#4", 1), (21, "A4", 1), (22, "B4", 1), (23, "C#5", 1),
        (24, "B4", 2), (26, "A4", 6),
        (32, "F#4", 1), (33, "F#4", 1), (34, "C#5", 2), (36, "E5", 2), (38, "C#5", 2),
        (40, "B4", 1), (41, "A4", 1), (42, "B4", 6),
        (48, "F#4", 1), (49, "F#4", 1), (50, "A4", 1), (51, "B4", 1), (52, "C#5", 4),
        (56, "A4", 1), (57, "B4", 1), (58, "A4", 2), (60, "F#4", 4),
    ],
}

SONG = [INTRO, HOOK, HOOK, HUM, HOOK, VERSE, HOOK, HUM, HOOK]
START = 0.05

# ---- helpers -----------------------------------------------------------------

NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
OPEN_MIDI = {6: 40, 5: 45, 4: 50, 3: 55, 2: 59, 1: 64}


def midi(note):
    return NAMES.index(note[:-1]) + 12 * (int(note[-1]) + 1)


def fingering(note):
    """Melody stays on the top two strings: B4 and above on string 1."""
    m = midi(note)
    string = 1 if m >= midi("B4") else 2
    return string, m - OPEN_MIDI[string]


def bars(section):
    """Yield the two half-bar chords of every bar in a section."""
    for entry in section["chords"]:
        names = entry.split()
        yield names[0], names[-1]


def section_starts():
    bar = 0
    for section in SONG:
        yield bar, section
        bar += len(section["chords"])


TOTAL_BARS = sum(len(s["chords"]) for s in SONG)

# ---- the two layers ----------------------------------------------------------


def play_chords(guitar):
    human = random.Random(3)
    bar = 0
    previous = None
    for _, section in section_starts():
        for first, second in bars(section):
            for eighth, direction, touch in STRUM:
                name = first if eighth < 4 else second
                t = START + bar * BAR + eighth * EIGHTH + human.uniform(-0.007, 0.007)
                if name != previous:
                    unused = set(OPEN_STRINGS) - {s for s, _ in SHAPES[name]} - {1}
                    for string in unused:
                        guitar.mute(t - 0.01, string)
                    previous = name
                shape = SHAPES[name]
                # an up-stroke only catches the top strings, high string first
                strings = shape if direction == "down" else shape[:1:-1]
                for i, (string, fret) in enumerate(strings):
                    guitar.pluck(t + i * 0.011, string, fret, touch + human.uniform(-0.05, 0.05))
            bar += 1

    # last chord: one slow strum, left to ring
    t = START + bar * BAR
    for i, (string, fret) in enumerate(SHAPES["F#m7"]):
        guitar.pluck(t + i * 0.05, string, fret, 0.7 - i * 0.03)


def play_melody(guitar):
    human = random.Random(17)
    notes = []  # (time, string, fret, velocity, length in seconds)
    for bar, section in section_starts():
        for eighth, note, length in section["melody"]:
            string, fret = fingering(note)
            t = START + bar * BAR + eighth * EIGHTH + human.uniform(-0.005, 0.005)
            accent = 0.86 if eighth % 4 == 0 else 0.74
            notes.append((t, string, fret, accent + human.uniform(-0.05, 0.05), length * EIGHTH))
    notes.append((START + TOTAL_BARS * BAR + 0.28, *fingering("F#4"), 0.8, 99))

    for t, string, fret, velocity, length in notes:
        guitar.pluck(t, string, fret, velocity)
        # let the note ring a touch past its length, unless the same string is picked again first
        release = t + length + 0.6 * EIGHTH
        later = [n[0] for n in notes if n[1] == string and n[0] > t]
        if length < 99 and (not later or min(later) > release + 0.02):
            guitar.mute(release, string)


# ---- mixing ------------------------------------------------------------------


def mix(layers):
    """Sum (samples, level) layers and normalise to -1 dBFS."""
    length = max(len(samples) for samples, _ in layers)
    out = [0.0] * length
    for samples, level in layers:
        for i, x in enumerate(samples):
            out[i] += level * x
    peak = max(abs(x) for x in out) or 1.0
    gain = 10 ** (-1 / 20) / peak
    return [x * gain for x in out]


def write_wav(path, samples, sample_rate):
    pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for x in samples))
    with wave.open(str(path), "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())


def check_melody_against_chords():
    """How many on-the-beat melody notes are chord tones? A cheap sanity check."""
    hits = total = 0
    for _, section in section_starts():
        chords = [c for pair in bars(section) for c in pair]  # one per half-bar
        for eighth, note, _ in section["melody"]:
            if eighth % 4 == 0:
                total += 1
                hits += note[:-1] in TONES[chords[eighth // 4]]
    return hits, total


if __name__ == "__main__":
    here = Path(__file__).parent
    chords, melody = Guitar(seed=7), Guitar(seed=23)
    play_chords(chords)
    play_melody(melody)

    chord_samples, melody_samples = chords.render(), melody.render()
    if "--layers" in sys.argv:
        write_wav(here / "chords.wav", chord_samples, chords.sr)
        write_wav(here / "melody.wav", melody_samples, melody.sr)

    samples = mix([(chord_samples, CHORD_LEVEL), (melody_samples, 1.0)])
    out = here / "baitikochi_chuste.wav"
    write_wav(out, samples, chords.sr)

    seconds = len(samples) / chords.sr
    assert 55 <= seconds <= 66, seconds
    hits, total = check_melody_against_chords()
    print(f"{out.name}: {seconds:.1f}s, {TOTAL_BARS} bars, "
          f"{hits}/{total} on-beat melody notes are chord tones")
