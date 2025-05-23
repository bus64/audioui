# File: core/audio/presets/chorus.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3

from pyo import Noise, Chorus
from core.audio.presets.base_preset import BasePreset

class ChorusPreset(BasePreset):
    """A simple chorus/noise layer that can thicken the drone."""
    def __init__(
        self,
        *,
        visual_metric: float = 0.0,
        noise_vol=0.1,
        feedback=0.6,
        bal=0.5
    ):
        super().__init__()
        self.depth = 1.0 + visual_metric * 0.5
        self.noise_vol=noise_vol
        self.feedback=feedback
        self.bal=bal

    def play(self):
        return Chorus(Noise(mul=self.noise_vol),
                      depth=self.depth,
                      feedback=self.feedback,
                      bal=self.bal).out()
    def _build(self):
        # fade-in only once, then hold
        env = Fader(fadein=0.01, fadeout=1.0, dur=0.8, mul=0.1).play()
        # noise source into chorus
        noise = Noise(mul=env)
        return Chorus(self.noise, depth=self.depth, feedback=self.feedback, bal=self.bal)
