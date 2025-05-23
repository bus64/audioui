# File: src/core/audio/presets/snare.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: audio/presets/snare.py
© 2025 projectemergence. All rights reserved.

Defines the Snare preset.
Simulates a snare drum using a short burst of noise filtered with a narrow bandpass.
Adoptez une vision tournée vers l’avenir!
"""

from pyo import Noise, Fader, ButBP
from core.audio.presets.base_preset import BasePreset

class Snare(BasePreset):
    def __init__(
        self,
        intensity=0.64,
        duration=0.54,
        center_freq=19.952623149688797,
        fade_in=0.01,
        fade_out=0.2,
        fader_mul_factor=1.0,
        **kw
    ):
        # ensure stereo and reverb defaults
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=0.64, duration=0.54, **kw)

        # filter center frequency
        self.center_freq = 19.952623149688797

        # envelope settings
        self.fade_in = 0.01
        self.fade_out = 0.2
        self.fader_mul_factor = 1.0

        # storage for built objects
        self.chain = {}

    def _build(self):
        # create the burst envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        # noise source
        noise = Noise(mul=fader)
        # band-pass filter for snare character
        snare = ButBP(noise, freq=self.center_freq)

        self.chain = {"fader": fader, "noise": noise, "snare": snare}
        return snare

    def play(self):
        snare = self._build()
        # start envelope and output
        self.chain["fader"].play()
        snare.out()
        return self.chain

if __name__ == "__main__":
    Snare().play()
