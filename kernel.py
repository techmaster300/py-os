import os
import datetime
import json

class VirtualOS:
    def __init__(self, root_dir="vfs"):
        self.root_dir = os.path.abspath(root_dir)
        self.cwd = "/"
        if not os.path.exists(self.root_dir):
            os.makedirs(self.root_dir)
            # Create some default files
            self._create_default_files()

    def _create_default_files(self):
        with open(os.path.join(self.root_dir, "welcome.txt"), "w") as f:
            f.write("Welcome to BlindOS. This is a safe environment for you to explore.")
        os.makedirs(os.path.join(self.root_dir, "documents"))

    def get_real_path(self, virtual_path):
        # Very basic path resolution
        if virtual_path.startswith("/"):
            rel_path = virtual_path.lstrip("/")
        else:
            # Handle relative paths from current cwd
            current_abs_vpath = os.path.join(self.cwd, virtual_path)
            rel_path = os.path.normpath(current_abs_vpath).lstrip("/")
        
        return os.path.join(self.root_dir, rel_path)

    def execute(self, command_str):
        parts = command_str.lower().split()
        if not parts:
            return "No command entered."
        
        cmd = parts[0]
        args = parts[1:]

        if cmd == "help":
            return "Available commands: list, open, create, delete, where, time, exit."
        
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
                self.cwd = os.path.join(self.cwd, file_name).replace("\\", "/")
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
            if os.path.exists(real_path):
                if os.path.isdir(real_path):
                    os.rmdir(real_path)
                else:
                    os.remove(real_path)
                return f"Deleted {file_name}."
            else:
                return f"Item {file_name} not found."

        return f"Unknown command: {cmd}. Type help for a list of commands."

