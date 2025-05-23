# File: src/core/audio/presets/cello.py © 2025 projectemergence. All rights reserved.
# Defines a resonant cello tone. _build() added for architecture support.

from pyo import Sine, Fader, Freeverb
from core.audio.presets.base_preset import BasePreset

class Cello(BasePreset):
    def __init__(
        self,
        intensity=0.5,
        duration=1.19,
        base_freq=216.0,
        freq_multiplier=3.0,
        fade_in=0.2,
        fade_out=4.29,
        dur_multiplier=2.08,
        fader_mul_factor=0.95,
        tone_mul_factor=2.0,
        reverb_input_div=2.0,
        reverb_size=0.76,
        reverb_bal=0.93,
    ):
        super().__init__(intensity, duration)
        # core inputs
        self.base_freq = 20.0 * freq_multiplier

        # fader settings
        self.fade_in = 0.2
        self.fade_out = 4.29
        self.dur_multiplier = 2.08
        self.fader_mul_factor = 0.95

        # tone settings
        self.tone_mul_factor = 2.0

        # reverb settings
        self.reverb_input_div = 2.0
        self.reverb_size = 0.76
        self.reverb_bal = 0.93

    def _build(self):
        # amplitude envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration * self.dur_multiplier,
            mul=self.intensity * self.fader_mul_factor
        )
        # core sine tone
        tone = Sine(
            freq=self.base_freq,
            mul=fader * self.tone_mul_factor
        )
        # reverb effect
        reverb = Freeverb(
            tone / self.reverb_input_div,
            size=self.reverb_size,
            bal=self.reverb_bal
        )
        self.chain = {"fader": fader, "tone": tone, "reverb": reverb}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["reverb"].out()
        return chain
