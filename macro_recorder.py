import time
import threading
import pyautogui
from pynput import keyboard, mouse
import os

# Set pyautogui failsafe
pyautogui.FAILSAFE = True

# 125% screen size (DPI scaling) support
# On Windows, setting DPI awareness ensures pynput and pyautogui use physical pixels,
# fixing coordinate misalignment when screen scaling is > 100% (e.g. 125%).
if os.name == 'nt':
    import ctypes
    try:
        # Per monitor DPI aware (Windows 8.1+)
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            # Windows 8 or older
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

class MacroRecorder:
    def __init__(self):
        self.recording = False
        self.playing = False
        self.events = []
        self.start_time = 0

        self.keyboard_controller = keyboard.Controller()
        self.mouse_controller = mouse.Controller()

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
                    print("--- Recording Started ---")
                    self.events = []
                    self.start_time = time.time()
                else:
                    print("--- Recording Stopped ---")
            return

        # ' key to start replay
        if char == "'":
            if not self.recording and not self.playing:
                print("--- Replay Started ---")
                self.playing = True
                threading.Thread(target=self.play_macro, daemon=True).start()
            return

        # Failsafe keys
        if self.playing:
            if char in [';', ':', ']', '[']:
                print(f"--- Failsafe Triggered ({char})! Stopping ---")
                self.playing = False
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
            print("No events to replay.")
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
                print("--- PyAutoGUI Failsafe Triggered (Corner)! Stopping ---")
                self.playing = False
                break
            except Exception as e:
                print(f"Error during playback: {e}")

        if self.playing:
            print("--- Replay Finished ---")
        self.playing = False

    def run(self):
        print("Macro Recorder Running.")
        print("  Press ` to start/stop recording.")
        print("  Press ' to replay the exact movements and typing.")
        print("  Failsafes: Press ;, :, ], or [ during replay to abort.")
        print("  PyAutoGUI Failsafe: Move mouse to any of the 4 screen corners to abort.")

        with keyboard.Listener(on_press=self.on_press, on_release=self.on_release) as kb_listener:
            with mouse.Listener(on_move=self.on_move, on_click=self.on_click, on_scroll=self.on_scroll) as mouse_listener:
                kb_listener.join()
                mouse_listener.join()

if __name__ == "__main__":
    recorder = MacroRecorder()
    try:
        recorder.run()
    except KeyboardInterrupt:
        print("Exiting...")
