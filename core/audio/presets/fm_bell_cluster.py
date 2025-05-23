# File: src/core/audio/presets/fm_bell_cluster.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
FMBellCluster – FM-based bell cluster with feedback, chorus and reverb.
"""

from pyo import FM, Chorus, Freeverb, Fader
from core.audio.presets.base_preset import BasePreset

class FMBellCluster(BasePreset):
    def __init__(
        self,
        intensity=0.6,
        duration=4.0,
        carrier_freq=330.0,
        mod_ratio=2.0,
        index=5.0,
        chorus_depth=1.2,
        chorus_feedback=0.3,
        reverb_size=0.8,
        reverb_bal=0.4,
        fade_in=0.01,
        fade_out=1.0,
        **kw
    ):
        kw.setdefault('enable_reverb', True)
        kw.setdefault('stereo_w', 0.2)
        super().__init__(intensity=intensity, duration=duration, **kw)

        # FM params
        self.carrier_freq = carrier_freq
        self.mod_ratio = mod_ratio
        self.index = index

        # chorus
        self.chorus_depth = chorus_depth
        self.chorus_feedback = chorus_feedback

        # reverb
        self.reverb_size = reverb_size
        self.reverb_bal = reverb_bal

        # envelope
        self.fade_in = fade_in
        self.fade_out = fade_out

    def _build(self):
        env = Fader(fadein=self.fade_in, fadeout=self.fade_out,
                    dur=self.duration, mul=self.intensity).play()
        # FM carrier/modulator
        bell = FM(carrier=self.carrier_freq,
                  ratio=self.mod_ratio,
                  index=self.index,
                  mul=env)
        # add richness
        ch = Chorus(bell, depth=self.chorus_depth,
                    feedback=self.chorus_feedback)
        # space
        rv = Freeverb(ch, size=self.reverb_size,
                      bal=self.reverb_bal)
        self.chain = {"env": env, "bell": bell, "chorus": ch, "reverb": rv}
        return rv

    def play(self):
        out = self._build()
        out.out()
        return self.chain
