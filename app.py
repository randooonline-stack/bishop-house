import os
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import eventlet

# Monkey patch for eventlet (required for Gunicorn/Async)
eventlet.monkey_patch()

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bishop_secure_key_99'

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='eventlet')

# In-Memory Storage
active_members = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. NETWORK & LOCATION ---
@socketio.on('join_network')
def handle_join(data):
    # Store session ID (sid) to target specific users for calls
    data['sid'] = request.sid
    data['lastActive'] = 0  # Reset or track real time
    active_members[data['name']] = data
    emit('network_update', list(active_members.values()), broadcast=True)

@socketio.on('update_location')
def handle_location(data):
    if data['name'] in active_members:
        active_members[data['name']].update({
            'lat': data['lat'],
            'lon': data['lon'],
            'lastActive': data['lastActive']
        })
        emit('network_update', list(active_members.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    # Remove user or mark offline
    to_remove = [k for k, v in active_members.items() if v.get('sid') == request.sid]
    for k in to_remove:
        del active_members[k]
    emit('network_update', list(active_members.values()), broadcast=True)

# --- 2. LIVE CHAT ---
@socketio.on('send_message')
def handle_message(data):
    # Broadcast to all (client filters for private view)
    emit('receive_message', data, broadcast=True)

# --- 3. VOICE CALL SIGNALING (Relay) ---
@socketio.on('call_request')
def handle_call_req(data):
    # data: { target_sid, caller_name, ... }
    socketio.emit('incoming_call', data, to=data['target_sid'])

@socketio.on('call_response')
def handle_call_res(data):
    socketio.emit('call_response_relay', data, to=data['target_sid'])

@socketio.on('webrtc_signal')
def handle_signal(data):
    socketio.emit('webrtc_signal_relay', data, to=data['target_sid'])

@socketio.on('end_call')
def handle_end(data):
    socketio.emit('call_ended', data, to=data['target_sid'])

# --- 4. TERMINAL ---
@socketio.on('terminal_command')
def execute_command(data):
    cmd = data.get('command', '').lower().strip()
    output = f"BISHOP KERNEL: Command '{cmd}' executed."
    if cmd == 'scan': output = f"SCAN COMPLETE: {len(active_members)} nodes active."
    emit('terminal_output', {'output': output})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port)
