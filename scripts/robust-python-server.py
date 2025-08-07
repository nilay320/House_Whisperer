#!/usr/bin/env python3
"""Robust local test server for the Python chat API with proper streaming."""

import os
import sys
import json
import traceback
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))

# Import our chat functions
from chat import get_embedding, retrieve, generate_stream

class RobustChatHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        """Custom logging."""
        print(f"🌐 {self.address_string()} - {format % args}")

    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        print("🔧 Handling OPTIONS request")
        self.send_response(200)
        self._set_cors_headers()
        self.end_headers()

    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/health':
            self._handle_health()
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        """Handle POST requests."""
        parsed_url = urlparse(self.path)
        
        if parsed_url.path == '/api/chat':
            self._handle_chat()
        else:
            self.send_response(404)
            self._set_cors_headers()
            self.end_headers()

    def _handle_health(self):
        """Health check endpoint."""
        print("❤️  Health check request")
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self._set_cors_headers()
        self.end_headers()
        
        response = {"status": "healthy", "message": "Robust Python API is running"}
        self.wfile.write(json.dumps(response).encode())

    def _handle_chat(self):
        """Handle chat requests with robust error handling."""
        try:
            print("💬 Chat request received")
            
            # Parse request body
            content_length = int(self.headers.get('Content-Length', 0))
            if content_length == 0:
                print("❌ No request body")
                self._send_error(400, "No request body")
                return
                
            post_data = self.rfile.read(content_length)
            request_data = json.loads(post_data.decode('utf-8'))
            
            message = request_data.get('message')
            if not message:
                print("❌ No message in request")
                self._send_error(400, "Message is required")
                return
            
            print(f"📨 Query: {message}")
            
            # Retrieve relevant context
            print("🔍 Retrieving context...")
            context = retrieve(message)
            print(f"📋 Found {len(context)} relevant chunks")
            
            # Send response headers
            self.send_response(200)
            self.send_header('Content-Type', 'text/event-stream')
            self.send_header('Cache-Control', 'no-cache')
            self.send_header('Connection', 'keep-alive')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
            self.send_header('Access-Control-Allow-Headers', 'Content-Type')
            self.end_headers()
            
            print("📡 Starting stream...")
            
            # Stream the response with error handling
            chunk_count = 0
            try:
                for chunk in generate_stream(message, context):
                    try:
                        self.wfile.write(chunk.encode())
                        self.wfile.flush()
                        chunk_count += 1
                        
                        # Add small delay to prevent overwhelming
                        if chunk_count % 10 == 0:
                            import time
                            time.sleep(0.01)
                            
                    except BrokenPipeError:
                        print(f"🔌 Client disconnected after {chunk_count} chunks")
                        break
                    except Exception as e:
                        print(f"❌ Error writing chunk {chunk_count}: {e}")
                        break
                        
            except Exception as e:
                print(f"❌ Error generating stream: {e}")
                traceback.print_exc()
                
            print(f"✅ Stream completed: {chunk_count} chunks sent")
                
        except json.JSONDecodeError as e:
            print(f"❌ JSON decode error: {e}")
            self._send_error(400, f"Invalid JSON: {str(e)}")
        except Exception as e:
            print(f"❌ Chat error: {e}")
            traceback.print_exc()
            self._send_error(500, f"Server error: {str(e)}")

    def _send_error(self, status_code, message):
        """Send error response."""
        try:
            self.send_response(status_code)
            self.send_header('Content-Type', 'application/json')
            self._set_cors_headers()
            self.end_headers()
            
            error_response = {"error": message}
            self.wfile.write(json.dumps(error_response).encode())
        except:
            # If we can't send error, just log it
            print(f"❌ Failed to send error response: {message}")

    def _set_cors_headers(self):
        """Set CORS headers."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')

def run_server(port=8000):
    """Run the robust server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, RobustChatHandler)
    
    print(f"🐍 Robust Python Chat API Server starting on port {port}")
    print(f"🏠 Local URL: http://localhost:{port}")
    print(f"🔗 Chat endpoint: http://localhost:{port}/api/chat")
    print(f"❤️  Health check: http://localhost:{port}/health")
    print("\n🎯 Ready for streaming chat requests!")
    print("Press Ctrl+C to stop the server\n")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Server stopped")
        httpd.server_close()

if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    run_server(port)