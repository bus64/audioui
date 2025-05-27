# File: src/core/audio/maestro/audio_maestro.py © 2025 projectemergence. All rights reserved.

import asyncio
import logging
import os
import pkgutil
import random
import time

from core.audio.audio_presets_registry import registry
from core.audio.maestro.maestro_compositor import Compositor
from core.audio.maestro.arrangement_engine import ArrangementEngine

class Maestro:
    """
    Async Generative Music Maestro using a single PresetRegistry.
    """
    def __init__(self, client):
        self.client = client
        self.logger = logging.getLogger(__name__)
        self.zones, self.tasks, self.sfx_events = {}, {}, []
        self.mute=False
        print(f"Mute is {self.mute}")
        # LFO state
        self.tempo, self.energy = 120.0, 0.7
        self._last_time, self._phase = time.time(), 0.02

        # Central registry
        self.presets_sig  = registry.presets_sig
        self.presets_meta = registry.presets_meta
        self.all_presets  = list(registry.preset_map)
        self.logger.info(f"All presets discovered: {self.all_presets}")

        # Compositor & arranger
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "melodies"))

        self.compositor = Compositor(base,maestro=self)
        self.arranger    = ArrangementEngine(self.client,maestro=self)

    def queue_sfx(self, name: str, *, delay: float = 0.0, params: dict = None):
        if self.mute==True:
            if old := self.tasks.pop(zone, None): old.cancel()
            self.client.stop_all()
            return
        self.sfx_events.append({
            "time_offset": delay,
            "preset":      name,
            "params":      params or {}
        })

    def enter_zone(self, zone: str, presets: set[str]):
        if self.mute==True:
            if old := self.tasks.pop(zone, None): old.cancel()
            self.client.stop_all()
            return
        if old := self.tasks.pop(zone, None): old.cancel()
        self.zones[zone] = presets
        self.tasks[zone] = asyncio.run_coroutine_threadsafe(self._zone_block_loop(zone), self.client.loop)

    set_zone = enter_zone

    def leave_zone(self, zone: str):
        if fut := self.tasks.pop(zone, None): fut.cancel()
        self.zones.pop(zone, None)

    async def _zone_block_loop(self, zone: str):
        if self.mute==True:
            if old := self.tasks.pop(zone, None): old.cancel()
            self.client.stop_all()
            return
        beats, first = 8.0, True
        while True:
            try:
                if first:
                    mel = random.choice(list(self.compositor.melodies.keys()))
                    self.compositor.start(mel)
                    first = False
                    self.logger.info(f"[{zone}] starting melody '{mel}'")

                self._update_tempo(); self._update_energy()
                raw      = self.compositor.next_block_events(beats)
                parts_fx = self.arranger.prepare_block(beats=beats)

                # Remap each part to a random preset
                remapped = {random.choice(self.all_presets): cfg for cfg in parts_fx.values()}
                self.logger.debug(f"[{zone}] remapped parts→presets: {list(remapped)}")

                events = []
                # raw melody under 'lead'
                for ev in raw:
                    events.append({
                        "time_offset": ev["time"] * (60.0/self.tempo),
                        "preset":      "piano", # Changed "lead" to "piano"
                        "params":      {
                            "notes":     ev["notes"],
                            "durations": ev["durations"],
                            "intensity": ev["intensity"],
                            "tempo":     self.tempo  # Pass current tempo
                        }
                    })
                # orchestration
                for p, cfg in remapped.items():
                    events.append({"time_offset": 0.0, "preset": p, "params": cfg})
                # queued SFX
                events.extend(self.sfx_events)
                self.sfx_events.clear()

                events.sort(key=lambda e: e["time_offset"])
                self.client.play_block(events)
                self.logger.debug(f"[{zone}] play_block → {len(events)} events")

                await asyncio.sleep(beats * (60.0/self.tempo))

            except asyncio.CancelledError:
                break
            except Exception as e:
                self.logger.warning(f"Error in zone '{zone}': {e}")

    def _update_tempo(self):
        if self.mute==True:
            if old := self.tasks.pop(zone, None): old.cancel()
            self.client.stop_all()
            return
        step = self.tempo * random.uniform(-0.07, 0.07)
        self.tempo = max(60.0, min(240.0, self.tempo + random.uniform(-step, step)))

    def _update_energy(self):
        if self.mute==True:
            if old := self.tasks.pop(zone, None): old.cancel()
            self.client.stop_all()
            return
        now, dt = time.time(), time.time() - self._last_time
        beat_time = 60.0/self.tempo
        self._phase   = (self._phase + dt/(32*beat_time)) % 1.0
        self.energy   = 0.7 + 0.3 * (__import__("math").sin(2*__import__("math").pi*self._phase))
        self._last_time = now
