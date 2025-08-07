#!/usr/bin/env python3
"""Quick script to restore data to Qdrant using the working approach."""

import os
import sys
from dotenv import load_dotenv

# Add the api directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env.local'))

def restore_data():
    """Run the working ingestion scripts to restore data."""
    print("🔄 Restoring data with working ingestion scripts...")
    
    # Use the old working scripts
    import subprocess
    
    try:
        # Run InterNACHI
        print("📄 Ingesting InterNACHI...")
        result = subprocess.run([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), 'ingest-by-document.js')
        ], capture_output=True, text=True, cwd=os.path.dirname(__file__))
        
        if result.returncode == 0:
            print("✅ InterNACHI ingested successfully")
        else:
            print(f"❌ InterNACHI failed: {result.stderr}")
            
    except Exception as e:
        print(f"❌ Error running ingestion: {e}")

if __name__ == "__main__":
    restore_data()