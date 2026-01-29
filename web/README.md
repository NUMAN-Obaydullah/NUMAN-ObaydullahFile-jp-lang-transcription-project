# Web Interface Documentation

## Overview

The web interface provides an interactive, real-time visualization of audio transcription and semantic predictions. Built with vanilla JavaScript (no frameworks required), it communicates with the backend server via WebSocket for low-latency updates.

## Architecture

### Components

1. **main.js** - Core application logic and WebSocket handling
2. **timeline.js** - Timeline visualization and transcript display
3. **export.js** - Export functionality (TXT/JSON)
4. **style.css** - Styling and animations

### Data Flow

```
Server → WebSocket → main.js → Update UI Components
User Action → main.js → WebSocket → Server
```

## Features

### Timeline Visualization

- **Real-time Updates**: New transcript segments appear instantly
- **Timestamps**: Each segment shows `start → end` time
- **Auto-scroll**: Automatically follows new content (can be disabled)
- **Color Coding**: New segments highlighted in green
- **Smooth Animations**: Fade-in effects for new content

### Predictions Panel

- **Keywords**: Displayed as colorful badges/tags
- **Next Terms**: Predicted upcoming words shown as tags
- **Summary**: Running summary of conversation
- **Performance Metrics**: TTFT, generation speed, total time

### Controls

- **Start Recording**: Begin audio capture and transcription
- **Stop Recording**: Pause transcription (resume with Start)
- **Reset**: Clear all data and start fresh
- **Export TXT**: Download transcript as text file
- **Export JSON**: Download transcript as JSON file

### Status Indicators

- **Connection Status**: Shows WebSocket connection state
- **Recording Status**: Shows whether recording is active
- **Audio Time**: Current position in audio stream

## UI States

### Connection States

1. **Connecting**: Initial connection to server
2. **Connected**: WebSocket established and ready
3. **Disconnected**: Connection lost (auto-reconnects)
4. **Error**: Connection error occurred

### Recording States

1. **Not Recording**: Initial state or after stop
2. **Recording**: Actively capturing and transcribing audio

## WebSocket Communication

### Message Types

#### From Server

- `transcript`: New transcript segment
- `prediction`: Updated keywords/summary/next terms
- `status`: Recording/connection status update
- `error`: Error message from server
- `reset`: Confirmation of reset

#### To Server

- `start_recording`: Request to start audio capture
- `stop_recording`: Request to stop audio capture
- `reset`: Request to clear all data
- `export`: Request export data (format: txt/json)

## Customization

### Styling

All styles are in `css/style.css`. Key CSS variables:

```css
:root {
    --primary-color: #4CAF50;      /* Primary accent color */
    --secondary-color: #2196F3;    /* Secondary accent color */
    --bg-dark: #1a1a2e;            /* Dark background */
    --bg-light: #0f3460;           /* Light background */
    /* ... more variables ... */
}
```

### Layout

The interface uses CSS Grid for responsive layout:

```css
.main-content {
    display: grid;
    grid-template-columns: 2fr 1fr;  /* 2:1 ratio left:right */
    gap: 20px;
}
```

### Animations

Key animations defined in CSS:

- `slideIn`: Slide-in effect for new transcripts
- `fadeInScale`: Fade and scale for keywords/terms
- `pulse`: Pulsing effect for status indicators

## Browser Compatibility

### Supported Browsers

- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

### Required Features

- WebSocket API
- ES6+ JavaScript
- CSS Grid
- CSS Custom Properties
- Fetch API (for future enhancements)

## Responsive Design

### Breakpoints

- **Desktop**: > 1200px (default layout)
- **Tablet**: 768px - 1200px (stacked panels)
- **Mobile**: < 768px (single column)

### Mobile Optimizations

- Touch-friendly button sizes
- Simplified layout
- Reduced animations
- Optimized font sizes

## Development

### File Structure

```
web/
├── index.html          # Main HTML structure
├── css/
│   └── style.css       # All styling
├── js/
│   ├── main.js         # Core app logic
│   ├── timeline.js     # Timeline component
│   └── export.js       # Export functionality
└── README.md           # This file
```

### Adding New Features

#### Add New UI Element

1. Add HTML element to `index.html`
2. Style in `css/style.css`
3. Add logic in appropriate JS file
4. Update this documentation

#### Add New WebSocket Message Type

1. Add handler in `main.js` `handleMessage()`
2. Add corresponding UI update function
3. Test with server

### Debugging

Enable console logging:

```javascript
// In browser console
localStorage.debug = 'true';  // Enable debug mode
```

View WebSocket messages:

```javascript
// In main.js, add to handleMessage():
console.log('Message:', message);
```

## Accessibility

### Features

- Semantic HTML structure
- ARIA labels (can be added if needed)
- Keyboard navigation support
- High contrast colors
- Clear visual feedback

### Future Improvements

- Screen reader support
- Keyboard shortcuts
- Focus management
- ARIA live regions for updates

## Performance

### Optimization Techniques

1. **Efficient DOM Updates**: Only update changed elements
2. **CSS Animations**: Hardware-accelerated transforms
3. **Event Throttling**: Prevent excessive updates
4. **Lazy Loading**: Load data on demand
5. **Memory Management**: Clean up old elements

### Performance Targets

- **UI Update Latency**: < 50ms
- **Animation Frame Rate**: 60fps
- **Memory Usage**: < 100MB
- **WebSocket Latency**: < 10ms

## Security

### Implemented

- Same-origin WebSocket connection
- Input sanitization (text content, not HTML)
- No eval() or dynamic code execution
- CORS configuration on server

### Considerations

- Currently localhost-only by default
- No authentication (single-user system)
- No encryption (use HTTPS/WSS for production)

## Testing

### Manual Testing Checklist

- [ ] WebSocket connects successfully
- [ ] Transcript segments appear in timeline
- [ ] Predictions update correctly
- [ ] Export TXT works
- [ ] Export JSON works
- [ ] Reset clears all data
- [ ] Auto-scroll works
- [ ] Status indicators update
- [ ] Reconnection works after disconnect
- [ ] UI is responsive on different screen sizes

### Browser Testing

Test on:
- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Mobile browsers (iOS Safari, Chrome Android)

## Troubleshooting

### WebSocket Won't Connect

**Check**:
- Server is running
- Correct host/port
- Browser console for errors
- Firewall/antivirus settings

### Timeline Not Updating

**Check**:
- WebSocket connected (status indicator)
- Server sending messages (server logs)
- Browser console for errors
- Network tab in dev tools

### Export Not Working

**Check**:
- Transcripts exist (timeline not empty)
- Browser allows downloads
- Check browser console for errors

### Performance Issues

**Check**:
- Number of transcript items (clear old ones)
- Browser dev tools performance tab
- Memory usage
- Network latency

## Future Enhancements

Potential improvements:

- [ ] Dark/light theme toggle
- [ ] Customizable colors
- [ ] Font size adjustment
- [ ] Timeline search/filter
- [ ] Bookmark important segments
- [ ] Playback controls (if audio recorded)
- [ ] Multi-language UI
- [ ] Keyboard shortcuts
- [ ] Print stylesheet
- [ ] Offline support (Service Worker)

## Contributing

When contributing to the web interface:

1. Follow existing code style
2. Test in multiple browsers
3. Update documentation
4. Consider accessibility
5. Optimize performance
6. Add comments for complex logic

## Resources

- [WebSocket API Documentation](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)
- [CSS Grid Guide](https://css-tricks.com/snippets/css/complete-guide-grid/)
- [JavaScript Best Practices](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide)

---

Last updated: 2026-01-29
