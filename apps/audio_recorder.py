import wx
import os
import sounddevice as sd
import soundfile as sf
import numpy as np
from datetime import datetime
from api import BlindApp

class AudioRecorderApp(BlindApp):
    """A fully-featured audio recording application for py-os."""
    
    def __init__(self, api):
        super().__init__(api)
        self.name = "Audio Recorder"
        self.description = "Record and save audio files."
        self.help_text = "Press Space to start/stop recording, or use the buttons. Enter a custom filename or use auto-generated names."
        self.docs = "Audio Recorder allows you to record audio from your microphone and save it as WAV files. Press Space for quick recording toggle."
        
        # Recording state
        self.is_recording = False
        self.recording_data = []
        self.sample_rate = 44100
        self.recording_thread = None
        self.recordings_dir = os.path.join(self.api.get_data_path(""), "recordings")
        
        # Ensure recordings directory exists
        if not os.path.exists(self.recordings_dir):
            os.makedirs(self.recordings_dir)
        
        self.frame = None
        self.filename_input = None
        self.start_btn = None
        self.stop_btn = None
        self.save_btn = None
        self.duration_label = None
        self.status_label = None
        self.recordings_list = None
        self.recording_time = 0

    def run(self):
        """Launch the audio recorder UI."""
        self.frame = wx.Frame(None, title="Audio Recorder", size=(600, 500))
        panel = wx.Panel(self.frame)
        panel.SetBackgroundColour(wx.Colour(0, 0, 0))
        
        sizer = wx.BoxSizer(wx.VERTICAL)
        
        # Title
        title = wx.StaticText(panel, label="Audio Recorder")
        title.SetForegroundColour(wx.Colour(255, 255, 255))
        title.SetFont(wx.Font(16, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD))
        sizer.Add(title, 0, wx.ALL | wx.CENTER, 15)
        
        # Filename input
        filename_label = wx.StaticText(panel, label="Filename (leave empty for auto-generated):")
        filename_label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(filename_label, 0, wx.ALL, 10)
        
        self.filename_input = wx.TextCtrl(panel)
        self.filename_input.SetBackgroundColour(wx.Colour(30, 30, 30))
        self.filename_input.SetForegroundColour(wx.Colour(200, 200, 200))
        sizer.Add(self.filename_input, 0, wx.EXPAND | wx.ALL, 10)
        
        # Duration display
        self.duration_label = wx.StaticText(panel, label="Duration: 0 seconds")
        self.duration_label.SetForegroundColour(wx.Colour(150, 255, 150))
        sizer.Add(self.duration_label, 0, wx.ALL | wx.CENTER, 10)
        
        # Status
        self.status_label = wx.StaticText(panel, label="Status: Ready")
        self.status_label.SetForegroundColour(wx.Colour(255, 255, 100))
        sizer.Add(self.status_label, 0, wx.ALL | wx.CENTER, 10)
        
        # Control buttons
        button_sizer = wx.BoxSizer(wx.HORIZONTAL)
        
        self.start_btn = wx.Button(panel, label="Start Recording")
        self.start_btn.SetBackgroundColour(wx.Colour(0, 100, 0))
        self.start_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.start_btn.Bind(wx.EVT_BUTTON, self.on_start_recording)
        button_sizer.Add(self.start_btn, 1, wx.EXPAND | wx.ALL, 5)
        
        self.stop_btn = wx.Button(panel, label="Stop Recording")
        self.stop_btn.SetBackgroundColour(wx.Colour(100, 0, 0))
        self.stop_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.stop_btn.Bind(wx.EVT_BUTTON, self.on_stop_recording)
        self.stop_btn.Enable(False)
        button_sizer.Add(self.stop_btn, 1, wx.EXPAND | wx.ALL, 5)
        
        sizer.Add(button_sizer, 0, wx.EXPAND | wx.ALL, 5)
        
        # Save button
        self.save_btn = wx.Button(panel, label="Save Recording")
        self.save_btn.SetBackgroundColour(wx.Colour(0, 50, 100))
        self.save_btn.SetForegroundColour(wx.Colour(255, 255, 255))
        self.save_btn.Bind(wx.EVT_BUTTON, self.on_save_recording)
        self.save_btn.Enable(False)
        sizer.Add(self.save_btn, 0, wx.EXPAND | wx.ALL, 10)
        
        # Recordings list
        recordings_label = wx.StaticText(panel, label="Saved Recordings:")
        recordings_label.SetForegroundColour(wx.Colour(255, 255, 255))
        sizer.Add(recordings_label, 0, wx.ALL, 10)
        
        self.recordings_list = wx.ListBox(panel)
        self.recordings_list.SetBackgroundColour(wx.Colour(20, 20, 20))
        self.recordings_list.SetForegroundColour(wx.Colour(255, 255, 255))
        self.refresh_recordings_list()
        sizer.Add(self.recordings_list, 1, wx.EXPAND | wx.ALL, 10)
        
        panel.SetSizer(sizer)
        
        # Keyboard bindings
        self.frame.Bind(wx.EVT_CHAR_HOOK, self.on_key_press)
        self.frame.Bind(wx.EVT_CLOSE, self.on_close)
        
        self.frame.Show()
        self.api.play_sound("launch")
        self.api.speak(f"{self.name} opened. Press Space to record or use the buttons.")

    def on_key_press(self, event):
        """Handle Space key for quick recording toggle."""
        keycode = event.GetKeyCode()
        if keycode == wx.WXK_SPACE:
            if self.is_recording:
                self.on_stop_recording()
            else:
                self.on_start_recording()
        else:
            event.Skip()

    def on_start_recording(self, event=None):
        """Start recording audio."""
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
        
        self.api.play_sound("launch")
        self.api.speak("Recording started. Press Space or click Stop Recording to stop.")
        
        # Start recording in a separate thread
        import threading
        self.recording_thread = threading.Thread(target=self._record_audio, daemon=True)
        self.recording_thread.start()
        
        # Update duration display
        self._update_duration()

    def _record_audio(self):
        """Record audio in background thread."""
        try:
            frames = []
            with sd.InputStream(samplerate=self.sample_rate, channels=1, callback=lambda indata, frames_count, time_info, status: frames.append(indata.copy())) as stream:
                while self.is_recording:
                    pass
            
            # Combine all frames
            if frames:
                self.recording_data = np.concatenate(frames, axis=0)
        except Exception as e:
            print(f"Recording error: {e}")
            self.api.speak(f"Recording error: {e}")

    def _update_duration(self):
        """Update recording duration display."""
        if self.is_recording:
            self.recording_time += 1
            wx.CallAfter(self.duration_label.SetLabel, f"Duration: {self.recording_time} seconds")
            import threading
            threading.Timer(1.0, self._update_duration).start()

    def on_stop_recording(self, event=None):
        """Stop recording audio."""
        if not self.is_recording:
            self.api.speak("Not currently recording.")
            return
        
        self.is_recording = False
        
        self.start_btn.Enable(True)
        self.stop_btn.Enable(False)
        self.save_btn.Enable(True)
        
        self.status_label.SetLabel("Status: Ready to save")
        self.status_label.SetForegroundColour(wx.Colour(0, 255, 0))
        
        self.api.play_sound("close")
        self.api.speak(f"Recording stopped. {self.recording_time} seconds recorded. Click Save Recording to save.")

    def on_save_recording(self, event=None):
        """Save the recorded audio."""
        if len(self.recording_data) == 0:
            self.api.speak("No recording to save.")
            return
        
        # Generate filename
        filename = self.filename_input.GetValue().strip()
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"recording_{timestamp}"
        
        # Ensure .wav extension
        if not filename.endswith(".wav"):
            filename += ".wav"
        
        filepath = os.path.join(self.recordings_dir, filename)
        
        # Handle duplicate filenames
        counter = 1
        base_path = filepath[:-4]
        while os.path.exists(filepath):
            filepath = f"{base_path}_{counter}.wav"
            counter += 1
        
        try:
            sf.write(filepath, self.recording_data, self.sample_rate)
            self.api.speak(f"Recording saved as {os.path.basename(filepath)}")
            
            # Reset
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
            self.api.speak(f"Error saving file: {e}")

    def refresh_recordings_list(self):
        """Refresh the list of saved recordings."""
        self.recordings_list.Clear()
        try:
            recordings = [f for f in os.listdir(self.recordings_dir) if f.endswith(".wav")]
            recordings.sort(reverse=True)
            for recording in recordings:
                self.recordings_list.Append(recording)
        except Exception as e:
            print(f"Error loading recordings: {e}")

    def on_close(self, event=None):
        """Cleanup and close the app."""
        self.is_recording = False
        if self.frame:
            self.frame.Destroy()
        self.api.play_sound("close")
        self.api.desktop.on_app_closed(self)
