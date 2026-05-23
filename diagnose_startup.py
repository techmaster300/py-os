import traceback
import sys
import os

def diagnose():
    log_file = "startup_error.log"
    try:
        with open(log_file, "w") as f:
            f.write("Starting diagnostic...\n")
            
            f.write("Checking imports...\n")
            import wx
            import speech
            import kernel
            import sounds
            f.write("Imports successful.\n")
            
            f.write("Initializing DesktopFrame...\n")
            from desktop import DesktopFrame
            # Create app but don't run MainLoop yet to avoid hanging
            app = wx.App()
            frame = DesktopFrame()
            f.write("Initialization successful.\n")
            
    except Exception as e:
        with open(log_file, "a") as f:
            f.write("\n--- ERROR DETECTED ---\n")
            f.write(traceback.format_exc())
            f.write("\n----------------------\n")
        print(f"Error captured in {log_file}. Please check that file.")

if __name__ == "__main__":
    diagnose()
