# File: src/core/audio/presets/whale_calls.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: audio/presets/whale_calls.py
© 2025 projectemergence. All rights reserved.

Defines the WhaleCalls preset class.
Provides a low–frequency whale call preset.

Adoptez une vision tournée vers l’avenir!
"""

from pyo import Sine, Fader
from core.audio.presets.base_preset import BasePreset

class WhaleCalls(BasePreset):
    def __init__(
        self,
        intensity=0.4,
        duration=4.0,
        freq=110.0,
        fade_in=1.0,
        fade_out=1.0,
        fader_mul_factor=1.0,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=intensity, duration=duration, **kw)
        # core frequency
        self.freq = freq
        # envelope settings
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.fader_mul_factor = fader_mul_factor
        # storage for chain
        self.chain = {}

    def _build(self):
        # amplitude envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        # carrier sine for whale call
        sine = Sine(freq=self.freq, mul=fader)
        self.chain = {"fader": fader, "sine": sine}
        return sine

    def play(self):
        sine = self._build()
        self.chain["fader"].play()
        sine.out()
        return self.chain

if __name__ == "__main__":
    WhaleCalls().play()
