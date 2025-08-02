"""
Vercel serverless function wrapper for FastAPI app
"""
import sys
import os

# Add parent directory to path to import our app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app

# Export the FastAPI app for Vercel
# Vercel will automatically handle the ASGI to serverless conversion
handler = app