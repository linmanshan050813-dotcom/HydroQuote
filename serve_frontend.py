"""
Simple HTTP server to serve the frontend demo
Run this alongside the FastAPI backend
"""
import http.server
import socketserver
import os
import sys
import codecs
import webbrowser
from pathlib import Path
from urllib.parse import urlparse, unquote


class ThreadingHTTPServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    """Handle each request in a separate thread to avoid head-of-line blocking."""
    daemon_threads = True
    allow_reuse_address = True

# Fix encoding for Windows
if sys.platform == 'win32':
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')

PORT = 3000
DIRECTORY = "frontend"
MAX_PORT_ATTEMPTS = 10

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def translate_path(self, path):
        """
        Serve frontend assets from frontend/, and map /hydroturbine_image/*
        to the project-root hydroturbine_image/ directory.
        """
        parsed = urlparse(path).path
        clean_path = unquote(parsed).lstrip("/")
        if clean_path.startswith("hydroturbine_image/"):
            rel = clean_path[len("hydroturbine_image/"):]
            return str((Path.cwd() / "hydroturbine_image" / rel).resolve())
        return super().translate_path(path)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Check if frontend directory exists
    if not Path(DIRECTORY).exists():
        print(f"Error: {DIRECTORY} directory not found!")
        return
    
    # Check if index.html exists
    if not Path(DIRECTORY, "index.html").exists():
        print(f"Error: {DIRECTORY}/index.html not found!")
        return
    
    print("=" * 60)
    print("🌊 HydroQuote AI - Frontend Demo Server")
    print("=" * 60)
    print(f"\n📁 Serving files from: {DIRECTORY}/")
    print(f"🌐 Frontend URL: http://localhost:{PORT}")
    print(f"🔌 Backend API: http://localhost:8000")
    print("\n⚠️  Make sure the FastAPI backend is running on port 8000!")
    print("\nPress Ctrl+C to stop the server\n")
    print("=" * 60)
    
    # Try to create server, handle port conflicts
    port = PORT
    httpd = None
    
    for attempt in range(MAX_PORT_ATTEMPTS):
        try:
            httpd = ThreadingHTTPServer(("", port), MyHTTPRequestHandler)
            break
        except OSError as e:
            if attempt < MAX_PORT_ATTEMPTS - 1:
                print(f"\n⚠️  Port {port} is in use, trying {port + 1}...")
                port += 1
            else:
                print(f"\n❌ Error: Could not find available port after {MAX_PORT_ATTEMPTS} attempts")
                print(f"   Ports {PORT}-{port} are all in use")
                print(f"\n   Try closing other applications or use a different port")
                return
    
    if httpd:
        print(f"\n✓ Server started on port {port}")
        
        # Open browser
        try:
            webbrowser.open(f"http://localhost:{port}")
            print(f"✓ Browser opened automatically")
        except:
            print(f"⚠️  Could not open browser automatically")
            print(f"   Please open: http://localhost:{port}")
        
        print(f"\n🚀 Server is running on http://localhost:{port}")
        print(f"   Press Ctrl+C to stop\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    main()

# Made with Bob
