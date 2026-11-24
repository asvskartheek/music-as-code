# Baitikochi Chuste

The melody of "Baitikochi Chuste" (from the film *Agnyaathavaasi*) on the synthesised guitar. F# minor, 4/4, about 88 bpm, 55 seconds.

## Run it

Needs Python 3 only. No packages to install.

```bash
cd examples/baitikochi-chuste
python3 baitikochi_chuste.py
```

That writes `baitikochi_chuste.wav` next to the script (about 3 seconds to render). The `.wav` is git-ignored, so generate it yourself.

Play it:

```bash
afplay baitikochi_chuste.wav        # macOS
aplay baitikochi_chuste.wav         # Linux
start baitikochi_chuste.wav         # Windows
```

You can also run it from the repo root: `python3 examples/baitikochi-chuste/baitikochi_chuste.py`.

## How the song is written

`SONG` is a list of notes. Times are seconds into the [source lesson video](https://www.youtube.com/watch?v=m5Y-zxXSo1U), measured from the player's own performance, so the timing is human and not on a grid.

| Entry | Meaning |
|---|---|
| `(8.36, G, 6)` | pluck the G string at fret 6, at 8.36 s |
| `(8.62, G, 4, "slide")` | the same note moves to fret 4 with no new pluck (slide, hammer-on or pull-off) |

The tab lines from the video sit above each section as comments.

## Change it

| Constant | Effect |
|---|---|
| `SPEED` | `1.0` is as played. `1.03` gives a true 90 bpm |
| `HOLD` | seconds a note rings when nothing follows it |
| `LAST_RING` | how long the final note rings |

Each note stops when the next one starts on another string, the way one hand position plays a tune.

## Where tab and playing disagree

The script follows the playing.

| Printed tab | Played |
|---|---|
| `4s5` in line 2 | slides to fret 6 |
| `D 2-4` opening the fifth line, first time | D4 then G2 |
| `1s2` opening line 2, second time | skipped |
