#File:  audio/presets/piano.py © 2025 projectemergence. All rights reserved.
# File: src/core/audio/presets/piano.py © 2025 projectemergence

from pyo import Sine, Fader
from core.audio.presets.base_preset import BasePreset

class Piano(BasePreset):
    def __init__(
        self,
        notes,
        durations,
        intensity=0.8,
        fade_in=0.01,
        fade_out=0.15,
        fader_mul_factor=1.0,
    ):
        super().__init__(intensity, duration=None)
        self.notes = notes
        self.durations = durations
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.fader_mul_factor = fader_mul_factor

    def _build(self):
        seq = []
        for note, dur in zip(self.notes, self.durations):
            f = Fader(fadein=self.fade_in,
                      fadeout=self.fade_out,
                      dur=dur,
                      mul=self.intensity * self.fader_mul_factor)
            s = Sine(freq=note, mul=f)
            seq.append((f, s))
        return seq
