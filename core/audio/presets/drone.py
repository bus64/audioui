# File: core/audio/presets/drone.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3

from pyo import Fader, Sine, SigTo
from core.audio.presets.base_preset import BasePreset

class DronePreset(BasePreset):
    """Continuous drone whose level & pitch track settled_ratio & visual_metric."""
    def __init__(self, *, settled_ratio: float = 0.0, visual_metric: float = 0.0,fade_in=0.5,fade_out=0.1,dur=0.89):
        super().__init__()  # uses default intensity/duration
        self.settled_ratio = 0.0
        self.visual_metric = 0.0
        self.fade_in=0.5
        self.fade_out=0.1
        self.dur=0.89
    def play(self):
        env  = Fader(fadein=self.fade_in, fadeout=self.fade_out, dur=0.89, mul=self.settled_ratio).play()
        freq = SigTo(value=200 + self.visual_metric * 800, time=0.1)
        return Sine(freq=freq, mul=env * 0.3).out()
    def _build(self):
        # one-liner envelope × drone
        env = Fader(fadein=self.fade_in, fadeout=self.fade_out, dur=0.89, mul=self.intensity).play()
        freq = SigTo(value=200 + self.visual_metric * 800, time=0.1)
        return Sine(freq=freq, mul=env * 0.3)