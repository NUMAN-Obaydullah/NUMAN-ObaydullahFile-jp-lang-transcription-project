/**
 * Export Module
 * Handles exporting transcripts to TXT and JSON formats
 */

class Exporter {
    constructor() {
        this.transcripts = [];
    }

    /**
     * Update internal transcript data
     */
    updateTranscripts(transcripts) {
        this.transcripts = transcripts;
    }

    /**
     * Export transcripts as TXT file
     */
    exportAsTxt() {
        if (this.transcripts.length === 0) {
            alert('No transcripts to export!');
            return;
        }

        const lines = [];
        const timestamp = this.getTimestamp();
        
        lines.push(`--- Transcript Export ${timestamp} ---\n`);
        
        for (const item of this.transcripts) {
            const timeStr = `${this.formatTime(item.start)} -> ${this.formatTime(item.end)}`;
            lines.push(`[${timeStr}] ${item.text}`);
        }
        
        lines.push(`\n--- End of Transcript (${this.transcripts.length} segments) ---`);
        
        const content = lines.join('\n');
        const filename = `transcript_${this.getFilenameTimestamp()}.txt`;
        
        this.downloadFile(content, filename, 'text/plain');
    }

    /**
     * Export transcripts as JSON file
     */
    exportAsJson() {
        if (this.transcripts.length === 0) {
            alert('No transcripts to export!');
            return;
        }

        const data = {
            exported_at: this.getTimestamp(),
            transcript_count: this.transcripts.length,
            transcripts: this.transcripts
        };
        
        const content = JSON.stringify(data, null, 2);
        const filename = `transcript_${this.getFilenameTimestamp()}.json`;
        
        this.downloadFile(content, filename, 'application/json');
    }

    /**
     * Download file to browser
     */
    downloadFile(content, filename, mimeType) {
        const blob = new Blob([content], { type: mimeType + ';charset=utf-8' });
        const url = URL.createObjectURL(blob);
        
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        
        // Clean up
        setTimeout(() => URL.revokeObjectURL(url), 100);
        
        console.log(`Exported: ${filename}`);
    }

    /**
     * Format time in seconds to HH:MM:SS
     */
    formatTime(seconds) {
        const h = Math.floor(seconds / 3600);
        const m = Math.floor((seconds % 3600) / 60);
        const s = Math.floor(seconds % 60);
        
        if (h > 0) {
            return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        } else {
            return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
        }
    }

    /**
     * Get human-readable timestamp
     */
    getTimestamp() {
        const now = new Date();
        return now.toLocaleString('ja-JP', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });
    }

    /**
     * Get filename-safe timestamp
     */
    getFilenameTimestamp() {
        const now = new Date();
        const year = now.getFullYear();
        const month = String(now.getMonth() + 1).padStart(2, '0');
        const day = String(now.getDate()).padStart(2, '0');
        const hour = String(now.getHours()).padStart(2, '0');
        const minute = String(now.getMinutes()).padStart(2, '0');
        const second = String(now.getSeconds()).padStart(2, '0');
        
        return `${year}${month}${day}_${hour}${minute}${second}`;
    }
}

// Export for use in main.js
window.Exporter = Exporter;
