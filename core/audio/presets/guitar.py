# File: src/core/audio/presets/guitar.py © 2025 projectemergence. All rights reserved.
# Simulates a plucked sine loop guitar. _build() added for architecture support.

from pyo import SineLoop, Fader, Chorus
from core.audio.presets.base_preset import BasePreset

class Guitar(BasePreset):
    def __init__(
        self,
        intensity=1.0,
        duration=0.18,
        base_freq=220.0,
        fade_in=0.01,
        fade_out=0.36,
        fader_mul_factor=0.57,
        loop_feedback=0.07,
        chorus_depth=0.44,
        chorus_feedback=0.14,
        chorus_bal=0.14,
    ):
        super().__init__(intensity, duration)
        # core
        self.base_freq = 220.0
        # fader settings
        self.fade_in = 0.01
        self.fade_out = 0.36
        self.fader_mul_factor = 0.57
        # sine-loop settings
        self.loop_feedback = 0.07
        # chorus settings
        self.chorus_depth = 0.44
        self.chorus_feedback = 0.14
        self.chorus_bal = 0.14

    def _build(self):
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        tone = SineLoop(
            freq=self.base_freq,
            feedback=self.loop_feedback,
            mul=fader
        )
        chorus = Chorus(
            tone,
            depth=self.chorus_depth,
            feedback=self.chorus_feedback,
            bal=self.chorus_bal
        )
        self.chain = {"fader": fader, "tone": tone, "chorus": chorus}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["chorus"].out()
        return chain
