/**
 * Browser Audio Player for RenderRemote
 * This script ensures audio plays in the browser instead of on the receiver computer
 */

class BrowserAudioPlayer {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.processorNode = null;
        this.pollTimer = null;
        this.pollInterval = 50; // ms
        this.bufferSize = 4096; // Larger buffer for smoother playback

        // Initialize when the page loads
        this.initAudioContext();
        
        // Automatically hook into the page's audio controls
        this.hookIntoPage();
    }
    
    // Initialize Web Audio API context
    initAudioContext() {
        try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({
                latencyHint: 'interactive',
                sampleRate: 48000 // Higher sample rate for better quality
            });
            console.log('Browser Audio: Audio context initialized successfully');
        } catch (e) {
            console.error('Browser Audio: Failed to initialize audio context:', e);
        }
    }
    
    // Hook into the page's existing audio controls
    hookIntoPage() {
        // Wait for the DOM to be fully loaded
        document.addEventListener('DOMContentLoaded', () => {
            this.patchExistingMicrophoneFunction();
            console.log('Browser Audio: Hooked into page audio controls');
        });
        
        // Also try immediately in case DOM is already loaded
        if (document.readyState === 'complete' || document.readyState === 'interactive') {
            setTimeout(() => this.patchExistingMicrophoneFunction(), 100);
        }
    }
    
    // Override the existing microphone start function
    patchExistingMicrophoneFunction() {
        // Store reference to this class for use in function overrides
        const self = this;
        
        // Find the audio control section
        const micStartBtn = document.getElementById('mic-start-btn');
        if (micStartBtn) {
            // Replace the click handler
            const originalClickHandler = micStartBtn.onclick;
            micStartBtn.onclick = null;
            
            micStartBtn.addEventListener('click', function() {
                // First start the audio in browser
                self.startAudio();
                
                // Then call the original function to start microphone on the server
                fetch(`/api/audio/start/${self.deviceId}`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        type: 'microphone'
                    })
                })
                .then(response => response.json())
                .then(data => {
                    if (data.status === 'success') {
                        // Update UI
                        const micStatus = document.getElementById('mic-status');
                        const micStatusText = document.getElementById('mic-status-text');
                        const micStopBtn = document.getElementById('mic-stop-btn');
                        
                        if (micStatus) {
                            micStatus.classList.remove('audio-status-off');
                            micStatus.classList.add('audio-status-on');
                        }
                        
                        if (micStatusText) {
                            micStatusText.textContent = 'الميكروفون يعمل';
                        }
                        
                        // Update buttons
                        micStartBtn.disabled = true;
                        if (micStopBtn) micStopBtn.disabled = false;
                        
                        console.log('Browser Audio: Microphone started on server and playing in browser');
                    } else {
                        console.error('Failed to start microphone:', data.message);
                    }
                })
                .catch(error => {
                    console.error('Error starting microphone:', error);
                });
            });
            
            // Do the same for stop button
            const micStopBtn = document.getElementById('mic-stop-btn');
            if (micStopBtn) {
                micStopBtn.addEventListener('click', function() {
                    // Stop browser audio playback
                    self.stopAudio();
                });
            }
            
            console.log('Browser Audio: Successfully patched microphone controls');
        } else {
            console.warn('Browser Audio: Could not find microphone button to patch');
        }
    }
    
    // Start audio playback in browser
    startAudio() {
        if (!this.audioContext) {
            console.error('Browser Audio: Audio context not available');
            return false;
        }
        
        if (this.isPlaying) {
            console.log('Browser Audio: Audio already playing');
            return true;
        }
        
        try {
            // Resume context if suspended (browser autoplay policy)
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
            
            // Create a script processor node for audio output
            this.processorNode = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
            
            // Set up the audio processing callback
            this.processorNode.onaudioprocess = (e) => {
                const outputBuffer = e.outputBuffer.getChannelData(0);
                
                if (this.audioQueue.length > 0) {
                    // Get audio data from our buffer
                    const audioData = this.audioQueue.shift();
                    
                    // Fill the output buffer with our audio data
                    for (let i = 0; i < outputBuffer.length; i++) {
                        outputBuffer[i] = i < audioData.length ? audioData[i] : 0;
                    }
                } else {
                    // If no data available, output silence
                    for (let i = 0; i < outputBuffer.length; i++) {
                        outputBuffer[i] = 0;
                    }
                }
            };
            
            // Connect the script processor to the audio output
            this.processorNode.connect(this.audioContext.destination);
            
            // Start polling for audio data
            this.isPlaying = true;
            this.startPolling();
            
            console.log('Browser Audio: Audio playback started');
            return true;
        } catch (e) {
            console.error('Browser Audio: Error starting audio playback:', e);
            return false;
        }
    }
    
    // Stop audio playback
    stopAudio() {
        if (!this.isPlaying) return;
        
        try {
            // Disconnect the audio node
            if (this.processorNode) {
                this.processorNode.disconnect();
                this.processorNode = null;
            }
            
            // Stop polling
            this.stopPolling();
            
            // Clear the buffer
            this.audioQueue = [];
            this.isPlaying = false;
            
            console.log('Browser Audio: Audio playback stopped');
        } catch (e) {
            console.error('Browser Audio: Error stopping audio playback:', e);
        }
    }
    
    // Start polling for audio data from the server
    startPolling() {
        if (this.pollTimer) return;
        
        this.pollTimer = setInterval(() => this.pollAudio(), this.pollInterval);
        console.log('Browser Audio: Started polling for audio data');
    }
    
    // Stop polling for audio data
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
            console.log('Browser Audio: Stopped polling for audio data');
        }
    }
    
    // Poll the server for audio data
    pollAudio() {
        if (!this.isPlaying) return;
        
        // Fetch audio data from the server
        fetch(`/api/audio/download/${this.deviceId}?audio_type=microphone&timestamp=${Date.now()}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.audio_data) {
                    try {
                        // Decode the base64 audio data
                        const binaryString = atob(data.audio_data);
                        const bytes = new Uint8Array(binaryString.length);
                        
                        // Convert binary string to byte array
                        for (let i = 0; i < binaryString.length; i++) {
                            bytes[i] = binaryString.charCodeAt(i);
                        }
                        
                        // Convert to float32 audio data
                        const audioData = new Float32Array(bytes.buffer);
                        
                        // Add to our buffer
                        this.audioQueue.push(audioData);
                        
                        // Limit buffer size to prevent memory issues
                        while (this.audioQueue.length > 10) {
                            this.audioQueue.shift();
                        }
                    } catch (e) {
                        console.error('Browser Audio: Error processing audio data:', e);
                    }
                }
            })
            .catch(error => {
                console.error('Browser Audio: Error polling audio data:', error);
            });
    }
}

// Initialize the browser audio player as soon as the script loads
const browserAudioPlayer = new BrowserAudioPlayer(document.querySelector('script').getAttribute('data-device-id') || window.deviceId);
