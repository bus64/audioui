# File: src/performances/async_hyper_manager.py © 2025 projectemergence. All rights reserved.
import os
import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from typing import Optional

class AsyncHyperManager:
    """
    Async “hyper” manager for tasks:
      - pure coroutines run on the loop
      - sync callables auto-offloaded to thread/process pools
      - max concurrency via semaphore
      - dynamic start/stop/list/cancel/await
    """
    def __init__(self,
                 *,
                 max_threads: int | None = None,
                 max_processes: int | None = None,
                 loop: Optional[asyncio.AbstractEventLoop] = None,
                 logger: logging.Logger | None = None):
        # allow caller to supply a fresh loop
        self.loop = loop or asyncio.get_event_loop()
        self.logger = logger or logging.getLogger(__name__)
        cpu = os.cpu_count() or 1
        self.thread_executor  = ThreadPoolExecutor(max_threads or cpu)
        self.process_executor = ProcessPoolExecutor(max_processes or cpu)
        # bind our semaphore to this loop
        self.semaphore = asyncio.Semaphore(max_threads or cpu)
        self._tasks: dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def schedule(self,
                       name: str,
                       fn: callable,
                       *args,
                       kind: str = "thread",
                       **kwargs) -> None:
        async with self._lock:
            if name in self._tasks:
                self.logger.warning(f"Task '{name}' exists, skipping")
                return
            await self.semaphore.acquire()
            if asyncio.iscoroutinefunction(fn):
                task = self.loop.create_task(self._runner(name, fn, *args, **kwargs))
            else:
                pool = self.thread_executor if kind == "thread" else self.process_executor
                task = self.loop.create_task(
                    self._runner(name,
                                 lambda *a, **k: self.loop.run_in_executor(pool, functools.partial(fn, *a, **k)),
                                 *args, **kwargs)
                )
            self._tasks[name] = task

    async def _runner(self, name: str, coro_fn: callable, *args, **kwargs):
        self.logger.info(f"▶ Starting '{name}'")
        try:
            return await coro_fn(*args, **kwargs)
        except asyncio.CancelledError:
            self.logger.info(f"✖ Cancelled '{name}'")
            raise
        except Exception as e:
            self.logger.exception(f"‼ Exception in '{name}': {e}")
        finally:
            async with self._lock:
                self._tasks.pop(name, None)
                self.semaphore.release()
                self.logger.info(f"✔ Finished '{name}'")

    def list_tasks(self) -> list[str]:
        return list(self._tasks.keys())

    async def cancel(self, name: str) -> None:
        async with self._lock:
            t = self._tasks.get(name)
            if t:
                t.cancel()

    async def wait(self, name: str) -> None:
        t = self._tasks.get(name)
        if t:
            await t

    async def shutdown(self) -> None:
        """Cancel & await all tasks, then tear down executors."""
        async with self._lock:
            for t in self._tasks.values():
                t.cancel()
        await asyncio.gather(*self._tasks.values(), return_exceptions=True)
        self.thread_executor.shutdown(wait=False)
        self.process_executor.shutdown(wait=False)

    def close(self):
        """
        Synchronous cleanup:
          1) run shutdown coroutine to cancel & wait tasks
          2) stop the loop
        """
        # 1) shutdown async tasks & executors
        fut = asyncio.run_coroutine_threadsafe(self.shutdown(), self.loop)
        fut.result()
        # 2) stop the loop
        self.loop.call_soon_threadsafe(self.loop.stop)
