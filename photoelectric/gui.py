"""Tkinter front panel. Replaces the front panel of Photoelectric_Effect_v6.vi."""

from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from .daq import DAQError, SimulatedApparatus
from .data import Experiment, Sample
from .physics import (
    INTENSITY_LABELS,
    LEDS,
    MAX_INTENSITY,
    intensity_for_position,
    led_for_position,
    round_thousandth,
    switch_position,
)

UI_PERIOD_MS = 20  # the original event loop used a 20 ms timeout
DISABLED_BOX = "#C8C8C8"


class Graph:
    def __init__(self, parent: tk.Widget, xlabel: str, ylabel: str) -> None:
        self.figure = Figure(figsize=(6.4, 4.2), dpi=100, layout="constrained")
        self.ax = self.figure.add_subplot()
        self.xlabel, self.ylabel = xlabel, ylabel
        self.canvas = FigureCanvasTkAgg(self.figure, master=parent)
        self.widget = self.canvas.get_tk_widget()
        self.plot([], [])

    def plot(self, x, y, fit_x=(), fit_y=(), line: bool = False) -> None:
        ax = self.ax
        ax.clear()
        ax.set_xlabel(self.xlabel)
        ax.set_ylabel(self.ylabel)
        ax.grid(True, alpha=0.3)
        if len(x):
            ax.plot(x, y, "o-" if line else "o", color="#1f5fbf", markersize=5, linewidth=1)
        if len(fit_x):
            ax.plot(fit_x, fit_y, "-", color="#d62728", linewidth=1.5, label="Best linear fit")
            ax.legend(loc="best")
        self.canvas.draw_idle()


