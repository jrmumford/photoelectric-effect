import argparse
import sys
from typing import Optional, Tuple


def check_hardware() -> Tuple[int, str]:
    """Report which LabJack driver loaded and one reading, for setting up a computer."""
    from .daq import DAQError, LabJackU6
    from .physics import intensity_for_position, led_for_position, switch_position

    try:
        daq = LabJackU6()
    except DAQError as e:
        return 1, f"FAILED: {e}"
    import LabJackPython

    try:
        pc, bias, color_v, intensity_v = daq.read()
    except DAQError as e:
        return 1, f"FAILED: {e}"
    finally:
        daq.close()
    return 0, "\n".join([
        f"Driver:       {getattr(LabJackPython.staticLib, '_name', '?')}",
        f"Photocurrent: {pc:.4f} nA",
        f"Bias voltage: {bias:.4f} V",
        f"Color switch: {color_v:.3f} V -> {led_for_position(switch_position(color_v)).name}",
        f"Intensity:    {intensity_v:.3f} V -> {intensity_for_position(switch_position(intensity_v))}",
        "OK",
    ])


def report(text: str, ok: bool, output: Optional[str]) -> None:
    if output:
        with open(output, "w") as f:
            f.write(text + "\n")
    elif sys.stdout is not None:
        print(text)
    else:  # the Windows app has no console window
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        (messagebox.showinfo if ok else messagebox.showerror)("Hardware check", text)
        root.destroy()


def main() -> None:
    parser = argparse.ArgumentParser(prog="photoelectric", description="Photoelectric Effect apparatus")
    parser.add_argument("--simulate", action="store_true",
                        help="run without a LabJack, using a simulated apparatus")
    parser.add_argument("--check-hardware", action="store_true",
                        help="report one reading from the LabJack and exit")
    parser.add_argument("--output", metavar="FILE",
                        help="with --check-hardware, write the report to FILE")
    args = parser.parse_args()
    if args.check_hardware:
        code, text = check_hardware()
        report(text, code == 0, args.output)
        sys.exit(code)
    from .gui import run

    run(simulate=args.simulate)


if __name__ == "__main__":
    main()
