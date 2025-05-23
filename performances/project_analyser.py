#File:  src/performances/project_analyser.py © 2025 projectemergence. All rights reserved.
#!/usr/bin/env python
"""
Project Analyser UI
© 2024 projectemergence. All rights reserved.

This UI integrates four analysis tools:
  1. Efficiency Meter – Monitors a Pygame-based game (expects main.py) and saves performance reports.
  2. Runtime Tester – Measures the wall‑clock runtime of each code file.
  3. Graphics Analyser – Searches for Pygame drawing calls (draw, blit, flip, update, etc.) in Python files.
  4. Project Summariser – Summarises the project folder (only code files: .py, .php, .html, .js, .css, .ts) 
     by generating a JSON report and a concatenated file with proper comment markers.
     
Reports are saved in "reports" inside the current directory (src/performances/reports).

The UI also provides a Reports Viewer to load CSV files and display them as sortable tables.
"""

import os
import sys
import time
import threading
import subprocess
import psutil
import tracemalloc
import re
import json
import ast
from datetime import datetime
import pandas as pd
import tkinter as tk
from tkinter import filedialog, scrolledtext, messagebox, ttk
from radon.complexity import cc_visit

try:
    import GPUtil
except ImportError:
    GPUtil = None

# ---------- Helper Functions & Global Variables ----------

def get_reports_dir(base_dir):
    reports_dir = os.path.join(base_dir, "reports")
    os.makedirs(reports_dir, exist_ok=True)
    return reports_dir

# Allowed code file extensions for summarisation.
ALLOWED_EXTENSIONS = {".py", ".php", ".html", ".js", ".css", ".ts"}

def get_comment_marker(ext):
    mapping = {
        ".py": "#",
        ".php": "//",
        ".html": "<!--",
        ".js": "//",
        ".css": "/*",
        ".ts": "//"
    }
    return mapping.get(ext, "#")

def get_version_from_path(file_path):
    parts = file_path.split(os.sep)
    for part in parts:
        if part.startswith("ALLV") and part[4:].isdigit():
            return part
    return "ALLV_unknown"

def extract_function_details(file_content):
    """Extract function names, arguments, and return statements from Python file content."""
    try:
        tree = ast.parse(file_content)
        functions = []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                args = [arg.arg for arg in node.args.args]
                returns = [ast.dump(n.value) for n in ast.walk(node) if isinstance(n, ast.Return) and n.value is not None]
                functions.append((node.name, args, returns))
        return functions
    except SyntaxError:
        return []

# ---------- Efficiency Meter Functions ----------

def get_all_cache_metrics(src_dir):
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

def monitor_process(pid, src_dir, log_func, metrics_data):
    try:
        process = psutil.Process(pid)
    except psutil.NoSuchProcess:
        log_func("Error: Process not found!")
        return
    start_time = time.time()
    while metrics_data.get("monitoring_active", True) and process.is_running():
        try:
            timestamp = time.time() - start_time
            cpu_usage = process.cpu_percent(interval=1)
            memory_usage = process.memory_info().rss / (1024 * 1024)
            if GPUtil:
                try:
                    gpus = GPUtil.getGPUs()
                    gpu_usage = sum(gpu.load for gpu in gpus) / len(gpus) * 100 if gpus else 0
                except Exception as e:
                    log_func(f"GPU monitoring error: {e}")
                    gpu_usage = 0
            else:
                gpu_usage = 0
            cache_count, cache_size = get_all_cache_metrics(src_dir)
            metrics_data["timestamp"].append(timestamp)
            metrics_data["cpu"].append(cpu_usage)
            metrics_data["memory"].append(memory_usage)
            metrics_data["gpu"].append(gpu_usage)
            metrics_data["cache_count"].append(cache_count)
            metrics_data["cache_size"].append(cache_size)
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            log_func(f"Monitoring error: {e}")
            break

def scan_complexity(src_dir):
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

