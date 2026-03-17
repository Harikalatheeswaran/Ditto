import argparse
import json
import os
import random
import time
import tkinter as tk
from tkinter import filedialog
from rich.console import Console
from rich.live import Live
from rich.prompt import Confirm, Prompt
from rich.panel import Panel
from rich.align import Align
from rich.rule import Rule
from rich.text import Text

import pynput
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, KeyCode, Controller as KeyboardController, Listener as KeyboardListener

console = Console()

# ==================== CONFIG ====================
HOTKEY = Key.f2               # Press F2 to start/stop recording
EMERGENCY_STOP_KEY = Key.esc
DEFAULT_FILE = "ditto_macro.json"

# Banner texts (replace these placeholders with your full ASCII art whenever you want)
BANNERS = [
    """
 /$$$$$$$  /$$   /$$     /$$              
| $$__  $$|__/  | $$    | $$              
| $$  \\ $$ /$$ /$$$$$$ /$$$$$$    /$$$$$$ 
| $$  | $$| $$|_  $$_/|_  $$_/   /$$__  $$
| $$  | $$| $$  | $$    | $$    | $$  \\ $$
| $$  | $$| $$  | $$ /$$| $$ /$$| $$  | $$
| $$$$$$$/| $$  |  $$$$/|  $$$$/|  $$$$$$/
|_______/ |__/   \\___/   \\___/   \\______/                                
    """,
    """
 ██████████    ███   █████     █████            
░░███░░░░███  ░░░   ░░███     ░░███             
 ░███   ░░███ ████  ███████   ███████    ██████ 
 ░███    ░███░░███ ░░░███░   ░░░███░    ███░░███
 ░███    ░███ ░███   ░███      ░███    ░███ ░███
 ░███    ███  ░███   ░███ ███  ░███ ███░███ ░███
 ██████████   █████  ░░█████   ░░█████ ░░██████ 
░░░░░░░░░░   ░░░░░    ░░░░░     ░░░░░   ░░░░░░                                       
    """,
    """
       ....             .         s         s                
   .xH888888Hx.        @88>      :8        :8                
 .H8888888888888:      %8P      .88       .88           u.   
 888*\"""?""*88888X      .      :888ooo   :888ooo  ...ue888b  
'f     d8x.   ^%88k   .@88u  -*8888888 -*8888888  888R Y888r 
'>    <88888X   '?8  ''888E`   8888      8888     888R I888> 
 `:..:`888888>    8>   888E    8888      8888     888R I888> 
        `"*88     X    888E    8888      8888     888R I888> 
   .xHHhx.."      !    888E   .8888Lu=  .8888Lu= u8888cJ888  
  X88888888hx. ..!     888&   ^%888*    ^%888*    "*888*P"   
 !   "*888888888"      R888"    'Y"       'Y"       'Y"      
        ^"***"`         ""                                   
    """,
]
#---------------------------------------------------------------------------------


def gen(text: str, style: str = 'bold'):
    """Generate Rich-styled string to eliminate repetitive console.print code.
    Example usage:
        console.print(gen("✅ Success!", "bold green"))
        console.print(gen("Press F2 to start", "cyan"))
    """
    return f"[{style}]{text}[/{style}]"
#---------------------------------------------------------------------------------


def sanitize_json_path(path: str) -> str:
    """Ensure the file path always ends with .json.
    - No extension → appends .json automatically.
    - Wrong extension → raises ValueError so the caller can surface a clear error.
    """
    root, ext = os.path.splitext(path)
    if ext == "":
        return root + ".json"
    if ext.lower() != ".json":
        raise ValueError(f"Only .json files are supported, got '{ext}'")
    return path
#---------------------------------------------------------------------------------


def show_banner():
    """Display a centered banner using Rich Panel + Align (called once at startup).
    Picks a random banner from the BANNERS list every run.
    """
    banner_text = random.choice(BANNERS)
    #banner_text = BANNERS[-1]
    panel_content = Align.center(banner_text, vertical="middle")
    
    panel = Panel(
        panel_content,
        title="🤖",
        subtitle=gen("The Ultimate Macro Recorder & Player", "dim cyan"),
        style="bold magenta",
        padding=(2, 6),
        expand=False
    )
    
    console.print(Align.center(panel))
    console.print("")  # breathing space
#---------------------------------------------------------------------------------


