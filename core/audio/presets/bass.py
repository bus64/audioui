# File: src/core/audio/presets/bass.py © 2025 projectemergence. All rights reserved.
# Defines the Bass preset, with optional distortion. _build() added for architecture support.

from pyo import Sine, Fader, Disto
from core.audio.presets.base_preset import BasePreset

class Bass(BasePreset):
    def __init__(
        self,
        intensity=0.98,
        duration=0.65,
        base_freq=1318.2567385564075,
        fade_in=0.0,
        fade_out=0.0,
        tone_freq_ratio=223.872113856834,
        tone_mul_factor=0.62,
        dist_drive=0.35,
        dist_slope=0.44,
        dist_mul_factor=0.56,
    ):
        super().__init__(intensity * 2, duration)
        # core inputs
        self.base_freq = 1318.2567385564075
        # fader constants
        self.fade_in = 0.0
        self.fade_out = 0.0
        # tone constants
        self.tone_freq_ratio = 223.872113856834
        self.tone_mul_factor = 0.62
        # distortion constants
        self.dist_drive = 0.35
        self.dist_slope = 0.44
        self.dist_mul_factor = 0.56

    def _build(self):
        # use named attributes everywhere instead of literals
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration * 2,
            mul=self.intensity
        )
        tone = Sine(
            freq=self.base_freq * self.tone_freq_ratio,
            mul=fader * self.tone_mul_factor
        )
        distorted = Disto(
            tone,
            drive=self.dist_drive,
            slope=self.dist_slope,
            mul=self.intensity * self.dist_mul_factor
        )
        self.chain = {"fader": fader, "tone": tone, "distorted": distorted}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["distorted"].out()
        return chain
