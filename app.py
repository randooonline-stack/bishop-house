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
# Structure: { 'username': { 'sid': '...', 'lat': 0, 'lon': 0, 'name': '...' } }
active_members = {}

@app.route('/')
def index():
    return render_template('index.html')

# --- 1. NETWORK & LOCATION ---
@socketio.on('join_network')
def handle_join(data):
    # Store session ID (sid) to target specific users for calls
    user_name = data.get('name')
    if user_name:
        data['sid'] = request.sid
        data['lastActive'] = data.get('lastActive', 0)
        active_members[user_name] = data
        
        print(f"BISHOP NETWORK: {user_name} connected via {request.sid}")
        # Broadcast list of active users so clients know SIDs
        emit('network_update', list(active_members.values()), broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    # Remove user based on SID
    user_to_remove = None
    for name, data in active_members.items():
        if data.get('sid') == request.sid:
            user_to_remove = name
            break
            
    if user_to_remove:
        print(f"BISHOP NETWORK: {user_to_remove} disconnected.")
        del active_members[user_to_remove]
        emit('network_update', list(active_members.values()), broadcast=True)

# --- 2. LIVE CHAT ---
@socketio.on('send_message')
def handle_message(data):
    # data: { target_name, target_sid, sender, message }
    target_sid = data.get('target_sid')
    
    # Send to target
    if target_sid:
        emit('receive_message', data, to=target_sid)
    
    # Send back to sender (confirmation) - optional, but good for UI consistency if not handled locally
    # We will handle "Me" bubble locally in JS, so strictly just forward here if needed.

# --- 3. VOICE CALL SIGNALING (Relay) ---
# WebRTC requires exchanging "Offers", "Answers", and "ICE Candidates" between peers.
# The server acts as the signal pipe.

@socketio.on('call_request')
def handle_call_req(data):
    # data: { target_sid, caller_name, caller_sid, offer }
    target_sid = data.get('target_sid')
    if target_sid:
        emit('incoming_call', data, to=target_sid)

@socketio.on('call_answer')
def handle_call_ans(data):
    # data: { target_sid, answer }
    target_sid = data.get('target_sid')
    if target_sid:
        emit('call_answered', data, to=target_sid)

@socketio.on('ice_candidate')
def handle_ice(data):
    # data: { target_sid, candidate }
    target_sid = data.get('target_sid')
    if target_sid:
        emit('receive_ice_candidate', data, to=target_sid)

@socketio.on('end_call')
def handle_end(data):
    target_sid = data.get('target_sid')
    if target_sid:
        emit('call_terminated', data, to=target_sid)

# --- 4. TERMINAL ---
@socketio.on('terminal_command')
def execute_command(data):
    cmd = data.get('command', '').lower().strip()
    output = f"BISHOP KERNEL: Command '{cmd}' executed."
    if cmd == 'scan': 
        output = f"SCAN COMPLETE: {len(active_members)} nodes active on secure grid."
    emit('terminal_output', {'output': output})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    socketio.run(app, host='0.0.0.0', port=port, debug=True)
