import socket
import json
import hashlib

def run_server():
    host = '127.0.0.1'
    port = 3030
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((host, port))
    print(f"Server started on {host}:{port}")

    # Database structure
    apps_data = {
        "Calculator": {"version": "2.0", "description": "Powerful math tool"},
        "Messaging": {"version": "1.5", "description": "Global chat"}
    }
    
    addons_data = {
        "Calculator": {
            "ScientificMode": {"version": "1.0", "description": "Advanced trig functions"}
        },
        "Messaging": {
            "EmojiPack": {"version": "1.1", "description": "Send fun symbols"}
        }
    }
    
    # Registry: {hashed_username: {data}}
    user_registry = {}
    # Active sessions: {address: username}
    users = {}
    message_counter = 0

    def hash_user(username):
        return hashlib.sha256(username.encode()).hexdigest()

    while True:
        data, addr = server.recvfrom(1024)
        try:
            req = json.loads(data.decode())
            cmd = req.get("command")
            
            if cmd == "create":
                username = req.get("username")
                if not username or hash_user(username) in user_registry:
                    resp = json.dumps({"status": "error", "message": "Username taken or invalid"})
                else:
                    user_registry[hash_user(username)] = {"status": "registered"}
                    resp = json.dumps({"status": "success", "message": "Account created"})
                server.sendto(resp.encode(), addr)
                
            elif cmd == "login":
                username = req.get("username")
                if hash_user(username) in user_registry:
                    users[addr] = username
                    resp = json.dumps({"status": "success", "message": f"Welcome {username}"})
                else:
                    resp = json.dumps({"status": "error", "message": "Account not found"})
                server.sendto(resp.encode(), addr)
            
            elif cmd == "message":
                if addr not in users:
                    server.sendto(json.dumps({"error": "Not logged in"}).encode(), addr)
                    continue
                message_counter += 1
                sender = users[addr]
                text = req.get("text", "")
                relay_msg = json.dumps({
                    "code": f"MSG-{message_counter:04d}",
                    "user": sender,
                    "text": text
                })
                for client in users:
                    server.sendto(relay_msg.encode(), client)
                    
            elif cmd == "list_apps":
                resp = json.dumps({"apps": apps_data})
                server.sendto(resp.encode(), addr)
            elif cmd == "get_addons":
                resp = json.dumps({"addons": addons_data.get(req.get("params", {}).get("app_name"), {})})
                server.sendto(resp.encode(), addr)
            elif cmd == "download_item":
                resp = json.dumps({"status": "downloaded", "item": req.get("params", {}).get("name")})
                server.sendto(resp.encode(), addr)
        except Exception as e:
            print(f"Server error: {e}")

if __name__ == '__main__':
    run_server()
