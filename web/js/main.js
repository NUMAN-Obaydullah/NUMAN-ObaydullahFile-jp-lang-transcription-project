/**
 * Main Application Module
 * Handles WebSocket communication and UI updates
 */

class TranscriptionApp {
    constructor() {
        this.ws = null;
        this.reconnectDelay = 1000;
        this.maxReconnectDelay = 30000;
        this.isConnecting = false;
        this.shouldReconnect = true;

        // Initialize modules
        this.timeline = new Timeline(
            document.getElementById('timeline-container'),
            document.getElementById('timeline-content')
        );
        this.exporter = new Exporter();

        // UI elements
        this.elements = {
            connectionStatus: document.getElementById('connection-status'),
            connectionText: document.getElementById('connection-text'),
            recordingStatus: document.getElementById('recording-status'),
            recordingText: document.getElementById('recording-text'),
            audioTime: document.getElementById('audio-time'),
            keywordsContainer: document.getElementById('keywords-container'),
            nextTermsContainer: document.getElementById('next-terms-container'),
            summaryContainer: document.getElementById('summary-container'),
            metricTtft: document.getElementById('metric-ttft'),
            metricSpeed: document.getElementById('metric-speed'),
            metricTotal: document.getElementById('metric-total'),
            startBtn: document.getElementById('start-btn'),
            stopBtn: document.getElementById('stop-btn'),
            resetBtn: document.getElementById('reset-btn'),
            exportTxtBtn: document.getElementById('export-txt-btn'),
            exportJsonBtn: document.getElementById('export-json-btn'),
            autoScrollCheckbox: document.getElementById('auto-scroll')
        };

        this.setupEventListeners();
        this.connect();
    }

    /**
     * Setup UI event listeners
     */
    setupEventListeners() {
        // Control buttons
        this.elements.startBtn.addEventListener('click', () => this.startRecording());
        this.elements.stopBtn.addEventListener('click', () => this.stopRecording());
        this.elements.resetBtn.addEventListener('click', () => this.reset());
        this.elements.exportTxtBtn.addEventListener('click', () => this.exportTxt());
        this.elements.exportJsonBtn.addEventListener('click', () => this.exportJson());

        // Auto-scroll checkbox
        this.elements.autoScrollCheckbox.addEventListener('change', (e) => {
            this.timeline.setAutoScroll(e.target.checked);
        });
    }

