# File: src/core/audio/maestro/arrangement_engine.py  © 2025 projectemergence. All rights reserved.

import random
from typing import Dict, List, Any
from core.audio.maestro.harmonic     import HarmonicAnalyser
from core.audio.maestro.progression  import ProgressionSynth
from core.audio.maestro.orchestrator import Orchestrator
from core.audio.maestro.automix      import AutoMixer

class ArrangementEngine:
    def __init__(self, client, maestro=None):
        self.client = client
        self.maestro=maestro
        self.ha     = HarmonicAnalyser()
        self.ps     = ProgressionSynth()
        self.orc    = Orchestrator()
        self.mix    = AutoMixer()

    def prepare_block(self, beats: float = 4.0) -> Dict[str, Dict[str, Any]]:
        if self.maestro.mute==True:
            return
        """
        1) Pull a full block of melody events from the Compositor.
        2) Analyze melody → chord progression → orchestration.
        3) Inject the raw melody as its own part.
        4) Auto-mix & return the per-part configs.
        """
        # 1) Gather raw block events
        raw = self.client.maestro.compositor.next_block_events(beats)

        # a) flatten melody for analysis
        melody = [(f, d) for ev in raw for f, d, _ in zip(ev['notes'], ev['durations'], ev['intensity'])]
        analysis = self.ha.describe(melody)

        # b) chord progression
        chords = self.ps.next(analysis, beats)
        chord_dur = beats / max(len(chords), 1)
        chord_durs = [chord_dur] * len(chords)

        # c) orchestration
        parts = self.orc.voice(chords, chord_durs)

        # 2) inject raw melody
        parts['melody'] = {
            'notes':     [f for ev in raw for f in ev['notes']],
            'durations': [d for ev in raw for d in ev['durations']],
            'intensity': [i for ev in raw for i in ev['intensity']],
        }

        # 3) batch auto-mix
        return self.mix.autoset(parts)
