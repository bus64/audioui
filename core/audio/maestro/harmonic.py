# File: src/core/audio/maestro/harmonic.py  © 2025 projectemergence. All rights reserved.

import math
from typing import List, Tuple, Dict
import functools

import numpy as np
from music21 import note, stream, analysis

# build major/minor triad templates in pitch‐class space
_NOTE_NAMES = ['C','C#','D','D#','E','F','F#','G','G#','A','A#','B']
_CHORD_TEMPLATES: Dict[str, List[int]] = {
    **{name: [i, (i+4)%12, (i+7)%12] for i,name in enumerate(_NOTE_NAMES)},      # major
    **{name+'m': [i, (i+3)%12, (i+7)%12] for i,name in enumerate(_NOTE_NAMES)},  # minor
}

class HarmonicAnalyser:
    """
    Real‐time key, chord & function estimation with caching:
      • @lru_cache on describe calls (cached by tuple(melody))
      • Input melody converted to hashable tuple internally
    """
    def __init__(self):
        # wrap the uncached implementation in an LRU cache
        self._describe_cached = functools.lru_cache(maxsize=128)(self._describe_uncached)

    def describe(self, melody: List[Tuple[float, float]]) -> Dict[str, List]:
        """
        Memoized wrapper. Converts `melody` list to a tuple for caching.
        """
        return self._describe_cached(tuple(melody))

    def _describe_uncached(
        self,
        melody: Tuple[Tuple[float, float], ...]
    ) -> Dict[str, List]:
        """
        Original implementation, renamed to _describe_uncached.
        """
        # 1) Key estimation
        s = stream.Stream()
        offset = 0.0
        for freq, dur in melody:
            n = note.Note()
            n.pitch.frequency = freq
            n.offset = offset
            n.quarterLength = dur
            s.insert(n)
            offset += dur
        key_obj = s.analyze("Krumhansl")
        key = f"{key_obj.tonic.name} {key_obj.mode}"

        # 2) collect events as (time, pitch_class)
        events = []
        t = 0.0
        for freq, dur in melody:
            midi = int(round(69 + 12*math.log2(freq/440.0)))
            pc = midi % 12
            events.append((t, pc))
            t += dur

        total_beats = math.ceil(offset)
        chords, durations = [], []
        tonic_pc = _NOTE_NAMES.index(key_obj.tonic.name)

        # 3) for each beat‐window pick best triad
        for b in range(total_beats):
            window = [pc for time, pc in events if b <= time < b+1]
            if not window:
                symbol = key_obj.tonic.name + ("" if key_obj.mode=="major" else "m")
            else:
                hist = np.zeros(12, int)
                for pc in window:
                    hist[pc] += 1
                best_score, symbol = -1, key_obj.tonic.name
                for sym, template in _CHORD_TEMPLATES.items():
                    score = sum(hist[pc] for pc in template)
                    if score > best_score:
                        best_score, symbol = score, sym
            chords.append(symbol)
            durations.append(1.0)

        # 4) map each chord → function (0=T,1=S,2=D)
        functions = []
        for sym in chords:
            root = sym.rstrip('m')
            root_pc = _NOTE_NAMES.index(root) if root in _NOTE_NAMES else tonic_pc
            interval = (root_pc - tonic_pc) % 12
            if interval in (7, 11):
                functions.append(2)
            elif interval in (2, 5):
                functions.append(1)
            else:
                functions.append(0)

        return {
            "key":       key,
            "chords":    chords,
            "functions": functions,
            "durations": durations
        }
