# File: src/core/audio/audio_engine_client.py  © 2025 projectemergence. All rights reserved.

import threading
import asyncio
import logging
import psutil, os, sys
from core.audio.audio_engine_server import AudioEngine, log as server_log
from core.audio.maestro.audio_maestro import Maestro

class AudioEngineClient:
    """
    Asyncio‐based AudioEngineClient with its own event loop:

      • Dedicated asyncio loop in a daemon thread  
      • asyncio.Queue for commands and acknowledgements  
      • Synchronous API: play_preset, play_block, schedule_preset, stop_preset, stop_all, list_scheduled, stop
    """
    def __init__(self, *, debug: bool = True):
        # — Logging setup —
        self.logger = logging.getLogger(__name__)
        if debug and not logging.getLogger().handlers:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s %(levelname)s:%(name)s:%(message)s",
            )

        # — Start a private asyncio loop in a background thread —
        self.loop = asyncio.new_event_loop()
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()

        # — Finish async init on that loop —
        init_fut = asyncio.run_coroutine_threadsafe(self._init_async(), self.loop)
        init_fut.result()  # block until ready

    def _run_loop(self):
        proc = psutil.Process()
        try:
            if sys.platform == "win32":
                proc.nice(psutil.IDLE_PRIORITY_CLASS)
            else:
                os.nice(10)
        except Exception:
            print("\n ################################################################################ \nIssue setting thread priority \n ################################################################################\n")
            pass
        
        asyncio.set_event_loop(self.loop)
        self.loop.run_forever()

    async def _init_async(self):
        # Queues for command/ack exchange
        self.cmd_queue: asyncio.Queue[dict] = asyncio.Queue()
        self.ack_queue: asyncio.Queue[dict] = asyncio.Queue()

        # Track scheduled presets so we can cancel them later
        self._sched: dict[str, asyncio.Future] = {}

        # Instantiate the server engine on this loop
        self.engine = AudioEngine(
            cmd_queue=self.cmd_queue,
            ack_queue=self.ack_queue
        )
        # Kick off the server’s asyncio run() coroutine
        self.loop.create_task(self.engine.run())

        # Instantiate Maestro
        self.maestro = Maestro(self)
        self.maestro.mute = False
        print(f"[AudioClient]Mute is {self.maestro.mute}")
    def play_preset(self, preset: str, **params) -> None:
        if self.maestro.mute==True:
            self.stop_all()
            return
        """
        Enqueue a 'play_preset' command. Non‐blocking.
        """
        asyncio.run_coroutine_threadsafe(
            self.cmd_queue.put({"cmd": "play_preset", "preset": preset, "params": params}),
            self.loop
        )
        self.logger.info(f"▶ play_preset {preset} {params}")

    def play_block(self, events: list[dict]) -> None:
        if self.maestro.mute==True:
            self.stop_all()
            return
        """
        Enqueue a list of events:
        - each event is {"time_offset": float, "preset": str, "params": dict}
        """
        asyncio.run_coroutine_threadsafe(
         self.cmd_queue.put({"cmd": "play_block", "events": events}),
         self.loop
        )
        self.logger.info(f"▶ play_block with {len(events)} events")

    def stop_preset(self, preset: str, *, fade: float = 1.0) -> None:
        """
        Fade‐out a single preset and cancel its scheduler.
        """
        asyncio.run_coroutine_threadsafe(
            self.cmd_queue.put({
                "cmd": "play_preset",
                "preset": preset,
                "params": {"intensity": 0, "fade": fade}
            }),
            self.loop
        )
        fut = self._sched.pop(preset, None)
        if fut and not fut.cancelled():
            fut.cancel()
        self.logger.info(f"✕ stopped preset {preset} (fade={fade}s)")

    def stop_all(self, *, fade: float = 1.0) -> None:
        """
        Stop all playing & scheduled presets.
        """
        for p in list(self._sched):
            self.stop_preset(p, fade=fade)


    def shutdown(self) -> None:
        """
        Gracefully shut down the server loop and its thread.
        """
        # 1) tell the engine to stop
        asyncio.run_coroutine_threadsafe(self.cmd_queue.put({"cmd": "stop"}), self.loop).result()
        # 2) stop the loop & join thread
        self.loop.call_soon_threadsafe(self.loop.stop)
        self._thread.join(timeout=2)
        self.logger.info("shutdown complete")

    def stop(self) -> None:
        """
        Alias for shutdown(), for legacy callers.
        """
        self.shutdown()

    async def _get_active_presets_async(self):
        await self.cmd_queue.put({"cmd": "get_active_presets"})
        # TODO: Implement a more robust ack matching system if needed
        # For now, assume the next item in ack_queue is the response
        response = await self.ack_queue.get()
        if response and response.get("ack") == "get_active_presets":
            return response.get("data")
        else:
            self.logger.error(f"Unexpected or missing ack for get_active_presets: {response}")
            return None

    def get_active_presets(self) -> list | None:
        """
        Retrieves the list of active presets from the audio engine.
        Blocks until the response is received.
        """
        if not self.loop.is_running():
            self.logger.error("Asyncio loop is not running. Cannot get active presets.")
            return None
        future = asyncio.run_coroutine_threadsafe(self._get_active_presets_async(), self.loop)
        try:
            return future.result(timeout=5)  # Add a timeout for safety
        except Exception as e:
            self.logger.error(f"Error getting active presets: {e}")
            return None

    async def _get_current_melody_async(self):
        await self.cmd_queue.put({"cmd": "get_current_melody"})
        # TODO: Implement a more robust ack matching system if needed
        response = await self.ack_queue.get()
        if response and response.get("ack") == "get_current_melody":
            return response.get("data")
        else:
            self.logger.error(f"Unexpected or missing ack for get_current_melody: {response}")
            return None

    def get_current_melody(self) -> str | None:
        """
        Retrieves the current melody name from the audio engine.
        Blocks until the response is received.
        """
        if not self.loop.is_running():
            self.logger.error("Asyncio loop is not running. Cannot get current melody.")
            return None
        future = asyncio.run_coroutine_threadsafe(self._get_current_melody_async(), self.loop)
        try:
            return future.result(timeout=5)  # Add a timeout for safety
        except Exception as e:
            self.logger.error(f"Error getting current melody: {e}")
            return None