def select_macro_file() -> str:
    """Open a native tkinter file dialog so the user can pick a .json macro file.
    Hides the root window so only the clean dialog appears.
    Returns the full path or empty string if user cancels.
    Used only in interactive replay mode.
    """
    root = tk.Tk()
    root.withdraw()                    # hide the empty tkinter window
    file_path = filedialog.askopenfilename(
        title="Select your Ditto Macro File",
        filetypes=[("Ditto Macro Files", "*.json"), ("All files", "*.*")],
        initialdir=os.getcwd()
    )
    root.destroy()
    return file_path
#---------------------------------------------------------------------------------


def serialize_key(key):
    """Convert any pynput key object into a JSON-serializable dictionary.
    Handles both character keys (like 'a') and special keys (like F2, Ctrl, etc.).
    """
    if isinstance(key, KeyCode) and key.char is not None:
        return {"kind": "char", "value": key.char}
    elif hasattr(key, "name"):
        return {"kind": "special", "value": key.name} # type: ignore
    return {"kind": "unknown", "value": str(key)}
#---------------------------------------------------------------------------------


def deserialize_key(data):
    """Convert JSON dictionary back into a valid pynput Key/KeyCode object."""
    if data["kind"] == "char":
        return KeyCode(char=data["value"])
    else:
        try:
            return getattr(Key, data["value"])
        except AttributeError:
            return KeyCode.from_char(data.get("value", ""))
#---------------------------------------------------------------------------------


def get_screen_size():
    """Return current primary screen width & height using tkinter.
    Used only during the bounds-check before replay.
    """
    try:
        root = tk.Tk()
        root.withdraw()
        w = root.winfo_screenwidth()
        h = root.winfo_screenheight()
        root.destroy()
        return w, h
    except Exception:
        console.print(gen("Could not detect screen size (fallback 1920×1080)", "yellow"))
        return 1920, 1080
#---------------------------------------------------------------------------------


def check_bounds(recorded_events):
    """Scan every mouse-click coordinate in the JSON and report any that are outside current screen bounds.
    Extremely useful when replaying on a laptop without the second monitor that was used during recording.
    """
    width, height = get_screen_size()
    out_of_bounds = []
    for item in recorded_events:
        e = item["event"]
        if e.get("type") == "mouse_click":
            x, y = e.get("x", 0), e.get("y", 0)
            if not (0 <= x <= width and 0 <= y <= height):
                out_of_bounds.append((x, y))
    return out_of_bounds, width, height
#---------------------------------------------------------------------------------


def perform_event(item, mouse, keyboard):
    """Replay a single recorded event (mouse click, scroll, or keyboard press/release)."""
    e = item["event"]
    if e["type"] == "mouse_click":
        mouse.position = (e["x"], e["y"])
        btn = getattr(Button, e["button"])
        if e["action"] == "press":
            mouse.press(btn)
        else:
            mouse.release(btn)
    elif e["type"] == "mouse_scroll":
        mouse.position = (e["x"], e["y"])
        mouse.scroll(e.get("dx", 0), e.get("dy", 0))
    elif e["type"] == "keyboard":
        k = deserialize_key(e["key"])
        if e["action"] == "press":
            keyboard.press(k)
        else:
            keyboard.release(k)
#---------------------------------------------------------------------------------


def format_event_description(e: dict) -> str:
    """Return a human-readable one-line description of a recorded event dict."""
    if e["type"] == "mouse_click":
        return f"\U0001f5b1  Mouse {e['button'].upper()} {e['action']:7s} @ ({e['x']:5d}, {e['y']:5d})"
    elif e["type"] == "mouse_scroll":
        return f"\U0001f5b1  Scroll @ ({e['x']:5d}, {e['y']:5d})  dx={e['dx']}  dy={e['dy']}"
    elif e["type"] == "keyboard":
        key_str = e["key"].get("value", "?")
        return f"\u2328   Key {e['action']:7s}  [{key_str}]"
    return f"\u2753  Unknown: {e['type']}"
#---------------------------------------------------------------------------------


