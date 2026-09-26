import time
import threading
import pyautogui
from pynput import keyboard, mouse
import os
import json
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

# Set pyautogui failsafe
pyautogui.FAILSAFE = True

# 125% screen size (DPI scaling) support
if os.name == 'nt':
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

def serialize_key(key):
    if isinstance(key, keyboard.Key):
        return {'type': 'key', 'name': key.name}
    elif hasattr(key, 'char') and key.char is not None:
        return {'type': 'keycode', 'char': key.char}
    elif hasattr(key, 'vk') and key.vk is not None:
        return {'type': 'keycode', 'vk': key.vk}
    else:
        return {'type': 'unknown', 'str': str(key)}

def deserialize_key(data):
    if not isinstance(data, dict):
        return data
    if data.get('type') == 'key':
        return getattr(keyboard.Key, data['name'])
    elif data.get('type') == 'keycode':
        if 'char' in data:
            return keyboard.KeyCode(char=data['char'])
        elif 'vk' in data:
            return keyboard.KeyCode(vk=data['vk'])
    return data.get('str', None)

def serialize_button(button):
    if isinstance(button, mouse.Button):
        return {'type': 'button', 'name': button.name}
    return str(button)

def deserialize_button(data):
    if isinstance(data, dict) and data.get('type') == 'button':
        return getattr(mouse.Button, data['name'])
    return data

def serialize_event(event):
    event_type, event_args, event_time = event
    if event_type in ('kb_press', 'kb_release'):
        return [event_type, serialize_key(event_args), event_time]
    elif event_type == 'mouse_move':
        return [event_type, event_args, event_time]
    elif event_type == 'mouse_click':
        x, y, button, pressed = event_args
        return [event_type, [x, y, serialize_button(button), pressed], event_time]
    elif event_type == 'mouse_scroll':
        return [event_type, event_args, event_time]
    return []

def deserialize_event(event_data):
    if not event_data:
        return None
    event_type = event_data[0]
    event_time = event_data[2]
    if event_type in ('kb_press', 'kb_release'):
        return (event_type, deserialize_key(event_data[1]), event_time)
    elif event_type == 'mouse_move':
        return (event_type, tuple(event_data[1]), event_time)
    elif event_type == 'mouse_click':
        x, y, button_data, pressed = event_data[1]
        return (event_type, (x, y, deserialize_button(button_data), pressed), event_time)
    elif event_type == 'mouse_scroll':
        return (event_type, tuple(event_data[1]), event_time)
    return None


class MacroRecorder:
    def __init__(self):
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = 0

        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

        self.on_status_change = None  # Callback for GUI updates

    def get_key_char(self, key):
        if hasattr(key, 'char') and key.char is not None:
            return key.char
        return None

    def on_press(self, key):
        char = self.get_key_char(key)

        # ` key to toggle recording
        if char == '`':
            if not self.playing:
                self.recording = not self.recording
                if self.recording:
                    self.events = []
                    self.start_time = time.time()
                    if self.on_status_change:
                        self.on_status_change("Recording")
                else:
                    if self.on_status_change:
                        self.on_status_change("Idle (Recording Stopped)")
            return

        # ' key to start replay
        if char == "'":
            if not self.recording and not self.playing:
                if self.on_status_change:
                    self.on_status_change("Playing")
                self.playing = True
                threading.Thread(target=self.play_macro, daemon=True).start()
            return

        # Failsafe keys
        if self.playing:
            if char in [';', ':', ']', '[']:
                self.playing = False
                if self.on_status_change:
                    self.on_status_change(f"Idle (Failsafe Triggered: {char})")
            return

        # Record keyboard press
        if self.recording:
            self.events.append(('kb_press', key, time.time() - self.start_time))

    def on_release(self, key):
        char = self.get_key_char(key)
        # Record keyboard release (except the toggle key)
        if self.recording and char != '`':
            self.events.append(('kb_release', key, time.time() - self.start_time))

    def on_move(self, x, y):
        # Record mouse move
        if self.recording:
            self.events.append(('mouse_move', (x, y), time.time() - self.start_time))

    def on_click(self, x, y, button, pressed):
        # Record mouse click
        if self.recording:
            self.events.append(('mouse_click', (x, y, button, pressed), time.time() - self.start_time))

    def on_scroll(self, x, y, dx, dy):
        # Record mouse scroll
        if self.recording:
            self.events.append(('mouse_scroll', (x, y, dx, dy), time.time() - self.start_time))

    def play_macro(self):
        if not self.events:
            if self.on_status_change:
                self.on_status_change("Idle (No events to replay)")
            self.playing = False
            return

        start_time = time.time()
        for event in self.events:
            if not self.playing:
                break

            event_type, event_args, event_time = event

            # Wait until it is time to execute the event
            while True:
                if not self.playing:
                    break
                current_time = time.time() - start_time
                if current_time >= event_time:
                    break
                time.sleep(0.001)

            if not self.playing:
                break

            try:
                # PyAutoGUI failsafe check (raises FailSafeException if mouse in corner)
                pyautogui.failSafeCheck()

                # Execute event
                if event_type == 'kb_press':
                    self.keyboard_controller.press(event_args)
                elif event_type == 'kb_release':
                    self.keyboard_controller.release(event_args)
                elif event_type == 'mouse_move':
                    x, y = event_args
                    self.mouse_controller.position = (x, y)
                elif event_type == 'mouse_click':
                    x, y, button, pressed = event_args
                    self.mouse_controller.position = (x, y)
                    if pressed:
                        self.mouse_controller.press(button)
                    else:
                        self.mouse_controller.release(button)
                elif event_type == 'mouse_scroll':
                    x, y, dx, dy = event_args
                    self.mouse_controller.position = (x, y)
                    self.mouse_controller.scroll(dx, dy)
            except pyautogui.FailSafeException:
                if self.on_status_change:
                    self.on_status_change("Idle (PyAutoGUI Corner Failsafe!)")
                self.playing = False
                break
            except Exception as e:
                print(f"Error during playback: {e}")

        if self.playing:
            if self.on_status_change:
                self.on_status_change("Idle (Replay Finished)")
        self.playing = False

    def export_events(self, filepath):
        data = [serialize_event(e) for e in self.events]
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def import_events(self, filepath):
        with open(filepath, 'r') as f:
            data = json.load(f)
        self.events = [deserialize_event(e) for e in data if e]

    def start_listeners(self):
        self.kb_listener = keyboard.Listener(on_press=self.on_press, on_release=self.on_release)
        self.mouse_listener = mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll)
        self.kb_listener.start()
        self.mouse_listener.start()

    def stop_listeners(self):
        self.kb_listener.stop()
        self.mouse_listener.stop()


