# TinyTask for Linux

A clone of [Tiny Task](https://web.archive.org/web/20171016105935/http://www.vtaskstudio.com/tinytask.php) for Linux. Tested on Hyprland Wayland Compositor.

---

## Demo

https://github.com/user-attachments/assets/cdd741f8-a761-4249-b063-c539d0857064

---

## Requirements
- **Python**: 3.7 or higher
- **pynput**
- **PyQt5**
- **tkinter** 
- **Elevated privileges**: Some features (global input capture) may require running as root, especially on Wayland.

---

## Quick Start

```bash
# Clone the repo
cd tinytask

# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run the enhanced GUI
python tinytask_enhanced.py
```

---

## Features

- **Record and Playback**: Mouse movements, clicks, scrolls, and keyboard inputs
- **Save/Load Macros**: Store macros as JSON files
- **Speed Control**: Playback speed from 0.1x to 5.0x
- **Loop Playback**: Run macros multiple times (1-999 loops)
- **Hotkey Support**: F8 (Record/Stop), F5 (Play), F9 (Stop Recording)
- **Macro Compilation**: Generate standalone Python scripts
- **Pause/Resume**: Control playback during execution
- **Statistics**: See macro details after recording

---

## Installation

### Option 1: Virtual Environment (Recommended)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### Option 2: System-wide Installation
```bash
# Arch Linux
sudo pacman -S python-pynput python-pyqt5

# Ubuntu/Debian
sudo apt install python3-pynput python3-pyqt5

# Other distros
pip install --break-system-packages pynput PyQt5
```

### Option 3: Arch Package Installation
If you want a system-wide install via Arch packaging:
```bash
# Build and install using PKGBUILD (requires base-devel group)
sudo pacman -S base-devel
makepkg -si
```
This will install TinyTask Enhanced as `/usr/bin/tinytask-enhanced` and add a desktop entry for your launcher menu.

---

## Usage

```bash
python tinytask_enhanced.py
```

---

## Hotkeys
| Key | Action |
|-----|--------|
| F8  | Start/Stop Recording |
| F5  | Play Macro |
| F9  | Stop Recording (while recording) |

---

## Macro Workflow

### Recording Macros
1. Click "Record" or press F8
2. Perform actions to automate
3. Click "Stop Recording", press F8 again, or F9
4. Save macro with "Save" or "Save As"

### Playing Macros
1. Load macro with "Load"
2. Set playback speed, loop count, mouse movement recording
3. Click "Play" or press F5
4. Use Pause/Resume and Stop as needed

### Macro Compilation
1. Record or load a macro
2. Click "Compile"
3. Choose output filename
4. Run the generated script independently

---

## License
Open source. Modify and distribute as you wish.

## Contributing
Pull requests welcome! Please test on multiple desktop environments and display servers.

## Support
For issues, include:
- Distribution and version
- Desktop environment
- Display server (X11/Wayland)
- Python version
- Error messages or unexpected behavior

---

## Changelog
### v0.1.0 
- Display server detection
- Safe key parsing (no eval())
- Speed control and looping
- Macro compilation
- Enhanced GUI with progress
- Pause/resume
- Improved error handling
