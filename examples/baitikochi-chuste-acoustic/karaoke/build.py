"""Prepare everything the karaoke video needs.

  chords.wav  - the strummed chord guitar alone, synthesised
  data.js     - chord changes, beat grid and timed lyric lines for index.html

Lyrics are read from lyrics.lrc in this folder (not in the repo: add your own).
Each line is a standard LRC line, timed from the start of the video:

    [00:12.40] words of the line

Without lyrics.lrc, the placeholder lines in lyrics.example.lrc are used.

Run:  python3 build.py   then   npx hyperframes render --output karaoke.mp4
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from baitikochi_chuste import (  # noqa: E402
    BAR, EIGHTH, SONG, START, TEMPO, TOTAL_BARS, Guitar, bars, play_chords, write_wav,
)

LENGTH = 62          # seconds of video
MAX_LINE = 8.0       # a line never stays highlighted longer than this
LRC = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


def chord_changes():
    """(time, name) every time the chord changes."""
    changes, bar = [], 0
    for section in SONG:
        for first, second in bars(section):
            for half, name in enumerate((first, second)):
                if not changes or changes[-1][1] != name:
                    changes.append((round(START + bar * BAR + half * 4 * EIGHTH, 3), name))
            bar += 1
    return changes


def lyric_lines(path):
    """Parse LRC into [{t, end, text}], sorted, clipped to the video."""
    stamped = []
    for raw in path.read_text(encoding="utf-8").splitlines():
        stamps = LRC.findall(raw)
        text = LRC.sub("", raw).strip()
        for minutes, seconds in stamps:
            stamped.append((int(minutes) * 60 + float(seconds), text))
    stamped.sort()
    lines = []
    for i, (t, text) in enumerate(stamped):
        if not text or t >= LENGTH - 1:
            continue  # an empty stamped line just ends the one before it
        following = stamped[i + 1][0] if i + 1 < len(stamped) else LENGTH
        lines.append({"t": round(t, 3), "end": round(min(following, t + MAX_LINE, LENGTH), 3), "text": text})
    return lines


if __name__ == "__main__":
    guitar = Guitar(seed=7)
    play_chords(guitar)
    samples = guitar.render()
    samples = (samples + [0.0] * (LENGTH * guitar.sr))[: LENGTH * guitar.sr]
    write_wav(HERE / "chords.wav", samples, guitar.sr)

    source = HERE / "lyrics.lrc"
    if not source.exists():
        source = HERE / "lyrics.example.lrc"
    lines = lyric_lines(source)

    data = {
        "length": LENGTH,
        "beat": 60 / TEMPO,
        "start": START,
        "beats": TOTAL_BARS * 4,
        "chords": [{"t": t, "name": name} for t, name in chord_changes()],
        "lines": lines,
    }
    (HERE / "data.js").write_text("window.KARAOKE = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
                                  encoding="utf-8")

    # the video's length is read from the page before any script runs
    page = HERE / "index.html"
    html = page.read_text(encoding="utf-8")
    page.write_text(re.sub(r'data-duration="\d+"', f'data-duration="{LENGTH}"', html), encoding="utf-8")

    print(f"chords.wav {LENGTH}s, {len(data['chords'])} chord changes, {len(lines)} lyric lines from {source.name}")
