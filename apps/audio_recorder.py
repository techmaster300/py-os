import os
import threading
from datetime import datetime

import numpy as np
import sounddevice as sd
import soundfile as sf
import wx

import audio_devices
from api import BlindApp


class AudioRecorderApp(BlindApp):
    """Combined recorder and audio player app."""

    def __init__(self, api):
        super().__init__(api)
        self.name = "Media Studio"
        self.description = "Record and play audio files."
        self.help_text = "Record, save, and play audio. Use Left/Right to seek, Up/Down for volume, Space play/pause."
        self.docs = "Media Studio records from your microphone and plays audio files with volume/speed control."
        self.sample_rate = 44100
        self.recordings_dir = os.path.join(self.api.get_data_path(""), "recordings")
        os.makedirs(self.recordings_dir, exist_ok=True)

        self._tick_interval = 500
        self.frame = None
        self.filename_input = None
        self.duration_label = None
        self.status_label = None
        self.recordings_list = None
        self.path_input = None

        self.is_recording = False
        self.recording_data = []
        self.recording_time = 0
        self.recording_thread = None

        self.current_playback_path = None
        self.is_playing = False
        self.is_paused = False
        self.playback_position = 0
        self.playback_data = None
        self.playback_rate = None
        self.playback_channels = None
        self.playback_lock = threading.Lock()
        self.volume = 1.0
        self.speed = 1.0

    def run(self, file_path=None):
        self.frame = self._create_frame("Media Studio", size=(700, 620))
        panel = self.make_panel(self.frame, "Media Studio Panel")
        sizer = self.vbox()

        title = wx.StaticText(panel, label="Media Studio")
        title.SetName("Media Studio Title")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 12)

        sizer.Add(self.make_static(panel, "Recording filename (optional):", "Filename Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.filename_input = self.make_textctrl(panel, name="Filename Input")
        sizer.Add(self.filename_input, 0, wx.EXPAND | wx.ALL, 10)

        self.duration_label = wx.StaticText(panel, label="Duration: 0 seconds")
        self.duration_label.SetName("Duration Display")
        self.duration_label.SetForegroundColour(wx.Colour(150, 255, 150))
        sizer.Add(self.duration_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        self.status_label = wx.StaticText(panel, label="Status: Ready")
        self.status_label.SetName("Status Display")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 100))
        sizer.Add(self.status_label, 0, wx.LEFT | wx.RIGHT | wx.BOTTOM, 10)

        rec_btn_row = self.hbox()
        self.start_btn = self.make_button(panel, "Start Recording", self.on_start_recording, "")
        self.stop_btn = self.make_button(panel, "Stop Recording", self.on_stop_recording, "")
        self.save_btn = self.make_button(panel, "Save Recording", self.on_save_recording, "")
        self.stop_btn.Enable(False)
        self.save_btn.Enable(False)
        rec_btn_row.Add(self.start_btn, 1, wx.EXPAND | wx.ALL, 5)
        rec_btn_row.Add(self.stop_btn, 1, wx.EXPAND | wx.ALL, 5)
        rec_btn_row.Add(self.save_btn, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(rec_btn_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.Add(self.make_static(panel, "Audio file path:", "Audio Path Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        file_row = self.hbox()
        self.path_input = self.make_textctrl(panel, name="Audio Path Input", style=wx.TE_PROCESS_ENTER)
        self.path_input.Bind(wx.EVT_TEXT_ENTER, self.on_load_path)
        browse_btn = self.make_button(panel, "Browse...", self.on_browse_file, "Browse Audio Files")
        load_btn = self.make_button(panel, "Load Path", self.on_load_path, "Load Audio Path")
        file_row.Add(self.path_input, 1, wx.EXPAND | wx.RIGHT, 8)
        file_row.Add(browse_btn, 0, wx.RIGHT, 6)
        file_row.Add(load_btn, 0)
        sizer.Add(file_row, 0, wx.EXPAND | wx.ALL, 10)

        playback_row = self.hbox()
        self.play_btn = self.make_button(panel, "Play", self.on_play, "Play Audio")
        self.pause_btn = self.make_button(panel, "Pause", self.on_pause_resume, "Pause Audio")
        self.stop_playback_btn = self.make_button(panel, "Stop", self.on_stop_playback, "Stop Playback")
        playback_row.Add(self.play_btn, 1, wx.EXPAND | wx.ALL, 5)
        playback_row.Add(self.pause_btn, 1, wx.EXPAND | wx.ALL, 5)
        playback_row.Add(self.stop_playback_btn, 1, wx.EXPAND | wx.ALL, 5)
        sizer.Add(playback_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        vol_speed_row = self.hbox()
        vol_label = self.make_static(panel, "Vol:", "Volume Label")
        vol_label.SetForegroundColour(wx.Colour(200, 200, 200))
        vol_speed_row.Add(vol_label, 0, wx.ALL | wx.CENTER, 8)
        self.vol_slider = self.make_slider(panel, 100, 0, 100, "Volume Slider", size=(120, -1))
        self.vol_slider.Bind(wx.EVT_SLIDER, self.on_volume_change)
        vol_speed_row.Add(self.vol_slider, 1, wx.ALL | wx.CENTER, 5)

        speed_label = self.make_static(panel, "Speed:", "Speed Label")
        speed_label.SetForegroundColour(wx.Colour(200, 200, 200))
        vol_speed_row.Add(speed_label, 0, wx.ALL | wx.CENTER, 8)
        self.speed_choice = self.make_choice(panel, ["0.5x", "0.75x", "1.0x", "1.25x", "1.5x", "2.0x"], "Speed Choice")
        self.speed_choice.SetSelection(2)
        self.speed_choice.Bind(wx.EVT_CHOICE, self.on_speed_change)
        vol_speed_row.Add(self.speed_choice, 0, wx.ALL | wx.CENTER, 5)
        sizer.Add(vol_speed_row, 0, wx.EXPAND | wx.LEFT | wx.RIGHT, 10)

        sizer.Add(self.make_static(panel, "Saved recordings:", "Recordings Label"), 0, wx.LEFT | wx.RIGHT | wx.TOP, 10)
        self.recordings_list = self.make_listbox(panel, name="Recordings List")
        self.recordings_list.Bind(wx.EVT_LISTBOX_DCLICK, self.on_open_selected_recording)
        sizer.Add(self.recordings_list, 1, wx.EXPAND | wx.ALL, 10)
        self.refresh_recordings_list()

        panel.SetSizer(sizer)
        self.frame.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        self.api.play_sound("launch")
        self.api.speak("Media Studio opened.")
        self._show_app(self.filename_input)

        if file_path:
            self.path_input.SetValue(file_path)
            self.load_playback_file(file_path)

    def on_tick(self):
        if self.is_recording:
            self.recording_time += 1
            self.duration_label.SetLabel(f"Duration: {self.recording_time} seconds")

    def on_volume_change(self, event):
        self.volume = self.vol_slider.GetValue() / 100.0
        if self.is_playing:
            with self.playback_lock:
                sd.default.device[1] = self._selected_output()

    def on_speed_change(self, event):
        speed_map = {"0.5x": 0.5, "0.75x": 0.75, "1.0x": 1.0, "1.25x": 1.25, "1.5x": 1.5, "2.0x": 2.0}
        sel = self.speed_choice.GetStringSelection()
        self.speed = speed_map.get(sel, 1.0)
        self.api.speak(f"Speed set to {sel}.")

    def get_terminal_commands(self):
        return {
            "record": "Start recording.",
            "stop": "Stop recording.",
            "save <name>": "Save the current recording.",
            "play": "Play loaded audio.",
            "pause": "Pause/Resume.",
            "stop_playback": "Stop playback.",
            "volume <0-100>": "Set volume level.",
            "speed <0.5|0.75|1.0|1.25|1.5|2.0>": "Set playback speed.",
        }

    def terminal_input(self, command):
        cmd = command.lower().split()
        if not cmd: return
        action = cmd[0]
        if action == "record":
            self.on_start_recording()
        elif action == "stop":
            self.on_stop_recording()
        elif action == "save":
            if len(cmd) > 1:
                self.filename_input.SetValue(cmd[1])
            self.on_save_recording()
        elif action == "play":
            self.on_play()
        elif action == "pause":
            self.on_pause_resume()
        elif action == "stop_playback":
            self.on_stop_playback()
        elif action == "volume" and len(cmd) > 1:
            try:
                v = max(0, min(100, int(cmd[1])))
                self.vol_slider.SetValue(v)
                self.volume = v / 100.0
                self.api.speak(f"Volume {v}.")
            except ValueError:
                self.api.terminal_output("Usage: volume <0-100>")
        elif action == "speed" and len(cmd) > 1:
            speed_map = {"0.5": 0, "0.75": 1, "1.0": 2, "1.25": 3, "1.5": 4, "2.0": 5}
            if cmd[1] in speed_map:
                self.speed_choice.SetSelection(speed_map[cmd[1]])
                self.on_speed_change(None)
        else:
            self.api.terminal_output("Unknown command. Type 'help' for available commands.")

    def on_start_recording(self, event=None):
        if self.is_recording:
            self.api.speak("Already recording.")
            return
        self.is_recording = True
        self.recording_data = []
        self.recording_time = 0
        self.start_btn.Enable(False)
        self.stop_btn.Enable(True)
        self.filename_input.Enable(False)
        self.status_label.SetLabel("Status: Recording...")
        self.status_label.SetForegroundColour(wx.Colour(255, 0, 0))
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
        self.api.speak("Recording started.")

    def _record_audio(self):
        try:
            config = audio_devices.load_device_config(self.api.data_dir)
            input_devices = audio_devices.list_input_devices()
            selected_input_index = audio_devices.resolve_selected_index(
                input_devices, config, "input_device_index", "input_device"
            )
            frames = []
            with sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                device=selected_input_index,
                callback=lambda indata, frames_count, time_info, status: frames.append(indata.copy())
            ):
                while self.is_recording:
                    pass
            if frames:
                self.recording_data = np.concatenate(frames, axis=0)
        except Exception:
            self.api.speak("Recording failed on selected mic. Trying default input.")
            try:
                frames = []
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=1,
                    callback=lambda indata, frames_count, time_info, status: frames.append(indata.copy())
                ):
                    while self.is_recording:
                        pass
                if frames:
                    self.recording_data = np.concatenate(frames, axis=0)
            except Exception as fallback_error:
                self.api.speak(f"Recording error: {fallback_error}")

    def on_stop_recording(self, event=None):
        if not self.is_recording:
            self.api.speak("Not recording.")
            return
        self.is_recording = False
        self.start_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.save_btn.Enable(True)
        self.status_label.SetLabel("Status: Ready to save recording")
        self.status_label.SetForegroundColour(wx.Colour(0, 255, 0))
        self.api.speak(f"Recording stopped. {self.recording_time} seconds.")

    def on_save_recording(self, event=None):
        if len(self.recording_data) == 0:
            self.api.speak("No recording to save.")
            return
        filename = self.filename_input.GetValue().strip()
        if not filename:
            filename = f"recording_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        if not filename.endswith(".wav"):
            filename += ".wav"
        filepath = os.path.join(self.recordings_dir, filename)
        counter = 1
        base = filepath[:-4]
        while os.path.exists(filepath):
            filepath = f"{base}_{counter}.wav"
            counter += 1
        try:
            sf.write(filepath, self.recording_data, self.sample_rate)
            self.api.speak(f"Saved {os.path.basename(filepath)}.")
            self.recording_data = []
            self.recording_time = 0
            self.filename_input.Clear()
            self.filename_input.Enable(True)
            self.save_btn.Enable(False)
            self.duration_label.SetLabel("Duration: 0 seconds")
            self.status_label.SetLabel("Status: Ready")
            self.status_label.SetForegroundColour(wx.Colour(255, 255, 100))
            self.refresh_recordings_list()
        except Exception as e:
            self.api.speak(f"Save error: {e}")

    def refresh_recordings_list(self):
        self.recordings_list.Clear()
        try:
            files = [f for f in os.listdir(self.recordings_dir) if f.lower().endswith((".wav", ".mp3", ".ogg", ".flac"))]
            files.sort(reverse=True)
            for name in files:
                self.recordings_list.Append(name)
        except Exception:
            pass

    def on_open_selected_recording(self, event=None):
        selected = self.recordings_list.GetStringSelection()
        if not selected:
            self.api.speak("No recording selected.")
            return
        full = os.path.join(self.recordings_dir, selected)
        self.path_input.SetValue(full)
        self.load_playback_file(full)

    def on_browse_file(self, event=None):
        wildcard = "Audio files (*.wav;*.mp3;*.ogg;*.flac)|*.wav;*.mp3;*.ogg;*.flac"
        dlg = wx.FileDialog(self.frame, "Choose audio file", wildcard=wildcard, style=wx.FD_OPEN | wx.FD_FILE_MUST_EXIST)
        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.path_input.SetValue(path)
            self.load_playback_file(path)
        dlg.Destroy()

    def on_load_path(self, event=None):
        self.load_playback_file(self.path_input.GetValue().strip())

    def on_key_press(self, event):
        key = event.GetKeyCode()
        if key == wx.WXK_SPACE:
            if not self.is_playing:
                self.on_play()
            else:
                self.on_pause_resume()
        elif key == wx.WXK_ESCAPE:
            self.on_stop_playback()
        elif key == wx.WXK_LEFT:
            self.seek(-5)
        elif key == wx.WXK_RIGHT:
            self.seek(5)
        elif key in (wx.WXK_UP, wx.WXK_DOWN):
            delta = 10 if key == wx.WXK_UP else -10
            new_val = max(0, min(100, self.vol_slider.GetValue() + delta))
            self.vol_slider.SetValue(new_val)
            self.volume = new_val / 100.0
            self.api.speak(f"Volume {new_val}.")
        else:
            event.Skip()

    def seek(self, seconds):
        with self.playback_lock:
            if self.playback_data is None: return
            pos_change = int(seconds * self.playback_rate)
            old_pos = self.playback_position
            self.playback_position = max(0, min(self.playback_data.shape[0]-1, self.playback_position + pos_change))
            if self.is_playing:
                sd.stop()
                self.on_play()
            total_sec = self.playback_data.shape[0] / self.playback_rate
            new_sec = self.playback_position / self.playback_rate
            self.api.speak(f"{new_sec:.0f} of {total_sec:.0f} seconds")

    def load_playback_file(self, path):
        if not path: return
        self.api.speak(f"Loading {os.path.basename(path)}...")
        threading.Thread(target=self._load_file_thread, args=(path,), daemon=True).start()

    def _load_file_thread(self, path):
        try:
            data, rate = sf.read(path, dtype="float32")
            if data.ndim == 1:
                data = data[:, np.newaxis]
            with self.playback_lock:
                self.current_playback_path = path
                self.playback_data = data
                self.playback_rate = rate
                self.playback_position = 0
                self.is_paused = False
            wx.CallAfter(self.api.speak, f"Loaded {os.path.basename(path)}.")
        except Exception as e:
            wx.CallAfter(self.api.speak, f"Could not load audio: {e}")

    def _selected_output(self):
        config = audio_devices.load_device_config(self.api.data_dir)
        outputs = audio_devices.list_output_devices()
        return audio_devices.resolve_selected_index(outputs, config, "output_device_index", "output_device")

    def on_play(self, event=None):
        with self.playback_lock:
            if self.playback_data is None:
                self.api.speak("Load a file first.")
                return
            if self.is_playing and not self.is_paused:
                self.api.speak("Already playing.")
                return
            segment = self.playback_data[self.playback_position :]
            if segment.size == 0:
                self.playback_position = 0
                segment = self.playback_data
            self.is_playing = True
            self.is_paused = False
        try:
            scaled = segment * self.volume
            sd.play(scaled, samplerate=int(self.playback_rate * self.speed), device=self._selected_output())
            self.api.speak("Playing audio.")
        except Exception as e:
            self.api.speak(f"Playback error: {e}")

    def on_pause_resume(self, event=None):
        with self.playback_lock:
            if self.playback_data is None:
                self.api.speak("Load a file first.")
                return
            if not self.is_playing:
                self.api.speak("Nothing is playing.")
                return
            if not self.is_paused:
                sd.stop()
                self.is_paused = True
                self.api.speak("Paused.")
            else:
                self.is_paused = False
                self.playback_position = 0
        if not self.is_paused:
            self.api.speak("Resuming from start.")
            self.on_play()

    def on_stop_playback(self, event=None):
        with self.playback_lock:
            if self.playback_data is None:
                return
            sd.stop()
            self.playback_position = 0
            self.is_playing = False
            self.is_paused = False
        self.api.speak("Playback stopped.")

    def on_close(self, event=None):
        self.is_recording = False
        try:
            sd.stop()
        except Exception:
            pass
        if self.frame:
            self.frame.Destroy()
        self.api.play_sound("close")
        self.api.desktop.on_app_closed(self)
