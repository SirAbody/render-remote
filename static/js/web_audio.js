/**
 * Web Audio Handler for RenderRemote
 * Handles browser-side audio processing for remote streaming
 */

class WebAudio {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.audioContext = null;
        this.audioBufferQueue = [];
        this.isPlaying = false;
        this.processorNode = null;
        this.pollingInterval = null;
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
            console.log('Web Audio context initialized');
        } catch (e) {
            console.error('Web Audio API not supported:', e);
        }
    }
    
    // Start audio playback from remote microphone
    startMicrophonePlayback() {
        if (!this.audioContext) {
            console.error('Audio context not available');
            return false;
        }
        
        // If audio context is suspended (browser requirement for autoplay), resume it
        if (this.audioContext.state === 'suspended') {
            this.audioContext.resume();
        }
        
        // Create script processor for audio output
        this.processorNode = this.audioContext.createScriptProcessor(this.bufferSize, 1, 1);
        
        // Fill the output buffer with audio data from server
        this.processorNode.onaudioprocess = (e) => {
            const outputBuffer = e.outputBuffer.getChannelData(0);
            
            // If we have audio data in buffer
            if (this.audioBufferQueue.length > 0) {
                const audioData = this.audioBufferQueue.shift();
                
                // Fill the output buffer with our audio data
                for (let i = 0; i < outputBuffer.length; i++) {
                    outputBuffer[i] = i < audioData.length ? audioData[i] : 0;
                }
            } else {
                // No data, fill with silence
                for (let i = 0; i < outputBuffer.length; i++) {
                    outputBuffer[i] = 0;
                }
            }
        };
        
        // Connect to audio output
        this.processorNode.connect(this.audioContext.destination);
        
        // Start polling for audio data from server
        this.isPlaying = true;
        this.startPolling();
        
        console.log('Microphone playback started');
        return true;
    }
    
    // Stop audio playback
    stopAudioPlayback() {
        if (this.processorNode) {
            this.processorNode.disconnect();
            this.processorNode = null;
        }
        
        this.isPlaying = false;
        this.stopPolling();
        this.audioBufferQueue = [];
        
        console.log('Audio playback stopped');
    }
    
    // Start polling for audio data
    startPolling() {
        if (this.pollingInterval) return;
        
        this.pollingInterval = setInterval(() => {
            this.pollAudioData();
        }, 50); // Poll every 50ms for responsive audio
        
        console.log('Started polling for audio data');
    }
    
    // Stop polling for audio data
    stopPolling() {
        if (this.pollingInterval) {
            clearInterval(this.pollingInterval);
            this.pollingInterval = null;
            console.log('Stopped polling for audio data');
        }
    }
    
    // Poll server for audio data
    pollAudioData() {
        if (!this.isPlaying) return;
        
        fetch(`/api/audio/download/${this.deviceId}?audio_type=microphone&timestamp=${Date.now()}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.audio_data) {
                    // Decode base64 audio data
                    try {
                        const binary = atob(data.audio_data);
                        const bytes = new Uint8Array(binary.length);
                        for (let i = 0; i < binary.length; i++) {
                            bytes[i] = binary.charCodeAt(i);
                        }
                        
                        // Convert to float32 audio data
                        const audioData = new Float32Array(bytes.buffer);
                        
                        // Add to buffer queue
                        this.audioBufferQueue.push(audioData);
                        
                        // Limit buffer size to prevent memory issues
                        while (this.audioBufferQueue.length > 10) {
                            this.audioBufferQueue.shift();
                        }
                    } catch (e) {
                        console.error('Error processing audio data:', e);
                    }
                }
            })
            .catch(error => {
                console.error('Error polling audio data:', error);
            });
    }
}

// Make WebAudio available globally
window.WebAudio = WebAudio;
