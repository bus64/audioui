# File: src/core/audio/maestro/progression.py  © 2025 projectemergence. All rights reserved.

import re
import random
import functools
import logging
from typing import Dict, Any, List, Optional, Tuple

import music21.key as m21key
import music21.roman as roman

logger = logging.getLogger(__name__)

class ProgressionSynth:
    """
    Rule‐based chord progression generator with caching:
      • Caches next() by (key_str, beats, time_signature)
      • Key objects & RomanNumeral creations memoized
      • Graceful fallback on any parsing error
    """

    GENRE_TEMPLATES: Dict[str, List[str]] = {
        'pop':       ['I', 'V', 'vi', 'IV'],
        'rock':      ['I', 'IV', 'V'],
        'blues':     ['I', 'IV', 'I', 'V'],
        'jazz':      ['ii', 'V', 'I'],
        'classical': ['I', 'vi', 'ii', 'V'],
        'funk':      ['I', 'bVII', 'IV', 'I'],
    }

    FUNCTION_MARKOV: Dict[str, List[str]] = {
        'T': ['S']*3 + ['D']*2 + ['T'],
        'S': ['D']*4 + ['T'],
        'D': ['T']*5 + ['S'],
    }

    RN_TO_FUNCTION: Dict[str, str] = {
        'I':'T','i':'T','vi':'T','VI':'T','III':'T','iii':'T',
        'ii':'S','II':'S','IV':'S','iv':'S',
        'V':'D','v':'D','vii°':'D','VII':'D'
    }

    def __init__(self, genre: str = 'pop', temperature: float = 0.5):
        self.genre       = genre if genre in self.GENRE_TEMPLATES else None
        self.temperature = max(0.0, min(1.0, temperature))

        # cache helpers
        self._key_obj     = functools.lru_cache(maxsize=32)(self._make_key)
        self._rn_obj      = functools.lru_cache(maxsize=256)(self._make_roman)
        self._next_cached = functools.lru_cache(maxsize=128)(self._next_uncached)

    def next(self, analysis: Dict[str,Any], beats: float) -> List[str]:
        """
        Public API: wraps cached _next_uncached, normalizing inputs.
        """
        raw_key = analysis.get('key', 'C major')
        # normalize flats/sharps
        key_str = raw_key.translate(str.maketrans({'♭':'b','♯':'#'}))
        # strip out any junk, collapse whitespace
        key_str = re.sub(r'[^A-Za-z #]+', ' ', key_str).strip()
        parts = key_str.split()
        if len(parts) >= 2:
            tonic, mode = parts[0].capitalize(), parts[1].lower()
            if mode not in ('major','minor'):
                mode = 'major'
            key_str = f"{tonic} {mode}"
        else:
            key_str = "C major"

        try:
            return list(self._next_cached(key_str, beats, analysis.get('time_signature')))
        except Exception as e:
            logger.warning(f"Progression failed for '{key_str}': {e}. Falling back to C major.")
            try:
                return list(self._next_cached("C major", beats, analysis.get('time_signature')))
            except Exception as e2:
                logger.error(f"Fallback progression also failed: {e2}. Returning ['C'].")
                return ['C']

    def _next_uncached(self,
                       key_str: str,
                       beats: float,
                       time_signature: Optional[str]
                      ) -> Tuple[str, ...]:
        # 1) parse key
        m21k = self._key_obj(key_str)

        # 2) determine bar count
        bar_beats = 4.0
        if time_signature:
            num, den = map(int, time_signature.split('/'))
            bar_beats = num * (4/den)
        n_bars = max(1, int(round(beats / bar_beats)))

        # 3) choose Roman numerals
        if self.genre:
            tpl = self.GENRE_TEMPLATES[self.genre]
            rns = (tpl * ((n_bars // len(tpl)) + 1))[:n_bars]
        else:
            rns, prev_fn = [], 'T'
            for _ in range(n_bars):
                fn = random.choice(self.FUNCTION_MARKOV[prev_fn])
                choices = [rn for rn,f in self.RN_TO_FUNCTION.items() if f == fn]
                rns.append(random.choice(choices))
                prev_fn = fn

        # 4) convert to chord symbols
        chords = []
        for rn in rns:
            rn_obj = self._rn_obj(rn, key_str)
            root    = rn_obj.root().name
            quality = rn_obj.quality
            chords.append(root + ('' if quality == 'major' else 'm'))
        return tuple(chords)

    def _make_key(self, key_str: str) -> m21key.Key:
        parts = key_str.strip().split()
        tonic = parts[0]
        mode  = parts[1] if len(parts) >= 2 else 'major'
        try:
            # use the two‐argument Key constructor to avoid string‐parsing issues
            return m21key.Key(tonic, mode)
        except Exception as e:
            logger.warning(f"_make_key: Key({tonic!r}, {mode!r}) failed: {e}. Falling back to C major.")
            return m21key.Key('C', 'major')

    def _make_roman(self, rn: str, key_str: str) -> roman.RomanNumeral:
        try:
            return roman.RomanNumeral(rn, self._key_obj(key_str))
        except Exception as e:
            logger.warning(f"_make_roman: invalid RN '{rn}' in '{key_str}': {e}. Using I in C major.")
            return roman.RomanNumeral('I', self._key_obj("C major"))
