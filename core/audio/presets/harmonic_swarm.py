# File: src/core/audio/presets/harmonic_swarm.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
HarmonicSwarm – multiple detuned partials with dynamic panning and delay feedback.
"""

import random # Added for random.uniform, though 'from random import uniform' was already there
from random import uniform 
from pyo import Sine, Fader, Delay, Pan, Sine as LFO
from core.audio.presets.base_preset import BasePreset

class HarmonicSwarm(BasePreset):
    def __init__(
        self,
        intensity=0.3,      # Default changed
        duration=5.0,       # Default changed
        base_freq=110.0,
        num_voices=6,
        freq_ratio=1.01,
        pan_rate=0.02,      # Default changed
        pan_depth=1.0,
        delay_times=(0.1,0.2,0.3),
        delay_feedback=0.3,
        delay_mul=0.4,
        fade_in=0.5,        # Default changed
        fade_out=1.5,       # Default changed
        detune_range=0.005, # New parameter
        pan_randomness=0.005, # New parameter
        **kw
    ):
        kw.setdefault('enable_reverb', True)
        kw.setdefault('stereo_w', 0.3)
        if duration == 0: # Ensure duration is not zero to prevent errors
            duration = 0.001 # A very small duration if zero is passed
        
        super().__init__(intensity=intensity, duration=duration, **kw) # Use passed intensity and duration

        # core
        self.base_freq = base_freq
        self.num_voices = num_voices
        self.freq_ratio = freq_ratio
        self.detune_range = detune_range       # Store new parameter
        self.pan_randomness = pan_randomness # Store new parameter

        # panning LFO
        self.pan_rate = pan_rate
        self.pan_depth = pan_depth

        # delay
        self.delay_times = delay_times
        self.delay_feedback = delay_feedback
        self.delay_mul = delay_mul

        # envelope
        self.fade_in = fade_in
        self.fade_out = fade_out

    def _build(self):
        # long fade for smooth crossfade
        gate = Fader(fadein=self.fade_in, fadeout=self.fade_out,
                     dur=self.duration, mul=self.intensity).play()

        # create voices
        voices = []
        for i in range(self.num_voices):
            # Apply detune randomness
            current_freq_ratio = self.freq_ratio + random.uniform(-self.detune_range, self.detune_range)
            actual_freq = self.base_freq * (current_freq_ratio**i) # Renamed 'detune' to 'actual_freq' for clarity
            
            osc = Sine(freq=actual_freq, mul=gate/self.num_voices)
            
            # Apply pan randomness
            current_pan_rate = self.pan_rate + random.uniform(-self.pan_randomness, self.pan_randomness)
            # Ensure pan rate is positive
            effective_pan_rate = max(0.001, current_pan_rate) 
            
            pan_lfo = LFO(freq=effective_pan_rate,
                          mul=self.pan_depth/2, add=0.5) # uniform(-0.01,0.01) removed as pan_randomness handles it
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
