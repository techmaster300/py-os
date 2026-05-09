import ctypes
import os
import pyttsx3
import threading
import queue
import time

class SpeechEngine:
    def __init__(self):
        self.nvda_dll = None
        self.use_nvda = False
        self.speech_queue = queue.Queue()
        
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
                
                if self.nvda_dll.nvdaController_testIfRunning() == 0:
                    self.use_nvda = True
                    print("NVDA integration active.")
            except Exception as e:
                print(f"Failed to load NVDA DLL: {e}")
        
        if not self.use_nvda:
            print("NVDA not found or not running. Using pyttsx3 queue.")
            self.tts_thread = threading.Thread(target=self._tts_worker, daemon=True)
            self.tts_thread.start()

    def speak(self, text, interrupt=True):
        if not text:
            return
            
        if self.use_nvda:
            if interrupt:
                self.nvda_dll.nvdaController_cancelSpeech()
            self.nvda_dll.nvdaController_speakText(ctypes.c_wchar_p(text))
        else:
            if interrupt:
                # Clear the queue for interrupt
                while not self.speech_queue.empty():
                    try:
                        self.speech_queue.get_nowait()
                    except queue.Empty:
                        break
            self.speech_queue.put(text)

    def _tts_worker(self):
        # Initialize engine inside the worker thread
        engine = pyttsx3.init()
        while True:
            try:
                text = self.speech_queue.get()
                if text:
                    engine.say(text)
                    engine.runAndWait()
                self.speech_queue.task_done()
            except Exception as e:
                print(f"TTS Worker error: {e}")
                # Re-init engine if it crashes
                try:
                    engine = pyttsx3.init()
                except:
                    pass
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
