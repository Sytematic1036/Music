"""
Simple music player launcher.
Run: python start_player.py
"""
import http.server
import socketserver
import webbrowser
import threading
from pathlib import Path

PORT = 8765
PLAYER_DIR = Path(__file__).parent / "output"

# Create player.html in output folder
PLAYER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Music Player</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(135deg, #1a1a2e, #16213e);
            color: #fff;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            margin: 0;
        }
        .player {
            background: rgba(255,255,255,0.1);
            border-radius: 20px;
            padding: 40px;
            text-align: center;
            max-width: 600px;
        }
        h1 { color: #e94560; }
        .files { margin: 20px 0; text-align: left; }
        .file-btn {
            display: block;
            background: #e94560;
            color: white;
            border: none;
            padding: 15px 20px;
            margin: 10px 0;
            border-radius: 10px;
            cursor: pointer;
            width: 100%;
            font-size: 1rem;
        }
        .file-btn:hover { background: #ff6b6b; }
        audio { width: 100%; margin-top: 20px; }
        #drop-zone {
            border: 2px dashed #555;
            padding: 30px;
            margin: 20px 0;
            border-radius: 10px;
        }
        #drop-zone.drag-over {
            border-color: #e94560;
            background: rgba(233,69,96,0.1);
        }
    </style>
</head>
<body>
    <div class="player">
        <h1>Music Pipeline Player</h1>

        <div class="files">
            <h3>Output Files:</h3>
            <button class="file-btn" onclick="playFile('03_production/production.mp3')">
                Production (MP3)
            </button>
            <button class="file-btn" onclick="playFile('03_production/production.wav')">
                Production (WAV)
            </button>
        </div>

        <div id="drop-zone">
            Drop audio file here
        </div>

        <button class="file-btn" style="background: #4a90d9;" onclick="document.getElementById('file-input').click()">
            📁 Bläddra och välj fil...
        </button>
        <input type="file" id="file-input" accept=".mp3,.wav,.mid,.midi,.ogg,.flac" style="display:none">

        <audio id="audio" controls></audio>

        <p id="status" style="color: #888; margin-top: 20px;"></p>
    </div>

    <script>
        const audio = document.getElementById('audio');
        const status = document.getElementById('status');
        const dropZone = document.getElementById('drop-zone');

        function playFile(path) {
            audio.src = path;
            audio.play();
            status.textContent = 'Playing: ' + path;
        }

        // File picker
        document.getElementById('file-input').addEventListener('change', e => {
            const file = e.target.files[0];
            if (file) {
                audio.src = URL.createObjectURL(file);
                audio.play();
                status.textContent = 'Playing: ' + file.name;
            }
        });

        // Drag and drop
        dropZone.addEventListener('dragover', e => {
            e.preventDefault();
            dropZone.classList.add('drag-over');
        });
        dropZone.addEventListener('dragleave', () => {
            dropZone.classList.remove('drag-over');
        });
        dropZone.addEventListener('drop', e => {
            e.preventDefault();
            dropZone.classList.remove('drag-over');
            const file = e.dataTransfer.files[0];
            if (file) {
                audio.src = URL.createObjectURL(file);
                audio.play();
                status.textContent = 'Playing: ' + file.name;
            }
        });
    </script>
</body>
</html>
"""

def main():
    # Write player HTML
    player_path = PLAYER_DIR / "player.html"
    PLAYER_DIR.mkdir(parents=True, exist_ok=True)
    with open(player_path, "w", encoding="utf-8") as f:
        f.write(PLAYER_HTML)

    print(f"Starting server on http://localhost:{PORT}")
    print(f"Serving from: {PLAYER_DIR}")
    print("Press Ctrl+C to stop\n")

    # Start server
    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, directory=str(PLAYER_DIR), **kwargs)
        def log_message(self, format, *args):
            print(f"  {args[0]}")

    # Open browser after short delay
    def open_browser():
        import time
        time.sleep(0.5)
        webbrowser.open(f"http://localhost:{PORT}/player.html")

    threading.Thread(target=open_browser, daemon=True).start()

    with socketserver.TCPServer(("", PORT), Handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\nServer stopped.")

if __name__ == "__main__":
    main()