def record_mode(file_path: str):
    """RECORD mode – the main recording engine.
    Press F2 once → starts recording.
    Press F2 again → stops and saves to JSON.
    Only records: mouse clicks (with exact coordinates), mouse scrolls, and all keyboard press/release.
    Mouse movement is deliberately ignored (saves huge file size and keeps replay fast).
    """
    console.print(Panel(
        Align.center(gen(f"Saving to: {file_path}", "cyan")),
        title=gen("🚀 DITTO RECORDER", "bold magenta"),
        border_style="magenta",
        padding=(1, 4),
    ))

    is_recording = False
    events = []
    start_time = 0.0
    stopped = False

    def start_recording():
        nonlocal is_recording, start_time, events
        is_recording = True
        start_time = time.monotonic()
        events = []
        console.print(Panel(
            gen("Press F2 again to stop.", "cyan"),
            title=gen("\u2705 RECORDING STARTED!", "bold green"),
            border_style="green",
            padding=(1, 4),
        ))

    def stop_recording():
        nonlocal is_recording, stopped
        is_recording = False
        if not events:
            console.print(Panel(
                gen("Nothing was recorded \u2014 try again.", "yellow"),
                title=gen("\u26a0\ufe0f  No Events Captured", "bold yellow"),
                border_style="yellow",
                padding=(1, 4),
            ))
            stopped = True
            return

        # Convert absolute timestamps → relative delays
        recorded = []
        prev_t = start_time
        for t, ev in events:
            delay = max(0.0, t - prev_t)
            recorded.append({"delay": delay, "event": ev})
            prev_t = t

        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(recorded, f, indent=2)
            console.print(Panel(
                gen(f"Saved {len(recorded)} events → {file_path}", "cyan"),
                title=gen("✅ RECORDING STOPPED", "bold green"),
                border_style="green",
                padding=(1, 4),
            ))
        except OSError as e:
            console.print(Panel(
                gen(str(e), "red"),
                title=gen("❌ Failed to Save Recording", "bold red"),
                border_style="red",
                padding=(1, 4),
            ))
        finally:
            stopped = True

    # ==================== LISTENERS ====================
    def on_move(x, y):
        pass  # Ignored (as requested)

    def on_click(x, y, button, pressed):
        if is_recording:
            ev = {
                "type": "mouse_click",
                "action": "press" if pressed else "release",
                "button": button.name,
                "x": int(x),
                "y": int(y),
            }
            events.append((time.monotonic(), ev))

    def on_scroll(x, y, dx, dy):
        if is_recording:
            ev = {
                "type": "mouse_scroll",
                "x": int(x),
                "y": int(y),
                "dx": dx,
                "dy": dy,
            }
            events.append((time.monotonic(), ev))

    def on_press(key):
        if key == HOTKEY:
            if not is_recording:
                start_recording()
            else:
                stop_recording()
            return  # never record the hotkey itself

        if is_recording:
            ev = {
                "type": "keyboard",
                "action": "press",
                "key": serialize_key(key),
            }
            events.append((time.monotonic(), ev))

    def on_release(key):
        if is_recording:
            ev = {
                "type": "keyboard",
                "action": "release",
                "key": serialize_key(key),
            }
            events.append((time.monotonic(), ev))

    mouse_listener = pynput.mouse.Listener(
        on_move=on_move, on_click=on_click, on_scroll=on_scroll
    )
    kb_listener = KeyboardListener(on_press=on_press, on_release=on_release)

    mouse_listener.start()
    kb_listener.start()

    console.print(Panel(
        gen("Press F2 to start recording.\n", "cyan") +
        gen("Mouse MOVEMENTS are NOT recorded \u2014 only clicks, scrolls & keys.", "dim"),
        title=gen("\u2139\ufe0f  DITTO Ready", "bold"),
        border_style="blue",
        padding=(1, 4),
    ))

    try:
        while not stopped:
            time.sleep(0.2)
    except KeyboardInterrupt:
        console.print(Panel(
            gen("Recording interrupted via Ctrl+C.", "yellow"),
            title=gen("\u26a0\ufe0f  Interrupted", "bold yellow"),
            border_style="yellow",
            padding=(1, 4),
        ))
    finally:
        if mouse_listener.running:
            mouse_listener.stop()
        if kb_listener.running:
            kb_listener.stop()

    console.print(Rule(gen("Recorder Closed", "dim"), style="dim"))
#---------------------------------------------------------------------------------


