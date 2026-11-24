"""The bossa nova jam again, as a trio: guitar, electric bass and drums.

Run:  python3 bossa_trio.py   ->  bossa_trio.wav
"""

import random
from pathlib import Path

from acoustic_guitar import Guitar
from bossa_nova import BAR, CHORDS, EIGHTH, ENDING, FINGERS, PROGRESSION
from drum_kit import Drums
from electric_bass import Bass
from mixer import mix, write_wav

# Root and fifth of each chord on the bass, as (string, fret). String 4 is the low E.
BASS_NOTES = {
    "Dm9":   [(3, 5), (4, 5)],
    "G13":   [(4, 3), (3, 5)],
    "Cmaj9": [(3, 3), (4, 3)],
    "Em7":   [(4, 0), (3, 2)],
    "A7b9":  [(3, 0), (2, 2)],
    "C6/9":  [(3, 3), (4, 3)],
}

# The bass and the kick drum share one heartbeat: 1 . . & 3 . . &
# (eighth, velocity). The two soft ones lean into the beat that follows.
HEARTBEAT = [(0, 0.85), (3, 0.55), (4, 0.8), (7, 0.55)]

END = len(PROGRESSION) * BAR + 0.05


def grid(seed, loose=0.006):
    human = random.Random(seed)  # each player is a few milliseconds off the grid in their own way

    def at(bar, eighth):
        return 0.05 + bar * BAR + eighth * EIGHTH + human.uniform(-loose, loose)

    return at, human


def play_guitar(guitar):
    """Fingers only: the thumb's bass notes now belong to the bass player."""
    at, human = grid(11)
    for bar, name in enumerate(PROGRESSION):
        for eighth, ring in FINGERS[bar % 2]:
            t = at(bar, eighth)
            touch = (0.62 if eighth % 2 == 0 else 0.7) + human.uniform(-0.07, 0.07)
            for i, (string, fret) in enumerate(CHORDS[name]["fingers"]):
                guitar.pluck(t + i * 0.004, string, fret, touch)
                guitar.mute(t + ring * EIGHTH, string)

    guitar.mute(END - 0.02)
    for i, (string, fret) in enumerate(CHORDS[ENDING]["fingers"]):
        guitar.pluck(END + 0.07 + i * 0.07, string, fret, 0.75 - i * 0.04)


def play_bass(bass):
    at, human = grid(23)
    chords = PROGRESSION + [ENDING]
    for bar, name in enumerate(PROGRESSION):
        root, fifth = BASS_NOTES[name]
        coming = BASS_NOTES[chords[bar + 1]][0]  # the last note of the bar is already the next chord
        for (eighth, touch), (string, fret) in zip(HEARTBEAT, [root, fifth, fifth, coming]):
            t = at(bar, eighth)
            bass.mute(t)  # one note at a time
            bass.pluck(t, string, fret, touch + human.uniform(-0.05, 0.05))

    bass.mute(END)
    bass.pluck(END, *BASS_NOTES[ENDING][0], 0.8)
    bass.mute(END + 3.2)


def play_drums(drums):
    at, human = grid(31, loose=0.004)
    last = len(PROGRESSION) - 1
    for bar in range(len(PROGRESSION)):
        fill = bar == 7  # a small tom fill before the last four bars

        for eighth in range(8):
            if fill and eighth >= 6:
                continue
            piece = "open_hat" if bar == last and eighth == 7 else "hat"
            drums.hit(at(bar, eighth), piece, (0.55 if eighth % 2 == 0 else 0.36) + human.uniform(-0.05, 0.05))

        for eighth, touch in HEARTBEAT:
            drums.hit(at(bar, eighth), "kick", touch * 0.9)

        # the cross-stick plays the same two-bar figure as the guitarist's fingers
        for eighth, _ in FINGERS[bar % 2]:
            drums.hit(at(bar, eighth), "rim", 0.7 + human.uniform(-0.06, 0.06))

        if fill:
            drums.hit(at(bar, 6), "tom_hi", 0.7)
            drums.hit(at(bar, 6.5), "tom_hi", 0.55)
            drums.hit(at(bar, 7), "tom_lo", 0.8)

    drums.hit(END, "hat", 0.3)  # the foot closes the hi-hat
    drums.hit(END, "kick", 0.75)
    drums.hit(END, "ride", 0.8)


def render():
    """Returns {name: (samples, gain, pan)}."""
    guitar, bass, drums = Guitar(), Bass(), Drums()
    play_guitar(guitar)
    play_bass(bass)
    play_drums(drums)
    return {
        "guitar": (guitar.render(), 1.0, -0.3),
        "bass":   (bass.render(), 0.45, 0.0),
        "drums":  (drums.render(), 0.7, 0.25),
    }


if __name__ == "__main__":
    out = Path(__file__).with_name("bossa_trio.wav")
    seconds = write_wav(str(out), *mix(list(render().values())))
    print(f"{out.name}: {seconds:.1f}s")
