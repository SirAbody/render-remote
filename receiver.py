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
from PIL import ImageGrab
from pathlib import Path
from datetime import datetime

# Set your server URL here
SERVER_URL = "https://render-remote.onrender.com"

class Receiver:
    def __init__(self, server_url):
        self.server_url = server_url
        self.system = platform.system()
        self.device_id = self._generate_device_id()
        self.screen_sharing_active = False
        self.screen_quality = 70  # JPEG quality (0-100)
        self.screen_interval = 0.5  # seconds between screen captures
        self.screen_thread = None
        self.stop_event = threading.Event()
        
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
            # Capture the entire screen
            img = ImageGrab.grab()
            
            # Get the screen dimensions for mouse control
            screen_width, screen_height = img.size
            
            # Resize image to reduce bandwidth if it's large
            if screen_width > 1920 or screen_height > 1080:
                img = img.resize((min(screen_width, 1920), min(screen_height, 1080)), resample=1)
                
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
            
            return {"status": "error", "message": "Invalid mouse action"}
        except Exception as e:
            print(f"Error controlling mouse: {str(e)}")
            return {"status": "error", "message": str(e)}
    
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
                        else:
                            print(f"Error sending screen data: {response.status_code}")
                    except Exception as e:
                        print(f"Error sending screen data: {str(e)}")
            except Exception as e:
                print(f"Error in screen sharing loop: {str(e)}")
                
            # Wait before next capture
            time.sleep(self.screen_interval)
    
    def run(self):
        """Main loop to poll and process commands"""
        print("Starting command polling...")
        
        try:
            while True:
                # Poll for commands
                commands = self.poll_commands()
                
                # Process each command
                for command_id, cmd in commands.items():
                    print(f"Received command: {cmd}")
                    
                    # Special commands that start with !
                    if cmd.startswith("!"):
                        if cmd.startswith("!download "):
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