def replay_mode(file_path: str):
    """REPLAY mode with full safety & emergency stop.
    Loads the JSON, asks for confirmation, optionally runs a bounds check,
    then replays every event with original timing. Press ESC anytime to abort.
    """
    console.print(Panel(
        Align.center(gen("🎥 DITTO REPLAYER", "bold magenta")),
        border_style="magenta",
        padding=(1, 6),
    ))

    if not os.path.exists(file_path):
        console.print(Panel(
            gen(f"File not found:\n  {file_path}", "red"),
            title=gen("❌ Error", "bold red"),
            border_style="red",
            padding=(1, 4),
        ))
        return

    try:
        with open(file_path, encoding="utf-8") as f:
            recorded = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        console.print(Panel(
            gen(str(e), "red"),
            title=gen("❌ Failed to Load Macro File", "bold red"),
            border_style="red",
            padding=(1, 4),
        ))
        return

    console.print(Panel(
        gen(f"{len(recorded)} events loaded from:\n", "cyan") +
        gen(f"  {file_path}", "dim"),
        title=gen("\U0001f4c2 Macro Loaded", "bold"),
        border_style="blue",
        padding=(1, 4),
    ))

    if not Confirm.ask(gen("⚠️  REPLAY will control your mouse & keyboard!", "yellow") + "\nContinue?", default=False):
        return

    # ── Bounds check ──
    if Confirm.ask(gen("Run bounds check first? (catches missing extra displays)", "cyan"), default=True):
        out_of_bounds, w, h = check_bounds(recorded)
        if out_of_bounds:
            console.print(Panel(
                gen(f"{len(out_of_bounds)} click(s) are outside the current screen boundary ({w}×{h}).\n", "bold red") +
                gen("This usually happens when replaying without the same monitor setup used during recording.", "dim"),
                title=gen("⚠️  Bounds Warning", "bold yellow"),
                border_style="yellow",
                padding=(1, 4),
            ))
            if not Confirm.ask(gen("Continue anyway?", "yellow"), default=False):
                return
        else:
            console.print(Panel(
                gen("All coordinates are within current screen bounds.", "green"),
                title=gen("✅ Bounds OK", "bold green"),
                border_style="green",
                padding=(1, 4),
            ))

    # ── Ask about live event view ──
    show_events = Confirm.ask(gen("Show events live as they replay?", "cyan"), default=False)

    # ── Replay with emergency stop ──
    mouse = MouseController()
    keyboard = KeyboardController()
    stop_replay = False

    def on_emergency(key):
        nonlocal stop_replay
        if key == EMERGENCY_STOP_KEY:
            stop_replay = True
            return False

    stop_listener = KeyboardListener(on_press=on_emergency) # type: ignore
    stop_listener.start()

    total = len(recorded)
    pad = len(str(total))

    console.print(Panel(
        gen("▶️  Replaying now...\n", "yellow") +
        gen("Press ESC to abort instantly.", "dim"),
        border_style="yellow",
        padding=(1, 4),
    ))

    if show_events:
        event_lines: list = []

        def make_event_panel() -> Panel:
            t = Text()
            for line in event_lines:
                t.append(line + "\n")
            return Panel(
                t,
                title=gen("🎬 Live Event Feed", "bold cyan"),
                subtitle=gen(f"  {len(event_lines)} / {total}  ", "dim"),
                border_style="cyan",
                padding=(0, 2),
            )

        try:
            with Live(make_event_panel(), console=console, refresh_per_second=15, vertical_overflow="visible") as live:
                for i, item in enumerate(recorded):
                    if stop_replay:
                        break
                    time.sleep(item["delay"])
                    perform_event(item, mouse, keyboard)
                    desc = format_event_description(item["event"])
                    event_lines.append(f"  [{i + 1:>{pad}}/{total}]  {desc}  +{item['delay']:.3f}s")
                    live.update(make_event_panel())
        except Exception as ex:
            console.print(Panel(
                gen(str(ex), "red"),
                title=gen("❌ Error During Replay", "bold red"),
                border_style="red",
                padding=(1, 4),
            ))
    else:
        try:
            for item in recorded:
                if stop_replay:
                    break
                time.sleep(item["delay"])
                perform_event(item, mouse, keyboard)
        except Exception as ex:
            console.print(Panel(
                gen(str(ex), "red"),
                title=gen("❌ Error During Replay", "bold red"),
                border_style="red",
                padding=(1, 4),
            ))

    if stop_listener.running:
        stop_listener.stop()

    if stop_replay:
        console.print(Panel(
            gen("Replay was aborted by pressing ESC.", "yellow"),
            title=gen("⛔ Emergency Stop", "bold red"),
            border_style="red",
            padding=(1, 4),
        ))
    else:
        console.print(Panel(
            gen(f"All {total} events replayed successfully.", "green"),
            title=gen("✅ Replay Finished", "bold green"),
            border_style="green",
            padding=(1, 4),
        ))
