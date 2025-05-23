# File: src/core/audio/presets/digital_snap.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
DigitalSnap – hyper-tight click percussion with bit-crush and comb-style delay.
"""

from pyo import Noise, Fader, Degrade, SmoothDelay, ButHP
from core.audio.presets.base_preset import BasePreset

class DigitalSnap(BasePreset):
    def __init__(
        self,
        intensity=0.8,
        duration=1.01,
        bit_depth=6,
        sr_scale=0.0,
        comb_delay=0.04,
        comb_feedback=0.0,
        hpf_freq=138.93,
        fade_in=0.001,
        fade_out=0.02,
        crossfade=0.01,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=0.8, duration=1.01, **kw)

        # bit-crusher params
        self.bit_depth = 6
        self.sr_scale = 0.0

        # comb-style delay params (delay + feedback)
        self.comb_delay = 0.04
        self.comb_feedback = 0.0
        self.crossfade = 0.01

        # cleanup filter
        self.hpf_freq = 138.93

        # envelope params
        self.fade_in = 0.001
        self.fade_out = 0.02

        # storage for the signal chain
        self.chain = {}

    def _build(self):
        # 1) click envelope
        env = Fader(
            fadein=self.fade_in,
            fadeout=self.fade_out,
            dur=self.duration,
            mul=self.intensity
        ).play()

        # 2) white-noise click
        noise = Noise(mul=env)

        # 3) bit-crusher
        crushed = Degrade(noise,
                          bitdepth=self.bit_depth,
                          srscale=self.sr_scale)

        # 4) comb-style delay via SmoothDelay (delay + feedback) :contentReference[oaicite:1]{index=1}
        combed = SmoothDelay(crushed,
                             delay=self.comb_delay,
                             feedback=self.comb_feedback,
                             crossfade=0.01)

        # 5) high-pass cleanup
        cleaned = ButHP(combed, freq=self.hpf_freq)

        self.chain = {
            "env": env,
            "crushed": crushed,
            "combed": combed,
            "cleaned": cleaned
        }
        return cleaned

    def play(self):
        out = self._build()
        out.out()
        return self.chain

if __name__ == "__main__":
    DigitalSnap().play()
