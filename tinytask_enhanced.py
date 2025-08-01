#!/usr/bin/env python3
"""
TinyTask for Linux - Enhanced GUI Version
A comprehensive macro recorder and player with full TinyTask feature parity
Tested on Hyprland Wayland compositor
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import json
import os
import sys
import time

# Try to import required dependencies
try:
    from pynput import mouse, keyboard
    from pynput.keyboard import Key, KeyCode
except ImportError as e:
    print(f"Missing required dependencies: {e}")
    print("Please install with: pip install pynput PyQt5")
    print("Or if using virtual environment: source .venv/bin/activate && pip install pynput PyQt5")
    sys.exit(1)


class DisplayServerInfo:
    """Detect and handle different display servers and desktop environments"""

    def __init__(self):
        self.session_type = os.environ.get('XDG_SESSION_TYPE', 'unknown')
        self.desktop = os.environ.get('XDG_CURRENT_DESKTOP', 'unknown')
        self.wayland_display = os.environ.get('WAYLAND_DISPLAY')
        self.x11_display = os.environ.get('DISPLAY')

    def get_info(self):
        return {
            'session_type': self.session_type,
            'desktop': self.desktop,
            'wayland_display': self.wayland_display,
            'x11_display': self.x11_display,
            'is_wayland': self.session_type == 'wayland',
            'is_x11': self.session_type == 'x11',
            'supports_recording': self._supports_recording()
        }

    def _supports_recording(self):
        """Check if the current environment supports input recording"""
        try:
            # Test if we can create mouse/keyboard controllers
            mouse.Controller()
            keyboard.Controller()
            return True
        except Exception:
            return False


class SafeKeyParser:
    """Safely parse keyboard events without using eval()"""

    @staticmethod
    def parse_key(key_str):
        """Parse key string safely"""
        if key_str.startswith("Key."):
            # Handle special keys like Key.space, Key.enter, etc.
            key_name = key_str.split('.')[1]
            return getattr(Key, key_name, key_str)
        elif key_str.startswith("'") and key_str.endswith("'") and len(key_str) == 3:
            # Handle single character keys like 'a', 'b', etc.
            return key_str[1]
        else:
            # Handle other cases
            try:
                return KeyCode.from_char(key_str)
            except:
                return key_str

    @staticmethod
    def key_to_string(key):
        """Convert key to string representation"""
        if hasattr(key, 'char') and key.char:
            return f"'{key.char}'"
        else:
            return str(key)


class EnhancedRecorder:
    def __init__(self):
        self.events = []
        self.recording = False
        self.start_time = None
        self.mouse_listener = None
        self.keyboard_listener = None
        self.stop_event = threading.Event()
        self.hotkey_stop = False
        self.mouse_move_threshold = 5  # Minimum pixel movement to record
        self.last_mouse_pos = (0, 0)
        self.record_mouse_moves = True
        self.display_info = DisplayServerInfo()

    def _record_event(self, event_type, event_data):
        if not self.recording:
            return
        timestamp = time.time() - self.start_time
        self.events.append({
            'type': event_type,
            'data': event_data,
            'time': timestamp
        })

    def _on_click(self, x, y, button, pressed):
        self._record_event('mouse_click', {
            'x': x, 'y': y,
            'button': str(button),
            'pressed': pressed
        })

    def _on_move(self, x, y):
        if not self.record_mouse_moves:
            return

        # Only record if movement exceeds threshold
        last_x, last_y = self.last_mouse_pos
        if abs(x - last_x) >= self.mouse_move_threshold or abs(y - last_y) >= self.mouse_move_threshold:
            self._record_event('mouse_move', {'x': x, 'y': y})
            self.last_mouse_pos = (x, y)

    def _on_scroll(self, x, y, dx, dy):
        self._record_event('mouse_scroll', {
            'x': x, 'y': y,
            'dx': dx, 'dy': dy
        })

    def _on_press(self, key):
        key_str = SafeKeyParser.key_to_string(key)
        self._record_event('key_press', {'key': key_str})

        # Check for stop hotkey (F9 by default)
        if key == Key.f9:
            self.stop()

    def _on_release(self, key):
        key_str = SafeKeyParser.key_to_string(key)
        self._record_event('key_release', {'key': key_str})

    def start(self):
        """Start recording"""
        self.events = []
        self.recording = True
        self.start_time = time.time()
        self.stop_event.clear()
        self.hotkey_stop = False

        try:
            self.mouse_listener = mouse.Listener(
                on_click=self._on_click,
                on_move=self._on_move,
                on_scroll=self._on_scroll
            )
            self.keyboard_listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release
            )

            self.mouse_listener.start()
            self.keyboard_listener.start()

            # Wait until stop_event is set
            self.stop_event.wait()

        except Exception as e:
            print(f"Recording error: {e}")
        finally:
            self._cleanup_listeners()

    def stop(self):
        """Stop recording"""
        self.stop_event.set()
        self.recording = False

    def _cleanup_listeners(self):
        """Clean up listeners"""
        if self.mouse_listener:
            self.mouse_listener.stop()
        if self.keyboard_listener:
            self.keyboard_listener.stop()

    def save(self, filename):
        """Save recorded events to file"""
        with open(filename, 'w') as f:
            json.dump(self.events, f, indent=2)

    def load(self, filename):
        """Load events from file"""
        with open(filename, 'r') as f:
            self.events = json.load(f)

    def get_stats(self):
        """Get recording statistics"""
        if not self.events:
            return {}

        stats = {
            'total_events': len(self.events),
            'duration': self.events[-1]['time'] if self.events else 0,
            'mouse_clicks': len([e for e in self.events if e['type'] == 'mouse_click']),
            'mouse_moves': len([e for e in self.events if e['type'] == 'mouse_move']),
            'key_presses': len([e for e in self.events if e['type'] == 'key_press']),
        }
        return stats


class EnhancedPlayer:
    def __init__(self, events):
        self.events = events
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
        self.playing = False
        self.paused = False
        self.speed_multiplier = 1.0
        self.loop_count = 1
        self.current_loop = 0

    def play(self, speed=1.0, loops=1, callback=None):
        """Play recorded events with speed control and looping"""
        self.speed_multiplier = speed
        self.loop_count = loops
        self.current_loop = 0
        self.playing = True

        try:
            while self.current_loop < self.loop_count and self.playing:
                self._play_sequence(callback)
                self.current_loop += 1

                if self.current_loop < self.loop_count:
                    time.sleep(0.1)  # Small delay between loops

        except Exception as e:
            print(f"Playback error: {e}")
        finally:
            self.playing = False

    def _play_sequence(self, callback=None):
        """Play single sequence of events"""
        if not self.events:
            return

        start_time = time.time()
        for i, event in enumerate(self.events):
            if not self.playing:
                break

            # Handle pause
            while self.paused and self.playing:
                time.sleep(0.1)

            if not self.playing:
                break

            # Calculate delay with speed multiplier
            target_time = event['time'] / self.speed_multiplier
            elapsed = time.time() - start_time
            delay = max(0, target_time - elapsed)

            if delay > 0:
                time.sleep(delay)

            # Execute event
            self._execute_event(event)

            # Update callback
            if callback:
                progress = (i + 1) / len(self.events)
                callback(progress, self.current_loop + 1, self.loop_count)

    def _execute_event(self, event):
        """Execute a single event"""
        try:
            if event['type'] == 'mouse_move':
                self.mouse_controller.position = (
                    event['data']['x'], event['data']['y'])

            elif event['type'] == 'mouse_click':
                btn_str = event['data']['button'].split('.')[-1]
                btn = getattr(mouse.Button, btn_str)
                if event['data']['pressed']:
                    self.mouse_controller.press(btn)
                else:
                    self.mouse_controller.release(btn)

            elif event['type'] == 'mouse_scroll':
                self.mouse_controller.scroll(
                    event['data']['dx'], event['data']['dy'])

            elif event['type'] == 'key_press':
                key = SafeKeyParser.parse_key(event['data']['key'])
                self.keyboard_controller.press(key)

            elif event['type'] == 'key_release':
                key = SafeKeyParser.parse_key(event['data']['key'])
                self.keyboard_controller.release(key)

        except Exception as e:
            print(f"Error executing event {event['type']}: {e}")

    def stop(self):
        """Stop playback"""
        self.playing = False

    def pause(self):
        """Pause playback"""
        self.paused = True

    def resume(self):
        """Resume playback"""
        self.paused = False


class MacroCompiler:
    """Compile macros to standalone executables"""

    @staticmethod
    def compile_to_script(events, output_path, python_path=None):
        """Compile macro to Python script"""
        if python_path is None:
            python_path = sys.executable

        script_content = f'''#!/usr/bin/env python3
"""
Generated macro script - TinyTask for Linux
Generated on: {time.strftime('%Y-%m-%d %H:%M:%S')}
"""

import json
import time
from pynput import mouse, keyboard

# Macro events
EVENTS = {json.dumps(events, indent=2)}

class MacroPlayer:
    def __init__(self):
        self.mouse_controller = mouse.Controller()
        self.keyboard_controller = keyboard.Controller()
    
    def parse_key(self, key_str):
        """Parse key string safely"""
        if key_str.startswith("Key."):
            key_name = key_str.split('.')[1]
            return getattr(keyboard.Key, key_name, key_str)
        elif key_str.startswith("'") and key_str.endswith("'") and len(key_str) == 3:
            return key_str[1]
        else:
            try:
                return keyboard.KeyCode.from_char(key_str)
            except:
                return key_str
    
    def play(self):
        print("Playing macro...")
        start_time = time.time()
        
        for event in EVENTS:
            time.sleep(max(0, event['time'] - (time.time() - start_time)))
            
            if event['type'] == 'mouse_move':
                self.mouse_controller.position = (event['data']['x'], event['data']['y'])
            elif event['type'] == 'mouse_click':
                btn = getattr(mouse.Button, event['data']['button'].split('.')[-1])
                if event['data']['pressed']:
                    self.mouse_controller.press(btn)
                else:
                    self.mouse_controller.release(btn)
            elif event['type'] == 'mouse_scroll':
                self.mouse_controller.scroll(event['data']['dx'], event['data']['dy'])
            elif event['type'] == 'key_press':
                key = self.parse_key(event['data']['key'])
                self.keyboard_controller.press(key)
            elif event['type'] == 'key_release':
                key = self.parse_key(event['data']['key'])
                self.keyboard_controller.release(key)
        
        print("Macro completed!")

if __name__ == "__main__":
    player = MacroPlayer()
    player.play()
'''

        with open(output_path, 'w') as f:
            f.write(script_content)

        # Make executable
        os.chmod(output_path, 0o755)
        return True


class EnhancedTinyTaskGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("TinyTask for Linux - Enhanced")
        self.root.geometry("600x500")

        # Initialize components
        self.recorder = EnhancedRecorder()
        self.player = None
        self.is_recording = False
        self.is_playing = False

        # Variables
        self.status_var = tk.StringVar(value="Ready")
        self.progress_var = tk.DoubleVar()
        self.speed_var = tk.DoubleVar(value=1.0)
        self.loops_var = tk.IntVar(value=1)
        self.record_moves_var = tk.BooleanVar(value=True)

        # Current file
        self.current_file = None

        # Threading
        self.record_thread = None
        self.play_thread = None

        self.create_widgets()
        self.update_display_info()

        # Setup hotkeys
        self.setup_global_hotkeys()

    def create_widgets(self):
        """Create all GUI widgets"""
        # Main frame
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Control buttons frame
        control_frame = ttk.LabelFrame(main_frame, text="Controls", padding=10)
        control_frame.pack(fill=tk.X, pady=(0, 10))

        # Record/Stop button
        self.record_btn = ttk.Button(control_frame, text="Record (F8)",
                                     command=self.toggle_record, width=15)
        self.record_btn.grid(row=0, column=0, padx=5, pady=5)

        # Play button
        self.play_btn = ttk.Button(control_frame, text="Play (F5)",
                                   command=self.play, width=15)
        self.play_btn.grid(row=0, column=1, padx=5, pady=5)

        # Pause button
        self.pause_btn = ttk.Button(control_frame, text="Pause",
                                    command=self.pause_resume, width=15)
        self.pause_btn.grid(row=0, column=2, padx=5, pady=5)

        # Stop button
        self.stop_btn = ttk.Button(control_frame, text="Stop",
                                   command=self.stop_playback, width=15)
        self.stop_btn.grid(row=0, column=3, padx=5, pady=5)

        # File operations frame
        file_frame = ttk.LabelFrame(
            main_frame, text="File Operations", padding=10)
        file_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Button(file_frame, text="Save", command=self.save,
                   width=12).grid(row=0, column=0, padx=5)
        ttk.Button(file_frame, text="Load", command=self.load,
                   width=12).grid(row=0, column=1, padx=5)
        ttk.Button(file_frame, text="Save As", command=self.save_as,
                   width=12).grid(row=0, column=2, padx=5)
        ttk.Button(file_frame, text="Compile", command=self.compile_macro,
                   width=12).grid(row=0, column=3, padx=5)

        # Settings frame
        settings_frame = ttk.LabelFrame(
            main_frame, text="Settings", padding=10)
        settings_frame.pack(fill=tk.X, pady=(0, 10))

        # Speed control
        ttk.Label(settings_frame, text="Speed:").grid(
            row=0, column=0, sticky=tk.W)
        speed_scale = ttk.Scale(settings_frame, from_=0.1, to=5.0,
                                variable=self.speed_var, orient=tk.HORIZONTAL, length=200)
        speed_scale.grid(row=0, column=1, padx=5, sticky=tk.W)
        self.speed_label = ttk.Label(settings_frame, text="1.0x")
        self.speed_label.grid(row=0, column=2, padx=5)
        speed_scale.configure(command=self.update_speed_label)

        # Loop control
        ttk.Label(settings_frame, text="Loops:").grid(
            row=1, column=0, sticky=tk.W)
        ttk.Spinbox(settings_frame, from_=1, to=999, textvariable=self.loops_var,
                    width=10).grid(row=1, column=1, padx=5, sticky=tk.W)

        # Record mouse moves
        ttk.Checkbutton(settings_frame, text="Record mouse movements",
                        variable=self.record_moves_var,
                        command=self.update_record_moves).grid(row=2, column=0, columnspan=2, sticky=tk.W)

        # Progress frame
        progress_frame = ttk.LabelFrame(
            main_frame, text="Progress", padding=10)
        progress_frame.pack(fill=tk.X, pady=(0, 10))

        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var,
                                            maximum=100, length=400)
        self.progress_bar.pack(fill=tk.X, pady=5)

        # Status and info frame
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding=10)
        info_frame.pack(fill=tk.BOTH, expand=True)

        # Status label
        self.status_label = ttk.Label(info_frame, textvariable=self.status_var,
                                      foreground="blue", font=("TkDefaultFont", 10, "bold"))
        self.status_label.pack(pady=5)

        # Info text area
        self.info_text = tk.Text(info_frame, height=8, wrap=tk.WORD)
        scrollbar = ttk.Scrollbar(
            info_frame, orient=tk.VERTICAL, command=self.info_text.yview)
        self.info_text.configure(yscrollcommand=scrollbar.set)

        self.info_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    def setup_global_hotkeys(self):
        """Setup global hotkeys (F8 for record, F5 for play)"""
        try:
            # Note: Global hotkeys might not work in all environments
            # This is a basic implementation
            self.root.bind('<F8>', lambda e: self.toggle_record())
            self.root.bind('<F5>', lambda e: self.play())
            self.root.focus_set()  # Ensure window can receive key events
        except Exception as e:
            print(f"Could not setup global hotkeys: {e}")

    def update_display_info(self):
        """Update display server information"""
        info = self.recorder.display_info.get_info()
        info_text = f"""Display Server Information:
