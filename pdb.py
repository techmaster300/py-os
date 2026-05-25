#!/usr/bin/env python3
"""
PyOS Debug Bridge (PDB) - CLI tool to communicate with a running PyOS instance.

Usage:
  pdb.py ping
  pdb.py shell <command>
  pdb.py exec <python_code>
  pdb.py reboot
  pdb.py recovery
  pdb.py safe
  pdb.py rom list
  pdb.py rom active
  pdb.py rom info <name>
  pdb.py rom switch <name>
  pdb.py rom install <path>
  pdb.py rom delete <name>
  pdb.py rom export
  pdb.py push <local> <remote>
  pdb.py pull <remote> <local>
  pdb.py logcat
  pdb.py getprop
"""

import json
import os
import socket
import sys

HOST = os.environ.get("PDB_HOST", "127.0.0.1")
PORT = int(os.environ.get("PDB_PORT", "5555"))


def send_command(cmd):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((HOST, PORT))
        s.sendall(cmd.encode("utf-8"))
        response = s.recv(65536).decode("utf-8", errors="replace")
        return response
    except socket.timeout:
        return "error: connection timed out"
    except ConnectionRefusedError:
        return "error: connection refused - is PyOS running?"
    except Exception as e:
        return f"error: {e}"
    finally:
        try:
            s.close()
        except Exception:
            pass


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    cmd = " ".join(sys.argv[1:])
    result = send_command(cmd)
    print(result)


if __name__ == "__main__":
    main()