def run_efficiency_meter(src_dir, log_func, reports_dir):
    log_func("Starting Efficiency Meter (launching game)...")
    metrics_data = {"timestamp": [], "cpu": [], "memory": [], "gpu": [], "cache_count": [], "cache_size": []}
    metrics_data["monitoring_active"] = True
    game_entry = os.path.join(src_dir, "main.py")
    if not os.path.isfile(game_entry):
        log_func("Error: main.py not found in the selected directory!")
        return
    tracemalloc.start()
    game_process = subprocess.Popen(
        [sys.executable, game_entry],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    monitor_thread = threading.Thread(target=monitor_process, args=(game_process.pid, src_dir, log_func, metrics_data), daemon=True)
    monitor_thread.start()
    try:
        game_process.wait()
    except KeyboardInterrupt:
        log_func("Game run interrupted by user.")
    finally:
        metrics_data["monitoring_active"] = False
        monitor_thread.join()
        tracemalloc.stop()
    complexities = scan_complexity(src_dir)
    df_metrics = pd.DataFrame(metrics_data)
    df_complexity = pd.DataFrame(complexities, columns=["File", "Complexity"])
    metrics_file = os.path.join(reports_dir, "session_metrics_report.csv")
    complexity_file = os.path.join(reports_dir, "src_complexity_report.csv")
    df_metrics.to_csv(metrics_file, index=False)
    df_complexity.to_csv(complexity_file, index=False)
    log_func(f"Efficiency Meter reports generated:\n - {metrics_file}\n - {complexity_file}")

# ---------- Runtime Tester Functions ----------

def test_runtime(file_path, timeout=10):
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
        return f"Error: {e}"

def run_runtime_tester(src_dir, timeout, log_func, reports_dir):
    results = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                if os.path.abspath(full_path) == os.path.abspath(__file__):
                    continue
                log_func(f"Testing: {full_path}")
                runtime = test_runtime(full_path, timeout=timeout)
                results.append({"File": full_path, "Runtime (s)": runtime})
    df = pd.DataFrame(results)
    report_file = os.path.join(reports_dir, "runtime_test_report.csv")
    df.to_csv(report_file, index=False)
    log_func(f"Runtime Tester completed. Report generated:\n - {report_file}")

# ---------- Graphics Analyser Functions ----------

# Regex patterns for common pygame drawing functions.
graphics_patterns = {
    "pygame_draw": re.compile(r"pygame\.draw\.\w+\("),
    "pygame_display_flip": re.compile(r"pygame\.display\.flip\("),
    "pygame_display_update": re.compile(r"pygame\.display\.update\("),
    "blit": re.compile(r"\.blit\("),
    "flip": re.compile(r"\.flip\("),
    "update": re.compile(r"\.update\("),
}

def analyse_file(file_path):
    results = []
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except Exception:
        return results
    for idx, line in enumerate(lines, start=1):
        for pattern_name, pattern in graphics_patterns.items():
            if pattern.search(line):
                results.append({
                    "File": file_path,
                    "Line": idx,
                    "Keyword": pattern_name,
                    "Code Snippet": line.strip()
                })
    return results

def run_graphics_analyser(src_dir, log_func, reports_dir):
    all_results = []
    for root, _, files in os.walk(src_dir):
        for file in files:
            if file.endswith(".py"):
                full_path = os.path.join(root, file)
                file_results = analyse_file(full_path)
                all_results.extend(file_results)
    if not all_results:
        log_func("No drawing-related function calls found.")
        return
    df = pd.DataFrame(all_results)
    report_file = os.path.join(reports_dir, "graphics_analysis_report.csv")
    df.to_csv(report_file, index=False)
    log_func(f"Graphics Analyser completed. Report generated:\n - {report_file}")

# ---------- Project Summariser Functions ----------

def save_folder_structure(root_folder, output_file, concatenated_output):
    file_structure = {}
    function_definitions = {}
    all_imports = set()
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')
    # Open the concatenated file for writing.
    with open(concatenated_output, "w", encoding="utf-8") as concat_file:
        # Write header with current year.
        concat_file.write(f"© {datetime.now().year} projectemergence. All rights reserved.\n\n")
        for dirpath, dirnames, filenames in os.walk(root_folder):
            # Skip __pycache__ and report/saves directories.
            dirnames[:] = [d for d in dirnames if d not in {"__pycache__", "reports", "saves"}]
            rel_path = os.path.relpath(dirpath, root_folder)
            if rel_path == ".": rel_path = ""
            file_structure[rel_path] = []
            for file in filenames:
                ext = os.path.splitext(file)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    file_path = os.path.join(dirpath, file)
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            file_content = f.read()
                    except Exception:
                        file_content = ""
                    file_structure[rel_path].append({"name": file, "content": file_content, "timestamp": timestamp})
                    if ext == ".py":
                        functions = extract_function_details(file_content)
                        function_definitions[file_path] = functions
                    # Write file content to concatenated file with appropriate comment header.
                    marker = get_comment_marker(ext)
                    concat_file.write(f"{marker} File: {file_path}\n")
                    for line in file_content.splitlines():
                        # For code files, we assume the content is code.
                        concat_file.write(f"{marker} {line}\n")
                    concat_file.write("\n\n")
    # Save the main report as JSON.
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(file_structure, outfile, indent=4)
    # Save a supplementary file with directory tree and function details.
    supplementary_output_file = output_file.replace(".txt", "_ProjectTree.txt")
    with open(supplementary_output_file, "w", encoding="utf-8") as sfile:
        for dirpath, dirnames, files in os.walk(root_folder):
            dirnames[:] = [d for d in dirnames if d not in {"__pycache__", "reports", "saves"}]
            rel_path = os.path.relpath(dirpath, root_folder)
            if rel_path == ".": rel_path = ""
            sfile.write(f"Directory: {rel_path}\n")
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in ALLOWED_EXTENSIONS:
                    file_path = os.path.join(dirpath, file)
                    sfile.write(f"  File: {file}\n")
                    if file_path in function_definitions:
                        sfile.write("    Functions:\n")
                        for func_name, args, return_values in function_definitions[file_path]:
                            args_str = ", ".join(args)
                            returns_str = ", ".join(return_values)
                            sfile.write(f"      {func_name}({args_str}) -> {returns_str}\n")
            sfile.write("\n")
    log_msg = (f"Folder structure saved to {output_file}\n"
               f"Supplementary file saved to {supplementary_output_file}\n"
               f"Concatenated file saved to {concatenated_output}")
    return log_msg

def summarise_project(root_folder, reports_dir, log_func):
    version = get_version_from_path(os.path.abspath(__file__))
    output_file = os.path.join(reports_dir, f"{version}report_{datetime.now().strftime('%Y%m%d%H%M%S')}.txt")
    concatenated_output = os.path.join(reports_dir, f"{version}_concatenated_{datetime.now().strftime('%Y%m%d%H%M%S')}.py")
    msg = save_folder_structure(root_folder, output_file, concatenated_output)
    log_func("Project Summariser completed:")
    log_func(msg)

# ---------- UI Code ----------

class ProjectAnalyserUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Project Analyser UI")
        self.geometry("800x600")
        # Base directory is assumed to be the parent of this script’s directory.
        self.base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__)))
        self.reports_dir = get_reports_dir(self.base_dir)
        self.create_widgets()

    def create_widgets(self):
        # Directory selection.
        dir_frame = tk.Frame(self)
        dir_frame.pack(pady=8)
        tk.Label(dir_frame, text="Select Project Directory:").pack(side=tk.LEFT, padx=5)
        self.dir_entry = tk.Entry(dir_frame, width=60)
        self.dir_entry.pack(side=tk.LEFT, padx=5)
        tk.Button(dir_frame, text="Browse", command=self.browse_directory).pack(side=tk.LEFT, padx=5)
        # Analysis buttons.
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Run Efficiency Meter", width=25, command=self.run_efficiency).pack(pady=4)
        tk.Button(btn_frame, text="Run Runtime Tester", width=25, command=self.run_runtime).pack(pady=4)
        tk.Button(btn_frame, text="Run Graphics Analyser", width=25, command=self.run_graphics).pack(pady=4)
        tk.Button(btn_frame, text="Summarise Project", width=25, command=self.run_summariser).pack(pady=4)
        tk.Button(btn_frame, text="View Reports", width=25, command=self.view_reports).pack(pady=4)
        # Log output.
        self.log_widget = scrolledtext.ScrolledText(self, width=95, height=20)
        self.log_widget.pack(pady=10)
        self.log("Project Analyser UI started.")

    def browse_directory(self):
        directory = filedialog.askdirectory()
        if directory:
            self.dir_entry.delete(0, tk.END)
            self.dir_entry.insert(0, directory)

    def log(self, message):
        self.log_widget.insert(tk.END, f"{message}\n")
        self.log_widget.see(tk.END)

    def run_efficiency(self):
        src_dir = self.dir_entry.get().strip()
        if not os.path.isdir(src_dir):
            messagebox.showerror("Error", "Please select a valid directory.")
            return
        self.log("Launching Efficiency Meter...")
        threading.Thread(target=run_efficiency_meter, args=(src_dir, self.log, self.reports_dir), daemon=True).start()

    def run_runtime(self):
        src_dir = self.dir_entry.get().strip()
        if not os.path.isdir(src_dir):
            messagebox.showerror("Error", "Please select a valid directory.")
            return
        self.log("Launching Runtime Tester (timeout=10s)...")
        threading.Thread(target=run_runtime_tester, args=(src_dir, 10, self.log, self.reports_dir), daemon=True).start()

    def run_graphics(self):
        src_dir = self.dir_entry.get().strip()
        if not os.path.isdir(src_dir):
            messagebox.showerror("Error", "Please select a valid directory.")
            return
        self.log("Launching Graphics Analyser...")
        threading.Thread(target=run_graphics_analyser, args=(src_dir, self.log, self.reports_dir), daemon=True).start()

    def run_summariser(self):
        src_dir = self.dir_entry.get().strip()
        if not os.path.isdir(src_dir):
            messagebox.showerror("Error", "Please select a valid directory.")
            return
        self.log("Launching Project Summariser...")
        # For summariser, we use the project root as the folder to summarise.
        threading.Thread(target=summarise_project, args=(src_dir, self.reports_dir, self.log), daemon=True).start()

    def view_reports(self):
        ReportViewer(self.reports_dir)

