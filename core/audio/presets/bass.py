# File: src/core/audio/presets/bass.py © 2025 projectemergence. All rights reserved.
# Defines the Bass preset, with optional distortion. _build() added for architecture support.

from pyo import Sine, Fader, Disto
from core.audio.presets.base_preset import BasePreset

class Bass(BasePreset):
    def __init__(
        self,
        intensity=0.98,
        duration=0.65,
        base_freq=82.41,      # E2
        fade_in=0.01,
        fade_out=0.2,
        tone_freq_ratio=2.0,  # Octave
        tone_mul_factor=0.62,
        dist_drive=0.05,
        dist_slope=0.1,
        dist_mul_factor=0.56,
        **kw  # Added **kw to capture any extra args for BasePreset
    ):
        if duration == 0: # Ensure duration is not zero
            duration = 0.001
        super().__init__(intensity=intensity, duration=duration, **kw) # Use passed intensity, duration
        
        # core inputs
        self.base_freq = base_freq
        # fader constants
        self.fade_in = fade_in
        self.fade_out = fade_out
        # tone constants
        self.tone_freq_ratio = tone_freq_ratio
        self.tone_mul_factor = tone_mul_factor
        # distortion constants
        self.dist_drive = dist_drive
        self.dist_slope = dist_slope
        self.dist_mul_factor = dist_mul_factor

    def _build(self):
        # use named attributes everywhere instead of literals
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration, # duration is now correctly passed from super
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
