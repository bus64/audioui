#File:  audio/maestro/resource_aware_arrangement_engine.py © 2025 projectemergence. All rights reserved.
# File: src/core/audio/maestro/resource_aware_arrangement_engine.py © 2025 projectemergence
import time
import psutil
from collections import deque
from core.audio.maestro.arrangement_engine import ArrangementEngine

class ResourceAwareArrangementEngine(ArrangementEngine):
    def __init__(
        self, client,
        cpu_idle_threshold: float = 50.0,
        mem_max_threshold: float = 85.0,
        block_beats: float = 32.0,
        max_queue_size: int = 4,
        target_fps: float = 60.0
    ):
        super().__init__(client)
        self.cpu_idle_threshold = cpu_idle_threshold
        self.mem_max_threshold = mem_max_threshold
        self.block_beats = block_beats
        self.max_queue_size = max_queue_size
        self.block_queue = deque()

        # for tick-based correlation
        self.target_dt = 1.0 / target_fps
        self.last_tick = time.time()

    def _wait_for_resources(self):
        # Wait if CPU load or tick time too high
        while psutil.cpu_percent(interval=0.05) > self.cpu_idle_threshold:
            time.sleep(0.05)

        # Tick-time correlation
        current_tick = time.time()
        actual_dt = current_tick - self.last_tick
        self.last_tick = current_tick

        if actual_dt > 1.2 * self.target_dt:  # threshold at 120% of target frame time
            time.sleep(0.1)  # delay block prep if loop is behind

    def prepare_block(self, beats: float = None):
        beats = beats if beats else self.block_beats
        self._wait_for_resources()

        parts = super().prepare_block(beats)

        # Memory-aware trimming
        mem_usage = psutil.virtual_memory().percent
        if mem_usage > self.mem_max_threshold:
            keep = max(1, len(parts) // 2)
            parts = dict(list(parts.items())[:keep])

        # CPU-aware voice count scaling
        cpu_usage = psutil.cpu_percent(interval=None)
        max_voices = max(1, int(len(parts) * (1 - cpu_usage / 100)))
        if len(parts) > max_voices:
            parts = dict(list(parts.items())[:max_voices])

        self.block_queue.append(parts)

        # Maintain queue size
        while len(self.block_queue) > self.max_queue_size:
            self.block_queue.popleft()

    def get_next_block(self, beats: float = None):
        if not self.block_queue:
            self.prepare_block(beats)
        return self.block_queue.popleft()
