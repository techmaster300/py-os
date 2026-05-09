# BlindOS: Python OS Simulator for the Blind

## Overview
A simulated operating system environment written in Python, designed specifically for blind users. It utilizes wxPython for a screen-reader-friendly GUI and integrates both `pyttsx3` and the NVDA Controller Client for robust audio feedback.

## Core Components
1. **Application Shell (wxPython)**
   - Single-window interface with focus management.
   - High-contrast visual feedback (for low-vision users).
   - Keyboard-centric navigation (no mouse required).

2. **Speech Engine**
   - Hybrid approach: Uses `nvda-controller-client` if NVDA is running, falling back to `pyttsx3`.
   - Queued speech to prevent overlapping.
   - Interruptible speech.

3. **Virtual File System (VFS)**
   - Simulated directory structure stored in a JSON or specific local folder.
   - Permissions and file types simulation.

4. **OS Commands**
   - `help`: Speak available commands.
   - `list`: Speak files in current directory.
   - `open <file>`: Read file contents aloud.
   - `create <file>`: Start a guided file creation process.
   - `time`: Speak current system time.
   - `where`: Speak current directory path.

## Implementation Steps
1. **Environment Setup**: Install `wxPython` and `pyttsx3`.
2. **Speech Wrapper**: Create a module that handles speech via NVDA or TTS.
3. **Core Logic**: Implement the VFS and command parser.
4. **GUI Development**: Build the wxPython frame with a command input and a log output.
5. **Integration**: Connect the GUI to the Core Logic and Speech Engine.
6. **Testing**: Verify with keyboard-only navigation.

## Design Decisions
- **Vanilla wxPython**: For standard OS widgets that screen readers recognize natively.
- **NVDA Integration**: Use `nvdaControllerClient64.dll` (if available) for direct communication with NVDA.
