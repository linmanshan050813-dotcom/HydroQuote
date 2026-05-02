"""
Simple HTTP server to serve the frontend demo
Run this alongside the FastAPI backend
"""
import http.server
import socketserver
import os
import webbrowser
from pathlib import Path

PORT = 3000
DIRECTORY = "frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
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
    
    # Create server
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        # Open browser
        try:
            webbrowser.open(f"http://localhost:{PORT}")
            print(f"\n✓ Browser opened automatically")
        except:
            print(f"\n⚠️  Could not open browser automatically")
            print(f"   Please open: http://localhost:{PORT}")
        
        print(f"\n🚀 Server is running...")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down server...")
            httpd.shutdown()

if __name__ == "__main__":
    main()

# Made with Bob
