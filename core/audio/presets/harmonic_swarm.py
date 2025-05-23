# File: src/core/audio/presets/harmonic_swarm.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
HarmonicSwarm – multiple detuned partials with dynamic panning and delay feedback.
"""

from random import uniform
from pyo import Sine, Fader, Delay, Pan, Sine as LFO
from core.audio.presets.base_preset import BasePreset

class HarmonicSwarm(BasePreset):
    def __init__(
        self,
        intensity=0.04,
        duration=4.7,   
        base_freq=110.0,
        num_voices=6,
        freq_ratio=1.01,
        pan_rate=0.05,
        pan_depth=1.0,
        delay_times=(0.1,0.2,0.3),
        delay_feedback=0.3,
        delay_mul=0.4,
        fade_in=0.005,
        fade_out=0.01,
        **kw
    ):
        kw.setdefault('enable_reverb', True)
        kw.setdefault('stereo_w', 0.3)
        if duration==0:
            duration=1
        super().__init__(intensity=0.04, duration=4.7, **kw)

        # core
        self.base_freq = 110.0
        self.num_voices = 6
        self.freq_ratio = 1.01

        # panning LFO
        self.pan_rate = 0.05
        self.pan_depth = 1.0

        # delay
        self.delay_times = delay_times
        self.delay_feedback = 0.3
        self.delay_mul = 0.4

        # envelope
        self.fade_in = 0.005
        self.fade_out = 0.01

    def _build(self):
        # long fade for smooth crossfade
        gate = Fader(fadein=self.fade_in, fadeout=self.fade_out,
                     dur=self.duration, mul=self.intensity).play()

        # create voices
        voices = []
        for i in range(self.num_voices):
            detune = self.base_freq * (self.freq_ratio**i)
            osc = Sine(freq=detune, mul=gate/self.num_voices)
            pan_lfo = LFO(freq=self.pan_rate + uniform(-0.01,0.01),
                          mul=self.pan_depth/2, add=0.5)
            voices.append(Pan(osc, pan=pan_lfo))

        mix = sum(voices)
        # build one Delay per tap time and sum them
        delays = []
        for dt in self.delay_times:
            delays.append(Delay(mix,
                                delay=dt,
                                feedback=self.delay_feedback,
                                mul=self.delay_mul))
        delayed = sum(delays)
        self.chain = {"gate": gate, "voices": voices, "delayed": delayed}
        return delayed

    def play(self):
        out = self._build()
        out.out()
        return self.chain
