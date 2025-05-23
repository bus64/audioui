# File: core/audio/presets/square_fall.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3

from pyo import Fader, Sine, IRPulse
from core.audio.presets.base_preset import BasePreset

class SquareFallPreset(BasePreset):
    """Burst of harmonics into a comb filter (square-fall)."""
    def __init__(self, *, intensity: float = 0.5, freq: float = 200, harmonics: int = 6):
        super().__init__()
        self.intensity = intensity
        self.freq      = freq
        self.harmonics = harmonics

    def play(self):
        env   = Fader(fadein=0.01, fadeout=0.25, dur=0.25, mul=self.intensity).play()
        burst = sum(Sine(freq=self.freq * (i+1), mul=env / (i+1))
                    for i in range(self.harmonics))
        IRPulse(input=burst, order=2048).out()
        return burst
    def _build(self):
        # envelope & additive burst
        env = Fader(fadein=0.01, fadeout=0.25, dur=0.25, mul=self.intensity).play()
        burst = sum(
            Sine(freq=self.freq * (i + 1), mul=env / (i + 1))
            for i in range(self.harmonics)
        )
        IRPulse(input=burst, order=2048).out()
        return burst