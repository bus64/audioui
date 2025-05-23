#File:  audio/maestro_mixer.py © 2025 projectemergence. All rights reserved.
import numpy as np
from collections import deque

class Mixer:
    """
    Perform real-time spectral analysis and drive a parametric EQ.
    """
    def __init__(self, client, sample_rate=48000, frame_size=1024):
        self.client       = client
        self.sr           = sample_rate
        self.N            = frame_size
        # rolling history of spectra for smoothing
        self.history      = deque(maxlen=4)
        # EQ band centers (Hz)
        self.bands        = [125, 250, 500, 1000, 2000, 4000, 8000, 16000]
        # initial gains
        self.band_gains   = {b: 1.0 for b in self.bands}

    def analyze_and_eq(self, audio_frame: np.ndarray):
        """
        audio_frame: 1-D float32 buffer of length N.
        """
        # 1) compute magnitude spectrum
        spec = np.abs(np.fft.rfft(audio_frame * np.hanning(self.N)))
        self.history.append(spec)
        avg_spec = np.mean(self.history, axis=0)

        # 2) for each band, find corresponding bin range
        freqs = np.fft.rfftfreq(self.N, 1/self.sr)
        for center in self.bands:
            # find nearest bin
            idx = np.argmin(np.abs(freqs - center))
            magnitude = avg_spec[idx]
            # map magnitude → desired gain (simple inverse)
            # clamp between 0.5 and 1.0
            gain = float(max(0.5, min(1.0, 1.0 - (magnitude / avg_spec.max())*0.5)))
            # smooth update (one-pole)
            self.band_gains[center] = 0.8*self.band_gains[center] + 0.2*gain
            # push to client’s EQ
            self.client.set_eq_gain(center, self.band_gains[center])
