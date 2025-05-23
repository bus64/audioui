#File:  src/thread_manager.py © 2025 projectemergence. All rights reserved.
#File:  src/thread_manager.py © 2024 projectemergence. All rights reserved.
import sys
import threading
import queue
import logging
import multiprocessing
import time
import linecache

# Removed trace_lines and sys.settrace usage for cleaner execution.

class ThreadManager:
    """
    A generalized Thread Manager to supervise threaded tasks in your application.
    It can cap the maximum number of concurrent threads based on CPU core/thread count
    or run in single-thread mode. Tasks can be started immediately or queued if the limit
    is reached. Provides methods to start, stop, list, check, wait, clear, and log threads.
    """

    def __init__(self, single_thread=False, max_threads=None, logger=None):
        """
        :param single_thread: If True, forces only one thread to run at a time.
        :param max_threads: Maximum number of threads allowed at once. 
                            If None, this will default to the CPU count.
        :param logger: Provide a custom logger, else uses default logging.
        """
        self.logger = logger or logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)

        # If single-thread mode is requested, override everything to 1
        if single_thread:
            self.max_threads = 1
        else:
            # If max_threads is not given, fall back to the system CPU count
            self.max_threads = max_threads if max_threads else multiprocessing.cpu_count()

        self.threads = {}         # thread_name -> threading.Thread object
        self.thread_queue = queue.Queue()  # queue of tasks (thread_name, target, args, kwargs, daemon)
        self.thread_lock = threading.Lock()  # lock to protect shared resources

        # A simple sentinel to notify we have an available slot if the manager is not saturated
        self.available_slot = threading.Event()
        self.available_slot.set()  # initially, we assume we have a free slot to start at least one thread

    def _thread_worker(self, thread_name, target, args, kwargs):
        # Removed sys.settrace(None) call since tracing is disabled.
        try:
            self.logger.info(f"Thread '{thread_name}' started.")
            target(*args, **kwargs)
        except Exception as e:
            self.logger.exception(f"Exception in thread '{thread_name}': {e}")
        finally:
            self._cleanup_thread(thread_name)

    def _cleanup_thread(self, thread_name):
        """
        Internal method to remove the thread from the dictionary upon completion
        and then attempt to process any waiting tasks from the queue.
        """
        with self.thread_lock:
            if thread_name in self.threads:
                self.logger.info(f"Thread '{thread_name}' is completing cleanup.")
                del self.threads[thread_name]

            # Process the next task from the queue if any are waiting
            if not self.thread_queue.empty():
                next_thread = self.thread_queue.get_nowait()
                self._start_thread_internal(*next_thread)
            else:
                # If the queue is empty, set the available_slot to True
                self.available_slot.set()

    def _can_start_thread(self):
        """
        Check if we are below the max_threads limit.
        """
        with self.thread_lock:
            return len(self.threads) < self.max_threads

    def _start_thread_internal(self, thread_name, target, args, kwargs, daemon):
        """
        Internal method that actually starts the thread object.
        Assumes we have capacity or it will be queued again.
        """
        with self.thread_lock:
            if thread_name in self.threads:
                self.logger.warning(f"Thread '{thread_name}' already exists and is alive.")
                return

            # Create the actual thread
            thread = threading.Thread(
                target=self._thread_worker,
                args=(thread_name, target, args, kwargs),
                daemon=daemon
            )
            self.threads[thread_name] = thread
            thread.start()
            self.logger.debug(f"Started thread '{thread_name}' internally.")

            # If we've reached capacity, clear available_slot
            if len(self.threads) >= self.max_threads:
                self.available_slot.clear()

    def start_thread(self, thread_name, target, *args, daemon=False, **kwargs):
        """
        Public method to start a new thread.
        If maximum threads are running, it will queue the thread until a slot is available.
        """
        with self.thread_lock:
            # If already running, skip
            if thread_name in self.threads:
                self.logger.warning(f"Thread '{thread_name}' is already running.")
                return

            # If there's room to start a new thread
            if self._can_start_thread():
                self._start_thread_internal(thread_name, target, args, kwargs, daemon)
            else:
                # Otherwise, queue it
                self.thread_queue.put((thread_name, target, args, kwargs, daemon))
                self.logger.info(f"Queued thread '{thread_name}' (max capacity reached).")

    def stop_thread(self, thread_name, timeout=2):
        """
        Attempt to stop a thread by joining it (voluntary finish).
        This method depends on whether the target function can exit gracefully.
        """
        with self.thread_lock:
            if thread_name in self.threads:
                thread = self.threads[thread_name]
                if thread.is_alive():
                    self.logger.info(f"Joining thread '{thread_name}' with timeout={timeout}.")
                    thread.join(timeout=timeout)
                # After join, if it's still alive, there's no forced kill in pure Python threads
                if thread.is_alive():
                    self.logger.warning(f"Thread '{thread_name}' is still running after join.")
                else:
                    self.logger.info(f"Thread '{thread_name}' has stopped.")
                if thread_name in self.threads:
                    del self.threads[thread_name]

    def wait_for_thread(self, thread_name):
        """
        Block until the specified thread is finished.
        """
        thread = None
        with self.thread_lock:
            thread = self.threads.get(thread_name, None)
        if thread is not None:
            thread.join()
            self.logger.info(f"Thread '{thread_name}' has finished waiting.")

    def check_thread(self, thread_name):
        """
        Check if a thread is alive.
        """
        with self.thread_lock:
            thread = self.threads.get(thread_name)
            return thread.is_alive() if thread else False

    def list_threads(self):
        """
        List all thread names currently in the manager.
        """
        with self.thread_lock:
            return list(self.threads.keys())

    def list_thread_status(self):
        """
        Return a dictionary of thread_name -> bool (is_alive).
        """
        status = {}
        with self.thread_lock:
            for name, th in self.threads.items():
                status[name] = th.is_alive()
        return status

    def clear_all_threads(self):
        """
        Join and remove all threads from the manager.
        """
        with self.thread_lock:
            thread_names = list(self.threads.keys())
        for name in thread_names:
            self.stop_thread(name)
        self.logger.info("Cleared all threads from the manager.")

    def process_queue(self):
        """
        Attempt to process queued threads (if there's capacity).
        You can call this periodically or let the manager do it automatically upon thread completion.
        """
        # Keep pulling from the queue while we have capacity
        while not self.thread_queue.empty() and self._can_start_thread():
            with self.thread_lock:
                thread_info = self.thread_queue.get_nowait()
            self._start_thread_internal(*thread_info)

    def log_threads(self):
        """
        Helper to log the current threads and their statuses.
        """
        statuses = self.list_thread_status()
        self.logger.info("Current Threads:")
        for thread_name, alive in statuses.items():
            self.logger.info(f"  {thread_name}: {'Alive' if alive else 'Not Alive'}")

    def wait_for_all(self):
        """
        Wait for all threads currently in the manager to finish.
        """
        names = self.list_threads()
        for name in names:
            self.wait_for_thread(name)

    @staticmethod
    def get_cpu_count():
        """
        Returns the number of CPUs available on the system.
        """
        return multiprocessing.cpu_count()
