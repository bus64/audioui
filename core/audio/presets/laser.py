# File: src/core/audio/presets/laser.py © 2025 projectemergence. All rights reserved.
# Futuristic laser sound with FM. _build() added for architecture support.

from pyo import Sine, Fader
from core.audio.presets.base_preset import BasePreset

class Laser(BasePreset):
    def __init__(
        self,
        intensity=0.9,
        duration=0.5,
        base_freq=800.0,
        mod_depth=50.0,
        mod_rate=20.0,
        fade_in=0.00,
        fade_out=0.2,
        fader_mul_factor=1.0,
    ):
        super().__init__(intensity, duration)
        # core
        self.base_freq = base_freq
        self.mod_depth = mod_depth
        self.mod_rate = mod_rate
        # envelope settings
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.fader_mul_factor = fader_mul_factor

    def _build(self):
        # amplitude envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        # modulator oscillator
        mod = Sine(freq=self.mod_rate, mul=self.mod_depth)
        # frequency-modulated carrier
        modulated_freq = self.base_freq + mod
        laser = Sine(freq=modulated_freq, mul=fader)
        self.chain = {"fader": fader, "mod": mod, "laser": laser}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["laser"].out()
        return chain
