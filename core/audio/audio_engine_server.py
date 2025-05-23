# File: src/core/audio/audio_engine_server.py  © 2025 projectemergence. All rights reserved.

import asyncio
import os
import time
import tempfile
import logging
from typing import Any, Dict,Literal
from core.audio.audio_presets_registry import registry
from core.audio.presets.base_preset               import BasePreset

import pyttsx3
from pyo import Server, SfPlayer
import pyo.lib._core as _pc

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
TTSProp = Literal["voice", "rate", "volume"]

# ─── PortAudio race‐fix ───────────────────────────────────────────────────────
_tmp = tempfile.mkdtemp(prefix="pyo_temp_")
os.environ.update({"TMP": _tmp, "TEMP": _tmp})
_orig_pa = _pc.pa_get_default_devices_from_host
def _safe_pa(host):
    try:
        return _orig_pa(host)
    except PermissionError as e:
        if e.errno != os.errno.EACCES:
            raise
        time.sleep(0.2)
        return _orig_pa(host)
_pc.pa_get_default_devices_from_host = _safe_pa

def log(msg: str) -> None:
    print(f"[AudioEngineServer] {msg}", flush=True)

class AudioEngine:
    """
    Asyncio-based AudioEngineServer with:
      • central PresetRegistry for hot-reload + introspection
      • pyo-based TTS & block playback
      • graceful shutdown on 'stop'
    """
    def __init__(self,
                 cmd_queue: asyncio.Queue,
                 ack_queue: asyncio.Queue | None = None,
                 *,
                 default_voice_id=None,
                 default_rate: int = 175,
                 default_volume: float = 1.0,
                 sample_rate: int = 44_100,
                 buffersize: int = 1024):
        self.cmd_queue      = cmd_queue
        self.ack_queue      = ack_queue
        self.shutdown_event = asyncio.Event()
        self._voices        = []
        self.active_presets = []
        self.current_melody = None
        self.CLEANUP_INTERVAL = 1.0  # seconds
        self._cleanup_task = None

        logger.info("initialising AudioEngineServer")

        # ─── TTS engine ───────────────────────────────────────────────────────
        self._tts = pyttsx3.init()
        self._tts.setProperty("rate", default_rate)
        self._tts.setProperty("volume", default_volume)
        if default_voice_id:
            self._tts.setProperty("voice", default_voice_id)
        logger.info("pyttsx3 TTS ready")

        # ─── Pyo server ───────────────────────────────────────────────────────
        self.server = Server(sr=sample_rate, buffersize=buffersize, nchnls=2).boot().start()
        logger.info(f"pyo server up (sr={sample_rate}, bs={buffersize})")

        # ─── Central PresetRegistry ───────────────────────────────────────────
        self.preset_map  = registry.preset_map
        self.presets_sig = registry.presets_sig
        logger.info("presets loaded → " + ", ".join(sorted(self.preset_map)))
        logger.debug("PRESET_MAP keys: %s", list(self.preset_map.keys()))
        logger.debug("PRESETS_SIG params: %s",
                     {k: list(sig.parameters.keys()) for k, sig in self.presets_sig.items()})
        self.mute=False

    async def _cleanup_stopped_presets(self):
        logger.debug("Running _cleanup_stopped_presets")
        # Iterate over a copy for safe removal
        for preset_info in self.active_presets[:]: 
            instance = preset_info.get("instance")
            if not instance:
                logger.warning("Preset_info missing 'instance': %s. Removing.", preset_info.get('name', 'Unknown'))
                try:
                    self.active_presets.remove(preset_info)
                except ValueError: # Should not happen if iterating over a copy and item is from original
                    logger.warning("Failed to remove preset_info that was already missing instance.")
                continue

            try:
                # Handle lists of Faders (e.g., from melody playback in BasePreset)
                if isinstance(instance, list):
                    if not instance: # Empty list
                        logger.info("Preset '%s' instance is an empty list. Removing.", preset_info.get("name", "Unknown"))
                        if preset_info in self.active_presets:
                             self.active_presets.remove(preset_info)
                        continue # Skip to next preset_info

                    all_faders_done = True 
                    fader_found = False
                    for fader_obj in instance: # Renamed to fader_obj to avoid conflict with pyo.Fader if imported directly
                        if hasattr(fader_obj, 'isDone') and callable(fader_obj.isDone):
                            fader_found = True
                            if not fader_obj.isDone():
                                all_faders_done = False
                                break 
                        # else: object in list is not a Fader or doesn't have isDone; ignore for this check.
                    
                    if fader_found and all_faders_done:
                        logger.info("Preset '%s' (melody/sequence) all faders are done. Removing.", preset_info.get("name", "Unknown"))
                        if preset_info in self.active_presets:
                            self.active_presets.remove(preset_info)
                    elif not fader_found:
                        # This case means the list didn't contain any objects that looked like Faders.
                        # This might be an unexpected state, so log it.
                        logger.debug("Preset '%s' instance is a list, but contains no faders with isDone method. Skipping cleanup for this item.", preset_info.get("name", "Unknown"))
                    else:
                        # If faders were found but not all are done, keep the preset active.
                        logger.debug("Preset '%s' (melody/sequence) still has active faders. Keeping.", preset_info.get("name", "Unknown"))
                    # Important: Continue to next preset_info after handling a list instance
                    continue 

                # Existing logic for single PyoObject instances
                if hasattr(instance, 'isPlaying') and callable(instance.isPlaying):
                    if not instance.isPlaying():
                        logger.info("Preset '%s' is no longer playing. Removing.", preset_info.get("name", "Unknown"))
                        if preset_info in self.active_presets:
                            self.active_presets.remove(preset_info)
                    # else: preset is playing, keep it
                elif hasattr(instance, 'getIsPlaying') and callable(instance.getIsPlaying): # Alternative common name
                    if not instance.getIsPlaying():
                        logger.info("Preset '%s' (using getIsPlaying) is no longer playing. Removing.", preset_info.get("name", "Unknown"))
                        if preset_info in self.active_presets:
                            self.active_presets.remove(preset_info)
                    # else: preset is playing, keep it
                else:
                    # If it's not a list and doesn't have a known playing check, log it.
                    logger.debug("Preset '%s' object type %s does not have a recognized isPlaying/getIsPlaying method or is not a list. Skipping cleanup for this item.", preset_info.get("name", "Unknown"), type(instance).__name__)

            except AttributeError as e:
                # This catch block is primarily for the case where 'instance' was expected to be a Pyo object 
                # but 'isPlaying' or 'getIsPlaying' was missing, or if 'isDone' was missing on a list item.
                logger.error(f"AttributeError checking preset {preset_info.get('name', 'Unknown')}: {e}. This might indicate an unexpected instance type or structure. Removing from active list for safety.")
                if preset_info in self.active_presets: # Check if not already removed
                    self.active_presets.remove(preset_info)
            except Exception as e:
                logger.error(f"Error checking if preset {preset_info.get('name', 'Unknown')} is playing: {e}. Removing from active list.")
                if preset_info in self.active_presets: # Check if not already removed
                     self.active_presets.remove(preset_info)
        logger.debug("Finished _cleanup_stopped_presets. Active presets count: %d", len(self.active_presets))


    async def _periodic_cleanup_task(self):
        while not self.shutdown_event.is_set():
            await asyncio.sleep(self.CLEANUP_INTERVAL)
            if self.shutdown_event.is_set(): # Re-check after sleep before cleanup
                break
            logger.debug("Periodic cleanup task waking up.")
            await self._cleanup_stopped_presets()

    async def run(self):
        logger.info("server run loop started")
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup_task())

        while not self.shutdown_event.is_set():
            try:
                cmd = await self.cmd_queue.get()
                logger.debug("run loop received cmd: %s", cmd)
                try:
                    await self._handle(cmd)
                finally:
                    self.cmd_queue.task_done()
            except asyncio.CancelledError:
                logger.info("Main run loop task cancelled.")
                break # Exit loop if server task is cancelled

        logger.info("Shutting down server...")
        # Stop and cleanup the periodic task
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                logger.info("Preset cleanup task successfully cancelled.")
            except Exception as e:
                logger.error(f"Exception during cleanup task shutdown: {e}")
        
        # separate calls to avoid chaining None
        self.server.stop()
        self.server.shutdown()
        logger.info("server shut down")

    async def _handle(self, cmd: Dict[str, Any]) -> None:
        logger.debug("handling command: %s", cmd)
        match cmd.get("cmd"):
            case "play_preset":
                await self._handle_play_preset(cmd)
            case "play_block":
                await self._handle_play_block(cmd)
            case "play_tts":
                self._handle_play_tts(cmd)
            case "set_tts":
                self._handle_set_tts(cmd)
            case "play_tts_direct":
                self._handle_play_tts_direct(cmd)
            case "get_active_presets":
                await self._handle_get_active_presets(cmd)
            case "get_current_melody":
                await self._handle_get_current_melody(cmd)
            case "stop":
                logger.debug("stop → shutting down")
                self.shutdown_event.set()
            case other:
                logger.warning("unhandled command: %r", other)

    async def _handle_get_active_presets(self, cmd: Dict[str, Any]) -> None:
        if not self.ack_queue:
            logger.warning("ack_queue not available for get_active_presets")
            return
        serialized_presets = []
        for preset_info in self.active_presets:
            serialized_presets.append({
                "name": preset_info["name"],
                "params": preset_info["params"],
                "instance": str(preset_info["instance"])  # Convert PyoObject to string
            })
        await self.ack_queue.put({"ack": "get_active_presets", "data": serialized_presets})

    async def _handle_get_current_melody(self, cmd: Dict[str, Any]) -> None:
        if not self.ack_queue:
            logger.warning("ack_queue not available for get_current_melody")
            return
        await self.ack_queue.put({"ack": "get_current_melody", "data": self.current_melody})

    async def _handle_play_preset(self, cmd: Dict[str, Any]) -> None:
        name, params = cmd["preset"], cmd.get("params", {})
        logger.debug("  play_preset → name=%s  params=%s", name, params)

        cls = self.preset_map.get(name)
        if not cls:
            logger.warning("  unknown preset '%s'", name)
            return

        allowed = set(self.presets_sig[name].parameters) - {"self", "args", "kwargs"}
        init_args = {k: v for k, v in params.items() if k in allowed}
        logger.debug("  allowed args=%s  init_args=%s", allowed, init_args)

        t0 = time.perf_counter()
        obj = cls(**init_args).play()
        self._voices.append(obj)
        self.active_presets.append({"name": name, "params": init_args, "instance": obj})
        dt = (time.perf_counter() - t0) * 1000
        logger.info("▶ %s %s (%.1f ms)", name, init_args, dt)

        if self.ack_queue:
            await self.ack_queue.put({"ok": True, "preset": name, "ts": time.time()})

    async def _handle_play_block(self, cmd: Dict[str, Any]) -> None:
        events = cmd.get("events", [])
        self.current_melody = cmd.get("name", "custom_melody")
        logger.debug("  play_block → scheduling %d events for melody: %s", len(events), self.current_melody)
        asyncio.create_task(self._process_block_events(events))

    def _handle_play_tts(self, cmd: Dict[str, Any]) -> None:
        text = cmd.get("text", "")
        logger.debug("  play_tts → text=%r", text)
        if not text:
            return

        fn = tempfile.mktemp(suffix=".wav")
        self._tts.save_to_file(text, fn)
        self._tts.runAndWait()
        SfPlayer(fn, loop=False).out()

    def _handle_play_tts_direct(self, cmd: Dict[str, Any]) -> None:
        text = cmd.get("text", "")
        logger.debug("  play_tts_direct → text=%r", text)
        if not text:
            return
        self._tts.say(text)
        #self._tts.runAndWait()

    def _handle_set_tts(self, cmd: Dict[str, Any]) -> None:
        """
        Update only those TTS properties that are provided and differ
        from the current settings.
        Supports:
          - 'rate'   (int)
          - 'volume' (float 0.0–1.0)
          - 'voice'  (either an int index into voices[] or a voice-id string)
        """
        # cache the voices list once (for index→id translation)
        voices_list = self._tts.getProperty('voices')

        for prop in ("rate", "volume", "voice"):
            # skip if not provided
            if prop not in cmd:
                continue

            new_val = cmd[prop]
            if new_val is None:
                continue

            if prop == "voice":
                # allow passing an index or a direct id
                if isinstance(new_val, int):
                    try:
                        new_id = voices_list[new_val].id
                    except (IndexError, AttributeError):
                        logger.warning("Invalid voice index: %r", new_val)
                        continue
                else:
                    new_id = new_val

                current = self._tts.getProperty("voice")
                if new_id != current:
                    self._tts.setProperty("voice", new_id)
                    logger.info("TTS property voice set to %s", new_id)

            else:
                # 'rate' or 'volume'
                current = self._tts.getProperty(prop)
                if new_val != current:
                    self._tts.setProperty(prop, new_val)
                    logger.info("TTS property %s set to %s", prop, new_val)


    async def _process_block_events(self, events: list[dict]):
        logger.debug("process_block_events start: %s", events)
        loop  = asyncio.get_running_loop()
        start = loop.time()

        logger.info(f"_process_block_events: Received {len(events)} events. Block start time: {start}, Loop time now: {loop.time()}")
        logger.debug(f"_process_block_events: Full events list: {events}")

        for ev in sorted(events, key=lambda e: e["time_offset"]):
            current_loop_time = loop.time()
            sleep_duration = max(0, (start + ev["time_offset"]) - current_loop_time)
            logger.info(f"  Processing event: {ev.get('preset')} at offset {ev['time_offset']:.3f}s. Start_block_time: {start:.3f}, current_loop_time: {current_loop_time:.3f}. Calculated sleep: {sleep_duration:.3f}s")
            logger.debug("  next event: %s", ev) # Retained original debug log for full event details
            await asyncio.sleep(sleep_duration)

            name, params = ev["preset"], ev.get("params", {})
            logger.debug("    firing preset '%s'  raw params=%s", name, params)

            cls = self.preset_map.get(name)
            if not cls:
                logger.warning("    [play_block] unknown preset '%s'", name)
                continue

            allowed = set(self.presets_sig[name].parameters) - {"self", "args", "kwargs"}
            pr_args = {k: v for k, v in params.items() if k in allowed}
            meta    = {k: v for k, v in params.items() if k not in allowed}
            logger.debug("    split → pr_args=%s  meta=%s", pr_args, meta)

            chain = cls(**pr_args).play()
            self._voices.append(chain) # Keep track of the PyoObject or list of Faders
            logger.info(f"    Fired preset {name}. Returned chain: {type(chain)}. Loop time after play: {loop.time():.3f}")
            # Original log line for play_block kept for consistency, though new one is more detailed for this purpose
            logger.info("▶ [play_block] %s %s @ %.2fs", name, pr_args, ev["time_offset"])


            if gain := meta.get("gain_db"):
                logger.debug("      applying gain_db=%.2f", gain)
                for node in getattr(chain, "values", lambda: [])():
                    try: node.mul *= 10 ** (gain/20)
                    except: pass

            if meta.get("enable_reverb"):
                logger.debug("      applying reverb")
                from pyo import Freeverb
                for sig in getattr(chain, "values", lambda: [])():
                    try: Freeverb(sig, size=0.8, bal=0.35).out()
                    except: pass

            if meta.get("enable_chorus"):
                logger.debug("      applying chorus")
                from pyo import Chorus
                for sig in getattr(chain, "values", lambda: [])():
                    try: Chorus(sig, depth=0.5, feedback=0.25, bal=0.5).out()
                    except: pass
        logger.info(f"_process_block_events: Finished processing all events. Loop time at end: {loop.time()}")
