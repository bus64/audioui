# File: audio_dev_ui.py
# Responsive UI with tabbed preset control and a melody selection tab

import os, json, time, math, traceback, inspect, importlib.util
from pathlib import Path
from tkinter import *
from tkinter import ttk
from core.audio.audio_engine_client import AudioEngineClient

PRESET_DIR = Path("core/audio/presets")
MELODY_DIR = Path("core/audio/melodies")
BG = '#121212'; FG = '#FFA726'; BTN = '#FF5722'; TR = '#1E1E1E'

client = AudioEngineClient()
client.maestro.mute = False
_state = {}

def discover_presets():
    from core.audio.presets.base_preset import BasePreset
    out = {}
    for py in PRESET_DIR.glob("*.py"):
        if py.stem.startswith("_") or py.stem in ("base_preset", "__init__"):
            continue
        try:
            spec = importlib.util.spec_from_file_location(py.stem, py)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            cls = next(c for _, c in inspect.getmembers(mod, inspect.isclass) if issubclass(c, BasePreset) and c is not BasePreset)
            sig = inspect.signature(cls.__init__)
            fields = [(n, p.default if p.default is not inspect._empty else 0.0)
                      for n, p in sig.parameters.items()
                      if n != "self"]
            out[py.stem] = (cls, fields)
        except Exception:
            print(f"[ERROR] {py.name}:"); traceback.print_exc()
    return out

def build_slider(parent, preset, param, default):
    def guess_range(n, v):
        if isinstance(v, bool): return 0, 1, IntVar
        if "freq" in n: return 20, 20000, DoubleVar
        if any(k in n for k in ("dur", "time")): return 0, 10, DoubleVar
        if "pan" in n: return -1, 1, DoubleVar
        if isinstance(v, int): return 0, max(v*2, 8), IntVar
        return 0.0, (v or 1.0) * 2, DoubleVar
    lo, hi, VType = guess_range(param, default)
    var = VType(value=default)
    _state[preset][param] = default
    frame = Frame(parent, bg=BG)
    frame.pack(fill=X, pady=2, padx=4)
    Label(frame, text=param, bg=BG, fg=FG, width=15).pack(side=LEFT)
    scl = Scale(frame, from_=lo, to=hi, resolution=0.01, orient=HORIZONTAL,
                bg=TR, fg=FG, troughcolor=TR, variable=var, length=200,
                highlightthickness=0)
    scl.pack(side=LEFT, fill=X, expand=True)
    def update_value(v):
        try: _state[preset][param] = float(v)
        except: pass
    scl.config(command=update_value)

def build_preset_tab(notebook, preset, fields):
    tab = Frame(notebook, bg=BG)
    canvas = Canvas(tab, bg=BG, highlightthickness=0)
    scrollbar = Scrollbar(tab, orient=VERTICAL, command=canvas.yview)
    canvas.configure(yscrollcommand=scrollbar.set)
    scroll_frame = Frame(canvas, bg=BG)
    scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
    canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
    scrollbar.pack(side=RIGHT, fill=Y)
    canvas.pack(side=LEFT, fill=BOTH, expand=True)
    for param, default in fields:
        build_slider(scroll_frame, preset, param, default)
    notebook.add(tab, text=preset)

def build_melody_tab(notebook):
    from tkinter import ttk
    tab = Frame(notebook, bg=BG)
    notebook.add(tab, text="🎼 Melody")

    Label(tab, text="Melody", bg=BG, fg=FG).pack(pady=4)
    melody_var = StringVar()
    melodies = [f.name[:-5] for f in MELODY_DIR.glob("*.json")]
    melody_menu = OptionMenu(tab, melody_var, *melodies)
    melody_menu.config(bg=TR, fg=FG)
    melody_menu.pack()

    Label(tab, text="Presets for orchestration", bg=BG, fg=FG).pack(pady=4)
    preset_box = Listbox(tab, selectmode=MULTIPLE, height=8, bg=TR, fg=FG, selectbackground=BTN, exportselection=False)
    for p in client.maestro.all_presets:
        preset_box.insert(END, p)
    preset_box.pack(fill=BOTH, expand=True, padx=20, pady=5)

    prog_frame = Frame(tab, bg=BG)
    prog_frame.pack(fill=X, pady=10)
    prog_label = Label(prog_frame, text="Progress", bg=BG, fg=FG)
    prog_label.pack(side=LEFT, padx=10)
    prog_var = DoubleVar(value=0.0)
    prog_bar = ttk.Progressbar(prog_frame, variable=prog_var, maximum=1.0, length=300)
    prog_bar.pack(side=LEFT, fill=X, expand=True)

    timer = {"active": False, "start": 0.0, "dur": 1.0}
    def tick_progress():
        if timer["active"]:
            elapsed = time.time() - timer["start"]
            prog_var.set(min(1.0, elapsed / timer["dur"]))
            if elapsed < timer["dur"]:
                tab.after(100, tick_progress)
            else:
                timer["active"] = False

    def trigger_melody():
        name = melody_var.get()
        if not name: return
        client.maestro.compositor.start(name)
        parts_cfg = client.maestro.arranger.prepare_block()
        if not parts_cfg: return
        raw_events = client.maestro.compositor.next_block_events(8.0)
        tempo = client.maestro.tempo
        total_secs = 8.0 * (60.0 / tempo)
        timer.update({"active": True, "start": time.time(), "dur": total_secs})
        tab.after(100, tick_progress)
        events = []
        for ev in raw_events:
            events.append({
                "time_offset": ev["time"] * (60.0/tempo),
                "preset": "lead",
                "params": {
                    "notes": ev["notes"],
                    "durations": ev["durations"],
                    "intensity": ev["intensity"]
                }
            })
        choices = [preset_box.get(i) for i in preset_box.curselection()]
        for part, cfg in parts_cfg.items():
            if not choices: continue
            events.append({
                "time_offset": 0.0,
                "preset": choices[hash(part)%len(choices)],
                "params": cfg
            })
        client.play_block(events)

    def stop_melody():
        timer["active"] = False
        prog_var.set(0.0)
        client.stop_all()

    Button(tab, text="▶ Play Melody", bg=BTN, fg="white", command=trigger_melody).pack(pady=5)
    Button(tab, text="■ Stop Melody", bg="#666", fg="white", command=stop_melody).pack(pady=3)


if __name__ == "__main__":
    root = Tk()
    root.title("Emergence Audio Dev UI")
    root.configure(bg=BG)
    root.geometry("700x600")

    topbar = Frame(root, bg=BG)
    topbar.pack(side=TOP, fill=X)
    Label(topbar, text="Emergence Audio Interface", bg=BG, fg=FG, font=("Arial", 12, "bold")).pack(side=LEFT, padx=10)
    Button(topbar, text="▶ Play", bg=BTN, fg="white", command=lambda: play_selected(notebook, presets)).pack(side=RIGHT, padx=5)
    Button(topbar, text="■ Stop", bg=BTN, fg="white", command=client.stop_all).pack(side=RIGHT, padx=5)

    notebook = ttk.Notebook(root)
    notebook.pack(fill=BOTH, expand=True)
    style = ttk.Style()
    style.theme_use("default")
    style.configure("TNotebook", background=BG)
    style.configure("TNotebook.Tab", background=TR, foreground=FG, lightcolor=BG, borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", BTN)])

    presets = discover_presets()
    for name, (_, fields) in presets.items():
        _state[name] = {}
        build_preset_tab(notebook, name, fields)

    build_melody_tab(notebook)
    root.mainloop()
