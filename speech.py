import ctypes
import os
import json
import pyttsx3
import threading
import queue
import time

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
        
        # Try to load NVDA Controller Client
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

        self.mode = self._load_mode()
        self._apply_mode()

    def _nvda_available(self):
        if not self.nvda_dll:
            return False
        try:
            return self.nvda_dll.nvdaController_testIfRunning() == 0
        except Exception:
            return False

    def _load_mode(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    mode = json.load(f).get("speech_mode", "auto")
                    if mode in ("auto", "nvda", "sapi", "force_nvda", "force_sapi"):
                        # Backward compatibility for older saved values.
                        if mode == "force_nvda":
                            mode = "nvda"
                        elif mode == "force_sapi":
                            mode = "sapi"
                        return mode
        except Exception:
            pass
        return "auto"

    def _save_mode(self):
        try:
            os.makedirs(self.config_dir, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump({"speech_mode": self.mode}, f, indent=2)
        except Exception:
            pass

    def _ensure_tts_thread(self):
        if self.tts_thread is None or not self.tts_thread.is_alive():
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()

    def _apply_mode(self):
        nvda_ok = self._nvda_available()
        if self.mode == "nvda":
            self.use_nvda = nvda_ok
            self.backend = "nvda" if nvda_ok else "sapi"
            if not nvda_ok:
                self._ensure_tts_thread()
            self._clear_queue()
        elif self.mode == "sapi":
            # Hard lock to SAPI path in this mode.
            self.use_nvda = False
            self.backend = "sapi"
            self._cancel_nvda_if_possible()
            self._ensure_tts_thread()
            self._clear_queue()
        else:
            self.use_nvda = nvda_ok
            self.backend = "nvda" if nvda_ok else "sapi"
            if not self.use_nvda:
                self._ensure_tts_thread()

    def _cancel_nvda_if_possible(self):
        try:
            if self.nvda_dll:
                self.nvda_dll.nvdaController_cancelSpeech()
        except Exception:
            pass

    def _clear_queue(self):
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
            except queue.Empty:
                break

    def set_mode(self, mode):
        if mode not in ("auto", "nvda", "sapi"):
            return False
        self.mode = mode
        self._save_mode()
        self._apply_mode()
        return True

    def get_mode(self):
        return self.mode

    def speak(self, text, interrupt=True):
        if not text:
            return

        # Enforce backend choice every call so mode cannot drift.
        if self.mode == "sapi":
            self.use_nvda = False
            self.backend = "sapi"
            self._cancel_nvda_if_possible()
            self._ensure_tts_thread()
        elif self.mode == "nvda":
            self.use_nvda = self._nvda_available()
            self.backend = "nvda" if self.use_nvda else "sapi"
            if not self.use_nvda:
                self._ensure_tts_thread()
        else:
            # Re-evaluate availability in auto mode as NVDA can start/stop at runtime.
            self._apply_mode()

        if self.use_nvda:
            if interrupt:
                self.nvda_dll.nvdaController_cancelSpeech()
            self.nvda_dll.nvdaController_speakText(ctypes.c_wchar_p(text))
        else:
            self._ensure_tts_thread()
            if interrupt:
                # Clear the queue for interrupt
                while not self.speech_queue.empty():
                    try:
                        self.speech_queue.get_nowait()
                    except queue.Empty:
                        break
            self.speech_queue.put(text)

    def _tts_worker(self):
        while True:
            try:
                text = self.speech_queue.get()
                if text:
                    # Recreate engine per utterance for stability after backend/mode switches.
                    engine = pyttsx3.init()
                    engine.say(text)
                    engine.runAndWait()
                    try:
                        engine.stop()
                    except Exception:
                        pass
                self.speech_queue.task_done()
            except Exception as e:
                print(f"TTS Worker error: {e}")
            time.sleep(0.1)

    def stop(self):
        if self.use_nvda:
            self.nvda_dll.nvdaController_cancelSpeech()
        else:
            # Clearing the queue is effectively 'stopping' future speech
            while not self.speech_queue.empty():
                try:
                    self.speech_queue.get_nowait()
                except queue.Empty:
                    break

# Singleton instance
engine = SpeechEngine()
