#File:  src/performances/efficiencymeter.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python
"""
Efficiencymeter Full: Report-Only Version for Monitoring a Pygame-based Game

Features:
- Two modes: 'test' for a single run test, 'session' for long-run monitoring.
- Launches the game from src/main.py.
- Monitors process metrics: CPU usage, memory usage, GPU usage (using GPUtil if available).
- Monitors all cache folders (any directory with 'cache' in its name) within the src directory,
  tracking file count and cumulative size to help detect memory leaks.
- Does not display real-time graphs; instead, it generates a full report (printed to console and saved as CSV)
  after the game run ends or if a crash occurs.
- Scans all .py files in src for cyclomatic complexity using radon.
- Exports CSV reports for both runtime metrics and source code complexity.

Dependencies:
- psutil
- pandas
- radon
- GPUtil (install via 'pip install GPUtil' for GPU monitoring)
"""

import os
import sys
import time
import threading
import subprocess
import argparse
import psutil
import tracemalloc
import pandas as pd
from radon.complexity import cc_visit

try:
    import GPUtil
except ImportError:
    GPUtil = None

# Global dictionary to collect metrics over time.
metrics_data = {
    "timestamp": [],
    "cpu": [],
    "memory": [],
    "gpu": [],
    "cache_count": [],
    "cache_size": []
}

# Flag to control monitoring loop.
monitoring_active = True

def get_all_cache_metrics(src_dir):
    """
    Recursively scans the src directory for any folder with 'cache' in its name (case-insensitive)
    and aggregates the metrics:
      - total file count
      - total size in MB of all files within those folders.
    """
    total_size = 0
    file_count = 0
    for root, dirs, _ in os.walk(src_dir):
        for d in dirs:
            if "cache" in d.lower():
                cache_path = os.path.join(root, d)
                for r, _, files in os.walk(cache_path):
                    file_count += len(files)
                    for f in files:
                        f_path = os.path.join(r, f)
                        if os.path.isfile(f_path):
                            total_size += os.path.getsize(f_path)
    total_size_mb = total_size / (1024 * 1024)
    return file_count, total_size_mb

def monitor_process(pid, src_dir):
    """
    Monitors the process with the given PID:
      - CPU usage (with a 1-second sampling interval)
      - Memory usage (in MB)
      - GPU usage (in percent, if GPUtil is available)
      - Cache folder metrics aggregated from any directory with 'cache' in its name in src_dir
    Appends the results to the global metrics_data dictionary.
    """
    global monitoring_active
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        print("Error: Process not found!")
        return

    start_time = time.time()
    while monitoring_active and process.is_running():
        try:
            timestamp = time.time() - start_time
            cpu_usage = process.cpu_percent(interval=1)
            memory_usage = process.memory_info().rss / (1024 * 1024)  # MB

            # GPU monitoring using GPUtil (if available)
            if GPUtil:
                try:
                    gpus = GPUtil.getGPUs()
                    if gpus:
                        gpu_usage = sum(gpu.load for gpu in gpus) / len(gpus) * 100
                    else:
                        gpu_usage = 0
                except Exception as e:
                    print("GPU monitoring error:", e)
                    gpu_usage = 0
            else:
                gpu_usage = 0

            # Aggregate metrics from all cache folders found within src_dir.
            cache_count, cache_size = get_all_cache_metrics(src_dir)

            # Append current metrics.
            metrics_data["timestamp"].append(timestamp)
            metrics_data["cpu"].append(cpu_usage)
            metrics_data["memory"].append(memory_usage)
            metrics_data["gpu"].append(gpu_usage)
            metrics_data["cache_count"].append(cache_count)
            metrics_data["cache_size"].append(cache_size)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            print("Monitoring error:", e)
            break

def scan_complexity(src_dir):
    """
    Scans all Python (.py) files in src_dir recursively,
    computing the cyclomatic complexity using radon.
    Returns a list of tuples: (file_path, complexity).
    """
    complexities = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, 'r', encoding="utf-8") as f:
                        code = f.read()
                    file_complexity = sum(c.complexity for c in cc_visit(code))
                    complexities.append((file_path, file_complexity))
                except Exception as e:
                    complexities.append((file_path, f"Error: {e}"))
    return complexities

def run_game_and_monitor(src_dir):
    """
    Launches the game (src/main.py) and monitors its performance:
      - Starts a background thread to sample process, GPU, and cache folder metrics.
      - Waits for the game process to finish (or crash).
      - Returns the collected metrics.
    """
    global monitoring_active

    game_entry = os.path.join(src_dir, "main.py")
    if not os.path.isfile(game_entry):
        print("Error: main.py not found in the provided src directory!")
        sys.exit(1)

    # Start tracemalloc if needed (psutil already provides real-time memory usage)
    tracemalloc.start()

    # Launch the game process. Redirect output to DEVNULL to prevent blocking.
    game_process = subprocess.Popen(
        [sys.executable, game_entry],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    # Start a monitoring thread.
    monitor_thread = threading.Thread(target=monitor_process, args=(game_process.pid, src_dir), daemon=True)
    monitor_thread.start()

    # Wait for the game process to finish (or crash).
    try:
        game_process.wait()
    except KeyboardInterrupt:
        print("Game run interrupted by user.")
    finally:
        monitoring_active = False
        monitor_thread.join()
        tracemalloc.stop()

    return metrics_data

def run_single_test(src_dir):
    """
    Runs the game in single test mode:
      - Executes the game and monitors performance in the background.
      - After the run (or crash), scans the src directory for code complexity.
      - Exports CSV reports for runtime metrics and source code complexity.
      - Prints summary reports to the console.
    """
    print("Running single test mode...")
    metrics = run_game_and_monitor(src_dir)
    complexities = scan_complexity(src_dir)

    df_metrics = pd.DataFrame(metrics)
    df_complexity = pd.DataFrame(complexities, columns=["File", "Complexity"])

    df_metrics.to_csv("session_metrics_report.csv", index=False)
    df_complexity.to_csv("src_complexity_report.csv", index=False)

    print("Reports generated: session_metrics_report.csv and src_complexity_report.csv")
    print("\n--- Session Metrics Report (First 10 Rows) ---")
    print(df_metrics.head(10))
    print("\n--- Source Code Complexity Report (First 10 Rows) ---")
    print(df_complexity.head(10))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Efficiencymeter for Monitoring a Pygame-based Game (Report-Only Version)"
    )
    parser.add_argument("mode", choices=["test", "session"],
                        help="Mode: 'test' for a single run, 'session' for long-run monitoring.")
    parser.add_argument("src_dir",
                        help="Path to the game source directory (should contain main.py and any cache folders).")

    args = parser.parse_args()

    if args.mode == "test":
        run_single_test(args.src_dir)
    elif args.mode == "session":
        print("Running long session mode. Press Ctrl+C to interrupt and finalize the report.")
        try:
            run_game_and_monitor(args.src_dir)
        except KeyboardInterrupt:
            print("Session interrupted. Finalizing report...")
        finally:
            complexities = scan_complexity(args.src_dir)
            df_metrics = pd.DataFrame(metrics_data)
            df_complexity = pd.DataFrame(complexities, columns=["File", "Complexity"])
            df_metrics.to_csv("session_metrics_report.csv", index=False)
            df_complexity.to_csv("src_complexity_report.csv", index=False)
            print("Reports generated: session_metrics_report.csv and src_complexity_report.csv")
            print("\n--- Session Metrics Report (First 10 Rows) ---")
            print(df_metrics.head(10))
            print("\n--- Source Code Complexity Report (First 10 Rows) ---")
            print(df_complexity.head(10))