class MacroRecorderGUI:
    def __init__(self, root, recorder):
        self.root = root
        self.recorder = recorder
        self.recorder.on_status_change = self.update_status

        self.root.title("Macro Recorder Studio")
        self.root.geometry("450x250")
        self.root.resizable(False, False)

        # Styling
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("TButton", padding=6, relief="flat", background="#e0e0e0")
        style.configure("TLabel", font=("Helvetica", 11))

        main_frame = ttk.Frame(self.root, padding="20 20 20 20")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status
        self.status_var = tk.StringVar(value="Status: Idle")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, font=("Helvetica", 12, "bold"), foreground="#333")
        status_label.grid(row=0, column=0, columnspan=2, pady=(0, 15), sticky="w")

        # Replay Name
        name_frame = ttk.Frame(main_frame)
        name_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")

        ttk.Label(name_frame, text="Replay Name:").pack(side=tk.LEFT, padx=(0, 10))
        self.name_var = tk.StringVar(value="my_macro")
        self.name_entry = ttk.Entry(name_frame, textvariable=self.name_var, width=30)
        self.name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Controls Group
        controls_frame = ttk.Frame(main_frame)
        controls_frame.grid(row=2, column=0, columnspan=2, pady=15)

        self.btn_export = ttk.Button(controls_frame, text="Export JSON", command=self.do_export)
        self.btn_export.grid(row=0, column=0, padx=5)

        self.btn_import = ttk.Button(controls_frame, text="Import JSON", command=self.do_import)
        self.btn_import.grid(row=0, column=1, padx=5)

        ttk.Label(main_frame, text="Hotkeys: ` to Record/Stop  |  ' to Play", font=("Helvetica", 9, "italic")).grid(row=3, column=0, columnspan=2, pady=(15, 0))

    def update_status(self, text):
        # Safely update GUI from background threads
        self.root.after(0, lambda: self.status_var.set(f"Status: {text}"))

    def do_export(self):
        if not self.recorder.events:
            messagebox.showwarning("Export", "No macro events recorded yet.")
            return
        default_name = f"{self.name_var.get()}.json"
        filepath = filedialog.asksaveasfilename(
            defaultextension=".json",
            initialfile=default_name,
            title="Export Macro",
            filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            try:
                self.recorder.export_events(filepath)
                messagebox.showinfo("Export", f"Successfully exported to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export:\n{e}")

    def do_import(self):
        filepath = filedialog.askopenfilename(
            title="Import Macro",
            filetypes=[("JSON files", "*.json")]
        )
        if filepath:
            try:
                self.recorder.import_events(filepath)

                # Try to extract a name from the filename
                filename = os.path.basename(filepath)
                name, _ = os.path.splitext(filename)
                self.name_var.set(name)

                messagebox.showinfo("Import", f"Successfully imported macro with {len(self.recorder.events)} events.")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to import:\n{e}")

def main():
    root = tk.Tk()
    recorder = MacroRecorder()

    # Start listeners in background thread
    recorder.start_listeners()

    app = MacroRecorderGUI(root, recorder)

    def on_closing():
        recorder.stop_listeners()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
