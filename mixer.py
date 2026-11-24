"""Put several instruments in one stereo recording.

Standard library only.
"""

import math
import wave
from array import array


def normalise(samples, dbfs=-1.0):
    peak = max(abs(x) for x in samples) or 1.0
    gain = 10 ** (dbfs / 20) / peak
    return [x * gain for x in samples]


def mix(tracks):
    """tracks: (samples, gain, pan) with pan from -1 (left) to +1 (right).

    Returns (left, right), normalised together to -1 dBFS.
    """
    length = max(len(samples) for samples, _, _ in tracks)
    left, right = [0.0] * length, [0.0] * length
    for samples, gain, pan in tracks:
        angle = (pan + 1) * math.pi / 4  # equal-power pan
        gl, gr = gain * math.cos(angle), gain * math.sin(angle)
        for i, x in enumerate(samples):
            left[i] += gl * x
            right[i] += gr * x
    both = normalise(left + right)
    return both[:length], both[length:]


def write_wav(path, left, right=None, sample_rate=44100):
    """16-bit wav: mono, or stereo when `right` is given. Returns seconds."""
    channels = [left] if right is None else [left, right]
    pcm = array("h", (int(max(-1.0, min(1.0, x)) * 32767) for frame in zip(*channels) for x in frame))
    with wave.open(path, "wb") as f:
        f.setnchannels(len(channels))
        f.setsampwidth(2)
        f.setframerate(sample_rate)
        f.writeframes(pcm.tobytes())
    return len(left) / sample_rate
