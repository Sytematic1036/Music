"""Simple standalone server for v3 - no external imports."""
import http.server
import socketserver
import json
import base64
import webbrowser
import sys
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Read MIDI data once at startup - use 01_melody.mid (02_arrangement.mid has parsing errors)
MIDI_PATH = Path('C:/Users/haege/Kod/Music/output_new/01_melody.mid')
with open(MIDI_PATH, 'rb') as f:
    MIDI_DATA = f.read()
MIDI_B64 = base64.b64encode(MIDI_DATA).decode('ascii')
print(f'Loaded MIDI: {len(MIDI_DATA)} bytes -> {len(MIDI_B64)} base64 chars')

# Minimal HTML for testing
HTML = """<!DOCTYPE html>
<html>
<head>
    <title>Test v3</title>
    <script src="https://unpkg.com/@tonejs/midi@2.0.28/build/Midi.js"></script>
</head>
<body style="background:#1a1a2e;color:white;font-family:sans-serif;padding:40px;">
    <h1>Rearrange v3 Test</h1>
    <button onclick="testMidi()">Test API MIDI</button>
    <input type="file" id="fileInput" accept=".mid,.midi" onchange="testFileMidi(event)">
    <pre id="output">Click button or select MIDI file to test...</pre>
    <script>
    async function testMidi() {
        const out = document.getElementById('output');
        try {
            out.textContent = 'Checking Midi class...\\n';
            out.textContent += 'typeof Midi: ' + typeof Midi + '\\n';
            out.textContent += 'typeof Tone: ' + typeof Tone + '\\n';
            out.textContent += 'typeof window.Midi: ' + typeof window.Midi + '\\n';

            // Try to find the Midi constructor
            let MidiClass = window.Midi || (typeof Tone !== 'undefined' && Tone.Midi);
            out.textContent += 'MidiClass found: ' + (MidiClass ? 'yes' : 'no') + '\\n\\n';

            out.textContent += 'Fetching MIDI data...\\n';
            const resp = await fetch('/api/find-midi?filename=test.mp3');
            out.textContent += 'Status: ' + resp.status + '\\n';
            const data = await resp.json();
            out.textContent += 'Found: ' + data.found + '\\n';
            out.textContent += 'Path: ' + data.midi_path + '\\n';
            out.textContent += 'Data length: ' + (data.midi_data ? data.midi_data.length : 0) + '\\n';

            if (data.midi_data) {
                // Decode base64 to binary string
                const binaryString = atob(data.midi_data);
                out.textContent += 'Binary string length: ' + binaryString.length + '\\n';

                // Create a proper ArrayBuffer (not using Uint8Array.from which can have issues)
                const buffer = new ArrayBuffer(binaryString.length);
                const view = new Uint8Array(buffer);
                for (let i = 0; i < binaryString.length; i++) {
                    view[i] = binaryString.charCodeAt(i);
                }

                out.textContent += 'Buffer size: ' + buffer.byteLength + '\\n';
                out.textContent += 'First 4 bytes: ' + view[0] + ',' + view[1] + ',' + view[2] + ',' + view[3] + '\\n';
                out.textContent += 'As text: ' + String.fromCharCode(view[0], view[1], view[2], view[3]) + '\\n';

                if (!MidiClass) {
                    throw new Error('Midi class not found! Check script loading.');
                }

                out.textContent += 'Creating Midi object...\\n';
                try {
                    const midi = new MidiClass(buffer);
                    out.textContent += 'Tracks: ' + midi.tracks.length + '\\n';
                    out.textContent += 'Duration: ' + midi.duration.toFixed(2) + 's\\n';
                    out.textContent += '\\nSUCCESS!';
                } catch (parseErr) {
                    out.textContent += 'Parse error: ' + parseErr + '\\n';
                    out.textContent += 'Error type: ' + (parseErr ? parseErr.constructor.name : 'null') + '\\n';
                    out.textContent += 'Message: ' + (parseErr ? parseErr.message : 'none') + '\\n';
                    console.error('MIDI parse error:', parseErr);
                }
            }
        } catch (e) {
            out.textContent += '\\nERROR: ' + e + '\\n';
            out.textContent += 'Type: ' + (e ? e.constructor.name : 'null') + '\\n';
            console.error('Full error:', e);
        }
    }

    async function testFileMidi(event) {
        const out = document.getElementById('output');
        const file = event.target.files[0];
        if (!file) return;

        out.textContent = 'Loading file: ' + file.name + '\\n';

        try {
            const buffer = await file.arrayBuffer();
            out.textContent += 'File size: ' + buffer.byteLength + ' bytes\\n';

            const view = new Uint8Array(buffer);
            out.textContent += 'First 4 bytes: ' + view[0] + ',' + view[1] + ',' + view[2] + ',' + view[3] + '\\n';
            out.textContent += 'As text: ' + String.fromCharCode(view[0], view[1], view[2], view[3]) + '\\n';

            out.textContent += 'Creating Midi from file...\\n';
            const midi = new Midi(buffer);
            out.textContent += 'Tracks: ' + midi.tracks.length + '\\n';
            out.textContent += 'Duration: ' + midi.duration.toFixed(2) + 's\\n';
            out.textContent += '\\nFILE LOAD SUCCESS!';
        } catch (e) {
            out.textContent += '\\nFILE ERROR: ' + e + '\\n';
            console.error('File error:', e);
        }
    }
    </script>
</body>
</html>
"""

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f'[{self.command}] {format % args}', flush=True)

    def do_GET(self):
        parsed = urlparse(self.path)
        print(f'Handling: {parsed.path}', flush=True)

        if parsed.path == '/' or parsed.path == '/index.html':
            self._send(HTML.encode(), 'text/html')
        elif parsed.path == '/api/find-midi':
            result = {
                'found': True,
                'midi_path': MIDI_PATH.name,
                'midi_data': MIDI_B64
            }
            self._send(json.dumps(result).encode(), 'application/json')
        else:
            self.send_error(404)

    def _send(self, data, content_type):
        self.send_response(200)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Connection', 'close')
        self.end_headers()
        self.wfile.write(data)
        print(f'Sent {len(data)} bytes', flush=True)

if __name__ == '__main__':
    PORT = 8765
    print(f'Starting on http://localhost:{PORT}', flush=True)

    # Use ThreadingTCPServer instead of regular TCPServer
    class ThreadingServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
        allow_reuse_address = True

    with ThreadingServer(('', PORT), Handler) as httpd:
        print('Server ready!', flush=True)
        webbrowser.open(f'http://localhost:{PORT}')
        httpd.serve_forever()
