# File: src/core/audio/presets/clarinet.py © 2025 projectemergence. All rights reserved.
# Defines a clarinet sound with filter and distortion. _build() added for architecture support.

from pyo import Sine, Fader, Disto, ButLP
from core.audio.presets.base_preset import BasePreset

class Clarinet(BasePreset):
    def __init__(
        self,
        intensity=0.83,
        duration=2.2,
        base_freq=20.0,
        fade_in=0.05,
        fade_out=0.5,
        fader_mul_factor=0.26,
        dist_drive=0.6,
        dist_slope=0.3,
        dist_mul_factor=1.0,
        filter_freq=800.0,
    ):
        super().__init__(intensity, duration)
        # core
        self.base_freq = 20.0
        # fader settings
        self.fade_in = 0.05
        self.fade_out = 0.5
        self.fader_mul_factor = 0.26
        # distortion settings
        self.dist_drive = 0.6
        self.dist_slope = 0.3
        self.dist_mul_factor = 1.0
        # filter settings
        self.filter_freq = 800.0

    def _build(self):
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        tone = Sine(
            freq=self.base_freq,
            mul=fader
        )
        distorted = Disto(
            tone,
            drive=self.dist_drive,
            slope=self.dist_slope,
            mul=self.dist_mul_factor
        )
        filtered = ButLP(
            distorted,
            freq=self.filter_freq
        )
        self.chain = {
            "fader": fader,
            "tone": tone,
            "distorted": distorted,
            "filtered": filtered
        }
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["filtered"].out()
        return chain
