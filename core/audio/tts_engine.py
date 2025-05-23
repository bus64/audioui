# File: src/core/audio/tts_engine.py  © 2025 projectemergence. All rights reserved.

import asyncio
from typing import Optional

import numpy as np
from scipy.signal import resample
import sounddevice as sd

class TTSEngine:
    """
    Async TTS engine using Coqui VITS:
      • Lazy‐loads the model on first use
      • Offloads synthesis & playback to a ThreadPoolExecutor
    """
    def __init__(self,
                 model_name: str = "tts_models/en/vctk/vits",
                 speaker: str = "p291",
                 rate: float = 1.0,
                 pitch_shift: float = 0.0):
        self._model_name = model_name
        self._speaker = speaker
        self._rate = rate
        self._pitch_shift = pitch_shift
        self._tts: Optional["TTS"] = None

    async def _ensure_loaded(self):
        if self._tts is None:
            from TTS.api import TTS
            loop = asyncio.get_running_loop()
            self._tts = await loop.run_in_executor(
                None, lambda: TTS(self._model_name, progress_bar=False, gpu=False)
            )

    async def speak(self, text: str) -> None:
        """
        Asynchronously synthesize and play `text`.
        """
        await self._ensure_loaded()
        loop = asyncio.get_running_loop()

        # 1) synthesize off‐thread
        audio = await loop.run_in_executor(
            None,
            lambda: self._tts.tts(text=text, speaker=self._speaker, return_type="numpy")
        )

        # 2) optional rate change
        if self._rate != 1.0:
            audio = resample(audio, int(len(audio) / self._rate))

        # 3) play off‐thread
        def _play():
            sd.play(audio, samplerate=22050)
            sd.wait()

        await loop.run_in_executor(None, _play)