class ReportViewer(tk.Toplevel):
    def __init__(self, reports_dir):
        super().__init__()
        self.title("Reports Viewer")
        self.geometry("900x600")
        self.reports_dir = reports_dir
        self.create_widgets()

    def create_widgets(self):
        top_frame = tk.Frame(self)
        top_frame.pack(fill=tk.X, pady=5)
        tk.Label(top_frame, text="Select CSV Report:").pack(side=tk.LEFT, padx=5)
        self.report_var = tk.StringVar()
        self.report_combo = ttk.Combobox(top_frame, textvariable=self.report_var, width=50)
        self.report_combo.pack(side=tk.LEFT, padx=5)
        tk.Button(top_frame, text="Load Report", command=self.load_report).pack(side=tk.LEFT, padx=5)
        # Table frame.
        self.tree = ttk.Treeview(self, columns=[], show="headings")
        self.tree.pack(fill=tk.BOTH, expand=True)
        # Attach a vertical scrollbar.
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        vsb.pack(side='right', fill='y')
        self.tree.configure(yscrollcommand=vsb.set)
        self.populate_report_list()

    def populate_report_list(self):
        files = [f for f in os.listdir(self.reports_dir) if f.endswith(".csv")]
        self.report_combo['values'] = files
        if files:
            self.report_combo.current(0)

    def load_report(self):
        filename = self.report_var.get()
        if not filename:
            messagebox.showerror("Error", "No report selected.")
            return
        filepath = os.path.join(self.reports_dir, filename)
        try:
            df = pd.read_csv(filepath)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load CSV: {e}")
            return
        # Clear existing tree.
        for col in self.tree.get_children():
            self.tree.delete(col)
        self.tree["columns"] = list(df.columns)
        for col in df.columns:
            self.tree.heading(col, text=col, command=lambda _col=col: self.sortby(_col, False))
            self.tree.column(col, width=100)
        # Insert rows.
        for index, row in df.iterrows():
            self.tree.insert("", "end", values=list(row))
    
    def sortby(self, col, descending):
        # Grab all values to sort.
        data = [(self.tree.set(child, col), child) for child in self.tree.get_children('')]
        try:
            data.sort(key=lambda t: float(t[0]) if t[0] not in {"Timeout", "Error"} else float('inf'), reverse=descending)
        except ValueError:
            data.sort(reverse=descending)
        for index, item in enumerate(data):
            self.tree.move(item[1], '', index)
        # Reverse sort next time.
        self.tree.heading(col, command=lambda: self.sortby(col, not descending))

if __name__ == "__main__":
    app = ProjectAnalyserUI()
    app.mainloop()
