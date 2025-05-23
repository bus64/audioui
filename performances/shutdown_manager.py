#File:  src/performances/shutdown_manager.py © 2025 projectemergence. All rights reserved.
import os
import sys
import shutil
import logging
import multiprocessing
import signal
import pygame
import time

# --- Cache clearing functionality ---
def clear_python_cache():
    """
    Recursively remove __pycache__ directories and .pyc files
    from the current working directory.
    """
    cwd = os.getcwd()
    for root, dirs, files in os.walk(cwd):
        for d in dirs:
            if d == '__pycache__':
                cache_dir = os.path.join(root, d)
                try:
                    shutil.rmtree(cache_dir)
                    logging.debug(f"Deleted cache directory: {cache_dir}")
                except Exception as e:
                    logging.warning(f"Error deleting cache directory {cache_dir}: {e}")
        for f in files:
            if f.endswith('.pyc'):
                file_path = os.path.join(root, f)
                try:
                    os.remove(file_path)
                    logging.debug(f"Deleted cache file: {file_path}")
                except Exception as e:
                    logging.warning(f"Error deleting cache file {file_path}: {e}")

def clear_all_caches(is_executable: bool):
    """
    Clears python caches and resets the log file.
    """
    clear_python_cache()
    log_file_path = 'dev_app.log'
    try:
        # Overwrite log file to clear it out.
        # with open(log_file_path, 'w'):
        #     pass
        logging.debug(f"Cleared log file: {log_file_path}")
    except Exception as e:
        logging.warning(f"Error clearing log file {log_file_path}: {e}")

def is_running_as_executable() -> bool:
    """
    Determine if the application is running as a bundled executable.
    """
    return getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')


# --- Graceful shutdown functionality ---
def graceful_shutdown(thread_manager, audio_client):
    """
    Gracefully shutdown the application by:
      - Stopping the audio engine.
      - Joining managed threads.
      - Shutting down any physics solver executor.
      - Terminating and killing active multiprocess children.
      - Clearing caches and quitting pygame.
      - Exiting the application.
    """
    logging.info("Initiating graceful shutdown...")

    # 1) Stop the audio engine client.
    try:
        audio_client.stop()
        logging.info("Audio engine client stopped gracefully.")
    except Exception as e:
        logging.warning(f"Error stopping audio engine client: {e}")

    # 2) Join managed threads.
    try:
        # Wait for each thread to finish gracefully
        for thread_name in thread_manager.list_threads():
            thread_manager.wait_for_thread(thread_name)
        logging.info("All managed threads have been joined.")
    except Exception as e:
        logging.warning(f"Error joining threads in thread_manager: {e}")

    # 3) Shutdown any custom executors (e.g., physics solver).
    try:
        from core.inventory.melt.physics_solver import shutdown_solver_executor
        shutdown_solver_executor()
        logging.info("Physics solver executor shut down.")
    except ImportError:
        # No physics solver module, ignore
        pass
    except Exception as e:
        logging.warning(f"Error shutting down solver executor: {e}")

    # 4) Ensure proper file permissions and delete problematic file
    try:
        file_path = 'C:\\Users\\lierm\\pa_retrieve_host_apis'
        # Change permissions to allow deletion
        os.chmod(file_path, 0o777)  # Grant full permissions
        os.remove(file_path)  # Delete the file
        logging.info(f"Deleted file {file_path} after changing permissions.")
    except Exception as e:
        logging.warning(f"Error deleting file {file_path}: {e}")

    # 5) Terminate and kill any active multiprocessing children.
    active = multiprocessing.active_children()
    if active:
        logging.info(f"Found {len(active)} active child process(es). Terminating...")
        for proc in active:
            try:
                proc.terminate()
                logging.info(f"Terminated child process pid={proc.pid}")
            except Exception as e:
                logging.warning(f"Error terminating process pid={proc.pid}: {e}")
        # Wait briefly and then force-kill remaining alive processes
        for proc in active:
            proc.join(timeout=2)
            if proc.is_alive():
                try:
                    proc.kill()
                    logging.info(f"Killed child process pid={proc.pid}")
                except Exception as e:
                    logging.warning(f"Failed to kill process pid={proc.pid}: {e}")
    else:
        logging.info("No active multiprocessing child processes found.")

    # 6) Clear caches and logs.
    clear_all_caches(is_executable=is_running_as_executable())

    # 7) Quit pygame and exit immediately.
    try:
        pygame.quit()
    except Exception as e:
        logging.warning(f"Error quitting pygame: {e}")
    sys.exit(0)



