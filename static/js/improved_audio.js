/**
 * Improved Audio Handler for RenderRemote
 * Handles browser-side audio processing to ensure audio is played in the browser
 */

class ImprovedAudio {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.audioContext = null;
        this.audioQueue = [];
        this.isPlaying = false;
        this.processorNode = null;
        this.pollTimer = null;
        this.pollInterval = 50; // ms
        this.bufferSize = 4096; // Larger buffer for smoother playback
        
        // Initialize audio context when possible
        this.initAudioContext();
    }
    
    // Initialize Web Audio API context
    initAudioContext() {
        try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({
                latencyHint: 'interactive',
                sampleRate: 48000 // Higher sample rate for better quality
            });
            console.log('ImprovedAudio: Audio context initialized successfully');
        } catch (e) {
            console.error('ImprovedAudio: Failed to initialize audio context:', e);
        }
    }
    
    // Start playback of microphone audio in browser
    startAudio() {
        if (!this.audioContext) {
            console.error('ImprovedAudio: Audio context not available');
            return false;
        }
        
        if (this.isPlaying) {
            console.log('ImprovedAudio: Audio already playing');
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
            
            console.log('ImprovedAudio: Audio playback started');
            return true;
        } catch (e) {
            console.error('ImprovedAudio: Error starting audio playback:', e);
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
            
            console.log('ImprovedAudio: Audio playback stopped');
        } catch (e) {
            console.error('ImprovedAudio: Error stopping audio playback:', e);
        }
    }
    
    // Start polling for audio data from the server
    startPolling() {
        if (this.pollTimer) return;
        
        this.pollTimer = setInterval(() => this.pollAudio(), this.pollInterval);
        console.log('ImprovedAudio: Started polling for audio data');
    }
    
    // Stop polling for audio data
    stopPolling() {
        if (this.pollTimer) {
            clearInterval(this.pollTimer);
            this.pollTimer = null;
            console.log('ImprovedAudio: Stopped polling for audio data');
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
                        console.error('ImprovedAudio: Error processing audio data:', e);
                    }
                }
            })
            .catch(error => {
                console.error('ImprovedAudio: Error polling audio data:', error);
            });
    }
}

// Make ImprovedAudio available globally
window.ImprovedAudio = ImprovedAudio;
