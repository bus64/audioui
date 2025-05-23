# File: audio/presets/metallic_rain.py © 2025 projectemergence. All rights reserved.
# © 2025 projectemergence
#!/usr/bin/env python3
"""
MetallicRain – spectral drizzle with stereo drift and tail.
(Fixed kw duplication 2025-04-23.)
"""

import random, time, threading
from pyo import Noise, ButBP, Sine, Fader, Mix
from core.audio.presets.base_preset import BasePreset

class MetallicRain(BasePreset):
    def __init__(
        self,
        intensity=0.4,
        duration=6.0,
        grain_rate=7,
        base_freq=432.0,
        width=0.9,
        fade_env=0.2,
        hiss_mul_factor=0.1,
        hiss_freq_ratio=1.2,
        hiss_q=0.2,
        sweep_start_ratio=1.8,
        sweep_end_ratio=0.4,
        sweep_dur=0.4,
        drop_rand_min=0.1,
        drop_rand_max=2.4,
        amp_rand_min=0.3,
        amp_rand_max=0.7,
        rate_rand_min=0.1,
        rate_rand_max=2.0,
        grain_bp_ratio=1.1,
        grain_bp_q=8.0,
        mix_voices=2,
        **kw
    ):
        kw.setdefault('stereo_w', width)
        kw.setdefault('enable_reverb', True)
        super().__init__(intensity=intensity, duration=duration, **kw)

        # core parameters
        self.grain_rate = grain_rate
        self.base_freq = base_freq

        # envelope / hiss
        self.fade_env = fade_env
        self.hiss_mul_factor = hiss_mul_factor
        self.hiss_freq_ratio = hiss_freq_ratio
        self.hiss_q = hiss_q

        # sweep (body) parameters
        self.sweep_start_ratio = sweep_start_ratio
        self.sweep_end_ratio = sweep_end_ratio
        self.sweep_dur = sweep_dur

        # randomization ranges
        self.drop_rand_min = drop_rand_min
        self.drop_rand_max = drop_rand_max
        self.amp_rand_min = amp_rand_min
        self.amp_rand_max = amp_rand_max
        self.rate_rand_min = rate_rand_min
        self.rate_rand_max = rate_rand_max

        # grain filter
        self.grain_bp_ratio = grain_bp_ratio
        self.grain_bp_q = grain_bp_q

        # final mix
        self.mix_voices = mix_voices

    def _grain(self, freq, dur, amp):
        """Create one grain: band-passed sine burst, auto-out."""
        grain = ButBP(
            Sine(freq=freq),
            freq=freq * self.grain_bp_ratio,
            q=self.grain_bp_q,
            mul=amp
        )
        grain.out()
        return grain

    def _build(self):
        # create shared envelope for hiss and grains
        fade = self._env(self.fade_env)

        # hiss floor
        hiss = ButBP(
            Noise(mul=fade * self.hiss_mul_factor),
            freq=self.base_freq * self.hiss_freq_ratio,
            q=self.hiss_q
        )

        # spawn grains in background
        def rain_loop():
            end_t = time.time() + (self.duration or 1e9)
            while time.time() < end_t:
                drop = self.base_freq * random.uniform(self.drop_rand_min, self.drop_rand_max)
                glide = self._sweep(
                    drop * self.sweep_start_ratio,
                    drop * self.sweep_end_ratio,
                    self.sweep_dur
                )
                dur = random.uniform(self.sweep_dur * 0.25, self.sweep_dur * 0.875)
                amp = fade * random.uniform(self.amp_rand_min, self.amp_rand_max)
                self._keep(self._grain(glide, dur, amp))
               
        threading.Thread(target=rain_loop, daemon=True).start()

        # mix to stereo
        mix = Mix([hiss], voices=self.mix_voices)
        self.chain = {"fade": fade, "hiss": hiss, "mix": mix}
        return mix

    def play(self):
        mix = self._build()
        mix.out()
        return self.chain

if __name__ == "__main__":
    MetallicRain().play()
