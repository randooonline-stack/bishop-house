import os
import subprocess
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit

# Initialize Flask App
app = Flask(__name__)
app.config['SECRET_KEY'] = 'bishop_secure_key_99'

# Initialize SocketIO (The Real-Time Engine)
# cors_allowed_origins="*" allows connections from anywhere (Phone, PC, etc.)
socketio = SocketIO(app, cors_allowed_origins="*")

# In-Memory Storage for Active Network (Resets if server restarts)
active_members = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. REAL-TIME RADAR & LOCATION ---
@socketio.on('update_location')
def handle_location(data):
    # data contains {name, lat, lon, role, lastActive}
    active_members[data['name']] = data
    # Broadcast the updated list to EVERYONE connected
    emit('network_update', list(active_members.values()), broadcast=True)

# --- 2. REAL-TIME CHAT ---
@socketio.on('send_message')
def handle_message(data):
    # Broadcast message to all clients
    # In a real app, you would filter by 'target', but for this demo we broadcast
    print(f"Msg: {data['sender']} -> {data['message']}")
    emit('receive_message', data, broadcast=True)

# --- 3. REAL TERMINAL EXECUTION ---
@socketio.on('terminal_command')
def execute_command(data):
    # Cloud Security: We strictly limit what runs on the real server to prevent crashes
    cmd = data.get('command', '').lower().strip()
    output = ""
    
    if cmd == 'ip':
        # On cloud, this shows the server's internal IP acting as a proxy
        output = "SERVER NODE: 10.0.x.x (Masked via Render Cloud)" 
    elif cmd == 'speed':
        output = "LATENCY TEST: 0.04ms (Internal Node Speed)"
    elif cmd == 'ping':
        output = "PING 8.8.8.8: 64 bytes from 8.8.8.8: icmp_seq=1 ttl=118 time=14.2 ms"
    elif cmd == 'help':
         output = "AVAILABLE TOOLS: ip, speed, ping, pass, calc"
    else:
        # Simulate successful execution for immersion
        output = f"BISHOP KERNEL: Command '{cmd}' executed successfully on secure node."
        
    emit('terminal_output', {'output': output})

if __name__ == '__main__':
    # Get the PORT from Render's environment variables (default to 5000 if local)
    port = int(os.environ.get("PORT", 5000))
    # '0.0.0.0' is required for cloud hosting
    socketio.run(app, host='0.0.0.0', port=port)