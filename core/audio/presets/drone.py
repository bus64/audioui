# File: core/audio/presets/drone.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3

from pyo import Fader, Sine, Sum
from core.audio.presets.base_preset import BasePreset

class Drone(BasePreset):  # Renamed class
    """Continuous drone with adjustable complexity."""
    def __init__(
        self,
        intensity=0.4,
        duration=10.0,
        base_freq=100.0,
        complexity=0.2, # Range 0-1
        fade_in=2.0,
        fade_out=2.0,
        lfo_mod_depth_factor=5.0, # New parameter
        lfo_mod_rate_factor=0.1,  # New parameter
        **kw
    ):
        if duration == 0: # Ensure duration is not zero
            duration = 0.001 
        super().__init__(intensity=intensity, duration=duration, **kw)
        
        self.base_freq = base_freq
        self.complexity = complexity # 0-1 range
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.lfo_mod_depth_factor = lfo_mod_depth_factor
        self.lfo_mod_rate_factor = lfo_mod_rate_factor
        # self.dur is inherited from BasePreset via super().__init__

    def _build(self):
        env = Fader(fadein=self.fade_in, fadeout=self.fade_out, dur=self.duration, mul=self.intensity).play()
        
        # Main LFO Modulation for primary sine
        # LFO rate and depth are scaled by complexity
        lfo_rate = max(0.001, self.complexity * self.lfo_mod_rate_factor)
        lfo_depth = self.complexity * self.lfo_mod_depth_factor
        mod_lfo = Sine(freq=lfo_rate, mul=lfo_depth)
        
        main_sine_freq = self.base_freq + mod_lfo
        main_sine = Sine(freq=main_sine_freq, mul=env)
        
        output_signal = main_sine
        
        # Secondary Oscillator (based on high complexity)
        if self.complexity > 0.5:
            detune_factor = 1.0 + (self.complexity - 0.5) * 0.02 
            secondary_amp_factor = (self.complexity - 0.5) * 0.5 
            
            secondary_sine_freq = self.base_freq * detune_factor
            # Ensure secondary sine also uses the main envelope
            secondary_sine = Sine(freq=secondary_sine_freq, mul=env * secondary_amp_factor)
            
            # Summing the main modulated sine and the secondary sine
            # Adjust overall gain if necessary, for now simple sum
            output_signal = Sum([main_sine, secondary_sine], mul=1.0) # mul=1.0 as env already scales them

        self.chain = output_signal # Storing the final output PyoObject
            
        return self.chain

    def play(self):
        # _build now correctly returns the PyoObject (or a chain of them)
        self.chain_output = self._build()
        self.chain_output.out()
        return self.chain_output # Return the Pyo object that is outputting sound