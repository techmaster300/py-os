import socket
import json

class NetworkService:
    def __init__(self, port=3030):
        self.port = port
        self.host = '127.0.0.1'

    def start(self):
        """No-op to maintain compatibility with system service patterns."""
        pass

    def send_request(self, command, params=None):
        """Sends a request to the server and returns the response."""
        try:
            client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            payload = json.dumps({"command": command, "params": params or {}})
            client.sendto(payload.encode(), (self.host, self.port))
            
            # Simple synchronous receive (blocking)
            client.settimeout(5.0)
            data, addr = client.recvfrom(1024)
            return json.loads(data.decode())
        except Exception as e:
            return {"error": str(e)}