Session Type: {info['session_type']}
Desktop Environment: {info['desktop']}
Wayland Display: {info['wayland_display'] or 'Not available'}
X11 Display: {info['x11_display'] or 'Not available'}
Recording Support: {'Yes' if info['supports_recording'] else 'No'}

Hotkeys:
F8 - Start/Stop Recording
F5 - Play Macro
F9 - Stop Recording (while recording)

Current File: {self.current_file or 'None'}
"""
        self.info_text.delete(1.0, tk.END)
        self.info_text.insert(1.0, info_text)

    def update_speed_label(self, value):
        """Update speed label"""
        speed = float(value)
        self.speed_label.config(text=f"{speed:.1f}x")

    def update_record_moves(self):
        """Update mouse movement recording setting"""
        self.recorder.record_mouse_moves = self.record_moves_var.get()

    def toggle_record(self):
        """Toggle recording state"""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        """Start recording"""
        if self.is_playing:
            messagebox.showwarning(
                "Busy", "Cannot record while playing. Stop playback first.")
            return

        self.is_recording = True
        self.status_var.set(
            "Recording... Press F9 to stop or click 'Record' again")
        self.record_btn.config(text="Stop Recording")

        # Disable other controls
        self.play_btn.config(state=tk.DISABLED)

        # Start recording in separate thread
        self.record_thread = threading.Thread(target=self._record_worker)
        self.record_thread.daemon = True
        self.record_thread.start()

    def _record_worker(self):
        """Worker thread for recording"""
        try:
            self.recorder.start()
        except Exception as e:
            messagebox.showerror("Recording Error", f"Failed to record: {e}")
        finally:
            # Update UI in main thread
            self.root.after(0, self._recording_finished)

    def _recording_finished(self):
        """Called when recording is finished"""
        self.is_recording = False
        self.status_var.set("Recording finished")
        self.record_btn.config(text="Record (F8)")
        self.play_btn.config(state=tk.NORMAL)

        # Update statistics
        stats = self.recorder.get_stats()
        if stats:
            stats_text = f"\nRecording Statistics:\n"
            stats_text += f"Total Events: {stats['total_events']}\n"
            stats_text += f"Duration: {stats['duration']:.2f} seconds\n"
            stats_text += f"Mouse Clicks: {stats['mouse_clicks']}\n"
            stats_text += f"Mouse Moves: {stats['mouse_moves']}\n"
            stats_text += f"Key Presses: {stats['key_presses']}\n"

            current_text = self.info_text.get(1.0, tk.END)
            self.info_text.delete(1.0, tk.END)
            self.info_text.insert(1.0, current_text + stats_text)

    def stop_recording(self):
        """Stop recording"""
        if self.is_recording:
            self.recorder.stop()

    def play(self):
        """Start playback"""
        if not self.recorder.events:
            messagebox.showwarning("No Macro", "No macro loaded or recorded.")
            return

        if self.is_recording:
            messagebox.showwarning(
                "Busy", "Cannot play while recording. Stop recording first.")
            return

        if self.is_playing:
            messagebox.showinfo("Already Playing", "Macro is already playing.")
            return

        self.is_playing = True
        self.status_var.set("Playing...")
        self.progress_var.set(0)

        # Disable controls
        self.record_btn.config(state=tk.DISABLED)
        self.play_btn.config(state=tk.DISABLED)

        # Create player and start playback
        self.player = EnhancedPlayer(self.recorder.events)
        self.play_thread = threading.Thread(target=self._play_worker)
        self.play_thread.daemon = True
        self.play_thread.start()

    def _play_worker(self):
        """Worker thread for playback"""
        try:
            speed = self.speed_var.get()
            loops = self.loops_var.get()
            self.player.play(speed=speed, loops=loops,
                             callback=self._play_progress_callback)
        except Exception as e:
            messagebox.showerror(
                "Playback Error", f"Failed to play macro: {e}")
        finally:
            self.root.after(0, self._playback_finished)

    def _play_progress_callback(self, progress, current_loop, total_loops):
        """Callback for playback progress"""
        self.root.after(0, lambda: self._update_progress(
            progress, current_loop, total_loops))

    def _update_progress(self, progress, current_loop, total_loops):
        """Update progress in main thread"""
        self.progress_var.set(progress * 100)
        self.status_var.set(
            f"Playing... Loop {current_loop}/{total_loops} ({progress*100:.1f}%)")

    def _playback_finished(self):
        """Called when playback is finished"""
        self.is_playing = False
        self.status_var.set("Playback finished")
        self.progress_var.set(0)

        # Re-enable controls
        self.record_btn.config(state=tk.NORMAL)
        self.play_btn.config(state=tk.NORMAL)

    def pause_resume(self):
        """Pause or resume playback"""
        if self.player and self.is_playing:
            if not self.player.paused:
                self.player.pause()
                self.pause_btn.config(text="Resume")
                self.status_var.set("Paused")
            else:
                self.player.resume()
                self.pause_btn.config(text="Pause")
                self.status_var.set("Playing...")

    def stop_playback(self):
        """Stop playback"""
        if self.player and self.is_playing:
            self.player.stop()

    def save(self):
        """Save macro"""
        if not self.recorder.events:
            messagebox.showwarning("No Macro", "No macro to save.")
            return

        if self.current_file:
            self.recorder.save(self.current_file)
            self.status_var.set(f"Saved to {self.current_file}")
        else:
            self.save_as()

    def save_as(self):
        """Save macro as new file"""
        if not self.recorder.events:
            messagebox.showwarning("No Macro", "No macro to save.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            self.recorder.save(filename)
            self.current_file = filename
            self.status_var.set(f"Saved to {filename}")
            self.update_display_info()

    def load(self):
        """Load macro from file"""
        filename = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )

        if filename:
            try:
                self.recorder.load(filename)
                self.current_file = filename
                self.status_var.set(f"Loaded from {filename}")
                self.update_display_info()

                # Show statistics
                stats = self.recorder.get_stats()
                if stats:
                    messagebox.showinfo("Macro Loaded",
                                        f"Loaded macro with {stats['total_events']} events\n"
                                        f"Duration: {stats['duration']:.2f} seconds")
            except Exception as e:
                messagebox.showerror(
                    "Load Error", f"Failed to load macro: {e}")

    def compile_macro(self):
        """Compile macro to standalone script"""
        if not self.recorder.events:
            messagebox.showwarning("No Macro", "No macro to compile.")
            return

        filename = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")]
        )

        if filename:
            try:
                MacroCompiler.compile_to_script(self.recorder.events, filename)
                messagebox.showinfo("Compilation Complete",
                                    f"Macro compiled to {filename}\n"
                                    f"Run with: python3 {filename}")
                self.status_var.set(f"Compiled to {filename}")
            except Exception as e:
                messagebox.showerror("Compilation Error",
                                     f"Failed to compile: {e}")


def main():
    """Main function"""
    # Check for required permissions
    if os.geteuid() != 0:
        print("Note: Running without root privileges. Some features may not work on all desktop environments.")
        print(
            "If you experience issues, try running with: sudo python3 tinytask_enhanced.py")

    # Create and run GUI
    root = tk.Tk()
    app = EnhancedTinyTaskGUI(root)

    try:
        root.mainloop()
    except KeyboardInterrupt:
        print("\nExiting...")
        if app.is_recording:
            app.recorder.stop()
        if app.is_playing and app.player:
            app.player.stop()


if __name__ == "__main__":
    main()
