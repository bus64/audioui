# File: src/core/audio/presets/violin.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: audio/presets/violin.py
© 2025 projectemergence. All rights reserved.

Defines the Violin preset.
Simulates a bowed string instrument using a sine oscillator with vibrato.
Adoptez une vision tournée vers l’avenir!
"""

from pyo import Sine, Fader
from core.audio.presets.base_preset import BasePreset

class Violin(BasePreset):
    def __init__(
        self,
        intensity=0.5,
        duration=3.0,
        base_freq=4063.57,
        vibrato_rate=5.0,
        vibrato_depth=5.0,
        fade_in=0.1,
        fade_out=0.5,
        fader_mul_factor=0.46,
    ):
        super().__init__(intensity, duration)
        # core tone params
        self.base_freq = 4063.57
        self.vibrato_rate = 5.0
        self.vibrato_depth = 5.0
        # envelope params
        self.fade_in = 0.1
        self.fade_out = 0.5
        self.fader_mul_factor = 0.46
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
        # vibrato LFO
        vibrato = Sine(freq=self.vibrato_rate, mul=self.vibrato_depth)
        # modulated carrier
        modulated_freq = self.base_freq + vibrato
        tone = Sine(freq=modulated_freq, mul=fader)
        self.chain = {"fader": fader, "vibrato": vibrato, "tone": tone}
        return self.chain

    def play(self):
        chain = self._build()
        chain["fader"].play()
        chain["tone"].out()
        return chain

if __name__ == "__main__":
    Violin().play()