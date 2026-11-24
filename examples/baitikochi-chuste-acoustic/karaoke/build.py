"""Prepare everything the karaoke video needs.

  chords.wav  - the fingerpicked chord guitar alone, synthesised
  data.js     - chord changes, beat grid and timed lyric lines for index.html

Lyrics are read from lyrics.lrc in this folder (not in the repo: add your own).
Each line is a standard LRC line, timed against the original recording (the video follows its clock):

    [00:27.35] words of the line

Without lyrics.lrc, the placeholder lines in lyrics.example.lrc are used.

Run:  python3 build.py   then   npx hyperframes render --output karaoke.mp4
"""

import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))

from baitikochi_chuste import BEAT, CHART, FIRST_LOOP_BEAT, LENGTH, render, write_wav  # noqa: E402

MAX_LINE = 8.0       # a line never stays highlighted longer than this
LRC = re.compile(r"\[(\d+):(\d+(?:\.\d+)?)\]")


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
    samples, sr = render()
    write_wav(HERE / "chords.wav", samples, sr)

    source = HERE / "lyrics.lrc"
    if not source.exists():
        source = HERE / "lyrics.example.lrc"
    lines = lyric_lines(source)

    pulse = BEAT / 2                      # the song is felt twice as fast as the chord beat
    start = FIRST_LOOP_BEAT * BEAT
    data = {
        "length": LENGTH,
        "beat": pulse,
        "start": round(start, 3),
        "beats": int((LENGTH - 1.5 - start) / pulse),
        "chords": [{"t": round(beat * BEAT, 3), "name": name} for beat, name in CHART],
        "lines": lines,
    }
    (HERE / "data.js").write_text("window.KARAOKE = " + json.dumps(data, ensure_ascii=False, indent=1) + ";\n",
                                  encoding="utf-8")

    # the video's length is read from the page before any script runs
    page = HERE / "index.html"
    html = page.read_text(encoding="utf-8")
    page.write_text(re.sub(r'data-duration="\d+"', f'data-duration="{LENGTH}"', html), encoding="utf-8")

    print(f"chords.wav {LENGTH}s, {len(data['chords'])} chord changes, {len(lines)} lyric lines from {source.name}")
