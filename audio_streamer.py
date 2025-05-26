#!/usr/bin/env python
# -*- coding: utf-8 -*-
# Copyright (c) 2025 SirAbody. All rights reserved.

import pyaudio
import threading
import time
import numpy as np
import base64
import wave
import io
import socket
import requests
import json
import struct

class AudioStreamer:
    def __init__(self, server_url, device_id, chunk=4096, channels=1, rate=48000, p=None):
        self.server_url = server_url
        self.device_id = device_id
        self.chunk = chunk
        self.channels = channels
        self.rate = rate
        self.format = pyaudio.paInt16
        
        # Initialize PyAudio
        self.p = p if p else pyaudio.PyAudio()
        
        # Audio streaming state
        self.mic_stream = None
        self.speaker_stream = None
        self.mic_active = False
        self.speaker_active = False
        self.stop_event = threading.Event()
        self.mic_thread = None
        self.speaker_thread = None
        
        # Get audio device information
        self.input_devices = self._get_input_devices()
        self.output_devices = self._get_output_devices()
        
        print(f"Audio Streamer initialized for device: {device_id}")
        print(f"Available input devices: {len(self.input_devices)}")
        print(f"Available output devices: {len(self.output_devices)}")
        
    def _get_input_devices(self):
        """Get available input (microphone) devices"""
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxInputChannels']
                })
        return devices
    
    def _get_output_devices(self):
        """Get available output (speaker) devices"""
        devices = []
        for i in range(self.p.get_device_count()):
            device_info = self.p.get_device_info_by_index(i)
            if device_info['maxOutputChannels'] > 0:
                devices.append({
                    'index': i,
                    'name': device_info['name'],
                    'channels': device_info['maxOutputChannels']
                })
        return devices
    
    def start_microphone_streaming(self, device_index=None):
        """Start streaming microphone audio to the server"""
        if self.mic_active:
            print("Microphone streaming is already active")
            return False
        
        # Reset stop event
        self.stop_event.clear()
        self.mic_active = True
        
        # Start microphone streaming in a new thread
        self.mic_thread = threading.Thread(
            target=self._microphone_streaming_loop,
            args=(device_index,)
        )
        self.mic_thread.daemon = True
        self.mic_thread.start()
        
        print("Microphone streaming started")
        return True
    
    def stop_microphone_streaming(self):
        """Stop microphone streaming"""
        if not self.mic_active:
            print("Microphone streaming is not active")
            return False
        
        # Signal the thread to stop
        self.stop_event.set()
        
        # Stop and close the stream
        if self.mic_stream:
            try:
                self.mic_stream.stop_stream()
                self.mic_stream.close()
            except Exception as e:
                print(f"Error stopping microphone stream: {str(e)}")
        
        # Wait for thread to finish
        if self.mic_thread and self.mic_thread.is_alive():
            self.mic_thread.join(timeout=5)
        
        self.mic_active = False
        print("Microphone streaming stopped")
        return True
    
    def start_speaker_streaming(self, device_index=None):
        """Start streaming audio from the server to speakers"""
        if self.speaker_active:
            print("Speaker streaming is already active")
            return False
        
        # Reset stop event
        self.stop_event.clear()
        self.speaker_active = True
        
        # Start speaker streaming in a new thread
        self.speaker_thread = threading.Thread(
            target=self._speaker_streaming_loop,
            args=(device_index,)
        )
        self.speaker_thread.daemon = True
        self.speaker_thread.start()
        
        print("Speaker streaming started")
        return True
    
    def stop_speaker_streaming(self):
        """Stop speaker streaming"""
        if not self.speaker_active:
            print("Speaker streaming is not active")
            return False
        
        # Signal the thread to stop
        self.stop_event.set()
        
        # Stop and close the stream
        if self.speaker_stream:
            try:
                self.speaker_stream.stop_stream()
                self.speaker_stream.close()
            except Exception as e:
                print(f"Error stopping speaker stream: {str(e)}")
        
        # Wait for thread to finish
        if self.speaker_thread and self.speaker_thread.is_alive():
            self.speaker_thread.join(timeout=5)
        
        self.speaker_active = False
        print("Speaker streaming stopped")
        return True
    
    def _microphone_streaming_loop(self, device_index=None):
        """Main loop for capturing and uploading microphone audio"""
        try:
            # Open microphone stream
            self.mic_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=self.chunk,
                input_device_index=device_index
            )
            
            print(f"Microphone stream opened with device index: {device_index}")
            
            # Start recording loop
            while not self.stop_event.is_set():
                try:
                    # Record audio chunk
                    audio_data = self.mic_stream.read(self.chunk, exception_on_overflow=False)
                    
                    # Encode audio data to base64
                    audio_b64 = base64.b64encode(audio_data).decode()
                    
                    # Send to server
                    try:
                        response = requests.post(
                            f"{self.server_url}/api/audio/upload/{self.device_id}",
                            json={
                                "audio_data": audio_b64,
                                "format": "pcm",
                                "channels": self.channels,
                                "rate": self.rate,
                                "timestamp": time.time()
                            },
                            timeout=1
                        )
                        
                        if response.status_code != 200:
                            print(f"Error uploading audio: {response.status_code}")
                    except Exception as e:
                        print(f"Error sending audio data: {str(e)}")
                        # Short delay to prevent flooding logs with errors
                        time.sleep(0.5)
                        
                except Exception as e:
                    print(f"Error recording audio: {str(e)}")
                    time.sleep(0.5)
        
        except Exception as e:
            print(f"Error in microphone streaming: {str(e)}")
        finally:
            # Ensure we clean up if there's an error
            if self.mic_stream:
                try:
                    self.mic_stream.stop_stream()
                    self.mic_stream.close()
                except:
                    pass
    
    def _speaker_streaming_loop(self, device_index=None):
        """Main loop for receiving and playing audio"""
        try:
            # Open speaker stream
            self.speaker_stream = self.p.open(
                format=self.format,
                channels=self.channels,
                rate=self.rate,
                output=True,
                frames_per_buffer=self.chunk,
                output_device_index=device_index
            )
            
            print(f"Speaker stream opened with device index: {device_index}")
            
            # Playback loop
            while not self.stop_event.is_set():
                try:
                    # Get audio data from server
                    response = requests.get(
                        f"{self.server_url}/api/audio/download/{self.device_id}",
                        timeout=1
                    )
                    
                    if response.status_code == 200:
                        audio_data = response.json()
                        
                        if audio_data and "audio_data" in audio_data:
                            # Decode audio from base64
                            audio_bytes = base64.b64decode(audio_data["audio_data"])
                            
                            # Only play audio locally if configured to do so
                            # Comment out or remove the next line to prevent local playback
                            # self.speaker_stream.write(audio_bytes)
                            # Just keep receiving audio data for the web interface to use
                    
                    # Add a small delay to prevent flooding the server with requests
                    time.sleep(0.05)
                    
                except Exception as e:
                    print(f"Error downloading or playing audio: {str(e)}")
                    time.sleep(0.5)
        
        except Exception as e:
            print(f"Error in speaker streaming: {str(e)}")
        finally:
            # Ensure we clean up if there's an error
            if self.speaker_stream:
                try:
                    self.speaker_stream.stop_stream()
                    self.speaker_stream.close()
                except:
                    pass
    
    def get_audio_devices(self):
        """Return the available audio devices"""
        return {
            "input": self.input_devices,
            "output": self.output_devices
        }
    
    def close(self):
        """Clean up resources"""
        self.stop_microphone_streaming()
        self.stop_speaker_streaming()
        
        if self.p:
            self.p.terminate()
            
        print("Audio Streamer closed")
