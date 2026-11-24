"""Baitikochi Chuste (Agnyaathavaasi) on one guitar. F# minor, 4/4, about 88 bpm.

Every note time is where the player's note fell in the source lesson video,
so the timing is a real performance, not a grid.

Run:  python3 baitikochi_chuste.py   ->  baitikochi_chuste.wav
"""

import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # the instrument lives at the repo root

from acoustic_guitar import Guitar  # noqa: E402

SPEED = 1.0                 # 1.0 = as played; 1.03 would be a true 90 bpm
B, G, D = 2, 3, 4           # string numbers
HOLD = 0.9                  # seconds a finger stays down when nothing follows
LAST_RING = 1.8             # the final note is left to ring

# Seconds into the video. (time, string, fret) is a pluck;
# (time, string, fret, "slide") is the note changing fret without a new pluck:
# a slide, hammer-on or pull-off, as the player did it.
SONG = [
    # G --6s4-2------2-4------2-4-4s6-----     (played twice)
    # D ---------4--------4-----------4---
    (8.36, G, 6), (8.62, G, 4, "slide"), (8.74, G, 2), (8.93, D, 4), (9.08, G, 2), (9.40, G, 4),
    (9.74, D, 4), (10.05, G, 2), (10.41, G, 4), (11.11, G, 4), (11.42, G, 6, "slide"), (11.62, D, 4),

    (13.89, G, 6), (14.10, G, 4, "slide"), (14.24, G, 2), (14.44, D, 4), (14.56, G, 2), (14.91, G, 4),
    (15.25, D, 4), (15.57, G, 2), (15.90, G, 4), (16.63, G, 4), (16.92, G, 6, "slide"), (17.13, D, 4),

    # G -1s2-2222---------2-4-4444-4s5-2-2s4-2
    # D --------------4-2---------------------
    (19.30, G, 1), (19.42, G, 2, "slide"), (20.31, G, 2), (20.53, G, 2), (20.66, G, 2),
    (20.87, D, 4), (21.06, D, 2, "slide"), (21.34, D, 2), (21.67, G, 2), (22.00, G, 2), (22.27, G, 4, "slide"),
    (22.99, G, 4), (23.19, G, 4), (23.32, G, 4), (23.50, G, 4), (23.62, G, 4), (23.78, G, 6, "slide"), (24.00, G, 6),
    (24.34, G, 2), (24.69, G, 4), (25.14, G, 2, "slide"), (25.48, G, 2),

    # G ---------6s9--464-464-464--2-2s4-2
    # D -444------------------------------
    (25.74, D, 4), (25.91, D, 4), (26.06, D, 4), (26.40, G, 4), (26.52, G, 9, "slide"),
    (26.77, G, 4), (27.10, G, 6), (27.42, G, 4), (27.65, G, 6), (27.77, G, 4),
    (28.10, G, 4), (28.30, G, 6), (28.45, G, 4), (28.77, G, 4), (28.97, G, 6), (29.11, G, 4),
    (29.46, G, 2), (29.81, G, 2), (30.19, G, 4), (30.52, G, 2, "slide"),

    # second line again (the player skips the opening 1s2 this time)
    (31.13, G, 2), (31.32, G, 2), (31.64, D, 4), (31.90, D, 2, "slide"), (32.10, D, 2), (32.41, G, 2),
    (32.76, G, 2), (33.05, G, 4, "slide"), (33.70, G, 4), (33.92, G, 4), (34.04, G, 4), (34.24, G, 4),
    (34.37, G, 4), (34.53, G, 6, "slide"), (34.74, G, 6), (35.08, G, 2), (35.44, G, 4),
    (35.79, G, 2, "slide"), (36.13, G, 2),

    # third line again
    (36.38, D, 4), (36.54, D, 4), (36.68, D, 4), (37.06, G, 4), (37.12, G, 8, "slide"),
    (37.42, G, 4), (37.76, G, 6), (38.10, G, 4), (38.31, G, 6), (38.43, G, 4),
    (38.77, G, 4), (38.97, G, 6), (39.12, G, 4), (39.43, G, 4), (39.63, G, 6), (39.75, G, 4),
    (40.10, G, 2), (40.42, G, 2), (40.79, G, 4), (41.13, G, 2, "slide"),

    # G -------4s6----------2------2-4
    # D -2-4---------2-4-------4------
    (41.67, D, 2), (41.88, D, 4), (42.21, G, 4), (42.34, G, 6, "slide"), (42.98, D, 2), (43.22, D, 4),
    (43.38, G, 2), (43.70, D, 4), (43.90, G, 2), (44.02, G, 4),

    # G -------4s6----------2-4-6-4-2
    # D -2-4----------4--------------
    (44.37, D, 4), (44.57, G, 2), (44.89, G, 4), (45.04, G, 6, "slide"), (45.78, D, 4),
    (45.99, G, 2), (46.10, G, 4), (46.43, G, 4), (46.50, G, 6, "slide"), (46.60, G, 4), (46.79, G, 2),

    # B -----------5------------------------------------
    # G -------4s6---6s4--4-2-4-------2-4-6-4-2-2-4-2---
    # D -2-4--------------------4---------------------4-
    (47.10, D, 2), (47.31, D, 4), (47.67, G, 4), (47.77, G, 6, "slide"), (47.99, B, 5),
    (48.10, G, 6), (48.47, G, 4), (48.82, G, 2), (49.01, G, 4), (49.76, D, 4),
    (50.00, G, 2), (50.32, G, 4), (50.52, G, 6, "slide"), (50.75, G, 4), (50.98, G, 2, "slide"), (51.10, G, 2),
    (51.27, G, 4, "slide"), (51.34, G, 2, "slide"), (51.56, D, 4),

    # G -------4s6----------2-4-6-4-2     (twice, each a little different)
    # D -2-4----------4--------------
    (52.24, D, 2), (52.50, D, 4), (52.82, G, 4), (52.95, G, 6, "slide"), (53.65, D, 2), (53.83, D, 4),
    (54.25, D, 4), (54.48, G, 2), (54.57, G, 4), (54.84, G, 2),

    (54.93, D, 2), (55.12, D, 4), (55.48, G, 4), (55.62, G, 6, "slide"), (56.35, D, 2), (56.55, D, 4),
    (56.70, G, 2), (57.01, G, 4), (57.10, G, 6, "slide"), (57.22, G, 2), (57.38, G, 2),

    # B --------------5-------------
    # G -------4s6-------6s4--4-2-4-
    # D -2-4------------------------
    (57.76, D, 2), (57.98, D, 4), (58.40, G, 4), (58.53, G, 6, "slide"), (58.71, B, 5), (59.20, G, 4),
    (59.50, G, 2), (59.72, G, 4),

    # G ------2-----2-4
    # D -22-4----4-----
    (60.44, D, 2), (60.67, D, 2), (60.90, D, 4), (60.99, G, 2), (61.35, D, 4), (61.47, G, 2),
    (61.67, G, 4),
]


