#File:  src/performances/graphics_analyser.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python
"""
Graphics Analyser for Pygame Projects

Features:
- Recursively searches a given directory for all Python (.py) files.
- Scans each file for lines containing Pygame drawing-related functions
  such as those starting with "pygame.draw", "pygame.display.flip/update", or any ".blit(", ".flip(", ".update(" calls.
- Collects details including file name, line number, matched keyword/pattern, and code snippet.
- Exports a CSV report ("graphics_analysis_report.csv") and prints a summary to the console.

Dependencies:
- pandas
- re (built-in)
"""

import os
import re
import sys
import argparse
import pandas as pd

# Define regex patterns for common pygame drawing functions.
# You can refine these patterns to reduce false positives.
patterns = {
    "pygame_draw": re.compile(r"pygame\.draw\.\w+\("),
    "pygame_display_flip": re.compile(r"pygame\.display\.flip\("),
    "pygame_display_update": re.compile(r"pygame\.display\.update\("),
    "blit": re.compile(r"\.blit\("),
    "flip": re.compile(r"\.flip\("),
    "update": re.compile(r"\.update\("),
}

def analyse_file(file_path):
    """
    Scans a single file for drawing-related function calls.
    Returns a list of dictionaries with the file name, line number, matched pattern, and code snippet.
    """
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return results

    for idx, line in enumerate(lines, start=1):
        # Check each pattern on the line.
        for pattern_name, pattern in patterns.items():
            if pattern.search(line):
                results.append({
                    "File": file_path,
                    "Line": idx,
                    "Keyword": pattern_name,
                    "Code Snippet": line.strip()
                })
                # If a line matches multiple patterns, you may get duplicates.
                # To avoid duplicates per line, uncomment the next line:
                # break
    return results

def analyse_directory(directory):
    """
    Recursively scans the directory for .py files and analyses each one.
    Returns a list of all findings.
    """
    all_results = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                file_results = analyse_file(full_path)
                all_results.extend(file_results)
    return all_results

def main(directory):
    print(f"Analysing Python files in directory: {directory}")
    results = analyse_directory(directory)
    
    if not results:
        print("No drawing-related function calls found.")
        return
    
    df = pd.DataFrame(results)
    report_file = "graphics_analysis_report.csv"
    df.to_csv(report_file, index=False)
    
    print(f"\nGraphics analysis report saved as: {report_file}")
    print("\n--- Report Summary (First 10 Rows) ---")
    print(df.head(10).to_string(index=False))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Graphics Analyser for Pygame Projects: Scans for drawing-related functions (draw, blit, flip, update, etc.)."
    )
    parser.add_argument("directory", help="Path to the project directory to analyse.")
    args = parser.parse_args()
    main(args.directory)