#---------------------------------------------------------------------------------


def main():
    """Main entry point.
    1. Shows the beautiful random banner.
    2. If user passed "record" or "replay" on command line → runs directly (CLI mode).
    3. If no argument given → interactive mode using Rich Prompt + tkinter file dialog for replay.
    """
    show_banner()

    parser = argparse.ArgumentParser(
        description="DITTO - The simple but powerful macro recorder & player (pynput + Rich)"
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["record", "replay"],
        default=None,
        help="record or replay (leave blank for interactive menu)"
    )
    parser.add_argument("--file", "-f", default=DEFAULT_FILE, help="JSON file path (CLI only)")
    args = parser.parse_args()

    # Validate / fix the --file extension early in CLI mode
    if args.mode is not None:
        try:
            args.file = sanitize_json_path(args.file)
        except ValueError as e:
            console.print(Panel(gen(str(e), "red"), title=gen("\u274c Invalid Filename", "bold red"), border_style="red", padding=(1, 4)))
            return

    if args.mode is None:
        # ==================== INTERACTIVE MODE ====================
        console.print(Rule(gen("Interactive Mode", "dim"), style="dim"))

        try:
            console.print(Panel(
                gen("  1. Record\n", "cyan") +
                gen("  2. Replay", "cyan"),
                title=gen("\U0001f3db  Select an Option", "bold"),
                border_style="blue",
                padding=(1, 4),
            ))

            choice = Prompt.ask(
                gen("Your choice"),
                choices=["1", "2"],
                default="1"
            )
            mode = "record" if choice == "1" else "replay"

            if mode == "record":
                raw_path = Prompt.ask(
                    gen("Enter filename to save the macro"),
                    default=DEFAULT_FILE
                )
                try:
                    file_path = sanitize_json_path(raw_path)
                except ValueError as e:
                    console.print(Panel(gen(str(e), "red"), title=gen("\u274c Invalid Filename", "bold red"), border_style="red", padding=(1, 4)))
                    return
                try:
                    record_mode(file_path)
                except Exception as e:
                    console.print(Panel(
                        gen(str(e), "red"),
                        title=gen("\u274c Recording Failed", "bold red"),
                        border_style="red",
                        padding=(1, 4),
                    ))
            else:
                console.print(gen("Please select your macro file...", "cyan"))
                try:
                    file_path = select_macro_file()
                    if not file_path:
                        console.print(gen("No file selected. Goodbye!", "yellow"))
                        return
                    replay_mode(file_path)
                except Exception as e:
                    console.print(Panel(
                        gen(str(e), "red"),
                        title=gen("\u274c Replay Failed", "bold red"),
                        border_style="red",
                        padding=(1, 4),
                    ))

        except KeyboardInterrupt:
            console.print(Panel(gen("Goodbye!", "yellow"), title=gen("\u26a0\ufe0f  Interrupted", "bold yellow"), border_style="yellow", padding=(1, 4)))
        except Exception as e:
            console.print(Panel(gen(str(e), "red"), title=gen("\u274c Unexpected Error", "bold red"), border_style="red", padding=(1, 4)))

    else:
        # ==================== CLI MODE ====================
        file_path = args.file
        try:
            if args.mode == "record":
                record_mode(file_path)
            else:
                replay_mode(file_path)
        except KeyboardInterrupt:
            console.print(Panel(gen("Goodbye!", "yellow"), title=gen("\u26a0\ufe0f  Interrupted", "bold yellow"), border_style="yellow", padding=(1, 4)))
        except Exception as e:
            console.print(Panel(gen(str(e), "red"), title=gen("\u274c Unexpected Error", "bold red"), border_style="red", padding=(1, 4)))
#---------------------------------------------------------------------------------


if __name__ == "__main__":
    #console.print(gen("Dependencies: pip install pynput rich", "dim"))
    try:
        main()
    except KeyboardInterrupt:
        console.print(Panel(gen("Goodbye!", "yellow"), title=gen("\u26a0\ufe0f  Aborted", "bold yellow"), border_style="yellow", padding=(1, 4)))
    except Exception as e:
        console.print(Panel(gen(str(e), "red"), title=gen("\u274c Fatal Error", "bold red"), border_style="red", padding=(1, 4)))