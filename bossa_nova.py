"""A short bossa nova jam for one guitar.

Run:  python3 bossa_nova.py   ->  bossa_nova.wav
"""

import random
from pathlib import Path

from acoustic_guitar import Guitar

TEMPO = 132                 # beats per minute
EIGHTH = 60 / TEMPO / 2     # the grid everything sits on: 8 eighths per bar
BAR = 8 * EIGHTH

# Chord shapes as (string, fret). String 6 is the low E, string 1 the high E.
# bass = root then fifth for the thumb; fingers = the three upper notes.
CHORDS = {
    "Dm9":   {"bass": [(5, 5), (6, 5)], "fingers": [(4, 3), (3, 5), (2, 5)]},
    "G13":   {"bass": [(6, 3), (5, 5)], "fingers": [(4, 3), (3, 4), (2, 5)]},
    "Cmaj9": {"bass": [(5, 3), (6, 3)], "fingers": [(4, 2), (3, 4), (2, 3)]},
    "Em7":   {"bass": [(5, 7), (6, 7)], "fingers": [(4, 5), (3, 7), (2, 8)]},
    "A7b9":  {"bass": [(5, 0), (6, 0)], "fingers": [(3, 3), (2, 2), (1, 3)]},
    "C6/9":  {"bass": [(5, 3), (6, 3)], "fingers": [(4, 2), (3, 2), (2, 3), (1, 3)]},
}

PROGRESSION = [
    "Dm9", "G13", "Cmaj9", "A7b9",
    "Dm9", "G13", "Em7",   "A7b9",
    "Dm9", "G13", "Cmaj9",
]
ENDING = "C6/9"

# The bossa feel. Thumb: steady on beats 1 and 3. Fingers: a syncopated
# two-bar figure that pushes against the thumb. (eighth, how long it rings)
THUMB = [0, 4]
FINGERS = [
    [(0, 2.6), (3, 2.6), (6, 1.2)],   # bar A:  1 . . & . . 4 .
    [(2, 2.6), (5, 1.6)],             # bar B:  . . 2 . . & . .
]


def play(guitar):
    human = random.Random(11)  # tiny timing and touch variations

    def at(bar, eighth):
        return 0.05 + bar * BAR + eighth * EIGHTH + human.uniform(-0.006, 0.006)

    for bar, name in enumerate(PROGRESSION):
        chord = CHORDS[name]

        for eighth, note in zip(THUMB, chord["bass"]):
            string, fret = note
            guitar.pluck(at(bar, eighth), string, fret, 0.85 + human.uniform(-0.06, 0.06))

        for eighth, ring in FINGERS[bar % 2]:
            t = at(bar, eighth)
            touch = (0.62 if eighth % 2 == 0 else 0.7) + human.uniform(-0.07, 0.07)
            for i, (string, fret) in enumerate(chord["fingers"]):
                guitar.pluck(t + i * 0.004, string, fret, touch)   # fingers land almost together
                guitar.mute(t + ring * EIGHTH, string)

    # Ending: thumb, then a slow roll up the last chord, left to ring.
    end = len(PROGRESSION) * BAR + 0.05
    chord = CHORDS[ENDING]
    guitar.mute(end - 0.02)
    notes = chord["bass"][:1] + chord["fingers"]
    for i, (string, fret) in enumerate(notes):
        guitar.pluck(end + i * 0.07, string, fret, 0.75 - i * 0.04)


if __name__ == "__main__":
    guitar = Guitar()
    play(guitar)
    out = Path(__file__).with_name("bossa_nova.wav")
    seconds = guitar.write_wav(str(out))
    assert 20 <= seconds <= 30, seconds
    print(f"{out.name}: {seconds:.1f}s")
