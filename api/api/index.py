"""
Vercel serverless function wrapper for FastAPI app
"""
import sys
import os

# Add parent directory to path to import our app
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

# Also ensure we can import from the current directory
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import the FastAPI app
try:
    from app import app
    # Export the app instance directly
    # Vercel expects this exact variable name
    app = app
except ImportError as e:
    # If import fails, create a simple error response app
    from fastapi import FastAPI, HTTPException
    app = FastAPI()
    
    @app.get("/api/health")
    async def health():
        return {"status": "error", "message": f"Failed to import main app: {str(e)}"}
    
    @app.post("/api/chat")
    async def chat():
        raise HTTPException(status_code=500, detail=f"App import failed: {str(e)}")