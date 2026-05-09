# BlindOS Simulator

An accessible operating system simulator for blind and visually impaired users.

## Features
- **Hybrid Speech Engine**: Automatically uses NVDA if running (via NVDA Controller Client), falls back to `pyttsx3` for offline TTS.
- **High Contrast GUI**: Built with `wxPython`, optimized for screen readers and low-vision users.
- **Virtual File System**: A safe, sandboxed environment (`/vfs` folder) to practice file management.
- **Keyboard Shortcuts**:
  - `Ctrl + T`: Speak current time.
  - `Ctrl + W`: Speak current location (path).
  - `Enter`: Execute command.

## Commands
- `help`: List available commands.
- `list`: Speak items in the current directory.
- `open <name>`: Open a folder or read a text file.
- `create <name>`: Create a new text file.
- `delete <name>`: Delete a file or empty folder.
- `time`: Speak the current time.
- `where`: Speak current directory.
- `exit`: Close the simulator.

## NVDA Integration (Optional)
To enable direct NVDA support:
1. Download `nvdaControllerClient64.dll` (for 64-bit Python) or `nvdaControllerClient32.dll` (for 32-bit Python) from the [NVDA GitHub Repository](https://github.com/nvaccess/nvda/tree/master/extras/controllerClient).
2. Place the DLL in the same folder as `desktop.py`.

---

## Installation Guide for GitHub

To get started with BlindOS and prepare it for use from source:

1.  **Clone the repository:**
    First, clone the project from GitHub to your local machine. Replace `<repository_url>` with the actual URL of your project's GitHub repository.
    ```bash
    git clone <repository_url>
    cd py-os 
    ```

2.  **Set up a virtual environment (Recommended):**
    Using a virtual environment is highly recommended to manage project dependencies without conflicts.
    ```bash
    # Create a virtual environment (e.g., named 'venv')
    python -m venv venv
    
    # Activate the virtual environment:
    # On Windows:
    .\venv\Scripts\activate
    # On macOS/Linux:
    # source venv/bin/activate
    ```

3.  **Install dependencies:**
    Install all required Python packages using the `requirements.txt` file.
    ```bash
    pip install -r requirements.txt
    ```

4.  **NVDA Controller Client DLL (for direct NVDA integration):**
    If you intend to use the direct NVDA integration feature, follow these steps:
    a. Download the appropriate DLL file: `nvdaControllerClient64.dll` (for 64-bit Python) or `nvdaControllerClient32.dll` (for 32-bit Python) from the [NVDA GitHub Repository extras page](https://github.com/nvaccess/nvda/tree/master/extras/controllerClient).
    b. Copy the downloaded DLL file into the main project directory (the same folder where `desktop.py` is located).

5.  **Run the application:**
    Execute the main application script to launch the simulator.
    ```bash
    python desktop.py
    ```

---
*Note: The compiled executable and build artifacts should be added to your `.gitignore` file if you are committing the source code to GitHub. This prevents large binary files from cluttering the repository.*
