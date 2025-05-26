/**
 * Audio Handler for RenderRemote
 * Handles audio streaming between the server and client browser
 */

class AudioHandler {
    constructor(deviceId) {
        this.deviceId = deviceId;
        this.audioContext = null;
        this.micStream = null;
        this.speakerStream = null;
        this.audioBuffer = [];
        this.isPlayingAudio = false;
        this.processingNode = null;
        this.audioBufferSize = 4096; // Larger buffer for smoother playback
        this.sampleRate = 48000; // Higher sample rate for better quality
        
        // Audio polling interval (ms)
        this.pollInterval = 50;
        this.pollIntervalId = null;
        
        // Initialize AudioContext when user interacts with page
        document.addEventListener('click', this.initAudioContext.bind(this), { once: true });
    }
    
    // Initialize Web Audio API context
    initAudioContext() {
        try {
            window.AudioContext = window.AudioContext || window.webkitAudioContext;
            this.audioContext = new AudioContext({
                latencyHint: 'interactive',
                sampleRate: this.sampleRate
            });
            console.log('Audio context initialized');
        } catch (e) {
            console.error('Web Audio API not supported:', e);
        }
    }
    
    // Start microphone capture in browser
    async startMicrophoneCapture() {
        if (!this.audioContext) this.initAudioContext();
        
        try {
            // Get user media (microphone)
            const stream = await navigator.mediaDevices.getUserMedia({ 
                audio: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });
            
            this.micStream = stream;
            const source = this.audioContext.createMediaStreamSource(stream);
            const processor = this.audioContext.createScriptProcessor(this.audioBufferSize, 1, 1);
            
            // Process audio data and send to server
            processor.onaudioprocess = (e) => {
                const audioData = e.inputBuffer.getChannelData(0);
                this.sendAudioToServer(audioData);
            };
            
            source.connect(processor);
            processor.connect(this.audioContext.destination);
            
            console.log('Microphone capture started');
            return true;
        } catch (e) {
            console.error('Error starting microphone capture:', e);
            return false;
        }
    }
    
    // Stop microphone capture
    stopMicrophoneCapture() {
        if (this.micStream) {
            this.micStream.getTracks().forEach(track => track.stop());
            this.micStream = null;
            console.log('Microphone capture stopped');
        }
    }
    
    // Start audio playback (to hear remote audio)
    startAudioPlayback() {
        if (!this.audioContext) this.initAudioContext();
        
        // Create a script processor node for audio output
        this.processingNode = this.audioContext.createScriptProcessor(this.audioBufferSize, 1, 1);
        
        // Connect it to the audio context destination (speakers)
        this.processingNode.connect(this.audioContext.destination);
        
        // Fill the output buffer with audio data from server
        this.processingNode.onaudioprocess = (e) => {
            const outputBuffer = e.outputBuffer.getChannelData(0);
            
            // If we have audio data in our buffer
            if (this.audioBuffer.length > 0) {
                // Get the oldest chunk from buffer
                const audioData = this.audioBuffer.shift();
                
                // Fill the output buffer
                for (let i = 0; i < outputBuffer.length; i++) {
                    outputBuffer[i] = i < audioData.length ? audioData[i] : 0;
                }
            } else {
                // No data, output silence
                for (let i = 0; i < outputBuffer.length; i++) {
                    outputBuffer[i] = 0;
                }
            }
        };
        
        // Start polling for audio data from server
        this.isPlayingAudio = true;
        this.startAudioPolling();
        
        console.log('Audio playback started');
        return true;
    }
    
    // Stop audio playback
    stopAudioPlayback() {
        if (this.processingNode) {
            this.processingNode.disconnect();
            this.processingNode = null;
        }
        
        this.isPlayingAudio = false;
        this.stopAudioPolling();
        this.audioBuffer = [];
        
        console.log('Audio playback stopped');
    }
    
    // Start polling for audio data from server
    startAudioPolling() {
        if (this.pollIntervalId) return;
        
        this.pollIntervalId = setInterval(() => {
            this.pollAudioFromServer();
        }, this.pollInterval);
        
        console.log('Audio polling started');
    }
    
    // Stop polling for audio data
    stopAudioPolling() {
        if (this.pollIntervalId) {
            clearInterval(this.pollIntervalId);
            this.pollIntervalId = null;
            console.log('Audio polling stopped');
        }
    }
    
    // Send audio data to server
    sendAudioToServer(audioData) {
        // Convert Float32Array to regular array for JSON
        const audioArray = Array.from(audioData);
        
        // Encode as base64 to reduce data size
        const base64Audio = btoa(String.fromCharCode.apply(null, 
            new Uint8Array(new Float32Array(audioArray).buffer)));
        
        // Send to server
        fetch(`/api/audio/upload/${this.deviceId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                audio_data: base64Audio,
                audio_type: 'microphone',
                timestamp: Date.now()
            })
        })
        .catch(error => {
            console.error('Error sending audio to server:', error);
        });
    }
    
    // Poll audio data from server
    pollAudioFromServer() {
        if (!this.isPlayingAudio) return;
        
        fetch(`/api/audio/download/${this.deviceId}?audio_type=speaker`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success' && data.audio_data) {
                    // Decode base64 audio data
                    const binary = atob(data.audio_data);
                    const bytes = new Uint8Array(binary.length);
                    for (let i = 0; i < binary.length; i++) {
                        bytes[i] = binary.charCodeAt(i);
                    }
                    
                    // Convert to float32 audio data
                    const audioData = new Float32Array(bytes.buffer);
                    
                    // Add to buffer (limit buffer size to prevent memory issues)
                    this.audioBuffer.push(audioData);
                    while (this.audioBuffer.length > 10) {
                        this.audioBuffer.shift();
                    }
                }
            })
            .catch(error => {
                console.error('Error polling audio from server:', error);
            });
    }
}

// Export the AudioHandler class
window.AudioHandler = AudioHandler;
