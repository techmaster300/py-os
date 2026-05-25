import ctypes
import os
import json
import threading
import queue
import time
from comtypes.client import CreateObject
import audio_devices

# SAPI speak flags (avoids comtypes.gen.SpeechLib import which can fail)
SVSFlagsAsync = 1
SVSFPurgeBeforeSpeak = 2

class SpeechEngine:
    def __init__(self):
        self.nvda_dll = None
        self.use_nvda = False
        self.mode = "auto"  # auto | nvda | sapi
        self.speech_queue = queue.Queue()
        self.tts_thread = None
        self.backend = "unknown"
        self.config_dir = os.path.join(os.path.expanduser("~"), ".py-os")
        self.config_path = os.path.join(self.config_dir, "speech_config.json")
        self.rate = 200 # Default speed (mapped to SAPI 0 or similar)
        
        # Load config (mode and rate)
        config = self._load_config()
        self.mode = config.get("speech_mode", "auto")
        self.rate = config.get("speech_rate", 200)

        # Try to load NVDA Controller Client only if not in sapi mode
        if self.mode != "sapi":
            dll_name = "nvdaControllerClient64.dll" if ctypes.sizeof(ctypes.c_void_p) == 8 else "nvdaControllerClient32.dll"
            dll_path = os.path.join(os.getcwd(), dll_name)
            
            if os.path.exists(dll_path):
                try:
                    self.nvda_dll = ctypes.windll.LoadLibrary(dll_path)
                    
                    # Define function signatures for reliability
                    self.nvda_dll.nvdaController_testIfRunning.restype = ctypes.c_int
                    self.nvda_dll.nvdaController_speakText.argtypes = [ctypes.c_wchar_p]
                    self.nvda_dll.nvdaController_speakText.restype = ctypes.c_int
                    self.nvda_dll.nvdaController_cancelSpeech.restype = ctypes.c_int
                except Exception as e:
                    print(f"Failed to load NVDA DLL: {e}")

        self._apply_mode()

        # Initialize SAPI engine if needed
        self.sapi_engine = None
        if self.mode != "nvda":
            self.sapi_engine = CreateObject("SAPI.SpVoice")
            self._apply_sapi_device()
            self._apply_rate()

    def _apply_sapi_device(self):
        """Routes SAPI output to the configured audio device."""
        if not self.sapi_engine: return
        
        config = audio_devices.load_device_config(self.config_dir)
        device_name = config.get("output_device")
        
        if device_name:
            # SAPI devices are often identified by category/token
            try:
                # Iterate through audio outputs to match the selected device name
                for token in self.sapi_engine.GetAudioOutputs():
                    if token.GetDescription() == device_name:
                        self.sapi_engine.AudioOutput = token
                        break
            except Exception as e:
                print(f"Could not route SAPI to {device_name}: {e}")

    def _apply_rate(self):
        """Map 50-400 to SAPI -10 to 10."""
        if self.sapi_engine:
            # Simple linear mapping: 50 -> -10, 225 -> 0, 400 -> 10
            # formula: (rate - 225) / 17.5 approx
            sapi_rate = int((self.rate - 225) / 17.5)
            sapi_rate = max(-10, min(10, sapi_rate))
            self.sapi_engine.Rate = sapi_rate

    def set_rate(self, rate):
        self.rate = rate
        self._apply_rate()
        self._save_config()

    def get_rate(self):
        return self.rate

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    mode = config.get("speech_mode", "auto")
                    if mode in ("force_nvda", "force_sapi"):
                        config["speech_mode"] = "nvda" if mode == "force_nvda" else "sapi"
                    return config
        except Exception:
            pass
        return {"speech_mode": "auto", "speech_rate": 200}

    def _save_config(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"speech_mode": self.mode, "speech_rate": self.rate}, f, indent=2)
        except Exception:
            pass

    def _nvda_available(self):
        if not self.nvda_dll:
            return False
        try:
            return self.nvda_dll.nvdaController_testIfRunning() == 0
        except Exception:
            return False

    def _ensure_tts_thread(self):
        if self.tts_thread is None or not self.tts_thread.is_alive():
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()

    def _apply_mode(self):
        nvda_ok = self._nvda_available()
        if self.mode == "nvda":
            self.use_nvda = nvda_ok
            self.backend = "nvda" if nvda_ok else "sapi"
            if not nvda_ok: self._ensure_tts_thread()
            self._clear_queue()
        elif self.mode == "sapi":
            self.use_nvda = False
            self.backend = "sapi"
            self._cancel_nvda_if_possible()
            self._ensure_tts_thread()
            self._clear_queue()
        else:
            self.use_nvda = nvda_ok
            self.backend = "nvda" if nvda_ok else "sapi"
            if not self.use_nvda: self._ensure_tts_thread()

    def _cancel_nvda_if_possible(self):
        try:
            if self.nvda_dll: self.nvda_dll.nvdaController_cancelSpeech()
        except Exception: pass

    def _clear_queue(self):
        while not self.speech_queue.empty():
            try: self.speech_queue.get_nowait()
            except queue.Empty: break

    def set_mode(self, mode):
        if mode not in ("auto", "nvda", "sapi"): return False
        self.mode = mode
        self._save_mode()
        self._apply_mode()
        
        # Re-init engine if needed
        if self.mode != "nvda" and not self.sapi_engine:
            self.sapi_engine = CreateObject("SAPI.SpVoice")
        return True

    def get_mode(self): return self.mode

    def get_sapi_voices(self):
        """Return list of available SAPI voices."""
        if not self.sapi_engine: return []
        return [voice.GetDescription() for voice in self.sapi_engine.GetVoices()]

    def set_sapi_voice(self, index):
        """Set SAPI voice by index."""
        if self.sapi_engine:
            voices = self.sapi_engine.GetVoices()
            if 0 <= index < voices.Count:
                self.sapi_engine.Voice = voices.Item(index)

    def set_sapi_rate(self, rate):
        """Set SAPI speech rate (Range -10 to 10)."""
        if self.sapi_engine:
            self.sapi_engine.Rate = rate

    def speak(self, text, interrupt=True):
        if not text: return

        # Enforce strict backend logic
        if self.mode == "sapi":
            self.use_nvda = False
        elif self.mode == "nvda":
            self.use_nvda = self._nvda_available()
        else:
            self.use_nvda = self._nvda_available()

        if self.use_nvda and self.nvda_dll:
            if interrupt: self.nvda_dll.nvdaController_cancelSpeech()
            self.nvda_dll.nvdaController_speakText(ctypes.c_wchar_p(text))
        else:
            self.use_nvda = False
            # Aggressively cancel NVDA speech if it's accidentally speaking
            if self.nvda_dll: self.nvda_dll.nvdaController_cancelSpeech()
            
            self._ensure_tts_thread()
            if interrupt:
                while not self.speech_queue.empty():
                    try: self.speech_queue.get_nowait()
                    except queue.Empty: break
            self.speech_queue.put(text)

    def _tts_worker(self):
        import pythoncom
        pythoncom.CoInitialize()
        while True:
            try:
                # Use a smaller timeout to check the queue faster
                try:
                    text = self.speech_queue.get(timeout=0.01)
                except queue.Empty:
                    time.sleep(0.01)
                    continue

                if text:
                    if not self.sapi_engine:
                        self.sapi_engine = CreateObject("SAPI.SpVoice")
                    self.sapi_engine.Speak(text, SVSFlagsAsync)
                self.speech_queue.task_done()
            except Exception as e:
                print(f"TTS Worker error: {e}")
        pythoncom.CoUninitialize()

    def stop(self):
        if self.use_nvda:
            self.nvda_dll.nvdaController_cancelSpeech()
        else:
            if self.sapi_engine:
                self.sapi_engine.Speak("", SVSFPurgeBeforeSpeak)
            while not self.speech_queue.empty():
                try: self.speech_queue.get_nowait()
                except queue.Empty: break

engine = SpeechEngine()