class App:
    def __init__(self, root: tk.Tk, daq, simulated: bool) -> None:
        self.root = root
        self.daq = daq
        self.simulated = simulated
        self.experiment = Experiment()
        self.current: Optional[Sample] = None
        self.previous: Optional[Sample] = None

        self._latest = None
        self._latest_seq = 0
        self._seen_seq = 0
        self._daq_error: Optional[str] = None
        self._lock = threading.Lock()
        self._running = True

        root.title("Photoelectric Effect" + ("  [SIMULATED]" if simulated else ""))
        root.protocol("WM_DELETE_WINDOW", self.quit)
        self._build()
        self._refresh_all_graphs()

        threading.Thread(target=self._acquire_loop, daemon=True).start()
        root.after(UI_PERIOD_MS, self._tick)

    # --- Layout -------------------------------------------------------------

    def _build(self) -> None:
        root = self.root
        big = ("Helvetica", 22, "bold")

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")

        def readout(col: int, title: str) -> tk.StringVar:
            box = ttk.LabelFrame(top, text=title, padding=(10, 4))
            box.grid(row=0, column=col, padx=6, sticky="nsew")
            var = tk.StringVar(value="—")
            ttk.Label(box, textvariable=var, font=big, width=8, anchor="e").pack()
            return var

        self.bias_var = readout(0, "Bias Voltage (V)")
        self.current_var = readout(1, "PhotoCurrent (nA)")

        led_box = ttk.LabelFrame(top, text="LED", padding=(10, 4))
        led_box.grid(row=0, column=2, padx=6, sticky="nsew")
        self.led_swatch = tk.Canvas(led_box, width=34, height=34, highlightthickness=1,
                                    highlightbackground="#888")
        self.led_swatch.grid(row=0, column=0, rowspan=2, padx=(0, 8))
        self.led_var = tk.StringVar(value="—")
        self.freq_var = tk.StringVar(value="")
        ttk.Label(led_box, textvariable=self.led_var, font=("Helvetica", 14, "bold"), width=16).grid(
            row=0, column=1, sticky="w")
        ttk.Label(led_box, textvariable=self.freq_var).grid(row=1, column=1, sticky="w")

        int_box = ttk.LabelFrame(top, text="LED Intensity", padding=(10, 4))
        int_box.grid(row=0, column=3, padx=6, sticky="nsew")
        self.intensity_boxes = []
        for i in range(MAX_INTENSITY):
            c = tk.Canvas(int_box, width=22, height=34, highlightthickness=1, highlightbackground="#888")
            c.grid(row=0, column=i, padx=2)
            self.intensity_boxes.append(c)
        self.intensity_var = tk.StringVar(value="")
        ttk.Label(int_box, textvariable=self.intensity_var, width=8).grid(row=0, column=MAX_INTENSITY, padx=6)

        if self.simulated:
            self._build_simulator_controls(root)

        notebook = ttk.Notebook(root)
        notebook.pack(fill="both", expand=True, padx=10, pady=(0, 6))
        self._build_frequency_tab(notebook)
        self._build_intensity_tab(notebook)
        self._build_iv_tab(notebook)

        bottom = ttk.Frame(root, padding=(10, 0, 10, 8))
        bottom.pack(fill="x")
        self.status_var = tk.StringVar(value="Ready.")
        ttk.Label(bottom, textvariable=self.status_var, foreground="#555").pack(side="left")
        ttk.Button(bottom, text="Stop", command=self.quit).pack(side="right")

    def _tab(self, notebook: ttk.Notebook, title: str, xlabel: str, ylabel: str):
        frame = ttk.Frame(notebook, padding=8)
        notebook.add(frame, text=title)
        graph = Graph(frame, xlabel, ylabel)
        graph.widget.pack(side="left", fill="both", expand=True)
        side = ttk.Frame(frame, padding=(10, 0, 0, 0))
        side.pack(side="right", fill="y")
        return graph, side

    @staticmethod
    def _button(parent, text: str, command: Callable[[], None]) -> None:
        ttk.Button(parent, text=text, command=command, width=24).pack(fill="x", pady=2)

    def _build_frequency_tab(self, nb: ttk.Notebook) -> None:
        self.freq_graph, side = self._tab(nb, "Stopping Potential vs. Frequency",
                                          "LED Frequency (Hz)", "Stopping Potential (V)")
        self._button(side, "Record Stopping Potential", self.on_record_frequency)
        self._button(side, "Clear Last Data Point", self.on_clear_last_frequency)
        self._button(side, "Clear All Data", self.on_clear_all_frequency)
        ttk.Separator(side).pack(fill="x", pady=8)
        self._button(side, "Calculate Slope", self.on_calculate_slope)
        self._button(side, "Calculate Planck's Constant", self.on_calculate_planck)
        results = ttk.Frame(side, padding=(0, 6))
        results.pack(fill="x")
        self.slope_var = tk.StringVar()
        self.intercept_var = tk.StringVar()
        self.planck_var = tk.StringVar()
        for r, (label, var) in enumerate((("Slope:", self.slope_var), ("Intercept:", self.intercept_var),
                                          ("Planck's Constant:", self.planck_var))):
            ttk.Label(results, text=label).grid(row=r, column=0, sticky="w")
            ttk.Label(results, textvariable=var, font=("Helvetica", 12, "bold")).grid(row=r, column=1, sticky="e")
        ttk.Separator(side).pack(fill="x", pady=8)
        self._button(side, "Save Data to File", self.on_save)
        self._button(side, "Read Data from File", self.on_load)

    def _build_intensity_tab(self, nb: ttk.Notebook) -> None:
        self.intensity_graph, side = self._tab(nb, "Stopping Potential vs. Intensity",
                                               "LED Intensity (arbitrary units)", "Stopping Potential (V)")
        self._button(side, "Record Stopping Potential", self.on_record_intensity)
        self._button(side, "Clear Last Data Point", self.on_clear_last_intensity)
        self._button(side, "Clear All Data", self.on_clear_all_intensity)

    def _build_iv_tab(self, nb: ttk.Notebook) -> None:
        self.iv_graph, side = self._tab(nb, "PhotoCurrent vs. Bias Voltage",
                                        "Bias Voltage (Volts)", "PhotoCurrent (nA)")
        self._button(side, "Begin Recording", self.on_begin_iv)
        self._button(side, "End Recording", self.on_end_iv)
        self._button(side, "Clear All Data", self.on_clear_iv)
        self.recording_var = tk.StringVar()
        ttk.Label(side, textvariable=self.recording_var, foreground="#c00000",
                  font=("Helvetica", 12, "bold")).pack(pady=8)
        ttk.Label(side, wraplength=190, foreground="#555", text=(
            "While recording, a point is added each time the reading changes. "
            "Sweep the bias voltage knob slowly.")).pack()

    def _build_simulator_controls(self, root: tk.Tk) -> None:
        box = ttk.LabelFrame(root, text="Simulated apparatus (no LabJack connected)", padding=(10, 4))
        box.pack(fill="x", padx=10, pady=(0, 6))
        sim: SimulatedApparatus = self.daq
        self.sim_color = tk.StringVar(value=LEDS[sim.color_position].name)
        self.sim_intensity = tk.StringVar(value=INTENSITY_LABELS[sim.intensity_position])
        self.sim_bias = tk.DoubleVar(value=sim.bias_voltage)

        ttk.Label(box, text="Color switch").grid(row=0, column=0, sticky="w")
        ttk.Combobox(box, textvariable=self.sim_color, values=[l.name for l in LEDS],
                     state="readonly", width=18).grid(row=0, column=1, padx=(4, 16))
        ttk.Label(box, text="Intensity switch").grid(row=0, column=2, sticky="w")
        ttk.Combobox(box, textvariable=self.sim_intensity, values=list(INTENSITY_LABELS),
                     state="readonly", width=10).grid(row=0, column=3, padx=(4, 16))
        ttk.Label(box, text="Bias knob (V)").grid(row=0, column=4, sticky="w")
        ttk.Scale(box, from_=-3.0, to=3.0, variable=self.sim_bias, length=260).grid(row=0, column=5, padx=4)

        def push(*_):
            color = [l.name for l in LEDS].index(self.sim_color.get())
            intensity = list(INTENSITY_LABELS).index(self.sim_intensity.get())
            sim.set_controls(color, intensity, self.sim_bias.get())

        for var in (self.sim_color, self.sim_intensity, self.sim_bias):
            var.trace_add("write", push)

    # --- Acquisition --------------------------------------------------------

    def _acquire_loop(self) -> None:
        while self._running:
            try:
                reading = self.daq.read()
            except DAQError as e:
                with self._lock:
                    self._daq_error = str(e)
                return
            with self._lock:
                self._latest = reading
                self._latest_seq += 1
            if self.simulated:
                time.sleep(0.03)

    def _tick(self) -> None:
        if not self._running:
            return
        with self._lock:
            reading, seq, error = self._latest, self._latest_seq, self._daq_error
        if error:
            self._running = False
            messagebox.showerror("Photoelectric Effect", error)
            self.quit()
            return
        if reading is not None and seq != self._seen_seq:
            self._seen_seq = seq
            self._process(reading)
        self.root.after(UI_PERIOD_MS, self._tick)

    def _process(self, reading) -> None:
        ain0, ain1, ain2, ain3 = reading
        led = led_for_position(switch_position(ain2))
        intensity = intensity_for_position(switch_position(ain3))
        sample = Sample(round_thousandth(ain0), round_thousandth(ain1), led.frequency_hz, intensity)

        self.current_var.set(f"{sample.photocurrent_na:.3f}")
        self.bias_var.set(f"{sample.voltage_v:.3f}")
        self.led_var.set(led.name)
        self.freq_var.set(f"{led.frequency_hz:.4e} Hz" if led.frequency_hz else "")
        self.led_swatch.delete("all")
        self.led_swatch.create_rectangle(0, 0, 40, 40, fill=led.color, outline="")
        for i, box in enumerate(self.intensity_boxes):
            box.delete("all")
            fill = led.color if i < intensity and led.wavelength_nm else DISABLED_BOX
            box.create_rectangle(0, 0, 30, 40, fill=fill, outline="")
        self.intensity_var.set(INTENSITY_LABELS[intensity])

        self.previous, self.current = self.current, sample
        if self.experiment.update_iv(self.previous, sample):
            self._refresh_iv()

    def quit(self) -> None:
        self._running = False
        try:
            self.daq.close()
        finally:
            self.root.destroy()

    # --- Button handlers ----------------------------------------------------

    def _guard(self, action: Callable[[], None], done: str = "") -> bool:
        try:
            action()
        except ValueError as e:
            self.status_var.set(str(e))
            self.root.bell()
            return False
        if done:
            self.status_var.set(done)
        return True

    def _need_sample(self) -> Optional[Sample]:
        if self.current is None:
            self.status_var.set("No reading from the apparatus yet.")
        return self.current

    def on_record_frequency(self) -> None:
        s = self._need_sample()
        if s and self._guard(lambda: self.experiment.record_vs_frequency(s),
                             f"Recorded {s.voltage_v:.3f} V at {s.frequency_hz or 0:.4e} Hz."):
            self._refresh_frequency()

    def on_clear_last_frequency(self) -> None:
        self.experiment.clear_last_frequency()
        self._refresh_frequency()

    def on_clear_all_frequency(self) -> None:
        self.experiment.clear_all_frequency()
        self._refresh_frequency()

    def on_calculate_slope(self) -> None:
        if self._guard(self.experiment.calculate_slope, "Linear fit done."):
            self._refresh_frequency()

    def on_calculate_planck(self) -> None:
        if self._guard(self.experiment.calculate_planck):
            self._refresh_frequency()

    def on_record_intensity(self) -> None:
        s = self._need_sample()
        if s and self._guard(lambda: self.experiment.record_vs_intensity(s),
                             f"Recorded {s.voltage_v:.3f} V at intensity {s.intensity}."):
            self._refresh_intensity()

    def on_clear_last_intensity(self) -> None:
        self.experiment.clear_last_intensity()
        self._refresh_intensity()

    def on_clear_all_intensity(self) -> None:
        self.experiment.clear_all_intensity()
        self._refresh_intensity()

    def on_begin_iv(self) -> None:
        self.experiment.begin_iv()
        self._refresh_iv()

    def on_end_iv(self) -> None:
        self.experiment.end_iv()
        self._refresh_iv()

    def on_clear_iv(self) -> None:
        self.experiment.clear_iv()
        self._refresh_iv()

    def on_save(self) -> None:
        path = filedialog.asksaveasfilename(title="Save Data to File", defaultextension=".txt",
                                            filetypes=[("Text data", "*.txt"), ("All files", "*")])
        if not path:
            return
        try:
            self.experiment.save(path)
        except OSError as e:
            messagebox.showerror("Save Data", str(e))
            return
        self.status_var.set(f"Saved {path}")

    def on_load(self) -> None:
        path = filedialog.askopenfilename(title="Read Data from File",
                                          filetypes=[("Text data", "*.txt"), ("All files", "*")])
        if not path:
            return
        try:
            self.experiment.load(path)
        except (OSError, ValueError) as e:
            messagebox.showerror("Read Data", f"Could not read {path}:\n{e}")
            return
        self._refresh_all_graphs()
        self.status_var.set(f"Loaded {path}")

    # --- Graph refresh ------------------------------------------------------

    def _refresh_all_graphs(self) -> None:
        self._refresh_frequency()
        self._refresh_intensity()
        self._refresh_iv()

    def _refresh_frequency(self) -> None:
        e = self.experiment
        self.freq_graph.plot(e.vs_frequency.frequency, e.vs_frequency.voltage, e.fit_frequency, e.fit_voltage)
        self.slope_var.set(f"{e.slope:.4e} V/Hz" if e.slope is not None else "—")
        self.intercept_var.set(f"{e.intercept:.3f} V" if e.intercept is not None else "—")
        self.planck_var.set(f"{e.planck:.4e} J·s" if e.planck is not None else "—")

    def _refresh_intensity(self) -> None:
        s = self.experiment.vs_intensity
        self.intensity_graph.plot(s.intensity, s.voltage)

    def _refresh_iv(self) -> None:
        s = self.experiment.iv_curve
        self.iv_graph.plot(s.voltage, s.photocurrent, line=True)
        self.recording_var.set("● RECORDING" if self.experiment.recording_iv else "")


def run(simulate: bool = False) -> None:
    root = tk.Tk()
    if simulate:
        daq = SimulatedApparatus()
    else:
        from .daq import LabJackU6
        try:
            daq = LabJackU6()
        except DAQError as e:
            root.withdraw()
            messagebox.showerror("Photoelectric Effect", str(e))
            root.destroy()
            raise SystemExit(1)
    App(root, daq, simulated=simulate)
    root.mainloop()
