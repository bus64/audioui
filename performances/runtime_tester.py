#File:  src/performances/runtime_tester.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python
"""
Runtime Tester for Python Files

Features:
- Recursively searches the specified directory for all .py files (except itself).
- Executes each file using the current Python interpreter.
- Measures the wall-clock runtime for each file.
- Uses a configurable timeout (default: 10 seconds) to avoid hangs.
- Generates a CSV report ("runtime_test_report.csv") and prints a summary to the console.

Dependencies:
- pandas
"""

import os
import sys
import time
import subprocess
import argparse
import pandas as pd

def test_runtime(file_path, timeout=10):
    """
    Runs the given Python file and measures its execution time.
    
    Parameters:
        file_path (str): Path to the Python file.
        timeout (int): Maximum allowed seconds for file execution.
        
    Returns:
        float or str: Runtime in seconds or "Timeout/Error" if execution failed.
    """
    start = time.perf_counter()
    try:
        subprocess.run(
            [sys.executable, file_path],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=timeout
        )
        end = time.perf_counter()
        return end - start
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        print(f"Error running {file_path}: {e}")
        return "Error"

def main(directory, timeout=10):
    results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                # Skip the runtime tester itself if it's in the same directory.
                if os.path.abspath(full_path) == os.path.abspath(__file__):
                    continue
                print(f"Testing {full_path}...")
                runtime = test_runtime(full_path, timeout=timeout)
                results.append({
                    "File": full_path,
                    "Runtime (s)": runtime
                })
    df = pd.DataFrame(results)
    report_file = "runtime_test_report.csv"
    df.to_csv(report_file, index=False)
    print("\nRuntime test report saved as:", report_file)
    print("\n--- Summary ---")
    print(df)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Runtime Tester for Python Files")
    parser.add_argument("directory", help="Directory to search for Python files")
    parser.add_argument("--timeout", type=int, default=10, help="Timeout in seconds for each file execution (default: 10)")
    args = parser.parse_args()
    main(args.directory, timeout=args.timeout)
