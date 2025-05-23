# File: src/core/audio/presets/wood_kick.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
# © 2025 projectemergence. All rights reserved.

"""
WoodKick – a clean, wooden-character kick with minimal noise.
Technique enhancements:
 • body: sine sweep (45→400 Hz) with high-pass DC removal
 • click: band-limited noise burst with high-pass cleanup
 • separate multi-stage envelopes for tight attack & body
 • gentle tanh saturation with pre-filter antialiasing
"""

from pyo import Sine, Noise, ButBP, ButHP, Biquad, Fader, SigTo, Tanh
from core.audio.presets.base_preset import BasePreset

class WoodKick(BasePreset):
    def __init__(
        self,
        intensity=0.3,
        duration=0.36,
        click_freq=1200.0,
        hp_cut=200.0,
        body_sweep_ratio=0.8,
        body_mul_factor=1.9,
        body_hpf_freq=20.0,
        body_hpf_q=0.707,
        body_hpf_type=2,
        click_env_fadein=0.0005,
        click_env_fadeout=0.05,
        click_env_dur=0.05,
        click_mul_factor=2.0,
        click_bp_q=55.0,
        sat_mul=1.5,
        sat_hpf_freq=200.0,
        sat_hpf_q=0.307,
        sat_hpf_type=2,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(
            intensity=2 * intensity,
            duration=duration,
            freq1=45.0,
            freq2=400.0,
            **kw
        )
        # click
        self.click_freq = click_freq
        self.hp_cut = hp_cut
        # body
        self.body_sweep_ratio = body_sweep_ratio
        self.body_mul_factor = body_mul_factor
        self.body_hpf_freq = body_hpf_freq
        self.body_hpf_q = body_hpf_q
        self.body_hpf_type = body_hpf_type
        # click envelope
        self.click_env_fadein = click_env_fadein
        self.click_env_fadeout = click_env_fadeout
        self.click_env_dur = click_env_dur
        self.click_mul_factor = click_mul_factor
        self.click_bp_q = click_bp_q
        # saturation
        self.sat_mul = sat_mul
        self.sat_hpf_freq = sat_hpf_freq
        self.sat_hpf_q = sat_hpf_q
        self.sat_hpf_type = sat_hpf_type

    def _body(self, env):
        glide = self._sweep(
            self.freq1,
            self.freq2,
            self.duration * self.body_sweep_ratio,
            exp=False
        )
        osc = Sine(freq=glide, mul=env * self.body_mul_factor)
        return Biquad(
            osc,
            freq=self.body_hpf_freq,
            q=self.body_hpf_q,
            type=self.body_hpf_type
        )

    def _click(self):
        env = Fader(
            fadein=self.click_env_fadein,
            fadeout=self.click_env_fadeout,
            dur=self.click_env_dur,
            mul=self.click_mul_factor * self.intensity
        ).play()
        noise = Noise(mul=env)
        bp = ButBP(noise, freq=self.click_freq, q=self.click_bp_q)
        return ButHP(bp, freq=self.hp_cut)

    def _build(self):
        env = self._env(.005)
        mix = self._body(env) + self._click()
        sat = Tanh(mix * self.sat_mul)
        out = Biquad(
            sat,
            freq=self.sat_hpf_freq,
            q=self.sat_hpf_q,
            type=self.sat_hpf_type
        )
        self.chain = {"body_env": env, "mix": mix, "out": out}
        return out

    def play(self):
        out = self._build()
        # start body envelope
        self.chain["body_env"].play()
        out.out()
        return self.chain

if __name__ == "__main__":
    WoodKick().play()