def play(guitar):
    human = random.Random(5)  # small touch variations; the timing is already human
    first = SONG[0][0]
    plucks = [n for n in SONG if len(n) == 3]

    for i, note in enumerate(SONG):
        time, string, fret = note[:3]
        t = 0.05 + (time - first) / SPEED
        if len(note) == 4:
            before = max(n[0] for n in SONG[:i] if n[1] == string)
            guitar.slide(t, string, fret, glide=min(0.1, (time - before) * 0.8 / SPEED))
            continue

        later = [n for n in plucks if n[0] > time]
        gap = later[0][0] - time if later else HOLD
        touch = 0.78 if gap >= 0.28 else 0.64 if gap >= 0.16 else 0.52   # quick notes are lighter
        guitar.pluck(t, string, fret, touch + human.uniform(-0.06, 0.06))

        # One hand position plays the tune: a finger lifts when the next string is played.
        sounding = max([time] + [n[0] for n in SONG[i + 1:] if len(n) == 4 and n[1] == string
                                 and not any(time < p[0] < n[0] and p[1] == string for p in plucks)])
        other = next((n[0] for n in later if n[1] != string), None)
        same = next((n[0] for n in later if n[1] == string), None)
        release = sounding + (HOLD if later else LAST_RING)
        if other is not None and other >= sounding:
            release = min(release, other + 0.07)
        if same is None or same > release:
            guitar.mute(0.05 + (release - first) / SPEED, string)


if __name__ == "__main__":
    guitar = Guitar()
    play(guitar)
    out = Path(__file__).with_name("baitikochi_chuste.wav")
    seconds = guitar.write_wav(str(out))
    print(f"{out.name}: {seconds:.1f}s")
