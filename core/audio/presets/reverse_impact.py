# File: src/core/audio/presets/reverse_impact.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
ReverseImpact – swells that reverse-decay into impacts.
"""

from pyo import Noise, Fader, NewTable, TableRec, TableRead, ButBP, Disto
from core.audio.presets.base_preset import BasePreset

class ReverseImpact(BasePreset):
    def __init__(
        self,
        intensity=0.43,
        duration=4.23,
        env_dur=2.2,
        bp_freq=800.0,
        bp_q=5.0,
        dist_drive=0.65,
        dist_slope=0.39,
        fade_in=0.07,
        fade_out=0.41,
        **kw
    ):
        super().__init__(intensity=0.43, duration=4.23, **kw)

        # envelope recording length
        self.env_dur = 2.2
        self.fade_in = 0.07
        self.fade_out = 0.41

        # bandpass
        self.bp_freq = 800.0
        self.bp_q = 5.0

        # distortion
        self.dist_drive = 0.65
        self.dist_slope = 0.39

    def _build(self):
        # create reversed envelope table
        tbl = NewTable(length=self.env_dur)
        env = Fader(fadein=self.env_dur, fadeout=0,
                    dur=self.env_dur, mul=self.intensity).play()
        # record noise burst
        rec = TableRec(Noise(mul=env), table=tbl).play()

        # read it *backwards*
        reader = TableRead(
            table=tbl,
            freq=-tbl.getRate(),  
                         
            mul=1.0
        )

        # then the rest of your chain
        filtered  = ButBP(reader, freq=self.bp_freq, q=self.bp_q)
        distorted = Disto(filtered,
                          drive=self.dist_drive,
                          slope=self.dist_slope,
                          mul=1.0)

        self.chain = {
            "env": env,
            "rec": rec,
            "reader": reader,
            "filtered": filtered,
            "distorted": distorted
        }
        return distorted


    def play(self):
        out = self._build()
        out.out()
        return self.chain
