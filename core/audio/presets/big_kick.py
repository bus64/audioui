# File: audio/presets/big_kick.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
# © 2025 projectemergence – v2

"""
BigKick 2.0 – modern electronic kick
• body: exponential sine sweep for punch
• click: tight noise burst with band-pass
• sub: optional low sine layer
• gating and HPF to remove noise floor
• antialias filtering around waveshaper
"""

from pyo import Sine, Noise, ButBP, ButHP, Fader, Clip, Biquad, Gate
from core.audio.presets.base_preset import BasePreset

class BigKick(BasePreset):
    def __init__(
        self,
        intensity=0.68,
        duration=0.6,
        freq1=160,
        freq2=45,
        click_len=0.015,
        click_freq=5000,
        add_sub=True,
        soft_clip=True,
        gate_thresh=0.001,
        body_env_fadein=0.002,
        body_sweep_ratio=0.89,
        click_env_fadein=0.0005,
        click_env_fadeout_ratio=0.7,
        click_mul_factor=0.35,
        click_bp_q=10.0,
        sub_freq_ratio=0.5,
        sub_mul_factor=0.5,
        lpf_freq=20000.0,
        lpf_q=0.707,
        lpf_type=1,
        clip_min=-0.9,
        clip_max=0.9,
        hpf_freq=20.0,
        hpf_q=0.707,
        hpf_type=2,
        **kw
    ):
        kw.setdefault('stereo_w', 0.0)
        kw.setdefault('enable_reverb', False)
        super().__init__(intensity=0.68,
                         duration=0.6,
                         freq1=160,
                         freq2=45,
                         **kw)

        # click parameters
        self.click_len = 0.015
        self.click_freq = 5000

        # behavior flags
        self.add_sub = True
        self.soft_clip = True
        self.gate_thresh = 0.001

        # body envelope / sweep
        self.body_env_fadein = 0.002
        self.body_sweep_ratio = 0.89

        # click envelope
        self.click_env_fadein = 0.0005
        self.click_env_fadeout_ratio = 0.7
        self.click_mul_factor = 0.35
        self.click_bp_q = 10.0

        # sub oscillator
        self.sub_freq_ratio = 0.5
        self.sub_mul_factor = 0.5

        # soft-clip / antialias filter
        self.lpf_freq = 20000.0
        self.lpf_q = 0.707
        self.lpf_type = 1
        self.clip_min = -0.9
        self.clip_max = 0.9

        # final high-pass filter
        self.hpf_freq = 20.0
        self.hpf_q = 0.707
        self.hpf_type = 2

    def _make_body(self, env):
        # exponential sweep for psycho-acoustic punch
        glide = self._sweep(
            self.freq1,
            self.freq2,
            self.duration * self.body_sweep_ratio,
            exp=True
        )
        return Sine(freq=glide, mul=env)

    def _make_click(self):
        env = Fader(
            fadein=self.click_env_fadein,
            fadeout=self.click_len * self.click_env_fadeout_ratio,
            dur=self.click_len,
            mul=self.intensity * self.click_mul_factor
        ).play()
        noise = Noise(mul=env)
        return ButBP(noise, freq=self.click_freq, q=self.click_bp_q)

    def _make_sub(self, env):
        sub_freq = max(self.freq2 * self.sub_freq_ratio, 20.0)
        return Sine(freq=sub_freq, mul=env * self.sub_mul_factor)

    def _build(self):
        # body envelope
        body_env = self._env(self.body_env_fadein)

        # components
        parts = [
            self._make_body(body_env),
            self._make_click()
        ]
        if self.add_sub:
            parts.append(self._make_sub(body_env))

        mix = sum(parts)

        if self.soft_clip:
            # antialias LPF before clipping
            mix = Biquad(
                mix,
                freq=self.lpf_freq,
                q=self.lpf_q,
                type=self.lpf_type
            )
            mix = Clip(mix, min=self.clip_min, max=self.clip_max)

        # gate to remove residual noise
        gated = Gate(mix, thresh=self.gate_thresh)

        # high-pass to remove subsonic rumble
        return Biquad(
            gated,
            freq=self.hpf_freq,
            q=self.hpf_q,
            type=self.hpf_type
        )
