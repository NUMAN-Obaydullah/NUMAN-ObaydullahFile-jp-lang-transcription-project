/**
 * Timeline Visualization Module
 * Handles rendering and display of transcript timeline
 */

class Timeline {
    constructor(containerElement, contentElement) {
        this.container = containerElement;
        this.content = contentElement;
        this.autoScroll = true;
        this.transcripts = [];
    }

    /**
     * Add new transcript segment to timeline
     */
    addTranscript(data) {
        // Store transcript
        this.transcripts.push(data);

        // Remove empty state if present
        const emptyState = this.content.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        // Create transcript item
        const item = document.createElement('div');
        item.className = 'transcript-item new';
        
        const timestamp = document.createElement('div');
        timestamp.className = 'transcript-timestamp';
        timestamp.textContent = `${this.formatTime(data.start)} → ${this.formatTime(data.end)}`;
        
        const text = document.createElement('div');
        text.className = 'transcript-text';
        text.textContent = data.text;
        
        item.appendChild(timestamp);
        item.appendChild(text);
        
        // Add to timeline
        this.content.appendChild(item);

        // Remove 'new' class after animation
        setTimeout(() => {
            item.classList.remove('new');
        }, 2000);

        // Auto-scroll if enabled
        if (this.autoScroll) {
            this.scrollToBottom();
        }
    }

    /**
     * Format time in seconds to MM:SS format
     */
    formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = Math.floor(seconds % 60);
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    }

    /**
     * Scroll timeline to bottom
     */
    scrollToBottom() {
        this.container.scrollTop = this.container.scrollHeight;
    }

    /**
     * Set auto-scroll state
     */
    setAutoScroll(enabled) {
        this.autoScroll = enabled;
    }

    /**
     * Clear all transcripts
     */
    clear() {
        this.transcripts = [];
        this.content.innerHTML = `
            <div class="empty-state">
                <p>👆 Click "Start Recording" to begin transcription</p>
            </div>
        `;
    }

    /**
     * Get all transcripts
     */
    getTranscripts() {
        return this.transcripts;
    }

    /**
     * Get transcript count
     */
    getCount() {
        return this.transcripts.length;
    }
}

// Export for use in main.js
window.Timeline = Timeline;
