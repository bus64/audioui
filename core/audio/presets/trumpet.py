# File: src/core/audio/presets/trumpet.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: audio/presets/trumpet.py
© 2025 projectemergence. All rights reserved.

Defines the Trumpet preset.
Emulates a bright brass sound with a characteristically brassy vibrato and warm filtering.
Adoptez une vision tournée vers l’avenir!
"""

from pyo import Sine, Fader, Chorus, ButLP, SigTo
from core.audio.presets.base_preset import BasePreset

class Trumpet(BasePreset):
    def __init__(
        self,
        intensity=0.8,
        duration=1.5,
        base_freq=440.0,
        vibrato_rate=6.0,
        vibrato_depth=10.0,
        fade_in=0.05,
        fade_out=0.7,
        fader_mul_factor=1.0,
        sigto_time_factor=1.0,
        lp_freq=1000.0,
        chorus_depth=1.0,
        chorus_feedback=0.25,
        chorus_bal=0.5,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=intensity, duration=duration, **kw)

        # core tone parameters
        self.base_freq = base_freq
        self.vibrato_rate = vibrato_rate
        self.vibrato_depth = vibrato_depth

        # envelope settings
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.fader_mul_factor = fader_mul_factor

        # SigTo (smooth freq) timing
        self.sigto_time_factor = sigto_time_factor

        # filtering
        self.lp_freq = lp_freq

        # chorus effect
        self.chorus_depth = chorus_depth
        self.chorus_feedback = chorus_feedback
        self.chorus_bal = chorus_bal

    def _build(self):
        # amplitude envelope
        fader = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity * self.fader_mul_factor
        )
        # smooth base frequency holder
        freq_mod = SigTo(
            value=self.base_freq,
            time=self.duration * self.sigto_time_factor
        )
        # vibrato oscillator
        vibrato = Sine(freq=self.vibrato_rate, mul=self.vibrato_depth)
        # combine base freq and vibrato
        modulated_freq = freq_mod + vibrato
        # carrier tone
        tone = Sine(freq=modulated_freq, mul=fader)
        # warm low-pass filter
        filtered = ButLP(tone, freq=self.lp_freq)
        # richness via chorus
        chorus = Chorus(
            filtered,
            depth=self.chorus_depth,
            feedback=self.chorus_feedback,
            bal=self.chorus_bal
        )

        self.chain = {
            "fader": fader,
            "freq_mod": freq_mod,
            "vibrato": vibrato,
            "tone": tone,
            "filtered": filtered,
            "chorus": chorus
        }
        return chorus

    def play(self):
        out = self._build()
        self.chain["fader"].play()
        out.out()
        return self.chain

if __name__ == "__main__":
    Trumpet().play()
