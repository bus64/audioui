# File: src/core/audio/maestro/orchestrator.py  © 2025 projectemergence. All rights reserved.
# orchestrator.py
from music21 import chord, instrument

REGISTER = {
    'bass': (28, 48),      # E1–C3
    'piano': (50, 96),     # D3–C7
    'pad': (40, 84),
    'lead': (60, 108),
}

class Orchestrator:
    def __init__(self):
        self.occ = {name: 0 for name in REGISTER}

    def voice(self, chords: list[str], rhythm: list[float]):
        parts = {}
        for symb, dur in zip(chords, rhythm):
            c = chord.Chord(symb)
            # FIX: c.bass() is a Pitch, so just .midi (no .pitch)
            bass_note = c.bass().midi

            # allocate bass
            parts.setdefault('bass', {'notes': [], 'durations': [], 'intensity': []})
            parts['bass']['notes'].append(self._fit(bass_note, 'bass'))
            parts['bass']['durations'].append(dur)
            parts['bass']['intensity'].append(.9)

            # allocate chord tones to piano spread over two octaves
            p_notes = [self._fit(n.pitch.midi, 'piano') for n in c.notes]
            parts.setdefault('piano', {'notes': [], 'durations': [], 'intensity': []})
            parts['piano']['notes'].extend(p_notes)
            parts['piano']['durations'].extend([dur/len(p_notes)] * len(p_notes))
            parts['piano']['intensity'].extend([.7] * len(p_notes))

        return parts

    def _fit(self, midi: int, role: str) -> int:
        low, high = REGISTER[role]
        while midi < low:
            midi += 12
        while midi > high:
            midi -= 12
        self.occ[role] += 1
        return midi
