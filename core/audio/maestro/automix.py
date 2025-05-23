# File: src/core/audio/maestro/automix.py  © 2025 projectemergence. All rights reserved.

import pyloudnorm as pyln
import numpy as np
from pydub import AudioSegment
from typing import Dict, Any

class AutoMixer:
    """
    Batch FFT & loudness EQ for entire blocks:
      • One integrated loudness measurement per part
      • Frequency‐bin cache by sample‐count
      • Heuristic reverb/chorus flags
    """
    def __init__(self, target_lufs: float = -14.0, sr: int = 48000):
        self.meter = pyln.Meter(sr)
        self.target = target_lufs
        self.sr = sr
        # cache rfftfreq arrays by length
        self._freq_cache: Dict[int, np.ndarray] = {}

    def autoset(self,
                parts: Dict[str, Dict[str, Any]],
                target_lufs: float | None = None
               ) -> Dict[str, Dict[str, Any]]:
        tgt = target_lufs if target_lufs is not None else self.target

        for name, cfg in parts.items():
            # render a quick sine‐stub
            seg = self._sine_stub(cfg['notes'], cfg['durations'], sr=self.sr)
            samples = np.array(seg.get_array_of_samples(), dtype=float)

            N = len(samples)
            if N not in self._freq_cache:
                # cache once
                self._freq_cache[N] = np.fft.rfftfreq(N, 1/self.sr)
            freqs = self._freq_cache[N]

            # compute magnitude spectrum (if you need it for advanced EQ later)
            _ = np.abs(np.fft.rfft(samples))

            # loudness‐based gain_dB
            loud = self.meter.integrated_loudness(samples)
            parts[name]['gain_db'] = 3 #tgt - loud

            # simple FX heuristics
            parts[name]['enable_reverb']  = np.mean(cfg['notes']) > 60
            parts[name]['enable_chorus']  = len(cfg['notes']) > 6

        return parts

    @staticmethod
    def _sine_stub(notes, durs, sr=48000) -> AudioSegment:
        """
        Quick AudioSegment of concatenated sine‐tones for level analysis.
        """
        samples = []
        for n, d in zip(notes, durs):
            # midi-to-frequency fallback if needed
            freq = n if isinstance(n, float) else 440.0
            N = int(sr * d)
            t = np.linspace(0, d, N, False)
            samples.append(np.sin(2 * np.pi * freq * t))
        arr = np.concatenate(samples)
        pcm = (arr * 32767).astype(np.int16).tobytes()
        return AudioSegment(pcm, frame_rate=sr, sample_width=2, channels=1)
