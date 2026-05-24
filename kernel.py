import os
import datetime
import json
import subprocess
import threading
import queue
import shutil

class VirtualOS:
    def __init__(self, root_dir="vfs"):
        self.root_dir = os.path.abspath(root_dir)
        self.cwd = "/"
        self.shell_proc = None
        self.shell_type = None
        self.output_queue = queue.Queue()
        self.output_callback = None
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
            self._create_default_files()
        self._trash_dir = os.path.join(self.root_dir, ".trash")
        if not os.path.exists(self._trash_dir):
            os.makedirs(self._trash_dir)

    def _create_default_files(self):
        with open(os.path.join(self.root_dir, "welcome.txt"), "w") as f:
            f.write("Welcome to BlindOS. This is a safe environment for you to explore.")
        os.makedirs(os.path.join(self.root_dir, "documents"))

    @property
    def _trash_info_path(self):
        return os.path.join(self._trash_dir, ".trash_info.json")

    def _load_trash_info(self):
        if os.path.exists(self._trash_info_path):
            try:
                with open(self._trash_info_path, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _save_trash_info(self, info):
        with open(self._trash_info_path, "w") as f:
            json.dump(info, f, indent=2)

    def get_real_path(self, virtual_path):
        # Ensure we're working with a normalized virtual path
        # Normalize to handle '..' etc.
        if virtual_path.startswith("/"):
            vpath = os.path.normpath(virtual_path)
        else:
            vpath = os.path.normpath(os.path.join(self.cwd, virtual_path))
        
        # Strip leading separators for joining with root_dir
        rel_path = vpath.lstrip(os.sep).lstrip("/")
        
        # Re-verify the final path is still under root_dir
        final_path = os.path.abspath(os.path.join(self.root_dir, rel_path))
        if not final_path.startswith(self.root_dir):
            return self.root_dir # Default to root if traversal attempted
            
        return final_path

    def _shell_reader(self):
        while self.shell_proc and self.shell_proc.poll() is None:
            try:
                line = self.shell_proc.stdout.readline()
                if line:
                    self.output_queue.put(line.rstrip())
            except Exception:
                break
        self.shell_proc = None
        self.shell_type = None
        if self.output_callback:
            self.output_callback("Windows Shell session ended.")

    def process_shell_output(self):
        while not self.output_queue.empty():
            if self.output_callback:
                self.output_callback(self.output_queue.get())

    def execute(self, command_str):
        if self.shell_proc:
            if command_str.lower().strip() == "exit":
                self.shell_proc.stdin.write("exit\n")
                self.shell_proc.stdin.flush()
                return "Exiting Windows Shell..."
            
            self.shell_proc.stdin.write(command_str + "\n")
            self.shell_proc.stdin.flush()
            return ""

        parts = command_str.lower().split()
        if not parts:
            return "No command entered."
        
        cmd = parts[0]
        args = parts[1:]

        if cmd == "help":
            return "Available commands: list, open, create, delete, delete_permanent, list_trash, restore, empty_trash, where, time, exit, shutdown, reboot, winshell."
        
        elif cmd == "list":
            real_path = self.get_real_path(self.cwd)
            items = os.listdir(real_path)
            if not items:
                return "The directory is empty."
            return f"Directory contains {len(items)} items: " + ", ".join(items)

        elif cmd == "where":
            return f"You are currently in {self.cwd}"

        elif cmd == "time":
            now = datetime.datetime.now()
            return f"The current time is {now.strftime('%H:%M')}."

        elif cmd == "open":
            if not args:
                return "Please specify a file name to open."
            file_name = args[0]
            real_path = self.get_real_path(file_name)
            
            if os.path.isdir(real_path):
                # If it's a directory, change to it
                self.cwd = os.path.normpath(os.path.join(self.cwd, file_name)).replace("\\", "/")
                return f"Opened directory {file_name}."
            
            if os.path.exists(real_path):
                with open(real_path, "r") as f:
                    content = f.read()
                return f"Reading {file_name}: {content}"
            else:
                return f"File {file_name} not found."

        elif cmd == "create":
            if not args:
                return "Please specify a name for the new file."
            file_name = args[0]
            real_path = self.get_real_path(file_name)
            with open(real_path, "w") as f:
                f.write("New file created by user.")
            return f"File {file_name} created successfully."

        elif cmd == "delete":
            if not args:
                return "Please specify a file name to delete."
            file_name = args[0]
            real_path = self.get_real_path(file_name)
            if not os.path.exists(real_path):
                return f"Item {file_name} not found."
            # Move to trash
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            trash_name = f"{ts}_{os.path.basename(real_path)}"
            trash_path = os.path.join(self._trash_dir, trash_name)
            shutil.move(real_path, trash_path)
            info = self._load_trash_info()
            info[trash_name] = {
                "original_name": os.path.basename(file_name),
                "original_path": os.path.relpath(real_path, self.root_dir),
                "deleted_at": ts
            }
            self._save_trash_info(info)
            return f"Moved {file_name} to Recycle Bin."

        elif cmd == "delete_permanent":
            if not args:
                return "Please specify a file name to permanently delete."
            file_name = args[0]
            real_path = self.get_real_path(file_name)
            if not os.path.exists(real_path):
                return f"Item {file_name} not found."
            if os.path.isdir(real_path):
                shutil.rmtree(real_path)
            else:
                os.remove(real_path)
            return f"Permanently deleted {file_name}."

        elif cmd == "list_trash":
            items = os.listdir(self._trash_dir)
            info = self._load_trash_info()
            trashed = [f for f in items if f != ".trash_info.json"]
            if not trashed:
                return "Recycle Bin is empty."
            lines = ["Recycle Bin contents:"]
            for f in trashed:
                entry = info.get(f, {})
                orig = entry.get("original_path", "unknown")
                lines.append(f"  {f} (originally: {orig})")
            return "\n".join(lines)

        elif cmd == "restore":
            if not args:
                return "Please specify a file name to restore from Recycle Bin."
            name = args[0]
            trash_path = os.path.join(self._trash_dir, name)
            if not os.path.exists(trash_path):
                # Try finding by original name
                info = self._load_trash_info()
                found = None
                for k, v in info.items():
                    if v.get("original_name") == name:
                        found = k
                        break
                if found:
                    trash_path = os.path.join(self._trash_dir, found)
                    name = found
                else:
                    return f"Item {name} not found in Recycle Bin."
            info = self._load_trash_info()
            entry = info.get(name, {})
            orig_rel = entry.get("original_path", name)
            restore_path = os.path.join(self.root_dir, orig_rel)
            os.makedirs(os.path.dirname(restore_path), exist_ok=True)
            shutil.move(trash_path, restore_path)
            info.pop(name, None)
            self._save_trash_info(info)
            return f"Restored {entry.get('original_name', name)}."

        elif cmd == "empty_trash":
            for item in os.listdir(self._trash_dir):
                item_path = os.path.join(self._trash_dir, item)
                if item == ".trash_info.json":
                    continue
                if os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                else:
                    os.remove(item_path)
            self._save_trash_info({})
            return "Recycle Bin emptied."

        elif cmd == "shutdown":
            if args and args[0] == "now":
                subprocess.Popen(["shutdown", "/s", "/t", "0"])
                return "System is shutting down..."
            return "Are you sure? Type 'shutdown now' to confirm."

        elif cmd == "reboot":
            if args and args[0] == "now":
                subprocess.Popen(["shutdown", "/r", "/t", "0"])
                return "System is rebooting..."
            return "Are you sure? Type 'reboot now' to confirm."

        elif cmd == "winshell":
            if not args or args[0] == "help":
                return "Winshell usage: \n'winshell powershell' or 'winshell cmd' to enter interactive mode.\n'winshell run <command>' to execute a single command."
            
            if args[0] == "run":
                command = " ".join(args[1:])
                if not command: return "Please specify a command to run."
                try:
                    result = subprocess.check_output(command, shell=True, stderr=subprocess.STDOUT, text=True)
                    return result if result else "Command executed successfully (no output)."
                except subprocess.CalledProcessError as e:
                    return f"Error executing command: {e.output}"
                except Exception as e:
                    return f"Failed to run command: {e}"

            shell_type = args[0]
            executable = "cmd.exe" if shell_type == "cmd" else "powershell.exe"
            
            if shell_type not in ["cmd", "powershell"]:
                return f"Unknown shell type: {shell_type}. Type 'winshell help' for options."

            try:
                self.shell_proc = subprocess.Popen(
                    [executable],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=0,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                self.shell_type = shell_type
                threading.Thread(target=self._shell_reader, daemon=True).start()
                return f"Switched to {shell_type}. Type 'exit' to return to PyOS."
            except Exception as e:
                return f"Failed to launch {shell_type}: {e}"

        return f"Unknown command: {cmd}. Type help for a list of commands."

