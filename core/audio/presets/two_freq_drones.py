# File: src/core/audio/presets/two_freq_drones.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
# © 2025 projectemergence

"""
TwoFreqDrones – subtle, continuously-evolving dual-sine drone.
• Always-on; no need to reschedule-loop.
• Slow random drift on both oscillators via band-limited LFO.
• Dual Faders give click-free start/stop and enable cross-fade
  when the engine really has to restart the preset.
"""

from random import random
from pyo import Sine, Fader, Sine as LFO
from core.audio.presets.base_preset import BasePreset   # unchanged

class TwoFreqDrones(BasePreset):
    def __init__(
        self,
        base_freq=65.4,
        ratio=4/3,
        drift_speed=0.04,
        intensity=0.5,
        fade=2.0,
        drift_mul_ratio=0.015,
        osc_amp_factor=0.5,
        mix_voices=2,
        **kw
    ):
        kw.setdefault('enable_reverb', True)
        kw.setdefault('stereo_w', 0.3)
        # duration=0 => infinite
        super().__init__(intensity=intensity, duration=0, **kw)

        # core parameters
        self.base_freq = base_freq
        self.ratio = ratio

        # drift LFO
        self.drift_speed = drift_speed
        self.drift_mul_ratio = drift_mul_ratio

        # cross-fade gate
        self.fade = fade

        # oscillator amplitude relative to gate
        self.osc_amp_factor = osc_amp_factor

        # mixing
        self.mix_voices = mix_voices

    def _drifting_osc(self, freq, amp):
        """Band-limited LFO to drift the oscillator frequency ±drift_mul_ratio."""
        drift = LFO(
            freq=self.drift_speed,
            phase=random(),
            mul=freq * self.drift_mul_ratio,
            add=freq
        )
        return Sine(freq=drift, mul=amp)

    def _build(self):
        # gate fader for crossfade
        gate = Fader(
            fadein=self.fade,
            fadeout=self.fade,
            dur=self.duration,
            mul=self.intensity
        ).play()

        # two drifting oscillators
        osc_a = self._drifting_osc(self.base_freq, gate * self.osc_amp_factor)
        osc_b = self._drifting_osc(self.base_freq * self.ratio, gate * self.osc_amp_factor)

        # mix to stereo voices
        mix = (osc_a + osc_b).mix(self.mix_voices)

        # store chain
        self.chain = {"gate": gate, "osc_a": osc_a, "osc_b": osc_b, "mix": mix}
        return mix

    def play(self):
        out = self._build()
        out.out()
        return self.chain

if __name__ == "__main__":
    TwoFreqDrones().play()