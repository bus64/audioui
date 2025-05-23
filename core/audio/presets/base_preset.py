# File: audio/presets/base_preset.py © 2025 projectemergence. All rights reserved.
# File: src/core/audio/presets/base_preset.py

from abc import ABC, abstractmethod
import time
from pyo import (Fader, Pan, SigTo, Freeverb, Chorus, ButLP, Sine)
import inspect
from typing import ClassVar, Dict, Type, Any

class PresetMeta(type):
    _registry: ClassVar[Dict[str, Type['BasePreset']]] = {}

    def __init__(cls, name: str, bases: tuple, namespace: dict[str, Any]):
        super().__init__(name, bases, namespace)
        # skip the abstract BasePreset itself
        if bases and BasePreset in bases:
            mod_name = cls.__module__.split('.')[-1]
            PresetMeta._registry[mod_name] = cls

class BasePreset(metaclass=PresetMeta):

    supports_melody: bool = True
    def __init__(
        self,
        intensity: float | list[float]       = 0.7,
        duration:  float | None               = 2.0,
        freq1:     float | None               = None,
        freq2:     float | None               = None,
        # ─── optional melody parameters ───────────────────────────────
        notes:      list[float] | None        = None,
        durations:  list[float] | None        = None,
        intensities:list[float] | None        = None,
        # ───────────────────────────────────────────────────────────────
        pan_pos:   float                      = 0.0,
        stereo_w:  float                      = 0.0,
        enable_reverb: bool                   = False,
        enable_chorus: bool                   = False,
        enable_filter: bool                   = False,
        filt_freq: float                      = 1200,
        **extra
    ):
        # allow either a single float or per-note list
        if isinstance(intensity, list):
            self._per_note_intensities = intensity
            base_int = max(intensity) if intensity else 0.0
        else:
            self._per_note_intensities = None
            base_int = intensity

        self.intensity     = max(base_int, 0.0)
        self.duration      = duration
        self.freq1, self.freq2 = freq1, freq2
        self._pan_pos      = max(min(pan_pos, 1), -1)
        self.stereo_w      = max(min(stereo_w, 1), 0)
        self.enable_reverb = enable_reverb
        self.enable_chorus = enable_chorus
        self.enable_filter = enable_filter
        self.filt_freq     = filt_freq
        self._keep_alive   = []               # guard vs GC

        # ─── store optional melody ────────────────────────────────────
        self.notes         = notes
        self.durations     = durations
        self._melody_ints  = intensities
        # ───────────────────────────────────────────────────────────────

    def _env(self, fade=.005) -> Fader:
        dur = self.duration or 0
        return Fader(fadein=fade, fadeout=fade*4, dur=dur, mul=self.intensity)

    def _fx_chain(self, sig):
        if self.enable_filter:
            sig = ButLP(sig, freq=self.filt_freq)
        if self.enable_chorus and self.stereo_w:
            sig = Chorus(sig, depth=.8*self.stereo_w, feedback=.25, bal=.5)
        if self.enable_reverb:
            sig = Freeverb(sig, size=.8, bal=.35)
        if self._pan_pos or self.stereo_w:
            sig = Pan(sig, outs=2, pan=self._pan_pos)
        return sig

    def _keep(self, *objs):
        self._keep_alive.extend(objs)
        return objs[0] if objs else None

    @abstractmethod
    def _build(self):
        """
        Subclasses must return either
          • a single Pyo object (dry signal), or
          • a list of (Fader, Pyo-object) tuples for sequences.
        """

    def play(self):
        # ─── if a melody was passed in, override build() ────────────
        if self.notes and self.durations:
            seq = []
            # intensities: explicit -> per-note list -> fallback to base
            ints = (
                self._melody_ints
                or self._per_note_intensities
                or [self.intensity] * len(self.notes)
            )
            for f, d, i in zip(self.notes, self.durations, ints):
                env = Fader(fadein=0.005, fadeout=0.02, dur=d, mul=i)
                osc = Sine(freq=f, mul=env)
                seq.append((env, osc))
            built = seq
        else:
            built = self._build()

        # sequence-of-notes case
        if isinstance(built, list):
            for fader, sig in built:
                fader.play()
                out = self._fx_chain(sig)
                self._keep(out).out()
            return built

        # single-shot case
        dry = built
        wet = self._fx_chain(dry)
        self._keep(wet).out()
        return wet

    def _sweep(self, start_freq, end_freq, duration, exp=False):
        """
        Glide from start_freq to end_freq over a given duration.
        """
        step = (end_freq - start_freq) / duration
        current = start_freq
        dt = 0.01
        start = time.time()
        while abs(time.time() - start) < duration:
            current += step * dt
        return end_freq