    /**
     * Connect to WebSocket server
     */
    connect() {
        if (this.isConnecting || (this.ws && this.ws.readyState === WebSocket.OPEN)) {
            return;
        }

        this.isConnecting = true;
        this.updateConnectionStatus('connecting');

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws`;

        console.log('Connecting to WebSocket:', wsUrl);

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('WebSocket connected');
                this.isConnecting = false;
                this.reconnectDelay = 1000;
                this.updateConnectionStatus('connected');
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleMessage(message);
                } catch (error) {
                    console.error('Error parsing message:', error);
                }
            };

            this.ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                this.isConnecting = false;
            };

            this.ws.onclose = () => {
                console.log('WebSocket disconnected');
                this.isConnecting = false;
                this.updateConnectionStatus('disconnected');

                // Attempt reconnection
                if (this.shouldReconnect) {
                    console.log(`Reconnecting in ${this.reconnectDelay}ms...`);
                    setTimeout(() => this.connect(), this.reconnectDelay);
                    this.reconnectDelay = Math.min(this.reconnectDelay * 2, this.maxReconnectDelay);
                }
            };
        } catch (error) {
            console.error('Error creating WebSocket:', error);
            this.isConnecting = false;
            this.updateConnectionStatus('error');
        }
    }

    /**
     * Handle incoming WebSocket message
     */
    handleMessage(message) {
        console.log('Received message:', message.type);

        switch (message.type) {
            case 'transcript':
                this.handleTranscript(message.data);
                break;
            case 'prediction':
                this.handlePrediction(message.data);
                break;
            case 'status':
                this.handleStatus(message.data);
                break;
            case 'error':
                this.handleError(message.data);
                break;
            case 'reset':
                this.handleResetConfirmation();
                break;
            case 'export_data':
                this.handleExportData(message.data);
                break;
            default:
                console.warn('Unknown message type:', message.type);
        }
    }

    /**
     * Handle transcript message
     */
    handleTranscript(data) {
        this.timeline.addTranscript(data);
        this.exporter.updateTranscripts(this.timeline.getTranscripts());
    }

    /**
     * Handle prediction message
     */
    handlePrediction(data) {
        // Update keywords
        this.updateKeywords(data.keywords || []);

        // Update next terms
        this.updateNextTerms(data.next_terms || []);

        // Update summary
        this.updateSummary(data.summary || '');

        // Update metrics
        if (data.metrics) {
            this.updateMetrics(data.metrics);
        }
    }

    /**
     * Update keywords display
     */
    updateKeywords(keywords) {
        if (keywords.length === 0) {
            this.elements.keywordsContainer.innerHTML = '<div class="empty-state-small">No keywords yet...</div>';
            return;
        }

        this.elements.keywordsContainer.innerHTML = '';
        keywords.forEach(keyword => {
            const tag = document.createElement('span');
            tag.className = 'keyword-tag';
            tag.textContent = keyword;
            this.elements.keywordsContainer.appendChild(tag);
        });
    }

    /**
     * Update next terms display
     */
    updateNextTerms(terms) {
        if (terms.length === 0) {
            this.elements.nextTermsContainer.innerHTML = '<div class="empty-state-small">No predictions yet...</div>';
            return;
        }

        this.elements.nextTermsContainer.innerHTML = '';
        terms.forEach(term => {
            const tag = document.createElement('span');
            tag.className = 'next-term-tag';
            tag.textContent = term;
            this.elements.nextTermsContainer.appendChild(tag);
        });
    }

    /**
     * Update summary display
     */
    updateSummary(summary) {
        if (!summary) {
            this.elements.summaryContainer.innerHTML = '<div class="empty-state-small">No summary yet...</div>';
            return;
        }

        this.elements.summaryContainer.textContent = summary;
    }

    /**
     * Update performance metrics
     */
    updateMetrics(metrics) {
        if (metrics.ttft_ms !== null && metrics.ttft_ms !== undefined) {
            this.elements.metricTtft.textContent = `${Math.round(metrics.ttft_ms)}ms`;
        }

        if (metrics.chars_per_sec !== null && metrics.chars_per_sec !== undefined) {
            this.elements.metricSpeed.textContent = `${Math.round(metrics.chars_per_sec)} c/s`;
        }

        if (metrics.total_s !== null && metrics.total_s !== undefined) {
            this.elements.metricTotal.textContent = `${metrics.total_s.toFixed(2)}s`;
        }
    }

    /**
     * Handle status message
     */
    handleStatus(data) {
        if (data.recording !== undefined) {
            this.updateRecordingStatus(data.recording);
        }

        if (data.audio_time !== undefined) {
            this.updateAudioTime(data.audio_time);
        }
    }

    /**
     * Handle error message
     */
    handleError(data) {
        console.error('Server error:', data);
        alert(`Error: ${data.message}`);
    }

    /**
     * Handle reset confirmation
     */
    handleResetConfirmation() {
        this.timeline.clear();
        this.exporter.updateTranscripts([]);
        this.updateKeywords([]);
        this.updateNextTerms([]);
        this.updateSummary('');
        this.updateMetrics({});
        this.updateAudioTime(0);
    }

    /**
     * Handle export data from server
     */
    handleExportData(data) {
        // This is used if server needs to send export data
        // Currently we handle exports client-side
        console.log('Export data received:', data);
    }

    /**
     * Update connection status indicator
     */
    updateConnectionStatus(status) {
        this.elements.connectionStatus.className = 'status-dot';
        
        switch (status) {
            case 'connected':
                this.elements.connectionStatus.classList.add('connected');
                this.elements.connectionText.textContent = 'Connected';
                break;
            case 'connecting':
                this.elements.connectionText.textContent = 'Connecting...';
                break;
            case 'disconnected':
                this.elements.connectionText.textContent = 'Disconnected';
                break;
            case 'error':
                this.elements.connectionText.textContent = 'Connection Error';
                break;
        }
    }

    /**
     * Update recording status indicator
     */
    updateRecordingStatus(isRecording) {
        if (isRecording) {
            this.elements.recordingStatus.classList.add('recording');
            this.elements.recordingText.textContent = 'Recording';
            this.elements.startBtn.disabled = true;
            this.elements.stopBtn.disabled = false;
        } else {
            this.elements.recordingStatus.classList.remove('recording');
            this.elements.recordingText.textContent = 'Not Recording';
            this.elements.startBtn.disabled = false;
            this.elements.stopBtn.disabled = true;
        }
    }

    /**
     * Update audio time display
     */
    updateAudioTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        this.elements.audioTime.textContent = 
            `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Send WebSocket message
     */
    sendMessage(message) {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify(message));
        } else {
            console.error('WebSocket not connected');
            alert('Not connected to server. Please refresh the page.');
        }
    }

    /**
     * Start recording
     */
    startRecording() {
        console.log('Starting recording...');
        this.sendMessage({ type: 'start_recording' });
    }

    /**
     * Stop recording
     */
    stopRecording() {
        console.log('Stopping recording...');
        this.sendMessage({ type: 'stop_recording' });
    }

    /**
     * Reset all state
     */
    reset() {
        if (confirm('Are you sure you want to reset? This will clear all transcripts.')) {
            console.log('Resetting...');
            this.sendMessage({ type: 'reset' });
        }
    }

    /**
     * Export transcripts as TXT
     */
    exportTxt() {
        this.exporter.exportAsTxt();
    }

    /**
     * Export transcripts as JSON
     */
    exportJson() {
        this.exporter.exportAsJson();
    }

    /**
     * Disconnect and cleanup
     */
    disconnect() {
        this.shouldReconnect = false;
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing Transcription App...');
    window.app = new TranscriptionApp();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
    if (window.app) {
        window.app.disconnect();
    }
});
