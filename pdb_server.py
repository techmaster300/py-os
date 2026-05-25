import json
import os
import socket
import subprocess
import sys
import threading
import traceback

HOST = "127.0.0.1"
PORT = 5555

class PDBServer:
    def __init__(self, data_dir, desktop_frame=None):
        self.data_dir = data_dir
        self.desktop = desktop_frame
        self._running = False
        self._server = None
        self._thread = None

    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._serve, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._server:
            try:
                self._server.close()
            except Exception:
                pass

    def _serve(self):
        self._server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server.settimeout(1.0)
        try:
            self._server.bind((HOST, PORT))
            self._server.listen(5)
        except OSError:
            self._running = False
            return
        while self._running:
            try:
                conn, addr = self._server.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except socket.timeout:
                continue
            except Exception:
                break

    def _handle(self, conn):
        try:
            data = conn.recv(65536).decode("utf-8", errors="replace")
            if not data:
                return
            response = self._dispatch(data.strip())
            conn.sendall((response + "\n").encode("utf-8"))
        except Exception as e:
            try:
                conn.sendall(f"error: {e}\n".encode("utf-8"))
            except Exception:
                pass
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _dispatch(self, cmd):
        parts = cmd.split()
        if not parts:
            return "error: empty command"
        verb = parts[0]
        if verb == "ping":
            return "pong"
        if verb == "reboot":
            threading.Thread(target=self._do_reboot, daemon=True).start()
            return "ok: rebooting"
        if verb == "recovery":
            threading.Thread(target=self._do_recovery, daemon=True).start()
            return "ok: rebooting to recovery"
        if verb == "safe":
            threading.Thread(target=self._do_safe, daemon=True).start()
            return "ok: rebooting to safe mode"
        if verb == "shell":
            return self._do_shell(" ".join(parts[1:]))
        if verb == "exec":
            return self._do_exec(" ".join(parts[1:]))
        if verb == "rom" and len(parts) >= 2:
            return self._do_rom(parts[1], " ".join(parts[2:]))
        if verb == "push" and len(parts) >= 3:
            return self._do_push(parts[1], parts[2])
        if verb == "pull" and len(parts) >= 3:
            return self._do_pull(parts[1], parts[2])
        if verb == "logcat":
            return self._do_logcat()
        if verb == "getprop":
            return self._do_getprop()
        return f"error: unknown command: {verb}"

    def _do_reboot(self):
        subprocess.Popen([sys.executable, __file__])
        wx_callafter_safe("ExitMainLoop")

    def _do_recovery(self):
        subprocess.Popen([sys.executable, __file__, "--recovery"])
        wx_callafter_safe("ExitMainLoop")

    def _do_safe(self):
        subprocess.Popen([sys.executable, __file__, "--safe"])
        wx_callafter_safe("ExitMainLoop")

    def _do_shell(self, cmdline):
        try:
            result = subprocess.run(cmdline, shell=True, capture_output=True, text=True, timeout=30)
            out = result.stdout + result.stderr
            return out if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "error: command timed out"
        except Exception as e:
            return f"error: {e}"

    def _do_exec(self, code):
        if not code:
            return "error: no code"
        try:
            local_vars = {"data_dir": self.data_dir, "desktop": self.desktop}
            exec(code, globals(), local_vars)
            result = local_vars.get("_", None)
            if result is not None:
                return str(result)
            return "ok"
        except Exception as e:
            return f"error: {traceback.format_exc()}"

    def _do_rom(self, action, arg):
        try:
            import rom_manager
        except ImportError:
            return "error: rom_manager not available"
        if action == "list":
            roms = rom_manager.list_roms(self.data_dir)
            lines = []
            active, _ = rom_manager.get_active_rom(self.data_dir)
            for name, data in roms:
                mark = "*" if name == active else " "
                lines.append(f" {mark} {data.get('name', name):20s} v{data.get('version', '?'):8s} by {data.get('author', '?')}")
            return "\n".join(lines) if lines else "(no ROMs)"
        if action == "switch" and arg:
            rom_manager.set_active_rom(self.data_dir, arg)
            return f"ok: switched to {arg}"
        if action == "info" and arg:
            rom = rom_manager.get_rom(self.data_dir, arg)
            if rom:
                return json.dumps(rom, indent=2)
            return f"error: ROM '{arg}' not found"
        if action == "install" and arg:
            if not os.path.exists(arg):
                return f"error: file not found: {arg}"
            name = rom_manager.install_rom(self.data_dir, arg)
            if name:
                return f"ok: installed {name}"
            return "error: invalid ROM file"
        if action == "delete" and arg:
            ok = rom_manager.delete_rom(self.data_dir, arg)
            return "ok" if ok else "error: not found or is Stock"
        if action == "export":
            path = os.path.join(self.data_dir, "exported_rom.json")
            rom_manager.export_current_config(self.data_dir, path)
            return f"ok: exported to {path}"
        if action == "active":
            name, data = rom_manager.get_active_rom(self.data_dir)
            return json.dumps(data, indent=2)
        return f"error: unknown rom subcommand: {action}"

    def _do_push(self, local, remote):
        if not os.path.exists(local):
            return f"error: local file not found: {local}"
        remote_path = remote if os.path.isabs(remote) else os.path.join(self.data_dir, remote)
        os.makedirs(os.path.dirname(remote_path), exist_ok=True)
        try:
            import shutil
            shutil.copy2(local, remote_path)
            return f"ok: {local} -> {remote_path}"
        except Exception as e:
            return f"error: {e}"

    def _do_pull(self, remote, local):
        remote_path = remote if os.path.isabs(remote) else os.path.join(self.data_dir, remote)
        if not os.path.exists(remote_path):
            return f"error: remote file not found: {remote_path}"
        os.makedirs(os.path.dirname(local), exist_ok=True)
        try:
            import shutil
            shutil.copy2(remote_path, local)
            return f"ok: {remote_path} -> {local}"
        except Exception as e:
            return f"error: {e}"

    def _do_logcat(self):
        import logging
        logs = []
        try:
            logfile = os.path.join(self.data_dir, "pyos.log")
            if os.path.exists(logfile):
                with open(logfile) as f:
                    logs = f.readlines()[-50:]
        except Exception:
            pass
        return "".join(logs) if logs else "(no logs)"

    def _do_getprop(self):
        props = {
            "pyos.version": "1.0",
            "pyos.platform": sys.platform,
            "pyos.python": sys.version,
            "pyos.data_dir": self.data_dir,
            "pyos.safe_mode": str(getattr(self.desktop, "safe_mode", False)),
            "pyos.recovery_mode": str(getattr(self.desktop, "recovery_mode", False)),
        }
        return json.dumps(props, indent=2)

def wx_callafter_safe(method):
    try:
        import wx
        app = wx.GetApp()
        if app:
            wx.CallAfter(getattr(app, method))
    except Exception:
        pass
