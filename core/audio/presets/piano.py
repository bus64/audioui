#File:  audio/presets/piano.py © 2025 projectemergence. All rights reserved.
# File: src/core/audio/presets/piano.py © 2025 projectemergence

from pyo import Sine, Fader
from core.audio.presets.base_preset import BasePreset

class Piano(BasePreset):
    def __init__(
        self,
        notes,
        durations,
        intensity=0.8,
        fade_in=0.01,
        fade_out=0.15,
        fader_mul_factor=1.0,
        tempo: float = 120.0, # New tempo parameter
    ):
        # Pass all relevant parameters including tempo to BasePreset
        # BasePreset handles notes, durations, intensities, and tempo for melody playback.
        # Piano's _build method might be overridden if it needs to behave differently from BasePreset's melody logic.
        # For now, assume Piano leverages BasePreset's melody handling.
        super().__init__(
            intensity=intensity, 
            duration=None, # Duration is per-note for melodies, handled by BasePreset
            notes=notes,
            durations=durations,
            # intensities could be passed if Piano had its own per-note intensity logic
            tempo=tempo
        )
        # Store parameters if Piano needs them directly, though BasePreset handles core melody logic.
        self.notes = notes 
        self.durations = durations
        self.fade_in = fade_in
        self.fade_out = fade_out
        self.fader_mul_factor = fader_mul_factor
        self.tempo = tempo # Store tempo

    def _build(self):
        # This _build method is specific to Piano if it doesn't use BasePreset's melody player.
        # If BasePreset.play() is used for Piano melodies (which it should be, given notes/durations are passed to super),
        # then this _build method is only called if .play() is invoked on a Piano instance
        # that *didn't* receive notes/durations in its __init__ (falling back to single-shot mode).
        # The subtask implies Piano is used for melodies, so BasePreset.play() will handle it.
        # If Piano is *only* for melodies passed to its constructor, this _build could raise NotImplementedError
        # or return a default sound. For now, keep it as is, but be aware of its role.
        
        # If this Piano instance is meant to play a single sound (not a melody sequence from constructor):
        if not self.notes or not self.durations: # Check if it's in single-shot mode
             # Default behavior for a single piano note if notes/durations not provided
             # (or if BasePreset's play() decided not to use its melody logic)
            default_freq = self.freq1 if self.freq1 is not None else 440 # Use freq1 or a default
            default_duration = self.duration if self.duration is not None else 1.0 # Use instance duration or default
            
            # The tempo conversion should happen here if this _build is for a single, duration-beat defined sound.
            # However, self.duration in BasePreset is already in seconds.
            # If 'dur' in this context was meant to be from a different source (e.g. specific Piano param in beats),
            # then conversion self.tempo would be needed. Assuming self.duration is already in seconds.
            fader_duration = default_duration

            f = Fader(fadein=self.fade_in,
                      fadeout=self.fade_out,
                      dur=fader_duration, 
                      mul=self.intensity * self.fader_mul_factor)
            s = Sine(freq=default_freq, mul=f)
            return s # Return single Pyo object as per BasePreset._build() expectation for single-shot

        # If Piano's _build is somehow used for sequences directly (less likely with BasePreset.play() changes):
        # This part of _build would be invoked if BasePreset.play() called self._build() AND self.notes was populated.
        # However, BasePreset.play() now has its own loop for notes/durations.
        # This implies that if notes/durations are provided, BasePreset.play() handles them directly.
        # If they are NOT provided, then this _build() is called.
        # The original Piano _build created a sequence. If it's for single-shot, it should return a single Pyo object.
        # For now, retaining original sequence logic if notes/durations are present,
        # but this path is less likely to be hit for melodies given BasePreset.play() changes.
        seq = []
        for note, dur_beats in zip(self.notes, self.durations):
            effective_tempo = self.tempo if self.tempo and self.tempo > 0 else 120.0
            duration_in_seconds = dur_beats * (60.0 / effective_tempo)

            f = Fader(fadein=self.fade_in,
                      fadeout=self.fade_out,
                      dur=duration_in_seconds, # Use converted duration
                      mul=self.intensity * self.fader_mul_factor)
            s = Sine(freq=note, mul=f)
            seq.append((f, s)) # BasePreset.play() expects list of (Fader, PyoObject)
        return seq
