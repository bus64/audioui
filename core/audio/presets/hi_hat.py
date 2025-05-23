# File: src/core/audio/presets/hi_hat.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: audio/presets/hi_hat.py
© 2025 projectemergence. All rights reserved.

Defines the Hi-Hat preset.
Simulates a hi-hat using filtered noise with a short burst envelope.
Adoptez une vision tournée vers l’avenir!
"""

from pyo import Noise, Fader, ButHP
from core.audio.presets.base_preset import BasePreset

class HiHat(BasePreset):
    def __init__(
        self,
        intensity=0.76,
        duration=1.85,
        cutoff=5654.76,
        fade_in=0.005,
        fade_out=0.21,
        fader_mul_factor=0.0,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=0.76, duration=1.85, **kw)
        # filter cutoff
        self.cutoff = 5654.76
        # envelope settings
        self.fade_in = 0.005
        self.fade_out = 0.21
        self.fader_mul_factor = 0.0

    def _build(self):
        # short burst envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        noise = Noise(mul=fader)
        hi_hat = ButHP(noise, freq=self.cutoff)
        self.chain = {"fader": fader, "noise": noise, "hi_hat": hi_hat}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["hi_hat"].out()
        return chain

if __name__ == "__main__":
    HiHat().play()
