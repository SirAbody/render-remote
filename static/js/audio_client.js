/**
 * Audio Client for RenderRemote
 * Handles streaming audio from/to the server in the browser
 */

class AudioClient {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.audioContext = null;
        this.streamDestination = null;
        this.audioBuffer = [];
        this.pollInterval = 100; // ms between polls
        this.pollTimer = null;
        this.isPlaying = false;
        this.audioNode = null;
        this.bufferSize = 4096; // Larger buffer for smoother playback
        
        // Initialize the Web Audio API
        this.initAudio();
    }
    
    // Initialize the Web Audio API context
    initAudio() {
        try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({
                latencyHint: 'interactive',
                sampleRate: 48000 // Higher sample rate for better quality
            });
            console.log('AudioClient: Web Audio API initialized successfully');
        } catch (e) {
            console.error('AudioClient: Web Audio API initialization failed:', e);
        }
    }
    
    // Start playing audio from the server
    startAudioPlayback() {
        if (!this.audioContext) {
            console.error('AudioClient: Audio context not available');
            return false;
        }
        
        if (this.isPlaying) {
            console.log('AudioClient: Audio playback already active');
            return true;
        }
        
        try {
            // Resume the audio context if it's suspended (browsers require user interaction)
            if (this.audioContext.state === 'suspended') {
                this.audioContext.resume();
            }
            
            // Create a script processor node for audio output
            this.audioNode = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
            
            // Set up the audio processing callback
            this.audioNode.onaudioprocess = (e) => {
                const outputBuffer = e.outputBuffer.getChannelData(0);
                
                if (this.audioBuffer.length > 0) {
                    // Get audio data from our buffer
                    const audioData = this.audioBuffer.shift();
                    
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
            this.audioNode.connect(this.audioContext.destination);
            
            // Start polling for audio data
            this.isPlaying = true;
            this.startPolling();
            
            console.log('AudioClient: Audio playback started');
            return true;
        } catch (e) {
            console.error('AudioClient: Error starting audio playback:', e);
            return false;
        }
    }
    
    // Stop audio playback
    stopAudioPlayback() {
        if (!this.isPlaying) return;
        
        try {
            // Disconnect the audio node
            if (this.audioNode) {
                this.audioNode.disconnect();
                this.audioNode = null;
            }
            
            // Stop polling
            this.stopPolling();
            
            // Clear the buffer
            this.audioBuffer = [];
            this.isPlaying = false;
            
            console.log('AudioClient: Audio playback stopped');
        } catch (e) {
            console.error('AudioClient: Error stopping audio playback:', e);
        }
    }
    
    // Start polling for audio data from the server
    startPolling() {
        if (this.pollTimer) return;
        
        this.pollTimer = setInterval(() => this.pollAudio(), this.pollInterval);
        console.log('AudioClient: Started polling for audio data');
    }
    
    // Stop polling for audio data
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
            console.log('AudioClient: Stopped polling for audio data');
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
                    this.audioBuffer.push(audioData);
                    
                    // Limit buffer size to prevent memory issues
                    // But keep enough data for smooth playback
                    while (this.audioBuffer.length > 10) {
                        this.audioBuffer.shift();
                    }
                }
            })
            .catch(error => {
                console.error('AudioClient: Error polling audio data:', error);
            });
    }
}

// Make the AudioClient available globally
window.AudioClient = AudioClient;
