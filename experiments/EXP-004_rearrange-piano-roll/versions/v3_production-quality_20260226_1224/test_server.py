"""Working v3 server - minimal but functional."""
import http.server
import socketserver
import json
import base64
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Import HTML from main file
from player_rearrange_v3 import BROWSER_PLAYER_V3_HTML

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # Show logs
        print(f'{self.address_string()} - {format % args}')

    def do_GET(self):
        parsed = urlparse(self.path)

        if parsed.path == '/' or parsed.path == '/player.html':
            response = BROWSER_PLAYER_V3_HTML.encode()
            self.send_response(200)
            self.send_header('Content-Type', 'text/html')
            self.send_header('Content-Length', len(response))
            self.end_headers()
            self.wfile.write(response)

        elif parsed.path == '/api/find-midi':
            params = parse_qs(parsed.query)
            filename = params.get('filename', ['test.mp3'])[0]
            print(f'[find-midi] Looking for: {filename}')

            midi_path = Path('C:/Users/haege/Kod/Music/output_new/02_arrangement.mid')
            if not midi_path.exists():
                midi_path = Path('C:/Users/haege/Kod/Music/output_new/01_melody.mid')

            if midi_path.exists():
                print(f'[find-midi] Found: {midi_path}')
                with open(midi_path, 'rb') as f:
                    data = f.read()
                result = {
                    'found': True,
                    'midi_path': midi_path.name,
                    'midi_data': base64.b64encode(data).decode()
                }
            else:
                print('[find-midi] Not found')
                result = {'found': False, 'midi_path': None}

            response = json.dumps(result).encode()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response))
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(response)

        else:
            self.send_error(404)

if __name__ == '__main__':
    PORT = 8765
    print(f'Starting v3 server on http://localhost:{PORT}')
    webbrowser.open(f'http://localhost:{PORT}')
    with socketserver.TCPServer(('', PORT), Handler) as httpd:
        print('Server ready!')
        httpd.serve_forever()
