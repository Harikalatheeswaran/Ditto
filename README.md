
---
# *__🤖 Ditto : The Ultimate Macro Recorder & Player__*
```
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
    
```
---

- Ditto is a lightweight Python tool that records your mouse and keyboard actions and replays them exactly, with original timing.
- It runs entirely in the terminal with a beautiful [Rich](https://github.com/Textualize/rich) UI.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🖱 Mouse recording | Captures clicks (left, right, middle) and scrolls with exact screen coordinates |
| ⌨️ Keyboard recording | Captures every key press and release, including special keys (Ctrl, Alt, F-keys, etc.) |
| ⏱ Timing preservation | Replays events with the exact delays between them, just as you performed them |
| 🎬 Live event feed | Optionally shows a live updating panel of every event as it fires during replay |
| 🖥 Bounds check | Detects clicks that fall outside the current screen — critical when replaying on a different monitor setup |
| ⛔ Emergency stop | Press `ESC` at any point during replay to abort instantly |
| 📁 File validation | Only `.json` files accepted; extension is auto-appended if omitted |
| 🎨 Rich terminal UI | Every status message, prompt, and error is displayed in a colour-coded panel |
| 🖥 Dual-mode | Run interactively (menu-driven) or headlessly via CLI arguments |

---

## 📦 Requirements

- Python ≥ 3.14
- pip dependencies:

```
pynput
rich
```

Install everything with:

```bash
pip install pynput rich
```

Or, if using the included `pyproject.toml` with a virtual environment:

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -e .
```

---

## 🚀 Usage

### Interactive mode (recommended)

Just run the script with no arguments:

```bash
python ditto.py
```

You will be presented with a menu:

```
╭─────────────────── 🏛  Select an Option ───────────────────╮
│   1. Record                                                │
│   2. Replay                                                │
╰────────────────────────────────────────────────────────────╯
Your choice [1/2] (1):
```

### CLI mode (scripting / automation)

```bash
# Record to a specific file
python ditto.py record --file my_macro.json

# Replay from a specific file
python ditto.py replay --file my_macro.json

# Extension is optional — .json is appended automatically
python ditto.py record --file my_macro
```

Full argument reference:

```
usage: ditto.py [-h] [--file FILE] [{record,replay}]

positional arguments:
  {record,replay}    record or replay (leave blank for interactive menu)

options:
  -h, --help         show this help message and exit
  --file, -f FILE    JSON file path  (default: ditto_macro.json)
```

---

## 🎙 Recording a Macro

1. Run `python ditto.py` and choose **1. Record**, or run `python ditto.py record`.
2. Enter a filename (or press Enter to use the default `ditto_macro.json`).
3. Ditto waits — your terminal will show:

   ```
   ╭────────────── ℹ️ DITTO Ready ──────────────╮
   │  Press F2 to start recording.               │
   │  Mouse MOVEMENTS are NOT recorded —         │
   │  only clicks, scrolls & keys.               │
   ╰─────────────────────────────────────────────╯
   ```

4. **Press `F2`** — recording starts immediately.
5. Perform all the actions you want to record (clicks, scrolls, typing).
6. **Press `F2` again** — recording stops and the macro is saved to the JSON file.

> **Note:** Mouse *movement* is deliberately **not** recorded. Only clicks, scrolls, and key events are captured. This keeps file sizes small and replays fast.

### Hotkeys during recording

| Key | Action |
|---|---|
| `F2` | Toggle recording start / stop |
| `Ctrl+C` | Abort Ditto immediately (recording is discarded) |

---

## ▶️ Replaying a Macro

1. Run `python ditto.py` and choose **2. Replay**, or run `python ditto.py replay`.
2. In interactive mode, a native file picker dialog opens — select your `.json` macro file.
3. Ditto shows how many events were loaded and asks a series of safety prompts:

### Safety prompts (in order)

**① Confirmation**
```
⚠️  REPLAY will control your mouse & keyboard!
Continue? [y/n] (n):
```
Default is **No** — you must explicitly type `y` to proceed.

**② Bounds check** *(optional but recommended)*
```
Run bounds check first? (catches missing extra displays) [y/n] (y):
```
Scans every recorded click coordinate against your current screen resolution. If any coordinates fall outside your screen (e.g. because you recorded on a dual-monitor setup but are now on a laptop), you get a warning and can choose to abort or continue anyway.

**③ Live event feed** *(optional)*
```
Show events live as they replay? [y/n] (n):
```
- **No** — silent replay, nothing printed.
- **Yes** — a live `🎬 Live Event Feed` panel is displayed and updates in real-time as each event fires, showing the event number, type, description, and timing:

  ```
  ╭──────────────────── 🎬 Live Event Feed ───────────────────────╮
  │  [  1/42]  🖱  Mouse LEFT   press  @  ( 512,  300)  +0.000s    │
  │  [  2/42]  🖱  Mouse LEFT   release @  ( 512,  300)  +0.082s   │
  │  [  3/42]  ⌨   Key press    [h]  +0.201s                      │
  │  ...                                                           │
  ╰──────────────────────── 3 / 42 ────────────────────────────────╯
  ```

### Emergency stop during replay

Press **`ESC`** at any time to abort the replay immediately. A confirmation panel is shown:

```
╭──────── ⛔ Emergency Stop ────────────╮
│  Replay was aborted by pressing ESC.   │
╰────────────────────────────────────────╯
```

---

## 📄 Macro File Format

Macros are saved as plain `.json` files. Each file is a list of event objects with a `delay` (seconds since the previous event) and an `event` descriptor:

```json
[
  {
    "delay": 0.0,
    "event": {
      "type": "mouse_click",
      "action": "press",
      "button": "left",
      "x": 512,
      "y": 300
    }
  },
  {
    "delay": 0.082,
    "event": {
      "type": "keyboard",
      "action": "press",
      "key": { "kind": "char", "value": "h" }
    }
  }
]
```

Supported event types: `mouse_click`, `mouse_scroll`, `keyboard`.

### File naming rules

- Only `.json` files are accepted.
- If you omit the extension, Ditto appends `.json` automatically.
- Any other extension (e.g. `.txt`, `.csv`) is rejected immediately with a clear error.

---

## ⚙️ Configuration

Open `ditto.py` and edit the constants at the top to customise behaviour:

```python
HOTKEY            = Key.f2    # Key to start/stop recording
EMERGENCY_STOP_KEY = Key.esc  # Key to abort replay
DEFAULT_FILE      = "ditto_macro.json"  # Default save filename
```

---

## 🗂 Project Structure

```
Ditto/
├── ditto.py          # Main script — all logic lives here
└── README.md         # This file
```

---
