# File: src/core/audio/maestro/maestro_compositor.py  © 2025 projectemergence. All rights reserved.

import os
import re
import json
import random
from typing import List, Tuple, Dict, Optional, Any

# A single note event: (frequency in Hz, duration in beats, intensity 0–1)
NoteEvent = Tuple[float, float, float]

class Compositor:
    """
    • Loads JSON5‐style melody files (comments allowed)
    • Captures all metadata (title, structure, remix params, etc.)
    • Falls back to legacy "notes" arrays when "hands" is absent
    • Exposes get_full_sequence(), next_event(), and next_block_events()
    """
    def __init__(self, repo_path: str, default_intensity: float = 0.8,maestro=None):
        self.repo_path         = repo_path
        self.default_intensity = default_intensity
        self.maestro=maestro
        # name → metadata dict (everything except 'hands'/'notes')
        self.metadata:  Dict[str, Dict[str, Any]]          = {}
        # name → list of hands → list of NoteEvent
        self.melodies:  Dict[str, List[List[NoteEvent]]]   = {}
        # name → tempo (BPM)
        self.tempos:    Dict[str, float]                   = {}
        # name → (beats_per_bar, beat_unit)
        self.meters:    Dict[str, Tuple[int,int]]          = {}

        # playback state
        self.current_hands:   List[List[NoteEvent]] = []
        self.idxs:            List[int]             = []
        self.current_melody:  Optional[str]         = None

        print(f"[Compositor] Scanning melodies in {self.repo_path}")
        self._load_repo()

    def _load_repo(self):
        if self.maestro.mute==True:
            return
        def strip_comments(text: str) -> str:
            without_block = re.sub(r'/\*.*?\*/', '', text, flags=re.DOTALL)
            without_line  = re.sub(r'//.*', '', without_block)
            return without_line

        for fn in sorted(os.listdir(self.repo_path)):
            if not fn.lower().endswith(".json"):
                continue
            path = os.path.join(self.repo_path, fn)
            name = fn[:-5]
            try:
                raw  = open(path, encoding="utf-8").read()
                data = json.loads(strip_comments(raw))
            except Exception as e:
                print(f"[Compositor] Failed to parse {fn}: {e}")
                continue

            md = {k: v for k, v in data.items() if k not in ("hands", "notes")}
            self.metadata[name] = md

            if "tempo" in data:
                self.tempos[name] = float(data["tempo"])
                print(f"[Compositor] '{name}': tempo={data['tempo']} BPM")
            if "time_signature" in data:
                tsig = data["time_signature"]
                try:
                    num, den = map(int, tsig.split("/"))
                    self.meters[name] = (num, den)
                    print(f"[Compositor] '{name}': time_signature={tsig}")
                except:
                    print(f"[Compositor] '{name}': invalid time_signature '{tsig}'")

            hands_raw = data.get("hands") or ([data["notes"]] if "notes" in data else None)
            hands_evs: List[List[NoteEvent]] = []
            if isinstance(hands_raw, list):
                for hl in hands_raw:
                    if not isinstance(hl, list):
                        continue
                    evs: List[NoteEvent] = []
                    for o in hl:
                        try:
                            f = float(o["frequency"])
                            d = float(o.get("duration_beats", o.get("duration", 1.0)))
                            i = float(o.get("intensity", self.default_intensity))
                            evs.append((f, d, i))
                        except:
                            continue
                    if evs:
                        hands_evs.append(evs)
            if hands_evs:
                self.melodies[name] = hands_evs
                print(f"[Compositor] Registered '{name}' with {len(hands_evs)} hand(s)")
            else:
                print(f"[Compositor] No valid events in '{name}', skipping")

    def start(self, melody_name: str):
        if self.maestro.mute==True:
            return
        """Begin fresh run through up to 4 hands."""
        self.current_melody = melody_name
        self.current_hands  = self.melodies.get(melody_name, [])
        self.idxs           = [0] * len(self.current_hands)
        print(f"[Compositor] Starting '{melody_name}' with {len(self.current_hands)} hand(s)")

    def next_event(self) -> Tuple[List[float], List[float], List[float]]:
        if self.maestro.mute==True:
            return
        """Return parallel lists: notes, durations, intensities."""
        if not self.current_hands:
            return [0.0], [1.0], [0.0]
        notes, durs, ints = [], [], []
        for hi, hand in enumerate(self.current_hands):
            f, d, i = hand[self.idxs[hi]]
            notes.append(f)
            durs.append(d)
            ints.append(max(-1,i))
            self.idxs[hi] = (self.idxs[hi] + 1) % len(hand)
        #print(f"[Compositor] next_event → notes={notes}, durs={durs}, ints={ints}")
        return notes, durs, ints

    def get_full_sequence(self) -> Tuple[List[float], List[float], List[float]]:
        if self.maestro.mute==True:
            return
        """Return entire first‐hand sequence."""
        if not self.current_hands:
            return [], [], []
        evs   = self.current_hands[0]
        return [f for f,_,_ in evs], [d for _,d,_ in evs], [i for _,_,i in evs]

    def get_tempo(self, default: float) -> float:
        if self.maestro.mute==True:
            return
        """Return stored tempo or default."""
        return self.tempos.get(self.current_melody, default)

    def get_meter(self) -> Tuple[int,int]:
        if self.maestro.mute==True:
            return
        """Return (beats_per_bar, beat_unit) or (4,4)."""
        return self.meters.get(self.current_melody, (4,4))

    def next_block_events(self, beats: float) -> List[Dict[str, Any]]:
        if self.maestro.mute==True:
            return
        """
        Gather events until we've covered `beats` beats.
        Returns a list of dicts:
          {"time": beat_offset,
           "notes": [...],
           "durations": [...],
           "intensity": [...]}
        """
        events: List[Dict[str, Any]] = []
        time_acc = 0.0
        while time_acc < beats:
            notes, durs, ints = self.next_event()
            events.append({
                "time":       time_acc,
                "notes":      notes,
                "durations":  durs,
                "intensity":  ints
            })
            # advance by the average duration of this batch
            time_acc += sum(durs) / len(durs)
        return events
