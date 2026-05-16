# PyOS Project Instructions

PyOS is an accessible operating system simulator built with Python and wxPython, specifically designed for blind and visually impaired users. It features a modular architecture, a hybrid speech engine (NVDA/SAPI), and a virtual file system.

## Project Overview

- **Core Goal:** Provide a safe, accessible environment for users to practice file management and system interactions.
- **Main Technologies:** 
    - **UI:** `wxPython` (optimized for screen readers).
    - **Speech:** `pyttsx3` (fallback) and `nvdaControllerClient` (direct NVDA integration).
    - **Audio:** `ffmpeg` and `sounddevice` for themed sound effects.
    - **Kernel:** A Virtual File System (VFS) simulating a Linux-like terminal and directory structure.
- **Architecture:**
    - `desktop.py`: The entry point and main UI coordinator. Handles app discovery and focus management.
    - `api.py`: Defines the `BlindApp` base class and `SystemAPI` bridge used by all plugins.
    - `kernel.py`: Implements the `VirtualOS` which handles command parsing and VFS operations.
    - `speech.py`: Manages the speech queue and backend selection.

## Building and Running

### Prerequisites
- Python 3.x
- FFmpeg (installed and in PATH)

### Commands
- **Run Simulator:** `python desktop.py`
- **Install Dependencies:** `pip install -r requirements.txt`
- **Lint/Syntax Check:** `python -m py_compile <file_path>`

## Development Conventions

### Creating Applications (Plugins)
All new features should be implemented as modular apps in the `apps/` directory.

- **Inheritance:** Every app must inherit from `api.BlindApp`.
- **Mandatory Properties:**
    - `self.name`: The display name of the app.
    - `self.description`: Short text spoken when the app is focused.
    - `self.help_text`: Spoken when the user presses **F1**.
    - `self.docs`: Spoken when the user presses **Ctrl+D**.
- **The `run()` Method:** This is the entry point for your app's UI. Use `wxPython` widgets.
- **Cleanup:** Always bind `wx.EVT_CLOSE` to `self.on_close` to ensure proper focus return to the desktop.

### User Interaction Guidelines
- **Speak, Don't Just Show:** Every visual change or focus shift must be accompanied by `self.api.speak()`.
- **Use System Sounds:** Use `self.api.play_sound(sound_type)` for common actions:
    - `'nav'`: Moving between items.
    - `'launch'`: Opening an app or file.
    - `'close'`: Closing a window.
    - `'alert'`: Errors or warnings.
- **Interruptible Speech:** By default, `self.api.speak(text, interrupt=True)` should be used to stop previous speech, ensuring the user only hears the most recent relevant information.

### Code Style
- Follow PEP 8 guidelines.
- Use explicit imports (avoid `from module import *`).
- Document complex logic with comments, as the user might be "reading" the code via a screen reader.

## Key Files
- `api.py`: The developer interface. Reference this for available API methods.
- `kernel.py`: The command execution engine. Update this to add system-wide terminal commands.
- `desktop.py`: The shell. Modify this for global hotkeys or UI-wide changes.
- `apps/DEVELOPER_GUIDE.md`: Detailed documentation for plugin authors.
