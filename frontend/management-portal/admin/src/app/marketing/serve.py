#!/usr/bin/env python3
"""
Simple HTTP server to serve the DotMac Platform website locally.
"""

import http.server
import os
import socketserver
import sys
import webbrowser
from pathlib import Path


class CustomHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    """Custom HTTP request handler with better MIME types and error handling."""

    def end_headers(self):
        # Enable CORS for local development
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def guess_type(self, path):
        """Improve MIME type guessing."""
        mimetype, encoding = super().guess_type(path)

        # Fix common MIME types
        if path.endswith(".js"):
            return "application/javascript", encoding
        elif path.endswith(".css"):
            return "text/css", encoding
        elif path.endswith(".json"):
            return "application/json", encoding
        elif path.endswith(".md"):
            return "text/markdown", encoding

        return mimetype, encoding


def main():
    # Change to website directory
    website_dir = Path(__file__).parent
    os.chdir(website_dir)

    # Configuration
    PORT = int(os.getenv("PORT", 8080))
    HOST = os.getenv("HOST", "localhost")

    print(
        f"""
🌐 DotMac Platform Website Server
==================================

Starting server at: http://{HOST}:{PORT}
Serving from: {website_dir}

Available pages:
• Main site: http://{HOST}:{PORT}/
• DNS Guide: http://{HOST}:{PORT}/docs/strategic-dns-deployment.html
• API Docs: http://{HOST}:{PORT}/docs/api-reference.html

Press Ctrl+C to stop the server
"""
    )

    try:
        with socketserver.TCPServer((HOST, PORT), CustomHTTPRequestHandler) as httpd:
            print("✅ Server started successfully!")

            # Open browser automatically
            try:
                webbrowser.open(f"http://{HOST}:{PORT}")
                print(f"🔗 Opened browser to http://{HOST}:{PORT}")
            except:
                print("❌ Could not open browser automatically")

            print(f"\n📡 Serving HTTP on {HOST} port {PORT} ...")
            httpd.serve_forever()

    except KeyboardInterrupt:
        print("\n\n👋 Server stopped by user")
        sys.exit(0)
    except OSError as e:
        if e.errno == 48:  # Address already in use
            print(f"❌ Port {PORT} is already in use!")
            print("💡 Try a different port: PORT=8081 python3 serve.py")
        else:
            print(f"❌ Error starting server: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
