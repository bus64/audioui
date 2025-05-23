#File:  src/performances/dirty_rect_manager.py © 2025 projectemergence. All rights reserved.
import pygame
from collections import deque

class DirtyRectManager:
    """
    Minimal API:
      • update()  – advance internal frame, rotate queues
      • add(r, p=0) – schedule rect r with optional priority p
      • draw(target, surf, pos=(0,0), p=0) – blit+add in one call
      • flush()   – pygame.display.update() on all due rects
    Everything else (buckets, history, frame-skip) is internal.
    """
    def __init__(self, frame_skip: int = 1, hold_frames: int = 1):
        self._fs = max(1, frame_skip)
        self._hg = max(0, hold_frames)
        self._buckets = [[] for _ in range(self._fs)]
        self._hist = deque(maxlen=self._hg + 1)
        for _ in range(self._hg + 1): self._hist.append([])
        self._fi = 0

    def update(self):
        """Rotate: move current bucket → history, clear it, advance frame index."""
        self._hist.append(self._buckets[self._fi])
        self._buckets[self._fi] = []
        self._fi = (self._fi + 1) % self._fs

    def add(self, rect: pygame.Rect, p: int = 0):
        """Schedule `rect` for redraw on frame (current + p) % frame_skip."""
        idx = (self._fi + p) % self._fs
        self._buckets[idx].append(rect)

    def draw(self, target: pygame.Surface, surf: pygame.Surface,
             pos: tuple[int,int]=(0,0), p: int = 0):
        """
        Blit `surf` onto `target` at `pos`, then add the resulting Rect().
        Optional `p` routes it into a future bucket.
        """
        r = target.blit(surf, pos)
        self.add(r, p)

    def flush(self):
        """Gather history + current bucket, issue a single pygame.display.update()."""
        rects = []
        for past in self._hist:
            rects.extend(past)
        rects.extend(self._buckets[self._fi])
        if rects:
            pygame.display.update(rects)
