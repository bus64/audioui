#File:  src/core/speech/speech_manager.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python3
"""
File: src/core/speech/speech_audio_manager.py
© 2024 projectemergence. All rights reserved.

Revised version to fix the issue where speech only works once. This version creates a persistent
pyttsx3 engine (instead of reinitializing it per utterance) and adds a longer delay before removing
temporary audio files to ensure the pyo server has sufficient time to load them.

Adoptez une vision tournée vers l’avenir!
"""

import pyttsx3
import queue
import random
import time
import os
import tempfile
from threading import Thread
from pyo import Server, SfPlayer, Harmonizer, Granulator, Freeverb, Disto, Degrade, Noise, ButLP

class SpeechManager:
    def __init__(self, default_voice_id=None, default_rate=175, default_volume=1.0,
                 sample_rate=44100, buffersize=512):
        self.default_rate = default_rate
        self.default_volume = default_volume
        self.default_voice_id = default_voice_id

        self.speech_queue = queue.Queue()

        self.engine = pyttsx3.init()
        self.engine.setProperty('rate', self.default_rate)
        self.engine.setProperty('volume', self.default_volume)
        if self.default_voice_id:
            self.engine.setProperty('voice', self.default_voice_id)

        self.tts_thread = Thread(target=self._run_tts_engine, daemon=True)
        self.tts_thread.start()

        self.server = Server(sr=sample_rate, buffersize=buffersize, nchnls=2).boot()
        self.server.start()

        self.current_player = None

    def _determine_style(self, text, context):
        if context.get("modem", False):
            return "modem56k"
        if context.get("idle", False):
            return "humming"
        word_count = len(text.split())
        style = "robot" if word_count > 2 else "short"
        if word_count >= 10:
            style = "long"
        if context.get("order_direction", 1) < 0:
            style = "trembling"
        elif context.get("order_direction", 1) > 0:
            style = "robot"
        if abs(context.get("global_angle", 0)) > 1.0:
            style = "calabiyau"
        if context.get("frame_counter", 0) % context.get("num_frames_per_transition", 128) < 10:
            style = "robot"
        return style

    def _transform_text_for_effects(self, text, style):
        if style in ["trembling", "long", "modem56k"]:
            return " ".join(word[0] + "-" + word if len(word) > 3 and random.random() < 0.2 else word
                            for word in text.split())
        return text

    def _apply_tts_style(self, engine, style, text):
        voices = engine.getProperty('voices')
        if style == "robot":
            robot_voice = next((v.id for v in voices if "robot" in v.name.lower()), (voices[0].id if voices else None))
            engine.setProperty('voice', robot_voice)
            engine.setProperty('rate', 150)
        elif style == "short":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 200)
        elif style == "long":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 170)
        elif style == "calabiyau":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 160)
        elif style == "trembling":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 180)
        elif style == "repeat":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 180)
        elif style == "humming":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 90)
            engine.setProperty('volume', 0.8)
            text = "♪ mmm mmm mmm ♪"
        elif style == "modem56k":
            engine.setProperty('voice', voices[0].id if voices else self.default_voice_id)
            engine.setProperty('rate', 140)
            engine.setProperty('volume', 0.9)
        else:
            engine.setProperty('voice', self.default_voice_id if self.default_voice_id else (voices[0].id if voices else ""))
            engine.setProperty('rate', self.default_rate)
            engine.setProperty('volume', self.default_volume)
        return text

    def _safe_remove(self, filename, attempts=10, delay=0.5):
        for _ in range(attempts):
            try:
                os.remove(filename)
                return
            except Exception:
                time.sleep(delay)
        print(f"Warning: Could not remove temporary file {filename} after {attempts} attempts.")

    def _play_audio(self, filename, context):
        if self.current_player is not None:
            self.current_player.stop()
        snd = SfPlayer(filename, speed=1, loop=False)
        style = self._determine_style("", context)
        pitch_shift = 4 if context.get("global_angle", 0) > 1.0 else -4 if context.get("global_angle", 0) < -1.0 else 0
        if pitch_shift:
            snd = Harmonizer(snd, transpo=pitch_shift)
        if context.get("idle", False):
            snd = Granulator(snd, grainSize=0.05, overlap=0.3, pitch=1.0, mul=0.8)
        rev_amount = 0.3 if context.get("order_direction", 1) > 0 else 0.7
        proc = Freeverb(snd, size=rev_amount, bal=0.4)
        if style == "modem56k":
            proc = Disto(proc, drive=0.8, slope=0.5, mul=0.8)
            proc = Degrade(proc, bitdepth=8, srscale=0.5)
            proc = proc + Noise(mul=0.05)
            proc = ButLP(proc, freq=3000)
        self.current_player = proc
        proc.out()
        print(f"Playing audio from {filename} with style '{style}'.")

    def _run_tts_engine(self):
        while True:
            try:
                item = self.speech_queue.get(block=True)
                if item is None:
                    break
                text, context = item
                if text == "__STOP__":
                    self.engine.stop()
                    if self.current_player is not None:
                        self.current_player.stop()
                    continue
                engine = self.engine
                engine.setProperty('rate', self.default_rate)
                engine.setProperty('volume', self.default_volume)
                if self.default_voice_id:
                    engine.setProperty('voice', self.default_voice_id)
                style = self._determine_style(text, context)
                text = self._transform_text_for_effects(text, style)
                text = self._apply_tts_style(engine, style, text)
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                    temp_filename = tmp.name
                engine.save_to_file(text, temp_filename)
                engine.runAndWait()
                self._play_audio(temp_filename, context)
                time.sleep(0.5)
                self._safe_remove(temp_filename)
                print(f"Utterance '{text}' processed.")
            except queue.Empty:
                continue

    def speak(self, text, context=None):
        if context is None:
            context = {}
        self.speech_queue.put((text, context))
        print(f"Queued text: {text}")

    def stop_speaking(self):
        try:
            while True:
                self.speech_queue.get_nowait()
        except queue.Empty:
            pass
        self.speech_queue.put(("__STOP__", {}))
        print("Stop command issued.")

    def shutdown(self):
        self.speech_queue.put(None)
        self.tts_thread.join(timeout=2)
        self.server.stop()
        self.server.shutdown()
        print("Shutdown complete.")
